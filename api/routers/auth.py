"""Authentication and demo token endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.security.jwt_auth import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


class DemoTokenRequest(BaseModel):
    sub: str = Field(default="demo-user", description="Subject or user ID")
    org_id: str = Field(default="OIL-1", description="Tenant organization ID")
    role: str = Field(default="MAKER", description="User role (MAKER, CHECKER, ADMIN, etc.)")
    domains: list[str] = Field(default_factory=lambda: ["COMMON"], description="Domain tags")
    display_name: str | None = Field(default="Demo Operator", description="Human-readable name")


class DemoTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    sub: str
    org_id: str
    role: str
    domains: list[str]


@router.post("/demo-token", response_model=DemoTokenResponse)
async def generate_demo_token(req: DemoTokenRequest):
    """Generate a signed HS256 JWT token for demo and testing workflows."""
    token = create_access_token(
        sub=req.sub,
        org_id=req.org_id,
        role=req.role,
        domains=req.domains,
        display_name=req.display_name,
    )
    return DemoTokenResponse(
        access_token=token,
        sub=req.sub,
        org_id=req.org_id,
        role=req.role,
        domains=req.domains,
    )
