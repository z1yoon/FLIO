"""
FLIO Document Authenticity Service
Validates that uploaded documents are real Korean official documents

Validates:
- Official issuer names (국세청, 세무서, 대학교, etc.)
- Document format/structure
- Document number patterns
- Official keywords and formatting
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple, Union
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

# Document type values (avoiding circular import)
# These match DocumentType enum values from ocr_verification_service
DOCUMENT_TYPE_VALUES = {
    'ID_CARD': 'id_card',
    'DIPLOMA': 'diploma',
    'INCOME_CERT': 'income_cert',
    'EMPLOYMENT_CERT': 'employment_cert'
}


class AuthenticityResult(BaseModel):
    """Result of document authenticity validation"""
    authenticity_score: float  # 0.0-1.0
    issuer_validated: bool
    format_validated: bool
    pattern_validated: bool
    flags: List[str]
    validation_details: Dict[str, Any]


class DocumentAuthenticityService:
    """
    Service for validating Korean official document authenticity
    Checks issuer, format, and patterns to ensure documents are real
    """

    # Official Korean document issuers
    OFFICIAL_ISSUERS = {
        'income_cert': [
            '국세청', '세무서', '세무서장', '국세청장', 
            '국세청장명의', '세무서장명의'
        ],
        'diploma': [
            '대학교', '대학', '전문대학', '대학원',
            '총장', '학장', '교수'
        ],
        'employment_cert': [
            '주식회사', '㈜', '회사', '기업', '법인',
            '대표이사', '사장', '인사팀'
        ],
        'id_card': [
            '행정안전부', '경찰청', '지방자치단체',
            '대한민국', '정부'
        ]
    }

    # Document number patterns
    DOCUMENT_PATTERNS = {
        'income_cert': r'[A-Z0-9\-]{10,20}',  # 국세청 증명서 번호
        'diploma': r'[A-Z0-9\-]{8,15}',        # 대학교 증명서 번호
        'id_card': r'\d{6}[-]\d{7}',           # 주민등록번호
        'employment_cert': r'[A-Z0-9\-]{5,20}'  # 회사 문서 번호
    }

    # Official format keywords that must be present
    FORMAT_KEYWORDS = {
        'income_cert': [
            '소득금액증명원', '국세청', '세무서', '발급일',
            '소득', '금액', '증명', '귀속'
        ],
        'diploma': [
            '졸업증명서', '학위증명서', '대학교', '학사', '석사', '박사',
            '졸업', '학위', '증명서'
        ],
        'employment_cert': [
            '재직증명서', '근무확인서', '입사일', '재직',
            '근무', '확인', '증명서'
        ],
        'id_card': [
            '주민등록증', '운전면허증', '대한민국',
            '주민등록', '면허'
        ]
    }

    # Required fields for each document type
    REQUIRED_FIELDS = {
        'income_cert': ['name', 'year', 'total_income'],
        'diploma': ['name', 'university', 'degree'],
        'employment_cert': ['name', 'company', 'position'],
        'id_card': ['name', 'birth_date', 'id_number']
    }

    async def validate_document(
        self,
        document_type: Union[str, Any],  # Accept DocumentType enum or string
        ocr_text: str,
        extracted_data: Dict[str, Any]
    ) -> AuthenticityResult:
        """
        Main validation method - checks all authenticity aspects
        """
        try:
            # Convert DocumentType enum to string if needed
            doc_type_str = document_type.value if hasattr(document_type, 'value') else str(document_type)
            logger.info(f"Validating authenticity for {doc_type_str}")

            # Convert to string for dictionary lookups
            doc_type_str = document_type.value if hasattr(document_type, 'value') else str(document_type)

            # 1. Validate issuer
            issuer_valid = self.validate_issuer(doc_type_str, ocr_text)

            # 2. Validate format
            format_valid = self.validate_format(doc_type_str, ocr_text)

            # 3. Validate patterns
            pattern_valid = self.validate_patterns(doc_type_str, extracted_data)

            # 4. Validate required fields
            fields_valid = self.validate_required_fields(doc_type_str, extracted_data)

            # 5. Calculate authenticity score
            authenticity_score = self.calculate_authenticity_score(
                issuer_valid, format_valid, pattern_valid, fields_valid
            )

            # 6. Collect flags
            flags = []
            if not issuer_valid:
                flags.append("issuer_not_validated")
            if not format_valid:
                flags.append("format_not_validated")
            if not pattern_valid:
                flags.append("pattern_not_validated")
            if not fields_valid:
                flags.append("required_fields_missing")

            return AuthenticityResult(
                authenticity_score=authenticity_score,
                issuer_validated=issuer_valid,
                format_validated=format_valid,
                pattern_validated=pattern_valid,
                flags=flags,
                validation_details={
                    'issuer_valid': issuer_valid,
                    'format_valid': format_valid,
                    'pattern_valid': pattern_valid,
                    'fields_valid': fields_valid
                }
            )

        except Exception as e:
            logger.error(f"Authenticity validation failed: {e}")
            # Return low score on error
            return AuthenticityResult(
                authenticity_score=0.0,
                issuer_validated=False,
                format_validated=False,
                pattern_validated=False,
                flags=['validation_error'],
                validation_details={'error': str(e)}
            )

    def validate_issuer(self, document_type: str, ocr_text: str) -> bool:
        """
        Check if document contains official issuer names
        """
        if document_type not in self.OFFICIAL_ISSUERS:
            return False

        text_lower = ocr_text.lower()
        official_issuers = self.OFFICIAL_ISSUERS[document_type]

        # Check if any official issuer appears in text
        for issuer in official_issuers:
            if issuer in ocr_text or issuer.lower() in text_lower:
                logger.debug(f"Found official issuer: {issuer}")
                return True

        logger.warning(f"No official issuer found for {document_type}")
        return False

    def validate_format(self, document_type: str, ocr_text: str) -> bool:
        """
        Check if document contains required format keywords
        """
        if document_type not in self.FORMAT_KEYWORDS:
            return False

        required_keywords = self.FORMAT_KEYWORDS[document_type]
        text_lower = ocr_text.lower()

        # Check if at least 3 required keywords are present
        found_keywords = 0
        for keyword in required_keywords:
            if keyword in ocr_text or keyword.lower() in text_lower:
                found_keywords += 1

        # Require at least 3 keywords for format validation
        is_valid = found_keywords >= 3

        if not is_valid:
            logger.warning(
                f"Format validation failed for {document_type}: "
                f"found {found_keywords}/{len(required_keywords)} keywords"
            )

        return is_valid

    def validate_patterns(
        self,
        document_type: str,
        extracted_data: Dict[str, Any]
    ) -> bool:
        """
        Validate document numbers and patterns match official formats
        """
        if document_type not in self.DOCUMENT_PATTERNS:
            return False

        pattern = self.DOCUMENT_PATTERNS[document_type]

        # Check ID number pattern for ID cards
        if document_type == 'id_card':
            id_number = extracted_data.get('id_number', '')
            if id_number:
                # Remove masking if present
                id_clean = id_number.replace('*', '').replace('-', '')
                if re.match(r'^\d{13}$', id_clean):
                    return True
                # Check if matches pattern with dashes
                if re.match(pattern, id_number):
                    return True

        # Check certificate numbers for other documents
        cert_fields = ['certificate_number', 'document_number', 'cert_number']
        for field in cert_fields:
            value = extracted_data.get(field)
            if value and re.match(pattern, str(value)):
                return True

        # For documents without explicit numbers, check if other patterns match
        # (e.g., dates, years)
        if document_type == 'income_cert':
            year = extracted_data.get('year')
            if year and re.match(r'^\d{4}$', str(year)):
                return True

        # If no explicit pattern to check, return True (lenient)
        if document_type == 'employment_cert':
            # Employment certs may not have document numbers
            return True

        logger.warning(f"Pattern validation failed for {document_type}")
        return False

    def validate_required_fields(
        self,
        document_type: str,
        extracted_data: Dict[str, Any]
    ) -> bool:
        """
        Check if all required fields are present
        """
        if document_type not in self.REQUIRED_FIELDS:
            return True  # No requirements = valid

        required = self.REQUIRED_FIELDS[document_type]
        missing_fields = []

        for field in required:
            if not extracted_data.get(field):
                missing_fields.append(field)

        if missing_fields:
            logger.warning(
                f"Missing required fields for {document_type}: {missing_fields}"
            )
            return False

        return True

    def calculate_authenticity_score(
        self,
        issuer_valid: bool,
        format_valid: bool,
        pattern_valid: bool,
        fields_valid: bool
    ) -> float:
        """
        Calculate overall authenticity score (0.0-1.0)
        
        Weights:
        - Issuer: 40% (most important - proves official source)
        - Format: 30% (proves document structure)
        - Pattern: 20% (proves document numbers)
        - Fields: 10% (proves completeness)
        """
        score = 0.0

        if issuer_valid:
            score += 0.4
        if format_valid:
            score += 0.3
        if pattern_valid:
            score += 0.2
        if fields_valid:
            score += 0.1

        # Clamp to 0.0-1.0
        return max(0.0, min(1.0, score))


# Singleton instance
document_authenticity_service = DocumentAuthenticityService()
