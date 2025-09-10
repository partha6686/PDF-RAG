from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime
import logging

from app.core.config import settings
from app.models.schemas import ChunkData, EmbeddingResult

logger = logging.getLogger(__name__)

class QdrantService:
    """Qdrant vector database service with document isolation"""

    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.base_collection_name = "doc"
        self.embedding_dimension = 768  # Gemini text-embedding-004 dimension

    def get_document_collection_name(self, document_id: str) -> str:
        """Get document-specific collection name"""
        # Sanitize document_id for collection name (alphanumeric + underscores only)
        sanitized_doc_id = "".join(c for c in document_id if c.isalnum() or c == "_")
        return f"{self.base_collection_name}_{sanitized_doc_id}"

    async def initialize(self):
        """Initialize Qdrant service"""
        try:
            # Test connection
            collections = await asyncio.to_thread(self.client.get_collections)
            logger.info(f"✅ Connected to Qdrant. Found {len(collections.collections)} collections")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {e}")
            raise

    async def ensure_document_collection(self, document_id: str) -> str:
        """Ensure document-specific collection exists"""
        collection_name = self.get_document_collection_name(document_id)

        try:
            # Check if collection exists
            collections = await asyncio.to_thread(self.client.get_collections)
            collection_exists = any(
                col.name == collection_name for col in collections.collections
            )

            if not collection_exists:
                logger.info(f"Creating collection for document {document_id}: {collection_name}")
                await asyncio.to_thread(
                    self.client.create_collection,
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    ),
                    optimizers_config={
                        "default_segment_number": 2,
                    },
                    replication_factor=1,
                )
                logger.info(f"✅ Created collection: {collection_name}")

            return collection_name
        except Exception as e:
            logger.error(f"Failed to ensure collection for document {document_id}: {e}")
            raise

    async def store_document_chunks(
        self,
        user_id: str,
        document_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> int:
        """Store document chunks with embeddings in document-specific collection"""
        collection_name = await self.ensure_document_collection(document_id)

        try:
            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                if embedding is None:
                    continue

                point = PointStruct(
                    id=hash(f"{document_id}_{i}") % (2**63 - 1),  # Generate consistent ID
                    vector=embedding,
                    payload={
                        "user_id": user_id,
                        "document_id": document_id,
                        "chunk_index": i,
                        "text": chunk["text"],
                        "chunk_size": chunk["size"],
                        "created_at": datetime.now().isoformat()
                    }
                )
                points.append(point)

            if not points:
                raise ValueError("No valid embeddings to store")

            # Store points in document's collection
            await asyncio.to_thread(
                self.client.upsert,
                collection_name=collection_name,
                wait=True,
                points=points
            )

            logger.info(f"✅ Stored {len(points)} chunks for document {document_id}")
            return len(points)

        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            raise

    async def search_similar_chunks(
        self,
        document_id: str,
        query_embedding: List[float],
        limit: int = 5
    ) -> List[EmbeddingResult]:
        """Search for similar chunks in document's collection"""
        collection_name = await self.ensure_document_collection(document_id)

        try:
            search_result = await asyncio.to_thread(
                self.client.search,
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True
            )

            logger.info(f"Search returned {len(search_result)} results for document {document_id}")
            if search_result:
                logger.info(f"First result structure: id={search_result[0].id}, payload={search_result[0].payload}")

            results = []
            for result in search_result:
                # Extract payload data safely
                payload = result.payload or {}
                results.append(EmbeddingResult(
                    chunk_id=result.id,
                    score=result.score,
                    text=payload.get("text", ""),
                    document_id=payload.get("document_id", document_id),
                    chunk_index=payload.get("chunk_index", 0)
                ))

            return results

        except Exception as e:
            logger.error(f"Search failed for document {document_id}: {e}")
            return []

    async def collection_exists(self, document_id: str) -> bool:
        """Check if document collection exists"""
        collection_name = self.get_document_collection_name(document_id)

        try:
            collections = await asyncio.to_thread(self.client.get_collections)
            return any(col.name == collection_name for col in collections.collections)
        except Exception as e:
            logger.error(f"Failed to check collection existence for {document_id}: {e}")
            return False

    async def delete_document_collection(self, document_id: str) -> bool:
        """Delete entire document collection"""
        collection_name = self.get_document_collection_name(document_id)

        try:
            # Check if collection exists before trying to delete
            if not await self.collection_exists(document_id):
                logger.info(f"Collection {collection_name} doesn't exist, nothing to delete")
                return True

            await asyncio.to_thread(
                self.client.delete_collection,
                collection_name=collection_name
            )

            logger.info(f"✅ Deleted collection for document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete collection for document {document_id}: {e}")
            raise
