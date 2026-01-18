"""
FLIO Behavioral Logging Middleware and Decorators
Provides utilities for automatic behavioral event logging
"""

import logging
from functools import wraps
from typing import Callable, Dict, Any, Optional
from fastapi import Request

from ..services.behavioral_tracking_service import (
    behavioral_tracking_service,
    EventType
)

logger = logging.getLogger(__name__)


def log_behavior(
    event_type: EventType,
    extract_user_id: Callable[[Any], str] = None,
    extract_field: Callable[[Any, Any], Optional[str]] = None,
    extract_old_value: Callable[[Any], Optional[str]] = None,
    extract_new_value: Callable[[Any], Optional[str]] = None
):
    """
    Decorator for automatic behavioral logging

    Usage:
        @log_behavior(
            event_type=EventType.PROFILE_EDIT,
            extract_user_id=lambda request: request.get("user_id"),
            extract_field=lambda request, response: "income",
            extract_old_value=lambda request: request.get("old_income"),
            extract_new_value=lambda request: request.get("new_income")
        )
        async def update_profile(request_data: dict):
            # Your endpoint logic
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the function first
            result = await func(*args, **kwargs)

            try:
                # Extract user_id from arguments
                user_id = None
                if extract_user_id:
                    # Try to extract from args or kwargs
                    for arg in args:
                        if hasattr(arg, '__dict__'):
                            user_id = extract_user_id(arg)
                            if user_id:
                                break
                    if not user_id and kwargs:
                        user_id = extract_user_id(kwargs)

                if not user_id:
                    # Try common patterns
                    for arg in args:
                        if isinstance(arg, dict) and 'user_id' in arg:
                            user_id = arg['user_id']
                            break
                        if hasattr(arg, 'user_id'):
                            user_id = arg.user_id
                            break

                if user_id:
                    # Extract field, old value, new value
                    field_changed = extract_field(*args, result) if extract_field else None
                    old_value = extract_old_value(*args) if extract_old_value else None
                    new_value = extract_new_value(result) if extract_new_value else None

                    # Log the event
                    await behavioral_tracking_service.log_event(
                        user_id=user_id,
                        event_type=event_type,
                        field_changed=field_changed,
                        old_value=old_value,
                        new_value=new_value
                    )

                    logger.info(f"Logged {event_type.value} for user {user_id}")

            except Exception as e:
                # Don't fail the request if logging fails
                logger.error(f"Failed to log behavior: {e}")

            return result

        return wrapper
    return decorator


async def log_profile_update(
    user_id: str,
    field: str,
    old_value: Any,
    new_value: Any
):
    """
    Helper function to log profile updates
    """
    # Determine event type based on field
    event_type_map = {
        'real_name': EventType.REAL_NAME_CHANGE,
        'annual_income_range': EventType.INCOME_CHANGE,
        'education_level': EventType.EDUCATION_CHANGE,
        'university_name': EventType.EDUCATION_CHANGE,
        'photo_url': EventType.PHOTO_CHANGE,
        'profile_photo_url': EventType.PHOTO_CHANGE,
    }

    event_type = event_type_map.get(field, EventType.PROFILE_EDIT)

    await behavioral_tracking_service.log_event(
        user_id=user_id,
        event_type=event_type,
        field_changed=field,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None
    )


async def log_answer_change(
    user_id: str,
    question_id: str,
    old_answer: Optional[str],
    new_answer: str,
    is_rewrite: bool = False
):
    """
    Helper function to log answer changes
    """
    event_type = EventType.ANSWER_REWRITE if is_rewrite else EventType.ANSWER_CHANGE

    await behavioral_tracking_service.log_event(
        user_id=user_id,
        event_type=event_type,
        field_changed=f"question_{question_id}",
        old_value=old_answer,
        new_value=new_answer,
        event_data={'question_id': question_id}
    )


async def log_document_upload(
    user_id: str,
    document_type: str,
    document_id: str
):
    """
    Helper function to log document uploads
    """
    await behavioral_tracking_service.log_event(
        user_id=user_id,
        event_type=EventType.DOCUMENT_UPLOAD,
        field_changed=document_type,
        event_data={
            'document_type': document_type,
            'document_id': document_id
        }
    )


async def log_match_action(
    user_id: str,
    match_user_id: str,
    action: str  # 'view', 'like', 'skip', 'reshuffle'
):
    """
    Helper function to log match actions
    """
    await behavioral_tracking_service.log_event(
        user_id=user_id,
        event_type=EventType.MATCH_ACTION,
        field_changed=action,
        event_data={
            'match_user_id': match_user_id,
            'action': action
        }
    )
