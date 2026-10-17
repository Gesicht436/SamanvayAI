"""Authentication and demo token endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.config import get_settings
from api.security.jwt_auth import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


class DemoTokenRequest(BaseModel):
    sub: str = Field(default="demo-user", min_length=1, max_length=100)


class DemoTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    sub: str
    org_id: str
    role: str
    domains: list[str]


@router.post("/demo-token", response_model=DemoTokenResponse)
def generate_demo_token(req: DemoTokenRequest):
    """Generate a signed HS256 JWT token for demo and testing workflows."""
    settings = get_settings()
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="Not found")
    if req.sub != "demo-user":
        raise HTTPException(status_code=400, detail="Demo subject is fixed.")
    token = create_access_token(
        sub=req.sub,
        org_id=settings.demo_org_id,
        role="MAKER",
        domains=["COMMON"],
        display_name="Demo Operator",
    )
    return DemoTokenResponse(
        access_token=token,
        sub=req.sub,
        org_id=settings.demo_org_id,
        role="MAKER",
        domains=["COMMON"],
    )
