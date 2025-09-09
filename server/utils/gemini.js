const { GoogleGenerativeAI } = require('@google/generative-ai');

let genAI = null;
let model = null;

/**
 * Initialize Gemini AI
 */
function initializeGemini() {
  if (!genAI) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey || apiKey === 'your-gemini-api-key-here') {
      throw new Error('GEMINI_API_KEY is required in .env file');
    }
    
    genAI = new GoogleGenerativeAI(apiKey);
    model = genAI.getGenerativeModel({ model: 'gemini-1.5-flash' }); // Updated model name
    console.log('Gemini AI initialized successfully');
  }
  return model;
}

/**
 * Generate chat response using Gemini with context
 */
async function generateChatResponse(question, context = '') {
  try {
    const geminiModel = initializeGemini();
    
    let prompt;
    
    if (context.trim()) {
      prompt = `You are a helpful AI assistant that answers questions based on provided PDF content. 

Context from PDF documents:
${context}

Question: ${question}

Instructions:
- Answer the question based on the provided context
- If the context doesn't contain relevant information, say so politely
- Be concise but thorough
- Reference specific parts of the context when applicable

Answer:`;
    } else {
      prompt = `You are a helpful AI assistant for a PDF analysis application.

Question: ${question}

The user hasn't uploaded any PDF documents yet, or no relevant content was found in their documents. Please provide a helpful response encouraging them to upload a PDF document first, and explain what you can help them with once they do.

Answer:`;
    }
    
    const result = await geminiModel.generateContent(prompt);
    const response = await result.response;
    return response.text();
    
  } catch (error) {
    console.error('Gemini API error:', error);
    
    // Fallback responses based on context availability
    if (context.trim()) {
      return `I found some relevant information in your PDF, but I'm having trouble generating a response right now. Here's what I found:\n\n${context}`;
    } else {
      return "I'd be happy to help you analyze your PDF content! Please upload a PDF document first, and then ask me questions about it.";
    }
  }
}

/**
 * Check if Gemini is properly configured
 */
function isGeminiConfigured() {
  const apiKey = process.env.GEMINI_API_KEY;
  return apiKey && apiKey !== 'your-gemini-api-key-here';
}

module.exports = {
  initializeGemini,
  generateChatResponse,
  isGeminiConfigured
};