# PDF RAG Server

Express.js server with Redis queue system for processing PDFs and vector search capabilities.

## Features

- **PDF Upload & Processing**: Upload PDFs with automatic text extraction, chunking, and embedding generation
- **Background Queue System**: BullMQ + Redis for reliable background processing
- **Vector Database**: Qdrant integration for semantic search
- **Smart Chat**: AI-powered chat with context from uploaded PDFs
- **Real-time Status**: Job progress tracking and status monitoring
- **Local Embeddings**: Uses Sentence Transformers for embedding generation (no external API required)

## Getting Started

### Prerequisites
- Node.js (v16 or higher)
- npm
- Docker & Docker Compose (for Redis and Qdrant)

### Installation

```bash
# Install dependencies
npm install

# Start Redis and Qdrant services
npm run services

# Start the server
npm start

# For development
npm run dev

# To stop services
npm run services:stop

# View service logs
npm run services:logs
```

The server will run on `http://localhost:3002`
- Redis: `localhost:6379`
- Qdrant: `localhost:6333`

## API Endpoints

### POST /api/upload
Upload a PDF file.

**Request:**
- Content-Type: `multipart/form-data`
- Field name: `pdf`
- File type: PDF only
- Max size: 10MB

**Response:**
```json
{
  "message": "PDF uploaded successfully",
  "file": {
    "filename": "pdf-1234567890-123456789.pdf",
    "originalname": "document.pdf",
    "size": 1048576
  }
}
```

### POST /api/chat
Send a message to the AI chat agent.

**Request:**
```json
{
  "message": "What is this document about?"
}
```

**Response:**
```json
{
  "response": "I'd be happy to help you with your PDF content!"
}
```

## File Storage

Uploaded PDFs are stored in the `uploads/` directory with unique filenames to prevent conflicts.

## Error Handling

The server handles various error cases:
- Invalid file types
- File size limits
- Missing files
- Server errors

All errors return appropriate HTTP status codes with JSON error messages.