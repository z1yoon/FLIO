"""
Auth router for user authentication operations
Handles email confirmation and user management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from app.models.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


class ConfirmEmailRequest(BaseModel):
    user_id: str


class ConfirmEmailResponse(BaseModel):
    success: bool
    user_id: str
    message: str


@router.post("/confirm-email", response_model=ConfirmEmailResponse)
async def confirm_email(request: ConfirmEmailRequest):
    """
    Auto-confirm user email using service role key
    This bypasses the email confirmation requirement
    """
    try:
        supabase = get_supabase_client()
        
        # Use admin API to update user and confirm email
        # The service role key allows us to update auth.users directly
        response = supabase.auth.admin.update_user_by_id(
            request.user_id,
            {"email_confirm": True}
        )
        
        if response.user:
            logger.info(f"Email confirmed for user: {request.user_id}")
            return ConfirmEmailResponse(
                success=True,
                user_id=request.user_id,
                message="Email confirmed successfully"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to confirm email"
            )
            
    except Exception as e:
        logger.error(f"Error confirming email: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to confirm email: {str(e)}"
        )
