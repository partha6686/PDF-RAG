import PyPDF2
from typing import List, Dict, Any, Union
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

class PDFService:
    """Service for processing PDF files"""

    def __init__(self):
        pass

    def extract_text_from_bytes(self, pdf_data: Union[bytes, BytesIO]) -> str:
        """Extract text from PDF bytes or BytesIO object"""
        try:
            # Handle both bytes and BytesIO objects
            if isinstance(pdf_data, BytesIO):
                pdf_stream = pdf_data
                pdf_stream.seek(0)  # Reset to beginning
            else:
                pdf_stream = BytesIO(pdf_data)

            pdf_reader = PyPDF2.PdfReader(pdf_stream)

            text_content = ""
            total_pages = len(pdf_reader.pages)

            logger.info(f"Processing PDF with {total_pages} pages")

            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content += f"\n\n--- Page {page_num + 1} ---\n\n"
                        text_content += page_text

                    # Log progress for large documents
                    if (page_num + 1) % 10 == 0:
                        logger.info(f"Processed {page_num + 1}/{total_pages} pages")

                except Exception as e:
                    logger.warning(f"Error processing page {page_num + 1}: {e}")
                    continue

            if not text_content.strip():
                raise ValueError("No text content found in PDF")

            logger.info(f"Successfully extracted {len(text_content)} characters from PDF")
            return text_content.strip()

        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            raise

    def create_text_chunks(
        self,
        text: str,
        chunk_size: int = 2000,
        chunk_overlap: int = 400
    ) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks"""
        try:
            if not text.strip():
                raise ValueError("Empty text provided for chunking")

            # Simple chunking strategy - split by sentences and group
            sentences = self._split_into_sentences(text)
            chunks = []
            current_chunk = ""
            current_size = 0
            chunk_index = 0

            for sentence in sentences:
                sentence_size = len(sentence)

                # If adding this sentence would exceed chunk_size, save current chunk
                if current_size + sentence_size > chunk_size and current_chunk:
                    # Create overlap by keeping some text from end of current chunk
                    overlap_text = self._get_overlap_text(current_chunk, chunk_overlap)

                    chunks.append({
                        "text": current_chunk.strip(),
                        "size": len(current_chunk),
                        "chunk_index": chunk_index,
                        "overlap": overlap_text
                    })

                    # Start new chunk with overlap
                    current_chunk = overlap_text + " " + sentence
                    current_size = len(current_chunk)
                    chunk_index += 1
                else:
                    # Add sentence to current chunk
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
                    current_size += sentence_size

            # Don't forget the last chunk
            if current_chunk.strip():
                chunks.append({
                    "text": current_chunk.strip(),
                    "size": len(current_chunk),
                    "chunk_index": chunk_index,
                    "overlap": ""
                })

            logger.info(f"Created {len(chunks)} chunks from text")
            return chunks

        except Exception as e:
            logger.error(f"Text chunking failed: {e}")
            raise

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        import re

        # Simple sentence splitting - can be improved with nltk if needed
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # If sentences are too short, combine them
        combined_sentences = []
        current_sentence = ""

        for sentence in sentences:
            if len(current_sentence) + len(sentence) < 200:
                current_sentence += sentence + ". "
            else:
                if current_sentence:
                    combined_sentences.append(current_sentence.strip())
                current_sentence = sentence + ". "

        if current_sentence:
            combined_sentences.append(current_sentence.strip())

        return combined_sentences

    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get overlap text from end of chunk"""
        if len(text) <= overlap_size:
            return text

        # Try to break at sentence boundaries
        overlap_text = text[-overlap_size:]

        # Find the first sentence boundary
        import re
        sentences = re.split(r'[.!?]+', overlap_text)
        if len(sentences) > 1:
            # Take from the second sentence onwards to avoid partial sentences
            return ". ".join(sentences[1:]).strip()

        return overlap_text

    def validate_pdf_file(self, file_bytes: bytes) -> Dict[str, Any]:
        """Validate PDF file and return metadata"""
        try:
            pdf_stream = BytesIO(file_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)

            metadata = {
                "valid": True,
                "page_count": len(pdf_reader.pages),
                "file_size": len(file_bytes),
                "has_text": False,
                "metadata": {}
            }

            # Check if PDF has extractable text
            if pdf_reader.pages:
                sample_text = pdf_reader.pages[0].extract_text()
                metadata["has_text"] = bool(sample_text.strip())

            # Get PDF metadata
            if pdf_reader.metadata:
                metadata["metadata"] = {
                    "title": pdf_reader.metadata.get("/Title", ""),
                    "author": pdf_reader.metadata.get("/Author", ""),
                    "subject": pdf_reader.metadata.get("/Subject", ""),
                    "creator": pdf_reader.metadata.get("/Creator", ""),
                }

            return metadata

        except Exception as e:
            logger.error(f"PDF validation failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
