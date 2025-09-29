#!/usr/bin/env python3
"""
Simplified test server for streaming functionality
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import uuid
from datetime import datetime

app = FastAPI(title="PDF RAG Test Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data storage
chats = {}
messages = {}

@app.get("/")
async def root():
    return {"message": "PDF RAG Test Server", "status": "healthy"}

@app.get("/health")
async def health():
    return {"status": "healthy", "services": {"api": "running"}}

@app.post("/api/chat/document/{document_id}/get-or-create")
async def get_or_create_chat(document_id: str):
    """Mock endpoint to create/get chat"""
    chat_id = f"chat-{document_id}"
    if chat_id not in chats:
        chats[chat_id] = {
            "chat_id": chat_id,
            "user_id": "test-user",
            "document_id": document_id,
            "title": f"Chat for Document {document_id}",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        messages[chat_id] = []

    return chats[chat_id]

@app.get("/api/chat/{chat_id}")
async def get_chat_messages(chat_id: str):
    """Get chat messages"""
    if chat_id not in messages:
        raise HTTPException(status_code=404, detail="Chat not found")

    return {
        "chat_id": chat_id,
        "user_id": "test-user",
        "document_id": chats[chat_id]["document_id"],
        "title": chats[chat_id]["title"],
        "created_at": chats[chat_id]["created_at"],
        "updated_at": chats[chat_id]["updated_at"],
        "messages": messages[chat_id]
    }

@app.post("/api/chat/{chat_id}/messages/stream")
async def send_message_stream(chat_id: str, message_data: dict):
    """Streaming chat endpoint"""
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")

    user_message = message_data.get("message", "")

    # Add user message
    user_msg = {
        "message_id": str(uuid.uuid4()),
        "chat_id": chat_id,
        "role": "user",
        "content": user_message,
        "created_at": datetime.utcnow().isoformat()
    }
    messages[chat_id].append(user_msg)

    async def generate_stream():
        # Send metadata
        yield f"data: {json.dumps({'type': 'metadata', 'sources': ['Source 1', 'Source 2'], 'context_chunks': []})}\n\n"

        # Simulate streaming response
        response_parts = [
            "This is a ",
            "streaming response ",
            "that demonstrates ",
            "how the chat ",
            "will work in real-time. ",
            "Each word appears ",
            "as it's generated, ",
            "creating a more ",
            "natural conversation ",
            "experience for users."
        ]

        for part in response_parts:
            yield f"data: {json.dumps({'type': 'content', 'content': part})}\n\n"
            await asyncio.sleep(0.1)  # Simulate processing delay

        # Send completion signal
        yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

        # Add assistant message to storage
        assistant_msg = {
            "message_id": str(uuid.uuid4()),
            "chat_id": chat_id,
            "role": "assistant",
            "content": "".join(response_parts),
            "created_at": datetime.utcnow().isoformat()
        }
        messages[chat_id].append(assistant_msg)

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
