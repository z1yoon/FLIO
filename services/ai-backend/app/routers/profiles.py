"""
FLIO Profile Management API Routes
Handles extended profile data, family background, and profile updates
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging

from ..models.database import get_supabase_client
from ..middleware.behavioral_logging import log_profile_update

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Request/Response Models ====================

class ExtendedProfileRequest(BaseModel):
    user_id: str
    # Physical
    height_cm: Optional[int] = None
    weight_kg: Optional[int] = None
    # Education
    education_level: Optional[str] = None
    university_name: Optional[str] = None
    major: Optional[str] = None
    graduation_year: Optional[int] = None
    # Career & Income
    employment_status: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    industry: Optional[str] = None
    annual_income_range: Optional[str] = None
    # Marital History
    marital_status: Optional[str] = None
    divorce_reason: Optional[str] = None
    has_children: Optional[bool] = None
    children_count: Optional[int] = None


class FamilyBackgroundRequest(BaseModel):
    user_id: str
    # Father
    father_occupation: Optional[str] = None
    father_education: Optional[str] = None
    father_alive: Optional[bool] = True
    # Mother
    mother_occupation: Optional[str] = None
    mother_education: Optional[str] = None
    mother_alive: Optional[bool] = True
    # Parents
    parents_status: Optional[str] = None
    parents_marital_status: Optional[str] = None
    parents_financial_stability: Optional[str] = None
    # Siblings
    sibling_count: Optional[int] = 0
    sibling_info: Optional[List[Dict[str, Any]]] = []
    birth_order: Optional[int] = 1
    # Property
    family_property_type: Optional[str] = None
    family_location: Optional[str] = None


class ProfileResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class FullProfileResponse(BaseModel):
    user_id: str
    # Basic info
    real_name: Optional[str] = None
    real_name_verified: bool = False
    height_cm: Optional[int] = None
    weight_kg: Optional[int] = None
    # Education
    education_level: Optional[str] = None
    university_name: Optional[str] = None
    major: Optional[str] = None
    graduation_year: Optional[int] = None
    # Career
    employment_status: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    industry: Optional[str] = None
    annual_income_range: Optional[str] = None
    # Marital
    marital_status: Optional[str] = None
    divorce_reason: Optional[str] = None
    has_children: bool = False
    children_count: int = 0
    # Verification & Trust
    verification_level: str = "none"
    trust_tier: str = "unverified"
    last_verified_at: Optional[str] = None
    # Family background (if available)
    family_background: Optional[Dict[str, Any]] = None
    # Completeness
    profile_completion: Optional[Dict[str, Any]] = None


# ==================== Endpoints ====================

@router.post("/extended", response_model=ProfileResponse)
async def update_extended_profile(request: ExtendedProfileRequest):
    """
    Update extended profile information (education, career, income, marital)

    This endpoint handles:
    - Physical attributes (height, weight)
    - Education background
    - Career and employment information
    - Income range
    - Marital history

    Triggers behavioral logging for profile updates
    """
    try:
        supabase = get_supabase_client()

        # Get current profile to track changes
        current_profile = supabase.table('profiles').select('*').eq(
            'user_id', request.user_id
        ).maybe_single().execute()

        # Build update data (only include fields that were provided)
        update_data = {}
        if request.height_cm is not None:
            update_data['height_cm'] = request.height_cm
        if request.weight_kg is not None:
            update_data['weight_kg'] = request.weight_kg
        if request.education_level is not None:
            update_data['education_level'] = request.education_level
        if request.university_name is not None:
            update_data['university_name'] = request.university_name
        if request.major is not None:
            update_data['major'] = request.major
        if request.graduation_year is not None:
            update_data['graduation_year'] = request.graduation_year
        if request.employment_status is not None:
            update_data['employment_status'] = request.employment_status
        if request.company_name is not None:
            update_data['company_name'] = request.company_name
        if request.job_title is not None:
            update_data['job_title'] = request.job_title
        if request.industry is not None:
            update_data['industry'] = request.industry
        if request.annual_income_range is not None:
            update_data['annual_income_range'] = request.annual_income_range
        if request.marital_status is not None:
            update_data['marital_status'] = request.marital_status
        if request.divorce_reason is not None:
            update_data['divorce_reason'] = request.divorce_reason
        if request.has_children is not None:
            update_data['has_children'] = request.has_children
        if request.children_count is not None:
            update_data['children_count'] = request.children_count

        if not update_data:
            return ProfileResponse(
                success=False,
                message="No fields to update"
            )

        # Update profile in database
        result = supabase.table('profiles').update(
            update_data
        ).eq('user_id', request.user_id).execute()

        # Log behavioral events for significant changes
        if current_profile.data:
            old_profile = current_profile.data

            # Check for critical field changes
            critical_fields = ['annual_income_range', 'education_level', 'university_name']
            for field in critical_fields:
                if field in update_data:
                    old_value = old_profile.get(field)
                    new_value = update_data[field]
                    if old_value != new_value:
                        await log_profile_update(
                            user_id=request.user_id,
                            field=field,
                            old_value=old_value,
                            new_value=new_value
                        )

        return ProfileResponse(
            success=True,
            message="Extended profile updated successfully",
            data=result.data[0] if result.data else None
        )

    except Exception as e:
        logger.error(f"Failed to update extended profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/family-background", response_model=ProfileResponse)
async def update_family_background(request: FamilyBackgroundRequest):
    """
    Create or update family background information

    This is optional information that helps with:
    - Trust score completeness component
    - Better matching based on family values
    - Traditional Korean marriage context
    """
    try:
        supabase = get_supabase_client()

        # Check if family background exists
        existing = supabase.table('user_family_background').select('id').eq(
            'user_id', request.user_id
        ).maybe_single().execute()

        # Build data
        background_data = request.dict(exclude={'user_id'}, exclude_none=True)
        background_data['user_id'] = request.user_id
        background_data['updated_at'] = 'now()'

        if existing.data:
            # Update existing record
            result = supabase.table('user_family_background').update(
                background_data
            ).eq('user_id', request.user_id).execute()
            message = "Family background updated successfully"
        else:
            # Insert new record
            result = supabase.table('user_family_background').insert(
                background_data
            ).execute()
            message = "Family background created successfully"

        # Log as profile edit (low risk)
        await log_profile_update(
            user_id=request.user_id,
            field='family_background',
            old_value=None,
            new_value='updated'
        )

        return ProfileResponse(
            success=True,
            message=message,
            data=result.data[0] if result.data else None
        )

    except Exception as e:
        logger.error(f"Failed to update family background: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/full", response_model=FullProfileResponse)
async def get_full_profile(user_id: str):
    """
    Get complete profile data including:
    - Extended profile fields
    - Family background
    - Verification status
    - Trust tier
    - Profile completeness
    """
    try:
        supabase = get_supabase_client()

        # Get profile data
        profile = supabase.table('profiles').select('*').eq(
            'user_id', user_id
        ).maybe_single().execute()

        if not profile.data:
            raise HTTPException(status_code=404, detail="Profile not found")

        profile_data = profile.data

        # Get family background
        family_bg = supabase.table('user_family_background').select('*').eq(
            'user_id', user_id
        ).maybe_single().execute()

        # Get trust score for completeness calculation
        trust_score = supabase.table('user_trust_scores').select(
            'completeness_score, calculation_details'
        ).eq('user_id', user_id).maybe_single().execute()

        # Calculate profile completeness
        profile_completion = _calculate_profile_completion(
            profile_data,
            family_bg.data,
            trust_score.data if trust_score.data else None
        )

        return FullProfileResponse(
            user_id=user_id,
            # Basic
            real_name=profile_data.get('real_name'),
            real_name_verified=profile_data.get('real_name_verified', False),
            height_cm=profile_data.get('height_cm'),
            weight_kg=profile_data.get('weight_kg'),
            # Education
            education_level=profile_data.get('education_level'),
            university_name=profile_data.get('university_name'),
            major=profile_data.get('major'),
            graduation_year=profile_data.get('graduation_year'),
            # Career
            employment_status=profile_data.get('employment_status'),
            company_name=profile_data.get('company_name'),
            job_title=profile_data.get('job_title'),
            industry=profile_data.get('industry'),
            annual_income_range=profile_data.get('annual_income_range'),
            # Marital
            marital_status=profile_data.get('marital_status', '미혼'),
            divorce_reason=profile_data.get('divorce_reason'),
            has_children=profile_data.get('has_children', False),
            children_count=profile_data.get('children_count', 0),
            # Verification
            verification_level=profile_data.get('verification_level', 'none'),
            trust_tier=profile_data.get('trust_tier', 'unverified'),
            last_verified_at=profile_data.get('last_verified_at'),
            # Family background
            family_background=family_bg.data,
            # Completeness
            profile_completion=profile_completion
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get full profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/completion")
async def get_profile_completion(user_id: str):
    """
    Get profile completion status
    Returns percentage completion and missing fields
    """
    try:
        supabase = get_supabase_client()

        profile = supabase.table('profiles').select('*').eq(
            'user_id', user_id
        ).maybe_single().execute()

        if not profile.data:
            raise HTTPException(status_code=404, detail="Profile not found")

        family_bg = supabase.table('user_family_background').select('*').eq(
            'user_id', user_id
        ).maybe_single().execute()

        completion = _calculate_profile_completion(profile.data, family_bg.data, None)

        return {
            "success": True,
            "data": completion
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profile completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Helper Functions ====================

def _calculate_profile_completion(
    profile: Dict,
    family_background: Optional[Dict],
    trust_data: Optional[Dict]
) -> Dict[str, Any]:
    """Calculate profile completion percentage and missing fields"""

    # Required fields for each section
    required_fields = {
        'physical': ['height_cm', 'weight_kg'],
        'education': ['education_level', 'university_name', 'major', 'graduation_year'],
        'career': ['employment_status', 'company_name', 'job_title', 'industry'],
        'income': ['annual_income_range'],
        'marital': ['marital_status'],
    }

    # Optional fields
    optional_fields = {
        'family_background': ['father_occupation', 'mother_occupation', 'sibling_count']
    }

    section_completion = {}
    missing_fields = {}
    total_required = 0
    total_filled = 0

    # Check required fields
    for section, fields in required_fields.items():
        filled = sum(1 for f in fields if profile.get(f) is not None and profile.get(f) != '')
        total_required += len(fields)
        total_filled += filled
        section_completion[section] = {
            'filled': filled,
            'total': len(fields),
            'percentage': (filled / len(fields)) * 100 if fields else 0
        }
        if filled < len(fields):
            missing_fields[section] = [f for f in fields if not profile.get(f)]

    # Check family background (optional but boosts completeness)
    if family_background:
        family_fields = optional_fields['family_background']
        family_filled = sum(1 for f in family_fields if family_background.get(f) is not None)
        section_completion['family_background'] = {
            'filled': family_filled,
            'total': len(family_fields),
            'percentage': (family_filled / len(family_fields)) * 100 if family_fields else 0,
            'is_optional': True
        }
    else:
        section_completion['family_background'] = {
            'filled': 0,
            'total': len(optional_fields['family_background']),
            'percentage': 0,
            'is_optional': True
        }

    # Overall percentage
    overall_percentage = (total_filled / total_required) * 100 if total_required > 0 else 0

    return {
        'overall_percentage': round(overall_percentage, 1),
        'required_filled': total_filled,
        'required_total': total_required,
        'section_completion': section_completion,
        'missing_fields': missing_fields,
        'has_family_background': family_background is not None,
        'can_start_matching': overall_percentage >= 70  # Need 70% to start matching
    }
