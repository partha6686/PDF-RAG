const fs = require('fs');
const pdfParse = require('pdf-parse');

/**
 * Extract text from PDF file
 */
async function extractTextFromPDF(filePath) {
  try {
    const pdfBuffer = fs.readFileSync(filePath);
    const data = await pdfParse(pdfBuffer);
    return data.text;
  } catch (error) {
    console.error('Error extracting text from PDF:', error);
    throw error;
  }
}

/**
 * Split text into chunks with overlap
 */
function chunkText(text, chunkSize = 1000, overlap = 200) {
  const chunks = [];
  const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
  
  let currentChunk = '';
  let currentSize = 0;
  
  for (let i = 0; i < sentences.length; i++) {
    const sentence = sentences[i].trim() + '.';
    const sentenceSize = sentence.length;
    
    // If adding this sentence would exceed chunk size
    if (currentSize + sentenceSize > chunkSize && currentChunk.length > 0) {
      chunks.push({
        text: currentChunk.trim(),
        index: chunks.length,
        size: currentSize
      });
      
      // Create overlap by including last few sentences
      const overlapSentences = [];
      let overlapSize = 0;
      let j = i - 1;
      
      while (j >= 0 && overlapSize < overlap) {
        const prevSentence = sentences[j].trim() + '.';
        if (overlapSize + prevSentence.length <= overlap) {
          overlapSentences.unshift(prevSentence);
          overlapSize += prevSentence.length;
        }
        j--;
      }
      
      currentChunk = overlapSentences.join(' ') + (overlapSentences.length > 0 ? ' ' : '') + sentence;
      currentSize = currentChunk.length;
    } else {
      currentChunk += (currentChunk.length > 0 ? ' ' : '') + sentence;
      currentSize += sentenceSize;
    }
  }
  
  // Add the last chunk if it has content
  if (currentChunk.trim().length > 0) {
    chunks.push({
      text: currentChunk.trim(),
      index: chunks.length,
      size: currentSize
    });
  }
  
  return chunks;
}

/**
 * Clean and normalize text
 */
function cleanText(text) {
  return text
    .replace(/\s+/g, ' ')           // Replace multiple whitespace with single space
    .replace(/\n+/g, ' ')           // Replace newlines with spaces
    .replace(/[^\w\s.,!?;:-]/g, '') // Remove special characters except basic punctuation
    .trim();
}

module.exports = {
  extractTextFromPDF,
  chunkText,
  cleanText
};