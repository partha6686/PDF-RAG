const { QdrantClient } = require('@qdrant/js-client-rest');
const { getEmbeddingDimension } = require('../utils/embeddings');

// Initialize Qdrant client
const qdrantClient = new QdrantClient({
  url: process.env.QDRANT_URL || 'http://localhost:6333'
});

const COLLECTION_NAME = 'pdf_documents_gemini'; // New collection name for Gemini embeddings

/**
 * Initialize Qdrant collection (recreate if dimension mismatch)
 */
async function initializeQdrantCollection() {
  try {
    const expectedDimension = getEmbeddingDimension();
    
    // Check if collection exists
    const collections = await qdrantClient.getCollections();
    const collectionExists = collections.collections.some(
      collection => collection.name === COLLECTION_NAME
    );

    if (collectionExists) {
      try {
        // Check if the existing collection has the correct dimension
        const collectionInfo = await qdrantClient.getCollection(COLLECTION_NAME);
        const currentDimension = collectionInfo.config.params.vectors.size;
        
        if (currentDimension !== expectedDimension) {
          console.log(`Collection dimension mismatch (${currentDimension} vs ${expectedDimension}). Recreating collection...`);
          await qdrantClient.deleteCollection(COLLECTION_NAME);
          const collectionExists = false; // Force recreation
        } else {
          console.log('Qdrant collection already exists with correct dimension');
          return;
        }
      } catch (error) {
        console.log('Error checking collection info, will recreate:', error.message);
        await qdrantClient.deleteCollection(COLLECTION_NAME).catch(() => {});
      }
    }

    // Create new collection
    console.log(`Creating Qdrant collection: ${COLLECTION_NAME} (${expectedDimension}D)`);
    
    await qdrantClient.createCollection(COLLECTION_NAME, {
      vectors: {
        size: expectedDimension,
        distance: 'Cosine', // Cosine similarity
      },
      optimizers_config: {
        default_segment_number: 2,
      },
      replication_factor: 1,
    });
    
    console.log('Qdrant collection created successfully');
  } catch (error) {
    console.error('Error initializing Qdrant collection:', error);
    throw error;
  }
}

/**
 * Store document chunks in Qdrant
 */
async function storeDocumentChunks(documentId, chunks, embeddings) {
  try {
    const points = chunks.map((chunk, index) => ({
      id: Math.floor(Math.random() * 1000000000), // Use random integer ID
      vector: embeddings[index],
      payload: {
        document_id: documentId,
        chunk_index: index,
        text: chunk.text,
        chunk_size: chunk.size,
        created_at: new Date().toISOString()
      }
    }));

    // Filter out points with null embeddings
    const validPoints = points.filter(point => point.vector !== null);
    
    if (validPoints.length === 0) {
      throw new Error('No valid embeddings to store');
    }

    await qdrantClient.upsert(COLLECTION_NAME, {
      wait: true,
      points: validPoints
    });

    console.log(`Stored ${validPoints.length} chunks for document ${documentId}`);
    return validPoints.length;
  } catch (error) {
    console.error('Error storing document chunks:', error);
    throw error;
  }
}

/**
 * Search similar document chunks
 */
async function searchSimilarChunks(queryEmbedding, limit = 5, scoreThreshold = 0.7) {
  try {
    const searchResult = await qdrantClient.search(COLLECTION_NAME, {
      vector: queryEmbedding,
      limit: limit,
      // Remove score threshold temporarily for debugging
      // score_threshold: scoreThreshold,
      with_payload: true,
      with_vector: false
    });

    return searchResult.map(result => ({
      id: result.id,
      score: result.score,
      text: result.payload.text,
      document_id: result.payload.document_id,
      chunk_index: result.payload.chunk_index
    }));
  } catch (error) {
    console.error('Error searching similar chunks:', error);
    throw error;
  }
}

/**
 * Get document chunks by document ID
 */
async function getDocumentChunks(documentId, limit = 100) {
  try {
    const searchResult = await qdrantClient.scroll(COLLECTION_NAME, {
      filter: {
        must: [
          {
            key: 'document_id',
            match: {
              value: documentId
            }
          }
        ]
      },
      limit: limit,
      with_payload: true,
      with_vector: false
    });

    return searchResult.points.map(point => ({
      id: point.id,
      text: point.payload.text,
      chunk_index: point.payload.chunk_index,
      chunk_size: point.payload.chunk_size
    }));
  } catch (error) {
    console.error('Error getting document chunks:', error);
    throw error;
  }
}

/**
 * Delete document and its chunks
 */
async function deleteDocument(documentId) {
  try {
    await qdrantClient.delete(COLLECTION_NAME, {
      filter: {
        must: [
          {
            key: 'document_id',
            match: {
              value: documentId
            }
          }
        ]
      }
    });

    console.log(`Deleted all chunks for document ${documentId}`);
  } catch (error) {
    console.error('Error deleting document:', error);
    throw error;
  }
}

module.exports = {
  qdrantClient,
  initializeQdrantCollection,
  storeDocumentChunks,
  searchSimilarChunks,
  getDocumentChunks,
  deleteDocument,
  COLLECTION_NAME
};