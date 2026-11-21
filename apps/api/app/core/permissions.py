from collections.abc import Callable
from enum import StrEnum
from typing import Any

from fastapi import Depends, HTTPException, status

from app.models.user import User, UserRole


class Permission(StrEnum):
    ASSETS_UPLOAD = "assets:upload"
    ASSETS_EDIT_ANY = "assets:edit_any"
    ASSETS_EDIT_OWN = "assets:edit_own"
    ASSETS_EDIT_METADATA = "assets:edit_metadata"
    CLAIMS_VERIFY = "claims:verify"
    SEARCH_USE = "search:use"
    AI_USE = "ai:use"
    EXPORTS_FULL = "exports:full"
    EXPORTS_WATERMARKED = "exports:watermarked"
    AUDIT_VIEW = "audit:view"
    USERS_MANAGE = "users:manage"


ROLE_PERMISSIONS_MATRIX: dict[UserRole, set[str]] = {
    UserRole.SUPER_ADMIN: {
        Permission.ASSETS_UPLOAD,
        Permission.ASSETS_EDIT_ANY,
        Permission.ASSETS_EDIT_OWN,
        Permission.ASSETS_EDIT_METADATA,
        Permission.CLAIMS_VERIFY,
        Permission.SEARCH_USE,
        Permission.AI_USE,
        Permission.EXPORTS_FULL,
        Permission.EXPORTS_WATERMARKED,
        Permission.AUDIT_VIEW,
        Permission.USERS_MANAGE,
    },
    UserRole.ADMIN: {
        Permission.ASSETS_UPLOAD,
        Permission.ASSETS_EDIT_ANY,
        Permission.ASSETS_EDIT_OWN,
        Permission.ASSETS_EDIT_METADATA,
        Permission.CLAIMS_VERIFY,
        Permission.SEARCH_USE,
        Permission.AI_USE,
        Permission.EXPORTS_FULL,
        Permission.EXPORTS_WATERMARKED,
        Permission.AUDIT_VIEW,
        Permission.USERS_MANAGE,
    },
    UserRole.RESEARCHER: {
        Permission.ASSETS_UPLOAD,
        Permission.ASSETS_EDIT_OWN,
        Permission.ASSETS_EDIT_METADATA,
        Permission.SEARCH_USE,
        Permission.AI_USE,
        Permission.EXPORTS_FULL,
        Permission.EXPORTS_WATERMARKED,
    },
    UserRole.REVIEWER: {
        Permission.CLAIMS_VERIFY,
        Permission.ASSETS_EDIT_METADATA,
        Permission.SEARCH_USE,
        Permission.AI_USE,
        Permission.EXPORTS_WATERMARKED,
    },
    UserRole.CONTRIBUTOR: {
        Permission.ASSETS_UPLOAD,
        Permission.ASSETS_EDIT_OWN,
        Permission.SEARCH_USE,
        Permission.EXPORTS_WATERMARKED,
    },
    UserRole.VIEWER: {
        Permission.SEARCH_USE,
        Permission.EXPORTS_WATERMARKED,
    },
}


def has_permission(role: UserRole, permission: str) -> bool:
    """Check if the specified role possesses the required permission."""
    perms = ROLE_PERMISSIONS_MATRIX.get(role, set())
    return permission in perms


def get_role_permissions(role: UserRole) -> list[str]:
    """Return all permissions granted to a given role sorted alphabetically."""
    return sorted(ROLE_PERMISSIONS_MATRIX.get(role, set()))


def require_permission(permission: str) -> Callable[..., Any]:
    """FastAPI dependency factory enforcing that the authenticated user possesses the permission."""
    from app.core.auth import get_current_user

    async def permission_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: missing '{permission}'",
            )
        return current_user

    return permission_checker
