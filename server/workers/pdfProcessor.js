const { Worker } = require('bullmq');
const { queueOptions } = require('../config/queue');
const { extractTextFromPDF, chunkText, cleanText } = require('../utils/textProcessor');
const { generateBatchEmbeddings } = require('../utils/embeddings');
const { storeDocumentChunks } = require('../config/qdrant');
const fs = require('fs');
const path = require('path');

/**
 * PDF Processing Worker
 */
const pdfWorker = new Worker('pdf-processing', async (job) => {
  const { filePath, originalName, documentId } = job.data;
  
  console.log(`Processing PDF: ${originalName} (ID: ${documentId})`);
  
  try {
    // Step 1: Extract text from PDF (5% of total work)
    console.log('📄 Extracting text from PDF...');
    await job.updateProgress({ percent: 5, message: '📄 Extracting text from PDF...' });
    
    const rawText = await extractTextFromPDF(filePath);
    console.log(`Extracted ${rawText.length} characters`);
    
    // Step 2: Clean and normalize text (5% of total work)
    console.log('🧹 Cleaning and normalizing text...');
    await job.updateProgress({ percent: 10, message: '🧹 Cleaning and normalizing text...' });
    
    const cleanedText = cleanText(rawText);
    
    // Step 3: Chunk the text (5% of total work)
    console.log('✂️ Chunking text into segments...');
    await job.updateProgress({ percent: 15, message: '✂️ Chunking text into segments...' });
    
    const chunkSize = parseInt(process.env.CHUNK_SIZE) || 1000;
    const chunkOverlap = parseInt(process.env.CHUNK_OVERLAP) || 200;
    const chunks = chunkText(cleanedText, chunkSize, chunkOverlap);
    console.log(`Created ${chunks.length} text chunks`);
    
    // Step 4: Generate embeddings for chunks (75% of total work - most time consuming)
    console.log(`🧠 Starting embedding generation for ${chunks.length} chunks...`);
    await job.updateProgress({ percent: 20, message: `🧠 Generating embeddings for ${chunks.length} chunks...` });
    
    const chunkTexts = chunks.map(chunk => chunk.text);
    
    // Progress callback for embedding generation
    const embeddingProgressCallback = (statusMessage) => {
      // Map embedding progress (0-100%) to overall progress (20-90%)
      const embeddingPercent = parseFloat(statusMessage.match(/\((\d+)%\)/)?.[1] || '0');
      const overallPercent = 20 + Math.round((embeddingPercent / 100) * 70);
      
      job.updateProgress({ 
        percent: overallPercent, 
        message: statusMessage 
      }).catch(err => console.warn('Progress update failed:', err));
    };
    
    const embeddings = await generateBatchEmbeddings(chunkTexts, embeddingProgressCallback);
    
    // Step 5: Store in Qdrant (10% of total work)
    console.log('💾 Storing chunks in vector database...');
    await job.updateProgress({ percent: 95, message: '💾 Storing chunks in vector database...' });
    
    const storedCount = await storeDocumentChunks(documentId, chunks, embeddings);
    
    // Step 6: Cleanup - delete the uploaded file after processing
    try {
      fs.unlinkSync(filePath);
      console.log(`Cleaned up temporary file: ${filePath}`);
    } catch (cleanupError) {
      console.warn(`Could not delete temporary file ${filePath}:`, cleanupError.message);
    }
    
    await job.updateProgress({ percent: 100, message: '🎉 PDF processing completed successfully!' });
    
    const result = {
      documentId,
      originalName,
      totalChunks: chunks.length,
      storedChunks: storedCount,
      textLength: cleanedText.length,
      status: 'completed',
      message: '🎉 PDF processing completed successfully!'
    };
    
    console.log(`PDF processing completed for ${originalName}:`, result);
    return result;
    
  } catch (error) {
    console.error(`Error processing PDF ${originalName}:`, error);
    
    // Try to cleanup file even on error
    try {
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    } catch (cleanupError) {
      console.warn(`Could not delete file on error ${filePath}:`, cleanupError.message);
    }
    
    throw error;
  }
}, queueOptions);

// Worker event handlers
pdfWorker.on('completed', (job, result) => {
  console.log(`Job ${job.id} completed successfully:`, result);
});

pdfWorker.on('failed', (job, err) => {
  console.error(`Job ${job.id} failed:`, err);
});

pdfWorker.on('progress', (job, progress) => {
  console.log(`Job ${job.id} progress: ${progress}%`);
});

console.log('PDF processing worker started');

module.exports = pdfWorker;