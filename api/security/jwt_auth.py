"""JWT authentication and authorization middleware for Samanvay.
Implements HS256 JWT encoding, decoding, maker-checker validation, and role/domain checks.
"""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from api.config import get_settings

security_scheme = HTTPBearer(auto_error=False)


class AuthUser(BaseModel):
    """Authenticated user context extracted from JWT claims."""

    sub: str = Field(..., description="User identifier (UUID or subject)")
    org_id: str = Field(..., description="Tenant organization ID")
    role: str = Field(..., description="Assigned user role")
    domains: list[str] = Field(default_factory=list, description="Domain tags for safety-critical checks")
    display_name: str | None = None


def create_access_token(
    sub: str,
    org_id: str,
    role: str,
    domains: list[str] | None = None,
    display_name: str | None = None,
    expires_in_hours: int = 24,
) -> str:
    """Generate HS256 signed JWT token."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "org_id": org_id,
        "role": role,
        "domains": domains or [],
        "display_name": display_name or sub,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=expires_in_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> AuthUser:
    """Decode and validate HS256 JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return AuthUser(
            sub=payload["sub"],
            org_id=payload["org_id"],
            role=payload["role"],
            domains=payload.get("domains", []),
            display_name=payload.get("display_name"),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Authentication token has expired."},
        )
    except (jwt.InvalidTokenError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid authentication token."},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security_scheme),
) -> AuthUser:
    """FastAPI dependency to extract and authenticate current user from Bearer header."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_CREDENTIALS", "message": "Bearer token required in Authorization header."},
        )
    return decode_access_token(credentials.credentials)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Security(security_scheme),
) -> AuthUser | None:
    """FastAPI dependency to optionally extract user context if credentials present."""
    if not credentials:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except HTTPException:
        return None



def require_role(*allowed_roles: str):
    """Dependency factory restricting access to specified roles."""

    async def role_checker(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_ROLE",
                    "message": f"Role '{current_user.role}' is not authorized. Allowed: {list(allowed_roles)}.",
                },
            )
        return current_user

    return role_checker


def require_domain(*required_domains: str):
    """Dependency factory verifying Checker has required domain tag for safety-critical operations."""

    async def domain_checker(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
        user_domains = set(current_user.domains)
        missing = [d for d in required_domains if d not in user_domains]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "DOMAIN_TAG_REQUIRED",
                    "required": list(required_domains),
                    "message": f"Approval requires domain tag(s): {missing}.",
                },
            )
        return current_user

    return domain_checker


def verify_maker_checker(proposer_sub: str, approver_sub: str) -> None:
    """Enforce Maker != Checker invariant (Section 4.7, 9.4)."""
    if proposer_sub == approver_sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "MAKER_CHECKER_VIOLATION",
                "message": "The approver must differ from the proposer.",
            },
        )
