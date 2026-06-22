"""User Authentication and Session Management Router."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import User, Session as UserSession

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Define OAuth2 scheme (reads from Authorization: Bearer <token> header)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)


# ── Password Hashing Helpers ──────────────────────────────────────────────────

def generate_salt() -> str:
    """Generate a random hex salt."""
    return secrets.token_hex(16)


def hash_password(password: str, salt: str) -> str:
    """Hash password using PBKDF2-SHA256 with 100,000 iterations."""
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    )
    return pwd_hash.hex()


# ── Dependency – Get Current User ─────────────────────────────────────────────

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Verify session token and return current User. Raises 401 if invalid."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Session token missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Lookup active session
    stmt = select(UserSession).where(UserSession.id == token)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if session.expires_at < datetime.utcnow():
        # Clean up expired session
        await db.delete(session)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get associated User
    stmt = select(User).where(User.id == session.user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user does not exist.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ── Pydantic Request/Response Schemas ─────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters.")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    # Check if email is already taken
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    existing_user = res.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    # Create new User
    salt = generate_salt()
    hashed_pwd = hash_password(payload.password, salt)

    new_user = User(
        email=payload.email,
        hashed_password=hashed_pwd,
        salt=salt,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    return new_user


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Log in with email and password, returning a 7-day session token."""
    # Find user by email
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Validate password
    hashed_input = hash_password(payload.password, user.salt)
    if hashed_input != user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Create session token
    session_id = uuid.uuid4().hex
    expires_at = datetime.utcnow() + timedelta(days=7)

    session = UserSession(
        id=session_id,
        user_id=user.id,
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()

    return {
        "access_token": session_id,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/logout")
async def logout(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke (delete) the active session token."""
    if token:
        stmt = select(UserSession).where(UserSession.id == token)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if session:
            await db.delete(session)
            await db.commit()

    return {"message": "Logged out successfully."}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get the currently logged-in user's details."""
    return current_user
