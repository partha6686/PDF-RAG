from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import uuid
from datetime import datetime

from app.core.auth import get_current_user
from app.models.schemas import (
    ChatCreate, ChatInfo, ChatListResponse, ChatWithMessages,
    ChatMessageCreate, ChatMessageInfo, ChatMessage, ChatResponse
)
from app.models.database import get_db, Document as DBDocument, Chat as DBChat, ChatMessage as DBChatMessage

router = APIRouter()

@router.post("/", response_model=ChatInfo)
async def create_chat(
    chat_data: ChatCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat for a document"""
    try:
        # Verify document exists and belongs to user
        document = db.query(DBDocument).filter(
            DBDocument.document_id == chat_data.document_id,
            DBDocument.user_id == current_user["user_id"]
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Create chat
        chat_id = str(uuid.uuid4())
        db_chat = DBChat(
            chat_id=chat_id,
            user_id=current_user["user_id"],
            document_id=chat_data.document_id,
            title=chat_data.title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(db_chat)
        db.commit()
        db.refresh(db_chat)
        
        return ChatInfo.model_validate(db_chat)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat: {str(e)}"
        )

@router.get("/document/{document_id}", response_model=ChatListResponse)
async def list_document_chats(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all chats for a specific document"""
    try:
        # Verify document exists and belongs to user
        document = db.query(DBDocument).filter(
            DBDocument.document_id == document_id,
            DBDocument.user_id == current_user["user_id"]
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Get chats for document
        chats = db.query(DBChat).filter(
            DBChat.document_id == document_id,
            DBChat.user_id == current_user["user_id"]
        ).order_by(DBChat.updated_at.desc()).all()
        
        chat_list = [ChatInfo.model_validate(chat) for chat in chats]
        
        return ChatListResponse(
            chats=chat_list,
            total=len(chat_list)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chats: {str(e)}"
        )

@router.get("/{chat_id}", response_model=ChatWithMessages)
async def get_chat_with_messages(
    chat_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat with all messages"""
    try:
        # Find chat
        chat = db.query(DBChat).filter(
            DBChat.chat_id == chat_id,
            DBChat.user_id == current_user["user_id"]
        ).first()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        # Get messages
        messages = db.query(DBChatMessage).filter(
            DBChatMessage.chat_id == chat_id
        ).order_by(DBChatMessage.created_at.asc()).all()
        
        chat_data = ChatInfo.model_validate(chat)
        message_list = [ChatMessageInfo.model_validate(msg) for msg in messages]
        
        return ChatWithMessages(
            **chat_data.model_dump(),
            messages=message_list
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat: {str(e)}"
        )

@router.post("/{chat_id}/messages", response_model=ChatResponse)
async def send_message(
    chat_id: str,
    message: ChatMessage,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message in a chat and get AI response"""
    try:
        # Find chat
        chat = db.query(DBChat).filter(
            DBChat.chat_id == chat_id,
            DBChat.user_id == current_user["user_id"]
        ).first()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        # Get document
        document = db.query(DBDocument).filter(
            DBDocument.document_id == chat.document_id
        ).first()
        
        # Store user message
        user_message_id = str(uuid.uuid4())
        user_message = DBChatMessage(
            message_id=user_message_id,
            chat_id=chat_id,
            role="user",
            content=message.message,
            created_at=datetime.utcnow()
        )
        db.add(user_message)
        
        # TODO: Get AI response using document context
        # For now, return a simple response
        ai_response = f"I received your message: '{message.message}'. AI response functionality will be implemented soon."
        context_chunks = []
        
        # Store AI response
        ai_message_id = str(uuid.uuid4())
        ai_message = DBChatMessage(
            message_id=ai_message_id,
            chat_id=chat_id,
            role="assistant",
            content=ai_response,
            sources=None,  # TODO: Add sources from context chunks
            created_at=datetime.utcnow()
        )
        db.add(ai_message)
        
        # Update chat timestamp
        chat.updated_at = datetime.utcnow()
        db.add(chat)
        
        db.commit()
        
        return ChatResponse(
            response=ai_response,
            context_chunks=context_chunks,
            sources=[]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )

@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a chat and all its messages"""
    try:
        # Find chat
        chat = db.query(DBChat).filter(
            DBChat.chat_id == chat_id,
            DBChat.user_id == current_user["user_id"]
        ).first()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        # Delete all messages
        db.query(DBChatMessage).filter(
            DBChatMessage.chat_id == chat_id
        ).delete()
        
        # Delete chat
        db.delete(chat)
        db.commit()
        
        return {
            "message": f"Chat {chat_id} deleted successfully",
            "chat_id": chat_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat: {str(e)}"
        )