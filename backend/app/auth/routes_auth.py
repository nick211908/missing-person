from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

from app.database.db import get_db
from app.models.user import User
from app.auth.auth import (
    hash_password, verify_password,
    create_access_token, get_current_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─── Schemas ──────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[str] = "officer"   # "admin" or "officer"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Endpoints ────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user. First registered user becomes admin automatically."""
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, detail="Username already taken.")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(400, detail="Email already registered.")

    # First ever user gets admin role
    role = "admin" if db.query(User).count() == 0 else body.role

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with username + password. Returns a JWT access token."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(400, detail="Account is disabled.")

    token = create_access_token(data={"sub": user.username, "role": user.role})
    return TokenResponse(access_token=token, username=user.username, role=user.role)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the currently authenticated user's profile."""
    return current_user
