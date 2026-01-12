"""
Authentication router.
"""
from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import DbSession, CurrentUser
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: DbSession):
    """
    Authenticate and get access token.
    
    - **username**: Admin username
    - **password**: Admin password
    """
    user = await auth_service.authenticate_user(db, request.username, request.password)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    # Update last login time
    await auth_service.update_last_login(db, user)
    
    # Create token
    token_response = await auth_service.create_user_token(user)
    
    return token_response


@router.post("/logout")
async def logout(current_user: CurrentUser):
    """
    Logout current user.
    
    Note: JWT tokens are stateless, so this endpoint just confirms logout.
    Client should discard the token.
    """
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """
    Get current authenticated user information.
    """
    return current_user
