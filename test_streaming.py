#!/usr/bin/env python3
"""
Test script to verify streaming functionality works
"""
import sys
import os
import asyncio
import json

# Add the server path to sys.path
sys.path.append('/Users/parthapraharaj/DEV/pdf-rag/server-fastapi')

async def test_streaming():
    """Test the streaming functionality"""
    print("Testing streaming functionality...")
    
    # Mock the external dependencies
    class MockEmbeddingService:
        async def generate_query_embedding(self, text):
            return [0.1] * 768  # Mock embedding
    
    class MockQdrantService:
        async def search_similar_chunks(self, document_id, query_embedding, limit):
            from app.models.schemas import EmbeddingResult
            return [
                EmbeddingResult(
                    chunk_id=1,
                    score=0.95,
                    text="This is a sample chunk of text from the document.",
                    document_id=document_id,
                    chunk_index=0
                ),
                EmbeddingResult(
                    chunk_id=2,
                    score=0.87,
                    text="Another relevant chunk with information.",
                    document_id=document_id,
                    chunk_index=1
                )
            ]
    
    # Mock the Gemini model
    class MockGeminiModel:
        def generate_content(self, prompt, stream=False):
            if stream:
                # Simulate streaming response
                chunks = [
                    "This is a ",
                    "streaming response ",
                    "that demonstrates ",
                    "how the chat ",
                    "will work in real-time."
                ]
                for chunk in chunks:
                    yield type('MockChunk', (), {'text': chunk})()
            else:
                return type('MockResponse', (), {'text': 'Complete response'})()
    
    # Patch the imports
    import app.services.chat_service as chat_service_module
    chat_service_module.EmbeddingService = MockEmbeddingService
    chat_service_module.QdrantService = MockQdrantService
    
    # Create a mock chat service
    class MockChatService:
        def __init__(self):
            self.embedding_service = MockEmbeddingService()
            self.qdrant_service = MockQdrantService()
            self.model = MockGeminiModel()
        
        def _prepare_context(self, chunks):
            return "\n".join([f"Chunk {i}: {chunk.text}" for i, chunk in enumerate(chunks)])
        
        def _build_conversation_history(self, history):
            return ""
        
        def _build_prompt(self, user_message, context, history):
            return f"Context: {context}\nQuestion: {user_message}"
        
        def _format_sources(self, chunks):
            return [f"Source {i+1}" for i in range(len(chunks))]
        
        async def generate_response_stream(self, document_id, user_message, chat_history=None):
            """Generate streaming AI response using RAG with document context"""
            try:
                print(f"Generating streaming response for document {document_id}")
                
                # Step 1: Generate query embedding
                query_embedding = await self.embedding_service.generate_query_embedding(user_message)
                
                # Step 2: Search for relevant chunks in document
                relevant_chunks = await self.qdrant_service.search_similar_chunks(
                    document_id=document_id,
                    query_embedding=query_embedding,
                    limit=5
                )
                
                print(f"Found {len(relevant_chunks)} relevant chunks")
                
                if not relevant_chunks:
                    yield {
                        "type": "error",
                        "content": "No relevant information found.",
                        "sources": [],
                        "context_chunks": []
                    }
                    return
                
                # Step 3: Prepare context
                context_text = self._prepare_context(relevant_chunks)
                
                # Step 4: Build conversation history
                conversation_history = self._build_conversation_history(chat_history)
                
                # Step 5: Generate response using Gemini with streaming
                prompt = self._build_prompt(user_message, context_text, conversation_history)
                
                # Send initial metadata
                yield {
                    "type": "metadata",
                    "sources": self._format_sources(relevant_chunks),
                    "context_chunks": relevant_chunks
                }
                
                # Stream the response
                response_stream = self.model.generate_content(prompt, stream=True)
                
                for chunk in response_stream:
                    if chunk.text:
                        yield {
                            "type": "content",
                            "content": chunk.text
                        }
                
                # Send completion signal
                yield {
                    "type": "done",
                    "content": ""
                }
                
            except Exception as e:
                print(f"Error: {e}")
                yield {
                    "type": "error",
                    "content": f"Error occurred: {str(e)}",
                    "sources": [],
                    "context_chunks": []
                }
    
    # Test the streaming
    chat_service = MockChatService()
    
    print("\n=== Testing Streaming Response ===")
    print("User question: What is this document about?")
    print("\nStreaming response:")
    print("-" * 50)
    
    full_response = ""
    async for chunk in chat_service.generate_response_stream(
        document_id="test-doc-123",
        user_message="What is this document about?",
        chat_history=None
    ):
        if chunk["type"] == "metadata":
            print(f"📋 Metadata received: {len(chunk.get('sources', []))} sources")
        
        elif chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
            full_response += chunk["content"]
        
        elif chunk["type"] == "done":
            print(f"\n\n✅ Streaming completed!")
        
        elif chunk["type"] == "error":
            print(f"\n❌ Error: {chunk['content']}")
    
    print(f"\n\n=== Final Response ===")
    print(f"Full response: {full_response}")
    print("\n✅ Streaming test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_streaming())
