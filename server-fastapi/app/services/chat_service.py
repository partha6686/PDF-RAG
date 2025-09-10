import google.generativeai as genai
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime

from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)

class ChatService:
    """Service for RAG-based chat using Google Gemini 2.5 Flash"""
    
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model_name = "gemini-2.0-flash-exp"  # Latest Gemini 2.5 Flash
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService()
        
        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                top_p=0.8,
                top_k=40,
                max_output_tokens=2048,
            ),
            system_instruction="""You are an intelligent document assistant specialized in answering questions based on uploaded PDF documents. 

Key guidelines:
1. Answer questions using ONLY the provided context from the documents
2. If the answer is not in the context, clearly state "I cannot find this information in the uploaded document"
3. Be precise and cite specific parts of the document when possible
4. If asked about something not in the document, suggest what information IS available
5. Keep responses concise but comprehensive
6. Use a helpful and professional tone

When provided with context chunks, use them to formulate accurate answers based on the document content."""
        )
    
    async def generate_response(
        self, 
        document_id: str, 
        user_message: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Generate AI response using RAG with document context"""
        try:
            logger.info(f"Generating response for document {document_id}")
            
            # Step 1: Generate query embedding
            query_embedding = await self.embedding_service.generate_query_embedding(user_message)
            
            # Step 2: Search for relevant chunks in document
            relevant_chunks = await self.qdrant_service.search_similar_chunks(
                document_id=document_id,
                query_embedding=query_embedding,
                limit=5  # Get top 5 most relevant chunks
            )
            
            if not relevant_chunks:
                return {
                    "response": "I cannot find any relevant information in the uploaded document to answer your question. The document may not have been processed yet or may not contain information related to your query.",
                    "sources": [],
                    "context_used": False
                }
            
            # Step 3: Prepare context for the AI model
            context_text = self._prepare_context(relevant_chunks)
            
            # Step 4: Build conversation history
            conversation_history = self._build_conversation_history(chat_history)
            
            # Step 5: Generate response using Gemini
            prompt = self._build_prompt(user_message, context_text, conversation_history)
            
            response = await self._generate_with_gemini(prompt)
            
            # Step 6: Format sources
            sources = self._format_sources(relevant_chunks)
            
            logger.info(f"Successfully generated response for document {document_id}")
            
            return {
                "response": response,
                "sources": sources,
                "context_used": True,
                "context_chunks": [
                    {
                        "text": chunk.text,
                        "score": chunk.score,
                        "chunk_index": chunk.chunk_index
                    }
                    for chunk in relevant_chunks
                ]
            }
            
        except Exception as e:
            logger.error(f"Chat response generation failed: {e}")
            return {
                "response": "I apologize, but I encountered an error while processing your question. Please try again.",
                "sources": [],
                "context_used": False,
                "error": str(e)
            }
    
    def _prepare_context(self, chunks: List[Any]) -> str:
        """Prepare context text from relevant chunks"""
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[Context {i} - Relevance: {chunk.score:.2f}]\n{chunk.text}")
        
        return "\n\n".join(context_parts)
    
    def _build_conversation_history(self, chat_history: Optional[List[Dict[str, str]]]) -> str:
        """Build conversation history for context"""
        if not chat_history:
            return ""
        
        history_parts = []
        for msg in chat_history[-6:]:  # Keep last 6 messages for context
            role = "Human" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")
            history_parts.append(f"{role}: {content}")
        
        return "\n".join(history_parts)
    
    def _build_prompt(self, user_message: str, context: str, history: str) -> str:
        """Build the complete prompt for Gemini"""
        prompt_parts = []
        
        if history:
            prompt_parts.append(f"Previous conversation:\n{history}\n")
        
        prompt_parts.append(f"Document Context:\n{context}\n")
        prompt_parts.append(f"Human Question: {user_message}\n")
        prompt_parts.append("Please provide a helpful answer based on the document context above. If the information is not in the context, clearly state that you cannot find it in the uploaded document.")
        
        return "\n".join(prompt_parts)
    
    async def _generate_with_gemini(self, prompt: str) -> str:
        """Generate response using Gemini model"""
        try:
            # Generate response
            response = await self.model.generate_content_async(prompt)
            
            if response.text:
                return response.text.strip()
            else:
                return "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
                
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise
    
    def _format_sources(self, chunks: List[Any]) -> List[str]:
        """Format sources for display"""
        sources = []
        for chunk in chunks:
            source = f"Document section (chunk {chunk.chunk_index + 1}) - Relevance: {chunk.score:.1%}"
            sources.append(source)
        return sources
    
    async def test_connection(self) -> bool:
        """Test if Gemini API is accessible"""
        try:
            test_response = await self.model.generate_content_async("Hello, can you respond?")
            return bool(test_response.text)
        except Exception as e:
            logger.error(f"Gemini API connection test failed: {e}")
            return False
    
    async def generate_chat_title(self, first_message: str) -> str:
        """Generate a short title for the chat based on the first message"""
        try:
            prompt = f"Generate a short (3-5 words) title for a chat that starts with this question: '{first_message}'. Just return the title, nothing else."
            
            response = await self.model.generate_content_async(prompt)
            
            if response.text:
                title = response.text.strip().replace('"', '').replace("'", "")
                return title if len(title) <= 50 else title[:50]
            else:
                return "Document Chat"
                
        except Exception as e:
            logger.warning(f"Chat title generation failed: {e}")
            return "Document Chat"