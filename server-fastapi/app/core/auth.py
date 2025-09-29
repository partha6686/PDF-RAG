from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database import get_db, User as DBUser

# Security scheme
security = HTTPBearer()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class JWTAuth:
    """Simple JWT authentication handler"""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    
    def create_access_token(self, data: dict) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + self.access_token_expire
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def hash_password(self, password: str) -> str:
        """Hash password"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_user(self, db: Session, email: str, password: str, name: str = None) -> Dict[str, Any]:
        """Create new user in PostgreSQL"""
        
        # Check if user already exists
        existing_user = db.query(DBUser).filter(DBUser.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )
        
        # Create user
        user_id = f"user_{email.replace('@', '_').replace('.', '_')}"
        db_user = DBUser(
            user_id=user_id,
            email=email,
            name=name or email.split("@")[0],
            password_hash=self.hash_password(password)
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return {
            "user_id": db_user.user_id,
            "email": db_user.email,
            "name": db_user.name
        }
    
    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user from PostgreSQL"""
        db_user = db.query(DBUser).filter(DBUser.email == email).first()
        
        if not db_user:
            return None
        
        if not self.verify_password(password, db_user.password_hash):
            return None
        
        return {
            "user_id": db_user.user_id,
            "email": db_user.email,
            "name": db_user.name
        }

# Global auth instance
jwt_auth = JWTAuth()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Dependency to get current authenticated user"""
    try:
        payload = jwt_auth.verify_token(credentials.credentials)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "name": payload.get("name", "User")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """Optional user dependency (for public endpoints with optional auth)"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None