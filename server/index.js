const express = require('express');
const cors = require('cors');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
require('dotenv').config();

// Import queue and vector DB
const { pdfProcessingQueue } = require('./config/queue');
const { initializeQdrantCollection, searchSimilarChunks } = require('./config/qdrant');
const { generateEmbedding } = require('./utils/embeddings');
const { generateChatResponse, isGeminiConfigured } = require('./utils/gemini');

const app = express();
const PORT = process.env.PORT || 3002;

// Create uploads directory if it doesn't exist
const uploadsDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

// Middleware
app.use(cors());
app.use(express.json());

// Configure multer for PDF uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadsDir);
  },
  filename: (req, file, cb) => {
    // Generate unique filename with timestamp
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, file.fieldname + '-' + uniqueSuffix + path.extname(file.originalname));
  }
});

// File filter to only allow PDFs
const fileFilter = (req, file, cb) => {
  if (file.mimetype === 'application/pdf') {
    cb(null, true);
  } else {
    cb(new Error('Only PDF files are allowed!'), false);
  }
};

const upload = multer({
  storage: storage,
  fileFilter: fileFilter,
  limits: {
    fileSize: 50 * 1024 * 1024 // 50MB limit
  }
});

// Routes
app.get('/', (req, res) => {
  res.json({ message: 'PDF RAG Server is running!' });
});

// PDF Upload route with queue integration
app.post('/api/upload', upload.single('pdf'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No PDF file uploaded' });
    }

    // Generate unique document ID
    const documentId = `doc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    console.log('PDF uploaded:', {
      documentId,
      filename: req.file.filename,
      originalname: req.file.originalname,
      size: req.file.size,
      path: req.file.path
    });

    // Add job to processing queue
    const job = await pdfProcessingQueue.add('process-pdf', {
      documentId,
      filePath: req.file.path,
      filename: req.file.filename,
      originalName: req.file.originalname,
      fileSize: req.file.size,
      uploadedAt: new Date().toISOString()
    }, {
      // Job options
      delay: 1000, // 1 second delay to ensure file is fully written
      attempts: 3,
      backoff: {
        type: 'exponential',
        delay: 2000,
      }
    });

    res.json({
      message: 'PDF uploaded successfully and queued for processing',
      documentId,
      jobId: job.id,
      file: {
        filename: req.file.filename,
        originalname: req.file.originalname,
        size: req.file.size
      }
    });
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ error: 'Failed to upload PDF' });
  }
});

// Enhanced Chat route with vector search
app.post('/api/chat', async (req, res) => {
  const { message, documentId } = req.body;

  if (!message) {
    return res.status(400).json({ error: 'Message is required' });
  }

  try {
    let context = '';
    let similarChunks = [];

    // Only search if we have embeddings working
    try {
      // Generate embedding for the query
      console.log('Generating embedding for query:', message);
      const queryEmbedding = await generateEmbedding(message);
      console.log('Query embedding generated, length:', queryEmbedding.length);

      // Search for similar chunks in the vector database (lowered threshold)
      console.log('Searching for similar chunks...');
      similarChunks = await searchSimilarChunks(queryEmbedding, 5, 0.3);
      console.log('Search results:', similarChunks.length, 'chunks found');

      if (similarChunks.length > 0) {
        console.log('First chunk score:', similarChunks[0].score);
        // Create context from similar chunks (without scores for cleaner prompt)
        context = similarChunks
          .map(chunk => chunk.text)
          .join('\n\n');
      }
    } catch (searchError) {
      console.warn('Vector search failed:', searchError.message);
      console.error('Full error:', searchError);
      // Continue with empty context
    }

    // Generate response using Gemini
    let response;
    if (isGeminiConfigured()) {
      response = await generateChatResponse(message, context);
    } else {
      // Fallback if Gemini not configured
      if (context) {
        response = `Based on your PDF content:\n\n${context}`;
      } else {
        response = "Please upload a PDF document first so I can help you analyze its content.";
      }
    }

    res.json({
      response,
      similarChunks: similarChunks.length,
      hasContext: context.length > 0,
      sources: similarChunks.map(chunk => ({
        documentId: chunk.document_id,
        score: chunk.score,
        preview: chunk.text.substring(0, 150) + '...'
      }))
    });
  } catch (error) {
    console.error('Chat error:', error);

    res.json({
      response: "I'm having trouble processing your question right now. Please try again or upload a PDF document first.",
      error: 'Chat service temporarily unavailable'
    });
  }
});

// Error handling middleware
app.use((error, req, res, next) => {
  if (error instanceof multer.MulterError) {
    if (error.code === 'LIMIT_FILE_SIZE') {
      return res.status(400).json({ error: 'File size too large. Maximum size is 50MB.' });
    }
  }

  if (error.message === 'Only PDF files are allowed!') {
    return res.status(400).json({ error: 'Only PDF files are allowed.' });
  }

  console.error(error);
  res.status(500).json({ error: 'Internal server error' });
});

// Add new API endpoints for job status and document management
app.get('/api/job/:jobId', async (req, res) => {
  try {
    const job = await pdfProcessingQueue.getJob(req.params.jobId);
    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }

    res.json({
      id: job.id,
      data: job.data,
      progress: job.progress,
      state: await job.getState(),
      returnValue: job.returnvalue,
      failedReason: job.failedReason
    });
  } catch (error) {
    console.error('Job status error:', error);
    res.status(500).json({ error: 'Failed to get job status' });
  }
});

// Initialize services and start server
async function startServer() {
  try {
    // Initialize Qdrant collection
    await initializeQdrantCollection();
    console.log('Qdrant collection initialized');

    // Start the PDF processing worker
    require('./workers/pdfProcessor');
    console.log('PDF processing worker started');

    app.listen(PORT, () => {
      console.log(`Server is running on http://localhost:${PORT}`);
      console.log('Queue system ready for PDF processing');
    });

  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

startServer();

module.exports = app;
