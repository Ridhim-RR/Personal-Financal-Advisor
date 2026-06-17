from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.auth import create_access_token, decode_access_token, hash_password, verify_password
from src.services.user_profile_service import UserProfileService
from app.backend.database.connection import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme")
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    svc = UserProfileService(db)
    user = svc.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user_id


@router.post("/register", response_model=AuthResponse)
def register(req: AuthRequest, db: Session = Depends(get_db)):
    svc = UserProfileService(db)
    existing = svc.get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = svc.create_user(email=req.email, password_hash=hash_password(req.password))
    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user_id=user.id)


@router.post("/login", response_model=AuthResponse)
def login(req: AuthRequest, db: Session = Depends(get_db)):
    svc = UserProfileService(db)
    user = svc.get_user_by_email(req.email)
    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user_id=user.id)


@router.post("/logout")
def logout():
    return {"message": "Logged out"}
