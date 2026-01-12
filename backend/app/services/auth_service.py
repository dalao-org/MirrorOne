"""
Authentication service.
"""
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.auth import TokenResponse


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> User | None:
    """
    Authenticate a user by username and password.
    
    Args:
        db: Database session
        username: Username to authenticate
        password: Plain text password
        
    Returns:
        User object if authenticated, None otherwise
    """
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if user is None:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    return user


async def create_user_token(user: User) -> TokenResponse:
    """
    Create a JWT token for a user.
    
    Args:
        user: User object
        
    Returns:
        TokenResponse with access token
    """
    token, expires_at = create_access_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at,
    )


async def update_last_login(db: AsyncSession, user: User) -> None:
    """
    Update user's last login timestamp.
    
    Args:
        db: Database session
        user: User object
    """
    user.last_login_at = datetime.now(UTC)
    await db.commit()


async def create_admin_user(db: AsyncSession, username: str, password: str) -> User:
    """
    Create an admin user.
    
    Args:
        db: Database session
        username: Admin username
        password: Plain text password
        
    Returns:
        Created User object
    """
    user = User(
        username=username,
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """
    Get a user by username.
    
    Args:
        db: Database session
        username: Username to look up
        
    Returns:
        User object or None
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()
