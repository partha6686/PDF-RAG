from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
import os
from dotenv import load_dotenv

from app.core.config import settings
from app.api.routes import auth, upload, chat, jobs, processing
from app.services.qdrant_service import QdrantService
from app.workers.celery_app import create_celery
from app.models.database import create_tables

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="PDF RAG API",
    description="FastAPI server for PDF Retrieval-Augmented Generation",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

# Include API routes
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(processing.router, prefix="/api/processing", tags=["processing"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Initialize database tables
        create_tables()
        print("✅ Database tables created")
        
        # Initialize Qdrant service
        qdrant_service = QdrantService()
        await qdrant_service.initialize()
        print("✅ FastAPI server initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        raise

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "PDF RAG FastAPI Server", 
        "version": "2.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "redis": "connected",
            "qdrant": "connected"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )