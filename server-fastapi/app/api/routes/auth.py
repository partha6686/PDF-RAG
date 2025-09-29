from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.core.auth import jwt_auth, get_current_user
from app.models.schemas import User
from app.models.database import get_db

router = APIRouter()

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    name: str = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

@router.post("/signup", response_model=Token)
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """Create a new user account"""
    try:
        user = jwt_auth.create_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            name=user_data.name
        )
        
        # Create access token
        token_data = {
            "sub": user["user_id"],
            "email": user["email"],
            "name": user["name"]
        }
        access_token = jwt_auth.create_access_token(token_data)
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=user
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signup failed: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return access token"""
    user = jwt_auth.authenticate_user(db, user_data.email, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create access token
    token_data = {
        "sub": user["user_id"],
        "email": user["email"],
        "name": user["name"]
    }
    access_token = jwt_auth.create_access_token(token_data)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user
    )

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user information"""
    return User(
        user_id=current_user["user_id"],
        email=current_user["email"],
        name=current_user["name"]
    )

@router.post("/logout")
async def logout():
    """Logout user (client should remove token)"""
    return {"message": "Successfully logged out. Please remove the token from client."}