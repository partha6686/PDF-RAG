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
    // Update job progress
    await job.updateProgress(10);
    
    // Step 1: Extract text from PDF
    console.log('Extracting text from PDF...');
    const rawText = await extractTextFromPDF(filePath);
    await job.updateProgress(30);
    
    // Step 2: Clean and normalize text
    console.log('Cleaning text...');
    const cleanedText = cleanText(rawText);
    await job.updateProgress(40);
    
    // Step 3: Chunk the text
    console.log('Chunking text...');
    const chunkSize = parseInt(process.env.CHUNK_SIZE) || 1000;
    const chunkOverlap = parseInt(process.env.CHUNK_OVERLAP) || 200;
    const chunks = chunkText(cleanedText, chunkSize, chunkOverlap);
    await job.updateProgress(50);
    
    // Step 4: Generate embeddings for chunks
    console.log(`Generating embeddings for ${chunks.length} chunks...`);
    const chunkTexts = chunks.map(chunk => chunk.text);
    const embeddings = await generateBatchEmbeddings(chunkTexts);
    await job.updateProgress(80);
    
    // Step 5: Store in Qdrant
    console.log('Storing chunks in vector database...');
    const storedCount = await storeDocumentChunks(documentId, chunks, embeddings);
    await job.updateProgress(95);
    
    // Step 6: Cleanup - delete the uploaded file after processing
    try {
      fs.unlinkSync(filePath);
      console.log(`Cleaned up temporary file: ${filePath}`);
    } catch (cleanupError) {
      console.warn(`Could not delete temporary file ${filePath}:`, cleanupError.message);
    }
    
    await job.updateProgress(100);
    
    const result = {
      documentId,
      originalName,
      totalChunks: chunks.length,
      storedChunks: storedCount,
      textLength: cleanedText.length,
      status: 'completed'
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