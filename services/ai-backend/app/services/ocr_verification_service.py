"""
FLIO OCR Verification Service
Document verification using Azure AI Vision

Supports Korean documents:
- 신분증 (ID cards): 주민등록증, 운전면허증, 여권
- 졸업증명서 (Diploma/Certificate)
- 소득금액증명원 (Income Certificate)
- 재직증명서 (Employment Certificate)
"""

import logging
import os
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
from pydantic import BaseModel
from enum import Enum
import httpx

from ..models.database import get_supabase_client
from .document_authenticity_service import document_authenticity_service

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Supported document types for verification"""
    ID_CARD = "id_card"
    DIPLOMA = "diploma"
    INCOME_CERT = "income_cert"
    EMPLOYMENT_CERT = "employment_cert"


class VerificationStatus(str, Enum):
    """Document verification status"""
    PENDING = "pending"
    PROCESSING = "processing"
    VERIFIED = "verified"
    FLAGGED = "flagged"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OCRResult(BaseModel):
    """OCR extraction result"""
    raw_text: str
    extracted_data: Dict[str, Any]
    confidence: float
    document_type_detected: str


class VerificationResult(BaseModel):
    """Document verification result"""
    document_id: str
    document_type: str
    match_score: float
    verification_status: str
    extracted_data: Dict[str, Any]
    comparison_details: Dict[str, Any]
    flags: List[str]
    authenticity_score: Optional[float] = None
    issuer_validated: Optional[bool] = None
    format_validated: Optional[bool] = None
    pattern_validated: Optional[bool] = None
    authenticity_flags: Optional[List[str]] = None


class OCRVerificationService:
    """
    Service for document verification using Azure AI Vision OCR
    Extracts and validates Korean documents for trust scoring
    """

    # Azure AI Vision endpoint and key
    VISION_ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT")
    VISION_KEY = os.getenv("AZURE_VISION_KEY")

    # Document field extraction patterns (Korean)
    EXTRACTION_PATTERNS = {
        DocumentType.ID_CARD: {
            'name': r'성\s*명[:\s]*([가-힣]+)',
            'birth_date': r'생년월일[:\s]*(\d{4}[.\-년]\s*\d{1,2}[.\-월]\s*\d{1,2})',
            'id_number': r'(\d{6}[-\s]?\d{7})',
            'issue_date': r'발급일[:\s]*(\d{4}[.\-년]\s*\d{1,2}[.\-월]\s*\d{1,2})',
            'address': r'주\s*소[:\s]*([가-힣0-9\s\-]+(?:동|로|길)[가-힣0-9\s\-]*)'
        },
        DocumentType.DIPLOMA: {
            'name': r'성\s*명[:\s]*([가-힣]+)|([가-힣]{2,4})\s*(?:귀하|님)',
            'university': r'([가-힣]+(?:대학교|대학|전문대학))',
            'major': r'(?:전공|학과)[:\s]*([가-힣]+(?:과|학|전공))',
            'degree': r'(학사|석사|박사|전문학사)',
            'graduation_date': r'(\d{4}[년.\s]+\d{1,2}[월.\s]+\d{1,2})',
            'certificate_number': r'(?:증명서\s*번호|제\s*)[\s:]*([A-Z0-9\-]+)'
        },
        DocumentType.INCOME_CERT: {
            'name': r'성\s*명[:\s]*([가-힣]+)',
            'id_number': r'주민등록번호[:\s]*(\d{6}[-\s]?\d{7})',
            'year': r'(\d{4})\s*년도?\s*(?:귀속|소득)',
            'total_income': r'(?:총\s*)?(?:소득|수입)\s*금액[:\s]*([0-9,]+)\s*원?',
            'issue_date': r'발급일[:\s]*(\d{4}[.\-년]\s*\d{1,2}[.\-월]\s*\d{1,2})',
            'issuer': r'국세청|세무서'
        },
        DocumentType.EMPLOYMENT_CERT: {
            'name': r'성\s*명[:\s]*([가-힣]+)',
            'company': r'(?:회사명|상호|사업장)[:\s]*([가-힣A-Za-z0-9\s]+(?:주식회사|㈜|회사|기업)?)',
            'position': r'(?:직위|직급|직책)[:\s]*([가-힣]+)',
            'department': r'(?:부서|소속)[:\s]*([가-힣]+(?:부|팀|실)?)',
            'employment_date': r'(?:입사일|근무시작)[:\s]*(\d{4}[.\-년]\s*\d{1,2}[.\-월]\s*\d{1,2})',
            'issue_date': r'발급일[:\s]*(\d{4}[.\-년]\s*\d{1,2}[.\-월]\s*\d{1,2})'
        }
    }

    # Field importance weights for match scoring
    FIELD_WEIGHTS = {
        DocumentType.ID_CARD: {
            'name': 0.40,
            'birth_date': 0.40,
            'id_number': 0.20
        },
        DocumentType.DIPLOMA: {
            'name': 0.30,
            'university': 0.35,
            'degree': 0.20,
            'graduation_date': 0.15
        },
        DocumentType.INCOME_CERT: {
            'name': 0.30,
            'year': 0.15,
            'total_income': 0.55
        },
        DocumentType.EMPLOYMENT_CERT: {
            'name': 0.30,
            'company': 0.40,
            'position': 0.20,
            'employment_date': 0.10
        }
    }

    def __init__(self):
        self.supabase = get_supabase_client()

        if not self.VISION_ENDPOINT or not self.VISION_KEY:
            logger.warning("Azure AI Vision credentials not configured")

    async def verify_document(
        self,
        user_id: str,
        document_type: DocumentType,
        image_url: str,
        user_claimed_data: Dict[str, Any]
    ) -> VerificationResult:
        """
        Main verification flow:
        1. Extract text from document using Azure OCR
        2. Parse extracted text for relevant fields
        3. Compare with user-claimed data
        4. Calculate match score and determine status
        """
        try:
            logger.info(f"Starting verification for user {user_id}, document type: {document_type}")

            # 1. Perform OCR
            ocr_result = await self._perform_ocr(image_url)

            if not ocr_result:
                return self._create_failed_result(
                    user_id, document_type.value,
                    "OCR 처리에 실패했습니다"
                )

            # 2. Parse document based on type
            extracted_data = self._parse_document(
                ocr_result.raw_text,
                document_type
            )

            # 3. NEW: Validate document authenticity
            authenticity_result = await document_authenticity_service.validate_document(
                document_type,
                ocr_result.raw_text,
                extracted_data
            )

            # 4. Compare with user claims
            match_score, comparison_details, flags = self._compare_data(
                extracted_data,
                user_claimed_data,
                document_type
            )

            # 5. NEW: Combine match score with authenticity score
            # Weight: 70% match score, 30% authenticity score
            combined_score = (match_score * 0.7) + (authenticity_result.authenticity_score * 0.3)

            # 6. Add authenticity flags to flags list
            if authenticity_result.flags:
                flags.extend([f"authenticity_{flag}" for flag in authenticity_result.flags])

            # 7. Determine verification status (now considers authenticity)
            status = self._determine_status(
                combined_score,
                flags,
                authenticity_result.authenticity_score
            )

            # 8. Store result in database
            document_id = await self._store_verification_result(
                user_id=user_id,
                document_type=document_type.value,
                image_url=image_url,
                ocr_result=ocr_result,
                extracted_data=extracted_data,
                user_claimed_data=user_claimed_data,
                match_score=match_score,
                comparison_details=comparison_details,
                flags=flags,
                status=status,
                authenticity_result=authenticity_result
            )

            logger.info(
                f"Verification completed: match={match_score:.2f}, "
                f"authenticity={authenticity_result.authenticity_score:.2f}, "
                f"combined={combined_score:.2f}, status={status}"
            )

            return VerificationResult(
                document_id=document_id,
                document_type=document_type.value,
                match_score=match_score,
                verification_status=status,
                extracted_data=extracted_data,
                comparison_details=comparison_details,
                flags=flags,
                authenticity_score=authenticity_result.authenticity_score,
                issuer_validated=authenticity_result.issuer_validated,
                format_validated=authenticity_result.format_validated,
                pattern_validated=authenticity_result.pattern_validated,
                authenticity_flags=authenticity_result.flags
            )

        except Exception as e:
            logger.error(f"Document verification failed: {e}")
            return self._create_failed_result(
                user_id, document_type.value,
                f"인증 처리 중 오류가 발생했습니다: {str(e)}"
            )

    async def _perform_ocr(self, image_url: str) -> Optional[OCRResult]:
        """
        Perform OCR using Azure AI Vision
        """
        if not self.VISION_ENDPOINT or not self.VISION_KEY:
            logger.error("Azure AI Vision not configured")
            return None

        try:
            # Azure AI Vision Read API endpoint
            endpoint = f"{self.VISION_ENDPOINT}/computervision/imageanalysis:analyze"

            headers = {
                "Ocp-Apim-Subscription-Key": self.VISION_KEY,
                "Content-Type": "application/json"
            }

            params = {
                "api-version": "2024-02-01",
                "features": "read",
                "language": "ko"  # Korean language
            }

            body = {
                "url": image_url
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    endpoint,
                    headers=headers,
                    params=params,
                    json=body
                )

                if response.status_code != 200:
                    logger.error(f"OCR API error: {response.status_code} - {response.text}")
                    return None

                result = response.json()

            # Extract text from response
            raw_text = self._extract_text_from_response(result)

            # Detect document type from content
            detected_type = self._detect_document_type(raw_text)

            # Calculate confidence based on text quality
            confidence = self._calculate_ocr_confidence(result)

            return OCRResult(
                raw_text=raw_text,
                extracted_data={},  # Will be filled by parse_document
                confidence=confidence,
                document_type_detected=detected_type
            )

        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return None

    def _extract_text_from_response(self, response: Dict) -> str:
        """Extract text from Azure AI Vision response"""
        try:
            text_parts = []

            read_result = response.get('readResult', {})
            blocks = read_result.get('blocks', [])

            for block in blocks:
                lines = block.get('lines', [])
                for line in lines:
                    text = line.get('text', '')
                    if text:
                        text_parts.append(text)

            return '\n'.join(text_parts)

        except Exception as e:
            logger.error(f"Failed to extract text from response: {e}")
            return ""

    def _detect_document_type(self, text: str) -> str:
        """Detect document type from OCR text"""
        text_lower = text.lower()

        if any(keyword in text for keyword in ['주민등록증', '운전면허증', '여권']):
            return DocumentType.ID_CARD.value
        elif any(keyword in text for keyword in ['졸업증명서', '학위증명서', '학위기']):
            return DocumentType.DIPLOMA.value
        elif any(keyword in text for keyword in ['소득금액증명', '원천징수', '국세청']):
            return DocumentType.INCOME_CERT.value
        elif any(keyword in text for keyword in ['재직증명', '근무확인', '재직확인']):
            return DocumentType.EMPLOYMENT_CERT.value

        return "unknown"

    def _calculate_ocr_confidence(self, response: Dict) -> float:
        """Calculate overall OCR confidence score"""
        try:
            confidences = []

            read_result = response.get('readResult', {})
            blocks = read_result.get('blocks', [])

            for block in blocks:
                lines = block.get('lines', [])
                for line in lines:
                    words = line.get('words', [])
                    for word in words:
                        conf = word.get('confidence', 0)
                        if conf:
                            confidences.append(conf)

            if confidences:
                return sum(confidences) / len(confidences)

            return 0.5  # Default confidence

        except Exception as e:
            logger.error(f"Failed to calculate OCR confidence: {e}")
            return 0.5

    def _parse_document(
        self,
        text: str,
        document_type: DocumentType
    ) -> Dict[str, Any]:
        """
        Parse OCR text and extract structured data based on document type
        """
        extracted = {}
        patterns = self.EXTRACTION_PATTERNS.get(document_type, {})

        for field_name, pattern in patterns.items():
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1) if match.lastindex else match.group(0)
                    extracted[field_name] = self._clean_extracted_value(value, field_name)
            except Exception as e:
                logger.warning(f"Failed to extract {field_name}: {e}")

        return extracted

    def _clean_extracted_value(self, value: str, field_name: str) -> Any:
        """Clean and normalize extracted values"""
        if not value:
            return None

        value = value.strip()

        # Handle income values
        if field_name in ['total_income', 'annual_income']:
            # Remove commas and convert to integer
            cleaned = re.sub(r'[,\s원]', '', value)
            try:
                return int(cleaned)
            except ValueError:
                return value

        # Handle dates
        if 'date' in field_name or field_name == 'year':
            # Normalize date format
            value = re.sub(r'[년월일.\s]', '-', value)
            value = re.sub(r'-+', '-', value).strip('-')
            return value

        # Handle ID numbers (mask for privacy)
        if field_name == 'id_number':
            # Only store last 4 digits for verification
            if len(value) >= 4:
                return f"****-***{value[-4:]}"

        return value

    def _compare_data(
        self,
        extracted: Dict[str, Any],
        claimed: Dict[str, Any],
        document_type: DocumentType
    ) -> Tuple[float, Dict[str, Any], List[str]]:
        """
        Compare extracted data with user-claimed data
        Returns: (match_score, comparison_details, flags)
        """
        weights = self.FIELD_WEIGHTS.get(document_type, {})
        comparison = {}
        flags = []
        total_weight = 0
        weighted_score = 0

        for field, weight in weights.items():
            extracted_value = extracted.get(field)
            claimed_value = claimed.get(field)

            field_match = False
            match_type = "missing"

            if extracted_value and claimed_value:
                # Normalize for comparison
                extracted_norm = self._normalize_for_comparison(extracted_value, field)
                claimed_norm = self._normalize_for_comparison(claimed_value, field)

                if extracted_norm == claimed_norm:
                    field_match = True
                    match_type = "exact"
                elif self._is_partial_match(extracted_norm, claimed_norm, field):
                    field_match = True
                    match_type = "partial"
                    weight *= 0.7  # Reduce weight for partial matches
                else:
                    match_type = "mismatch"
                    flags.append(f"{field}: OCR 결과와 입력값이 다릅니다")

            elif extracted_value and not claimed_value:
                match_type = "claimed_missing"
            elif not extracted_value and claimed_value:
                match_type = "ocr_failed"
                weight *= 0.5  # Reduce penalty if OCR couldn't extract

            comparison[field] = {
                "extracted": extracted_value,
                "claimed": claimed_value,
                "match": field_match,
                "match_type": match_type,
                "weight": weight
            }

            total_weight += weight
            if field_match:
                weighted_score += weight

        # Calculate final score
        match_score = weighted_score / total_weight if total_weight > 0 else 0

        return match_score, comparison, flags

    def _normalize_for_comparison(self, value: Any, field: str) -> str:
        """Normalize values for comparison"""
        if value is None:
            return ""

        value_str = str(value).lower().strip()

        # Remove common variations
        value_str = re.sub(r'\s+', '', value_str)

        # Handle income ranges
        if field in ['total_income', 'annual_income']:
            # Extract numeric value
            numbers = re.findall(r'\d+', value_str)
            if numbers:
                # Use the largest number (assuming it's the main income)
                return max(numbers, key=lambda x: int(x))

        # Handle education levels
        if field == 'education_level' or field == 'degree':
            education_map = {
                '학사': ['대졸', '학사', '대학교', '4년제'],
                '석사': ['석사', '대학원'],
                '박사': ['박사', '박사학위'],
                '전문학사': ['전문대', '2년제', '전문학사']
            }
            for standard, variations in education_map.items():
                if any(v in value_str for v in variations):
                    return standard

        return value_str

    def _is_partial_match(self, value1: str, value2: str, field: str) -> bool:
        """Check if two values are a partial match"""
        # Name matching (one contains the other)
        if field == 'name':
            return value1 in value2 or value2 in value1

        # University matching (fuzzy)
        if field == 'university':
            # Remove common suffixes
            clean1 = re.sub(r'대학교?$', '', value1)
            clean2 = re.sub(r'대학교?$', '', value2)
            return clean1 == clean2 or clean1 in clean2 or clean2 in clean1

        # Income matching (within 20% range)
        if field in ['total_income', 'annual_income']:
            try:
                num1 = int(re.sub(r'\D', '', value1))
                num2 = int(re.sub(r'\D', '', value2))
                ratio = min(num1, num2) / max(num1, num2)
                return ratio >= 0.8
            except (ValueError, ZeroDivisionError):
                return False

        return False

    def _determine_status(
        self,
        combined_score: float,
        flags: List[str],
        authenticity_score: float
    ) -> str:
        """
        Determine verification status based on combined score, flags, and authenticity
        
        Rules:
        - Authenticity score < 0.5 → REJECTED (document is likely fake)
        - Combined score >= 0.85 and no critical flags → VERIFIED
        - Combined score >= 0.60 → FLAGGED (needs review)
        - Otherwise → REJECTED
        """
        # Reject if authenticity is too low
        if authenticity_score < 0.5:
            logger.warning(f"Document rejected due to low authenticity score: {authenticity_score:.2f}")
            return VerificationStatus.REJECTED.value

        critical_flag_keywords = ['신분증', 'id_number', 'name', 'authenticity_']

        has_critical_flags = any(
            any(keyword in flag for keyword in critical_flag_keywords)
            for flag in flags
        )

        if combined_score >= 0.85 and not has_critical_flags:
            return VerificationStatus.VERIFIED.value
        elif combined_score >= 0.60:
            return VerificationStatus.FLAGGED.value
        else:
            return VerificationStatus.REJECTED.value

    async def _store_verification_result(
        self,
        user_id: str,
        document_type: str,
        image_url: str,
        ocr_result: OCRResult,
        extracted_data: Dict,
        user_claimed_data: Dict,
        match_score: float,
        comparison_details: Dict,
        flags: List[str],
        status: str,
        authenticity_result=None
    ) -> str:
        """Store verification result in database"""
        try:
            insert_data = {
                'user_id': user_id,
                'document_type': document_type,
                'file_url': image_url,
                'ocr_raw_text': ocr_result.raw_text,
                'ocr_extracted_data': extracted_data,
                'ocr_confidence_score': ocr_result.confidence,
                'ocr_processed_at': datetime.now().isoformat(),
                'user_input_data': user_claimed_data,
                'match_details': comparison_details,
                'match_score': match_score,
                'verification_status': status,
                'verification_flags': flags
            }

            # Add authenticity data if available
            if authenticity_result:
                insert_data.update({
                    'authenticity_score': authenticity_result.authenticity_score,
                    'issuer_validated': authenticity_result.issuer_validated,
                    'format_validated': authenticity_result.format_validated,
                    'pattern_validated': authenticity_result.pattern_validated,
                    'authenticity_flags': authenticity_result.flags
                })

            result = self.supabase.table('user_documents').insert(insert_data).execute()

            if result.data:
                return result.data[0]['id']

            return ""

        except Exception as e:
            logger.error(f"Failed to store verification result: {e}")
            return ""

    def _create_failed_result(
        self,
        user_id: str,
        document_type: str,
        error_message: str
    ) -> VerificationResult:
        """Create a failed verification result"""
        return VerificationResult(
            document_id="",
            document_type=document_type,
            match_score=0.0,
            verification_status=VerificationStatus.REJECTED.value,
            extracted_data={},
            comparison_details={"error": error_message},
            flags=[error_message],
            authenticity_score=None,
            issuer_validated=None,
            format_validated=None,
            pattern_validated=None,
            authenticity_flags=None
        )

    async def get_verification_status(self, user_id: str) -> Dict[str, Any]:
        """Get verification status for all document types"""
        try:
            result = self.supabase.table('user_documents').select(
                'document_type, verification_status, match_score, authenticity_score, created_at'
            ).eq('user_id', user_id).execute()

            status = {
                'id_card': {'verified': False, 'status': 'not_submitted'},
                'diploma': {'verified': False, 'status': 'not_submitted'},
                'income_cert': {'verified': False, 'status': 'not_submitted'},
                'employment_cert': {'verified': False, 'status': 'not_submitted'}
            }

            if result.data:
                for doc in result.data:
                    doc_type = doc['document_type']
                    if doc_type in status:
                        status[doc_type] = {
                            'verified': doc['verification_status'] == 'verified',
                            'status': doc['verification_status'],
                            'match_score': doc.get('match_score', 0),
                            'authenticity_score': doc.get('authenticity_score'),
                            'submitted_at': doc['created_at']
                        }

            return status

        except Exception as e:
            logger.error(f"Failed to get verification status: {e}")
            return {}


# Singleton instance
ocr_verification_service = OCRVerificationService()
