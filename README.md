# PDF RAG Application

A full-stack PDF analysis application with AI-powered chat using vector search and Google Gemini.

## Quick Start

```bash
# 1. Install all dependencies
npm run install:all

# 2. Start everything (services + server + client)
npm run dev
```

That's it! The app will be available at:
- **Client**: http://localhost:3001
- **Server**: http://localhost:3002

## What it includes

- ✅ **Next.js frontend** with PDF upload and chat interface
- ✅ **Express.js backend** with queue processing
- ✅ **Redis queue system** for background PDF processing
- ✅ **Qdrant vector database** for semantic search
- ✅ **Google Gemini AI** for intelligent chat responses
- ✅ **Local embeddings** using Sentence Transformers

## Manual Setup (if needed)

```bash
# Install dependencies
npm run install:all

# Start services only (Redis + Qdrant)
npm run services:start

# Start server only
cd server && npm run dev

# Start client only  
cd client && npm run dev

# Stop services
npm run services:stop
```

## Configuration

### Gemini API Key (Required)
1. Get a free API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Add to `server/.env`:
```
GEMINI_API_KEY=your-api-key-here
```

### Environment Variables
All configuration is in `server/.env`:
```
REDIS_HOST=localhost
REDIS_PORT=6380
QDRANT_URL=http://localhost:6333
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
GEMINI_API_KEY=your-api-key-here
```

## How it works

1. **Upload PDF** → File is uploaded and queued for processing
2. **Background Processing** → PDF is parsed, chunked, and embedded
3. **Vector Storage** → Chunks stored in Qdrant with embeddings
4. **Smart Chat** → Questions are matched with relevant content
5. **AI Response** → Gemini generates natural language answers

## Requirements

- Node.js 16+
- Docker & Docker Compose (for Redis and Qdrant)
- Google Gemini API key (free tier available)