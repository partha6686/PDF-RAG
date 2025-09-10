from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import uuid
import json
from datetime import datetime

from app.core.auth import get_current_user
from app.models.schemas import (
    ChatCreate, ChatInfo, ChatListResponse, ChatWithMessages,
    ChatMessageCreate, ChatMessageInfo, ChatMessage, ChatResponse
)
from app.models.database import get_db, Document as DBDocument, Chat as DBChat, ChatMessage as DBChatMessage
from app.services.chat_service import ChatService

router = APIRouter()

@router.post("/", response_model=ChatInfo)
async def create_chat(
    chat_data: ChatCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or get existing chat for a document (one chat per document)"""
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

        # Check if chat already exists for this document
        existing_chat = db.query(DBChat).filter(
            DBChat.document_id == chat_data.document_id,
            DBChat.user_id == current_user["user_id"]
        ).first()

        if existing_chat:
            # Return existing chat
            return ChatInfo.model_validate(existing_chat)

        # Create new chat with auto-generated title from document name
        chat_id = str(uuid.uuid4())
        # Remove file extension and use document name as title
        document_title = document.original_name.rsplit('.', 1)[0] if '.' in document.original_name else document.original_name

        db_chat = DBChat(
            chat_id=chat_id,
            user_id=current_user["user_id"],
            document_id=chat_data.document_id,
            title=document_title,
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

@router.get("/document/{document_id}/get-or-create", response_model=ChatInfo)
async def get_or_create_document_chat(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get or create the single chat for a document"""
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

        # Check if chat already exists for this document
        existing_chat = db.query(DBChat).filter(
            DBChat.document_id == document_id,
            DBChat.user_id == current_user["user_id"]
        ).first()

        if existing_chat:
            # Return existing chat
            return ChatInfo.model_validate(existing_chat)

        # Create new chat with auto-generated title from document name
        chat_id = str(uuid.uuid4())
        # Remove file extension and use document name as title
        document_title = document.original_name.rsplit('.', 1)[0] if '.' in document.original_name else document.original_name

        db_chat = DBChat(
            chat_id=chat_id,
            user_id=current_user["user_id"],
            document_id=document_id,
            title=document_title,
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
            detail=f"Failed to get or create chat: {str(e)}"
        )

@router.get("/document/{document_id}", response_model=ChatListResponse)
async def list_document_chats(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all chats for a specific document (legacy endpoint - now returns single chat)"""
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

        # Get the single chat for document
        chat = db.query(DBChat).filter(
            DBChat.document_id == document_id,
            DBChat.user_id == current_user["user_id"]
        ).first()

        chat_list = [ChatInfo.model_validate(chat)] if chat else []

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
    """Send a message in a chat and get AI response using RAG"""
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

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Check if document is processed
        if document.processing_status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document is not ready for chat. Please wait for processing to complete."
            )

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

        # Get chat history for context (last 10 messages)
        chat_history = db.query(DBChatMessage).filter(
            DBChatMessage.chat_id == chat_id
        ).order_by(DBChatMessage.created_at.desc()).limit(10).all()

        # Convert to format expected by ChatService
        history_for_ai = []
        for msg in reversed(chat_history):  # Reverse to get chronological order
            history_for_ai.append({
                "role": msg.role,
                "content": msg.content
            })

        # Initialize ChatService and generate AI response
        chat_service = ChatService()
        ai_result = await chat_service.generate_response(
            document_id=document.document_id,
            user_message=message.message,
            chat_history=history_for_ai
        )

        # Store AI response
        ai_message_id = str(uuid.uuid4())
        ai_message = DBChatMessage(
            message_id=ai_message_id,
            chat_id=chat_id,
            role="assistant",
            content=ai_result["response"],
            sources=json.dumps(ai_result.get("sources", [])),
            created_at=datetime.utcnow()
        )
        db.add(ai_message)

        # Update chat timestamp
        chat.updated_at = datetime.utcnow()
        db.add(chat)

        db.commit()

        return ChatResponse(
            response=ai_result["response"],
            context_chunks=ai_result.get("context_chunks", []),
            sources=ai_result.get("sources", [])
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )

@router.post("/{chat_id}/messages/stream")
async def send_message_stream(
    chat_id: str,
    message: ChatMessage,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message in a chat and get streaming AI response using RAG"""
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

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Check if document is processed
        if document.processing_status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document is not ready for chat. Please wait for processing to complete."
            )

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
        db.commit()  # Commit user message first

        # Get chat history for context (last 10 messages including the one we just added)
        chat_history = db.query(DBChatMessage).filter(
            DBChatMessage.chat_id == chat_id
        ).order_by(DBChatMessage.created_at.desc()).limit(10).all()

        # Convert to format expected by ChatService
        history_for_ai = []
        for msg in reversed(chat_history):  # Reverse to get chronological order
            history_for_ai.append({
                "role": msg.role,
                "content": msg.content
            })

        # Initialize ChatService and generate streaming AI response
        chat_service = ChatService()

        async def generate_stream():
            full_response = ""
            sources = []
            context_chunks = []

            async for chunk in chat_service.generate_response_stream(
                document_id=document.document_id,
                user_message=message.message,
                chat_history=history_for_ai
            ):
                if chunk["type"] == "metadata":
                    sources = chunk.get("sources", [])
                    context_chunks = chunk.get("context_chunks", [])
                    # Convert EmbeddingResult objects to dictionaries for JSON serialization
                    serializable_chunk = {
                        "type": chunk["type"],
                        "sources": sources,
                        "context_chunks": [
                            {
                                "chunk_id": c.chunk_id,
                                "score": c.score,
                                "text": c.text,
                                "document_id": c.document_id,
                                "chunk_index": c.chunk_index
                            } for c in context_chunks
                        ]
                    }
                    # Send metadata as JSON
                    yield f"data: {json.dumps(serializable_chunk)}\n\n"

                elif chunk["type"] == "content":
                    full_response += chunk["content"]
                    # Send content chunk as JSON
                    yield f"data: {json.dumps(chunk)}\n\n"

                elif chunk["type"] == "done":
                    # Store the complete AI response in database
                    ai_message_id = str(uuid.uuid4())
                    ai_message = DBChatMessage(
                        message_id=ai_message_id,
                        chat_id=chat_id,
                        role="assistant",
                        content=full_response,
                        sources=json.dumps(sources),
                        created_at=datetime.utcnow()
                    )
                    db.add(ai_message)

                    # Update chat timestamp
                    chat.updated_at = datetime.utcnow()
                    db.add(chat)
                    db.commit()

                    # Send completion signal
                    yield f"data: {json.dumps(chunk)}\n\n"

                elif chunk["type"] == "error":
                    # Store error message in database
                    ai_message_id = str(uuid.uuid4())
                    ai_message = DBChatMessage(
                        message_id=ai_message_id,
                        chat_id=chat_id,
                        role="assistant",
                        content=chunk["content"],
                        created_at=datetime.utcnow()
                    )
                    db.add(ai_message)
                    db.commit()

                    # Send error as JSON
                    yield f"data: {json.dumps(chunk)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )

@router.get("/debug/document/{document_id}")
async def debug_document_status(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check document processing status and vector search"""
    try:
        # Get document
        document = db.query(DBDocument).filter(
            DBDocument.document_id == document_id,
            DBDocument.user_id == current_user["user_id"]
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Check Qdrant collection
        from app.services.qdrant_service import QdrantService
        qdrant_service = QdrantService()
        collection_exists = await qdrant_service.collection_exists(document_id)

        # Test vector search with a simple query
        test_results = []
        if collection_exists and document.processing_status == "completed":
            try:
                from app.services.embedding_service import EmbeddingService
                embedding_service = EmbeddingService()
                test_embedding = await embedding_service.generate_query_embedding("test query")
                test_results = await qdrant_service.search_similar_chunks(
                    document_id=document_id,
                    query_embedding=test_embedding,
                    limit=3
                )
            except Exception as e:
                test_results = [{"error": str(e)}]

        return {
            "document_id": document_id,
            "processing_status": document.processing_status,
            "chunk_count": document.chunk_count,
            "created_at": document.created_at.isoformat(),
            "processed_at": document.processed_at.isoformat() if document.processed_at else None,
            "collection_exists": collection_exists,
            "test_search_results": len(test_results) if isinstance(test_results, list) else 0,
            "test_results": test_results[:2] if isinstance(test_results, list) else test_results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug failed: {str(e)}"
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
