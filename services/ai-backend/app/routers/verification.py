"""
FLIO Document Verification API Routes
Korean Marriage Agency Style (결혼정보회사)

Endpoints for document upload, OCR verification, and status checks.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging

from ..services.ocr_verification_service import (
    ocr_verification_service,
    DocumentType,
    VerificationResult
)
from ..services.trust_score_service import trust_score_service

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models

class DocumentVerifyRequest(BaseModel):
    """Request to verify a document"""
    user_id: str
    document_type: str  # id_card, diploma, income_cert, employment_cert
    image_url: str
    claimed_data: Dict[str, Any]


class VerificationStatusResponse(BaseModel):
    """Document verification status"""
    document_type: str
    document_type_korean: str
    verified: bool
    status: str
    match_score: Optional[float]
    authenticity_score: Optional[float] = None
    issuer_validated: Optional[bool] = None
    format_validated: Optional[bool] = None
    submitted_at: Optional[str]


class AllVerificationsResponse(BaseModel):
    """All document verification statuses for a user"""
    user_id: str
    overall_verification_level: str
    documents: List[VerificationStatusResponse]
    recommendations: List[str]


# Korean labels
DOCUMENT_TYPE_KOREAN = {
    'id_card': '신분증',
    'diploma': '학력증명서',
    'income_cert': '소득증명서',
    'employment_cert': '재직증명서'
}

VERIFICATION_STATUS_KOREAN = {
    'not_submitted': '미제출',
    'pending': '검토 대기',
    'processing': '처리 중',
    'verified': '인증 완료',
    'flagged': '확인 필요',
    'rejected': '인증 실패',
    'expired': '만료됨'
}


# API Endpoints

@router.post("/document/verify", response_model=VerificationResult)
async def verify_document(request: DocumentVerifyRequest):
    """
    Verify a document using Azure AI Vision OCR

    Flow:
    1. Extract text from document image
    2. Parse relevant fields based on document type
    3. Compare with user-claimed data
    4. Calculate match score
    5. Update trust score

    Supported document types:
    - id_card: 신분증 (주민등록증, 운전면허증, 여권)
    - diploma: 학력증명서 (졸업증명서, 학위증명서)
    - income_cert: 소득증명서 (소득금액증명원)
    - employment_cert: 재직증명서

    - **user_id**: User's unique identifier
    - **document_type**: Type of document
    - **image_url**: URL of document image
    - **claimed_data**: User's claimed information to verify
    """
    try:
        # Validate document type
        try:
            doc_type = DocumentType(request.document_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 문서 유형입니다: {request.document_type}"
            )

        # Perform verification
        result = await ocr_verification_service.verify_document(
            user_id=request.user_id,
            document_type=doc_type,
            image_url=request.image_url,
            user_claimed_data=request.claimed_data
        )

        # Recalculate trust score after verification
        await trust_score_service.calculate_trust_score(request.user_id)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{document_id}/status")
async def get_document_status(document_id: str):
    """
    Get verification status for a specific document

    - **document_id**: Document's unique identifier
    """
    try:
        from ..models.database import get_supabase_client
        supabase = get_supabase_client()

        result = supabase.table('user_documents').select(
            'id, user_id, document_type, verification_status, match_score, '
            'authenticity_score, issuer_validated, format_validated, pattern_validated, '
            'verification_flags, authenticity_flags, ocr_extracted_data, created_at, updated_at'
        ).eq('id', document_id).single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

        doc = result.data

        return {
            "document_id": doc['id'],
            "user_id": doc['user_id'],
            "document_type": doc['document_type'],
            "document_type_korean": DOCUMENT_TYPE_KOREAN.get(doc['document_type'], doc['document_type']),
            "verification_status": doc['verification_status'],
            "verification_status_korean": VERIFICATION_STATUS_KOREAN.get(doc['verification_status'], doc['verification_status']),
            "match_score": doc['match_score'],
            "authenticity_score": doc.get('authenticity_score'),
            "issuer_validated": doc.get('issuer_validated'),
            "format_validated": doc.get('format_validated'),
            "pattern_validated": doc.get('pattern_validated'),
            "flags": doc.get('verification_flags', []),
            "authenticity_flags": doc.get('authenticity_flags', []),
            "extracted_data": doc.get('ocr_extracted_data', {}),
            "submitted_at": doc['created_at'],
            "updated_at": doc['updated_at']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{user_id}", response_model=AllVerificationsResponse)
async def get_all_verification_status(user_id: str):
    """
    Get verification status for all document types

    Returns status of each document type and overall verification level

    - **user_id**: User's unique identifier
    """
    try:
        # Get verification status for all documents
        status = await ocr_verification_service.get_verification_status(user_id)

        # Build response
        documents = []
        for doc_type, info in status.items():
            documents.append(VerificationStatusResponse(
                document_type=doc_type,
                document_type_korean=DOCUMENT_TYPE_KOREAN.get(doc_type, doc_type),
                verified=info.get('verified', False),
                status=info.get('status', 'not_submitted'),
                match_score=info.get('match_score'),
                authenticity_score=info.get('authenticity_score'),
                issuer_validated=None,  # Not available in summary, use detailed endpoint
                format_validated=None,  # Not available in summary, use detailed endpoint
                submitted_at=info.get('submitted_at')
            ))

        # Calculate overall verification level
        verified_count = sum(1 for d in documents if d.verified)

        if verified_count >= 4:
            overall_level = "full"
        elif verified_count >= 2:
            overall_level = "basic"
        elif verified_count >= 1:
            overall_level = "partial"
        else:
            overall_level = "none"

        # Generate recommendations
        recommendations = []
        if not status.get('id_card', {}).get('verified'):
            recommendations.append("신분증을 인증하여 기본 신뢰도를 확보하세요")
        if not status.get('diploma', {}).get('verified'):
            recommendations.append("학력증명서를 인증하면 신뢰도가 올라갑니다")
        if not status.get('income_cert', {}).get('verified'):
            recommendations.append("소득증명서 인증으로 경제력을 증명하세요")
        if not status.get('employment_cert', {}).get('verified'):
            recommendations.append("재직증명서 인증으로 직업 정보를 검증하세요")

        if not recommendations:
            recommendations.append("모든 문서가 인증되었습니다! VIP 회원 자격입니다.")

        return AllVerificationsResponse(
            user_id=user_id,
            overall_verification_level=overall_level,
            documents=documents,
            recommendations=recommendations
        )

    except Exception as e:
        logger.error(f"Failed to get verification status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/required-fields/{document_type}")
async def get_required_fields(document_type: str):
    """
    Get required fields for a document type verification

    Use this to show users what information to provide

    - **document_type**: Type of document (id_card, diploma, etc.)
    """
    required_fields = {
        'id_card': {
            'name': {'label': '성명', 'type': 'text', 'required': True},
            'birth_date': {'label': '생년월일', 'type': 'date', 'required': True},
        },
        'diploma': {
            'name': {'label': '성명', 'type': 'text', 'required': True},
            'university': {'label': '대학교명', 'type': 'text', 'required': True},
            'major': {'label': '전공', 'type': 'text', 'required': False},
            'degree': {'label': '학위', 'type': 'select', 'required': True,
                      'options': ['전문학사', '학사', '석사', '박사']},
            'graduation_year': {'label': '졸업년도', 'type': 'number', 'required': True}
        },
        'income_cert': {
            'name': {'label': '성명', 'type': 'text', 'required': True},
            'year': {'label': '소득연도', 'type': 'number', 'required': True},
            'total_income': {'label': '총소득금액', 'type': 'number', 'required': True,
                           'description': '연간 총소득 (원 단위)'}
        },
        'employment_cert': {
            'name': {'label': '성명', 'type': 'text', 'required': True},
            'company': {'label': '회사명', 'type': 'text', 'required': True},
            'position': {'label': '직위/직급', 'type': 'text', 'required': True},
            'employment_date': {'label': '입사일', 'type': 'date', 'required': False}
        }
    }

    if document_type not in required_fields:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 문서 유형입니다: {document_type}"
        )

    return {
        "document_type": document_type,
        "document_type_korean": DOCUMENT_TYPE_KOREAN.get(document_type, document_type),
        "fields": required_fields[document_type],
        "instructions": _get_upload_instructions(document_type)
    }


def _get_upload_instructions(document_type: str) -> List[str]:
    """Get upload instructions for document type"""
    instructions = {
        'id_card': [
            "주민등록증, 운전면허증, 또는 여권 앞면을 촬영해주세요",
            "문서 전체가 보이도록 촬영해주세요",
            "빛 반사가 없도록 주의해주세요",
            "주민등록번호는 뒷자리 4자리만 저장됩니다"
        ],
        'diploma': [
            "졸업증명서 또는 학위증명서를 촬영해주세요",
            "발급일이 6개월 이내인 문서를 권장합니다",
            "학교 직인이 선명하게 보여야 합니다"
        ],
        'income_cert': [
            "국세청 발급 소득금액증명원을 촬영해주세요",
            "홈택스에서 발급받을 수 있습니다",
            "최근 연도 소득이 포함되어야 합니다"
        ],
        'employment_cert': [
            "회사에서 발급받은 재직증명서를 촬영해주세요",
            "발급일이 1개월 이내인 문서를 권장합니다",
            "회사 직인 또는 인사부서 확인이 필요합니다"
        ]
    }

    return instructions.get(document_type, [])


@router.delete("/document/{document_id}")
async def delete_document(document_id: str, user_id: str):
    """
    Delete a submitted document

    User can re-submit if needed

    - **document_id**: Document's unique identifier
    - **user_id**: User's unique identifier (for authorization)
    """
    try:
        from ..models.database import get_supabase_client
        supabase = get_supabase_client()

        # Verify ownership
        check_result = supabase.table('user_documents').select(
            'user_id'
        ).eq('id', document_id).single().execute()

        if not check_result.data:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

        if check_result.data['user_id'] != user_id:
            raise HTTPException(status_code=403, detail="삭제 권한이 없습니다")

        # Delete document
        supabase.table('user_documents').delete().eq('id', document_id).execute()

        # Recalculate trust score
        await trust_score_service.calculate_trust_score(user_id)

        return {
            "success": True,
            "message": "문서가 삭제되었습니다"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
