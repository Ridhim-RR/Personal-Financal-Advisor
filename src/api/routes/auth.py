from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.auth import create_access_token, hash_password, verify_password
from src.api.deps import get_user_service
from src.services.user_profile_service import UserProfileService

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
async def register(body: RegisterRequest, svc: UserProfileService = Depends(get_user_service)):
    existing = svc.get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = svc.create_user(email=body.email, password_hash=hash_password(body.password))
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer", "user_id": user.id}


@router.post("/login")
async def login(body: LoginRequest, svc: UserProfileService = Depends(get_user_service)):
    user = svc.get_user_by_email(body.email)
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer", "user_id": user.id}


@router.post("/logout")
async def logout():
    return {"message": "Logout successful — discard the token on the client"}
