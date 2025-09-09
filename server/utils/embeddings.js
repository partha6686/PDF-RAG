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
            parts: [{ text: text }]
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
 * Generate embeddings for multiple text chunks (with rate limiting)
 */
async function generateBatchEmbeddings(texts) {
  const embeddings = [];
  const BATCH_DELAY = 100; // 100ms delay between requests to respect rate limits
  
  for (let i = 0; i < texts.length; i++) {
    try {
      const text = texts[i];
      console.log(`Generating embedding ${i + 1}/${texts.length}`);
      
      const embedding = await generateEmbedding(text);
      embeddings.push(embedding);
      
      // Add delay between requests to respect rate limits
      if (i < texts.length - 1) {
        await new Promise(resolve => setTimeout(resolve, BATCH_DELAY));
      }
    } catch (error) {
      console.error(`Error generating embedding for chunk ${i + 1}:`, error);
      // Push null for failed embeddings to maintain array alignment
      embeddings.push(null);
    }
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