const { GoogleGenerativeAI } = require('@google/generative-ai');

let genAI = null;

/**
 * Initialize Gemini embedding model
 */
function initializeEmbeddingModel() {
  if (!genAI) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey || apiKey === 'your-gemini-api-key-here') {
      throw new Error('GEMINI_API_KEY is required in .env file for embeddings');
    }
    
    genAI = new GoogleGenerativeAI(apiKey);
    console.log('Gemini embedding API initialized');
  }
  return genAI;
}

/**
 * Generate embeddings for a text chunk using Gemini API
 */
async function generateEmbedding(text) {
  try {
    const genAI = initializeEmbeddingModel();
    
    const response = await fetch(
      'https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent',
      {
        method: 'POST',
        headers: {
          'x-goog-api-key': process.env.GEMINI_API_KEY,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'models/text-embedding-004',
          content: {
            parts: [{ text: text.substring(0, 2048) }] // Limit text length for faster processing
          }
        })
      }
    );

    if (!response.ok) {
      throw new Error(`Gemini API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return data.embedding.values;
  } catch (error) {
    console.error('Error generating Gemini embedding:', error);
    throw error;
  }
}

/**
 * Generate embeddings for multiple text chunks (with progress callback)
 */
async function generateBatchEmbeddings(texts, progressCallback = null) {
  const BATCH_SIZE = 10; // Process 10 embeddings concurrently
  const BATCH_DELAY = 50; // Reduced delay between batches
  const embeddings = [];
  
  console.log(`Generating embeddings for ${texts.length} chunks using concurrent batching...`);
  
  // Process in batches for better performance
  for (let i = 0; i < texts.length; i += BATCH_SIZE) {
    const batch = texts.slice(i, i + BATCH_SIZE);
    const batchNum = Math.floor(i/BATCH_SIZE) + 1;
    const totalBatches = Math.ceil(texts.length/BATCH_SIZE);
    
    console.log(`Processing embedding batch ${batchNum}/${totalBatches}`);
    
    // Update progress if callback provided
    if (progressCallback) {
      const embeddingProgress = Math.round((i / texts.length) * 100);
      progressCallback(`🧠 Generating embeddings... Batch ${batchNum}/${totalBatches} (${embeddingProgress}%)`);
    }
    
    // Process batch concurrently
    const batchPromises = batch.map(async (text, index) => {
      try {
        const embedding = await generateEmbedding(text);
        return { index: i + index, embedding, success: true };
      } catch (error) {
        console.error(`Error generating embedding for chunk ${i + index + 1}:`, error.message);
        return { index: i + index, embedding: null, success: false };
      }
    });
    
    // Wait for all embeddings in this batch
    const batchResults = await Promise.all(batchPromises);
    
    // Store results in correct order
    batchResults.forEach(result => {
      embeddings[result.index] = result.embedding;
    });
    
    // Small delay between batches to respect rate limits
    if (i + BATCH_SIZE < texts.length) {
      await new Promise(resolve => setTimeout(resolve, BATCH_DELAY));
    }
  }
  
  const successCount = embeddings.filter(e => e !== null).length;
  console.log(`Embedding generation completed: ${successCount}/${texts.length} successful`);
  
  if (progressCallback) {
    progressCallback(`✅ Embeddings complete! Generated ${successCount}/${texts.length} embeddings`);
  }
  
  return embeddings;
}

/**
 * Get embedding dimension for Gemini text-embedding-004
 */
function getEmbeddingDimension() {
  // Gemini text-embedding-004 produces 768-dimensional embeddings
  return 768;
}

module.exports = {
  initializeEmbeddingModel,
  generateEmbedding,
  generateBatchEmbeddings,
  getEmbeddingDimension
};