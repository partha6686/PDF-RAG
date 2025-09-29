# FastAPI PDF RAG Server

## Quick Start
```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your Clerk and Google API keys (see SETUP.md)

# 2. Start everything
docker-compose up --build
```

## What runs:
- **FastAPI Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs  
- **Celery Worker**: Background PDF processing
- **Redis + Qdrant**: Infrastructure services

## Key Features
✅ **User isolation** - Each user's PDFs are separated  
✅ **Clerk authentication** - Secure JWT validation  
✅ **Real-time progress** - Live PDF processing updates  
✅ **Hot reload** - Code changes update instantly  

## Required Setup
See [SETUP.md](SETUP.md) for Clerk API keys configuration.

That's it! 🚀