from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.permissions import get_role_permissions
from app.models.user import User

router = APIRouter(tags=["auth"])


class UserMeResponse(BaseModel):
    id: str
    clerk_user_id: str
    email: str
    full_name: str | None
    role: str
    is_active: bool
    permissions: list[str]


@router.get("/me", response_model=UserMeResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Retrieve current authenticated user profile and effective permissions."""
    return {
        "id": str(current_user.id),
        "clerk_user_id": current_user.clerk_user_id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "permissions": get_role_permissions(current_user.role),
    }
