// Use dynamic import for ES modules
let pipeline = null;

// Initialize the sentence transformer model
let sentenceEmbedder = null;

/**
 * Initialize the embedding model
 */
async function initializeEmbeddingModel() {
  if (!sentenceEmbedder) {
    console.log('Loading sentence embedding model...');
    
    // Dynamic import for ES modules
    if (!pipeline) {
      const { pipeline: pipelineFunc } = await import('@xenova/transformers');
      pipeline = pipelineFunc;
    }
    
    // Using all-MiniLM-L6-v2 model - good balance of speed and quality
    sentenceEmbedder = await pipeline(
      'feature-extraction', 
      'Xenova/all-MiniLM-L6-v2'
    );
    console.log('Embedding model loaded successfully');
  }
  return sentenceEmbedder;
}

/**
 * Generate embeddings for a text chunk
 */
async function generateEmbedding(text) {
  try {
    const model = await initializeEmbeddingModel();
    const output = await model(text, { 
      pooling: 'mean', 
      normalize: true 
    });
    
    // Convert tensor to array
    return Array.from(output.data);
  } catch (error) {
    console.error('Error generating embedding:', error);
    throw error;
  }
}

/**
 * Generate embeddings for multiple text chunks
 */
async function generateBatchEmbeddings(texts) {
  const embeddings = [];
  
  for (const text of texts) {
    try {
      const embedding = await generateEmbedding(text);
      embeddings.push(embedding);
    } catch (error) {
      console.error(`Error generating embedding for text: ${text.substring(0, 100)}...`, error);
      // Push null for failed embeddings to maintain array alignment
      embeddings.push(null);
    }
  }
  
  return embeddings;
}

/**
 * Get embedding dimension
 */
function getEmbeddingDimension() {
  // all-MiniLM-L6-v2 produces 384-dimensional embeddings
  return 384;
}

module.exports = {
  initializeEmbeddingModel,
  generateEmbedding,
  generateBatchEmbeddings,
  getEmbeddingDimension
};