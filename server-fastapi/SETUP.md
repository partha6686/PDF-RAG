# 🚀 Setup Instructions

## Required Environment Variables

### 1. Get Google Gemini API Key
Go to: https://makersuite.google.com/app/apikey

### 2. Set up environment
**Copy these values to your `.env` file:**

```env
# Your Google Gemini API Key (free)
GOOGLE_API_KEY=AIza...your-google-key

# JWT Secret (change this in production!)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production-123

# Token expiration (days)
ACCESS_TOKEN_EXPIRE_DAYS=30
```

### 3. Quick Start
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your Google API key
nano .env

# 3. Start everything
docker-compose up --build
```

### 4. What you need:
- ✅ **GOOGLE_API_KEY** - From Google AI Studio (free)
- ✅ **JWT_SECRET_KEY** - Random secret for JWT signing

### 5. First Time Setup:
1. Visit: http://localhost:3000
2. **Sign up** with any email/password  
3. **Upload PDFs** and start chatting!

### 6. Verify Setup:
- Frontend: http://localhost:3000
- FastAPI: http://localhost:8000/docs
- Create account and upload PDFs
- Chat with your documents

**No external auth services needed!** 🎉