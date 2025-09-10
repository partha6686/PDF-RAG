from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.core.config import settings

# Database setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    documents = relationship("Document", back_populates="user")
    chats = relationship("Chat", back_populates="user")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    s3_key = Column(String, nullable=False)  # MinIO/S3 object key
    processing_status = Column(String, default="pending")  # pending, processing, completed, failed
    chunk_count = Column(Integer, default=0)
    qdrant_collection = Column(String, nullable=False)  # Collection name in Qdrant
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    chats = relationship("Chat", back_populates="document")

class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False, index=True)
    title = Column(String, nullable=False)  # Auto-generated or user-provided title
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="chats")
    document = relationship("Document", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, index=True, nullable=False)
    chat_id = Column(String, ForeignKey("chats.chat_id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)  # JSON string of source chunks
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()