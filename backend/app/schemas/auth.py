"""
Authentication schemas.
"""
from pydantic import BaseModel, Field
from datetime import datetime


class LoginRequest(BaseModel):
    """Login request body."""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class UserResponse(BaseModel):
    """User information response."""
    id: int
    username: str
    last_login_at: datetime | None
    created_at: datetime
    
    model_config = {"from_attributes": True}
