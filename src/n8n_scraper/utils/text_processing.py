"""Text processing utilities for chunking and cleaning text.

This module provides functionality for:
1. Splitting text into chunks for vector search
2. Cleaning and normalizing text
3. Extracting metadata from text
"""

import re
import html
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ..core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    content: str
    start_index: int
    end_index: int
    word_count: int
    char_count: int
    metadata: Dict[str, Any]


class TextProcessor:
    """Utility class for text processing and chunking."""
    
    def __init__(self):
        """Initialize the text processor."""
        # Common patterns for text cleaning
        self.html_pattern = re.compile(r'<[^>]+>')
        self.whitespace_pattern = re.compile(r'\s+')
        self.url_pattern = re.compile(r'https?://[^\s]+')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        
        # Sentence boundary patterns
        self.sentence_endings = re.compile(r'[.!?]+\s+')
        self.paragraph_breaks = re.compile(r'\n\s*\n')
    
    def clean_text(self, text: str, 
                   remove_html: bool = True,
                   normalize_whitespace: bool = True,
                   preserve_urls: bool = False,
                   preserve_emails: bool = False) -> str:
        """Clean and normalize text.
        
        Args:
            text: Input text
            remove_html: Whether to remove HTML tags
            normalize_whitespace: Whether to normalize whitespace
            preserve_urls: Whether to preserve URLs
            preserve_emails: Whether to preserve email addresses
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Remove HTML tags
        if remove_html:
            text = self.html_pattern.sub(' ', text)
        
        # Handle URLs
        if not preserve_urls:
            text = self.url_pattern.sub('[URL]', text)
        
        # Handle emails
        if not preserve_emails:
            text = self.email_pattern.sub('[EMAIL]', text)
        
        # Normalize whitespace
        if normalize_whitespace:
            text = self.whitespace_pattern.sub(' ', text)
        
        # Strip and return
        return text.strip()
    
    def split_text(self, text: str, 
                   chunk_size: int = 1000, 
                   overlap: int = 200,
                   split_on_sentences: bool = True,
                   split_on_paragraphs: bool = True) -> List[str]:
        """Split text into chunks with optional overlap.
        
        Args:
            text: Input text
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks in characters
            split_on_sentences: Whether to try to split on sentence boundaries
            split_on_paragraphs: Whether to try to split on paragraph boundaries
            
        Returns:
            List of text chunks
        """
        if not text or chunk_size <= 0:
            return []
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        
        # First try to split on paragraphs if enabled
        if split_on_paragraphs:
            paragraphs = self.paragraph_breaks.split(text)
            if len(paragraphs) > 1:
                current_chunk = ""
                
                for paragraph in paragraphs:
                    paragraph = paragraph.strip()
                    if not paragraph:
                        continue
                    
                    # If adding this paragraph would exceed chunk size
                    if len(current_chunk) + len(paragraph) + 2 > chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            
                            # Start new chunk with overlap
                            if overlap > 0 and len(current_chunk) > overlap:
                                current_chunk = current_chunk[-overlap:] + "\n\n" + paragraph
                            else:
                                current_chunk = paragraph
                        else:
                            # Paragraph itself is too long, split it further
                            para_chunks = self._split_long_text(
                                paragraph, chunk_size, overlap, split_on_sentences
                            )
                            chunks.extend(para_chunks[:-1])  # Add all but last
                            current_chunk = para_chunks[-1] if para_chunks else ""
                    else:
                        if current_chunk:
                            current_chunk += "\n\n" + paragraph
                        else:
                            current_chunk = paragraph
                
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                return [chunk for chunk in chunks if chunk.strip()]
        
        # Fall back to sentence-based or character-based splitting
        return self._split_long_text(text, chunk_size, overlap, split_on_sentences)
    
    def _split_long_text(self, text: str, 
                        chunk_size: int, 
                        overlap: int,
                        split_on_sentences: bool) -> List[str]:
        """Split long text using sentence or character boundaries.
        
        Args:
            text: Input text
            chunk_size: Target chunk size
            overlap: Overlap size
            split_on_sentences: Whether to split on sentences
            
        Returns:
            List of text chunks
        """
        chunks = []
        
        if split_on_sentences:
            # Try to split on sentence boundaries
            sentences = self.sentence_endings.split(text)
            if len(sentences) > 1:
                current_chunk = ""
                
                for i, sentence in enumerate(sentences):
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    # Add sentence ending back (except for last sentence)
                    if i < len(sentences) - 1:
                        sentence += ". "
                    
                    # Check if adding this sentence would exceed chunk size
                    if len(current_chunk) + len(sentence) > chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            
                            # Start new chunk with overlap
                            if overlap > 0 and len(current_chunk) > overlap:
                                current_chunk = current_chunk[-overlap:] + sentence
                            else:
                                current_chunk = sentence
                        else:
                            # Single sentence is too long, split by characters
                            char_chunks = self._split_by_characters(
                                sentence, chunk_size, overlap
                            )
                            chunks.extend(char_chunks[:-1])
                            current_chunk = char_chunks[-1] if char_chunks else ""
                    else:
                        current_chunk += sentence
                
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                return [chunk for chunk in chunks if chunk.strip()]
        
        # Fall back to character-based splitting
        return self._split_by_characters(text, chunk_size, overlap)
    
    def _split_by_characters(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text by character count with overlap.
        
        Args:
            text: Input text
            chunk_size: Target chunk size
            overlap: Overlap size
            
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # If this is not the last chunk, try to find a good break point
            if end < len(text):
                # Look for whitespace near the end
                break_point = end
                for i in range(end, max(start + chunk_size // 2, end - 100), -1):
                    if text[i].isspace():
                        break_point = i
                        break
                end = break_point
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            if end >= len(text):
                break
            
            start = max(start + 1, end - overlap)
        
        return chunks
    
    def extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extract metadata from text.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary of extracted metadata
        """
        metadata = {
            'char_count': len(text),
            'word_count': len(text.split()),
            'line_count': text.count('\n') + 1,
            'paragraph_count': len(self.paragraph_breaks.split(text)),
            'sentence_count': len(self.sentence_endings.split(text)),
            'has_urls': bool(self.url_pattern.search(text)),
            'has_emails': bool(self.email_pattern.search(text)),
            'has_html': bool(self.html_pattern.search(text))
        }
        
        # Extract URLs and emails if present
        if metadata['has_urls']:
            metadata['urls'] = self.url_pattern.findall(text)
        
        if metadata['has_emails']:
            metadata['emails'] = self.email_pattern.findall(text)
        
        # Language detection (simple heuristic)
        metadata['language'] = self._detect_language_simple(text)
        
        return metadata
    
    def _detect_language_simple(self, text: str) -> str:
        """Simple language detection based on character patterns.
        
        Args:
            text: Input text
            
        Returns:
            Detected language code
        """
        # Very basic language detection
        # In a real implementation, you might use a proper language detection library
        
        # Count ASCII vs non-ASCII characters
        ascii_chars = sum(1 for c in text if ord(c) < 128)
        total_chars = len(text)
        
        if total_chars == 0:
            return 'unknown'
        
        ascii_ratio = ascii_chars / total_chars
        
        # Simple heuristic: if mostly ASCII, assume English
        if ascii_ratio > 0.9:
            return 'en'
        else:
            return 'unknown'
    
    def create_chunks_with_metadata(self, text: str, 
                                   chunk_size: int = 1000, 
                                   overlap: int = 200,
                                   **kwargs) -> List[TextChunk]:
        """Create text chunks with detailed metadata.
        
        Args:
            text: Input text
            chunk_size: Target chunk size
            overlap: Overlap size
            **kwargs: Additional arguments for split_text
            
        Returns:
            List of TextChunk objects
        """
        chunks = self.split_text(text, chunk_size, overlap, **kwargs)
        text_chunks = []
        
        current_pos = 0
        for i, chunk_content in enumerate(chunks):
            # Find the actual position of this chunk in the original text
            start_index = text.find(chunk_content, current_pos)
            if start_index == -1:
                # Fallback if exact match not found
                start_index = current_pos
            
            end_index = start_index + len(chunk_content)
            
            # Extract metadata for this chunk
            chunk_metadata = self.extract_metadata(chunk_content)
            chunk_metadata['chunk_index'] = i
            chunk_metadata['total_chunks'] = len(chunks)
            
            text_chunk = TextChunk(
                content=chunk_content,
                start_index=start_index,
                end_index=end_index,
                word_count=chunk_metadata['word_count'],
                char_count=chunk_metadata['char_count'],
                metadata=chunk_metadata
            )
            
            text_chunks.append(text_chunk)
            current_pos = end_index
        
        return text_chunks
    
    def merge_chunks(self, chunks: List[str], max_size: int = 2000) -> List[str]:
        """Merge small chunks together up to a maximum size.
        
        Args:
            chunks: List of text chunks
            max_size: Maximum size for merged chunks
            
        Returns:
            List of merged chunks
        """
        if not chunks:
            return []
        
        merged = []
        current_chunk = ""
        
        for chunk in chunks:
            # If adding this chunk would exceed max size
            if len(current_chunk) + len(chunk) + 1 > max_size:
                if current_chunk:
                    merged.append(current_chunk.strip())
                current_chunk = chunk
            else:
                if current_chunk:
                    current_chunk += " " + chunk
                else:
                    current_chunk = chunk
        
        if current_chunk:
            merged.append(current_chunk.strip())
        
        return merged
    
    def get_text_statistics(self, text: str) -> Dict[str, Any]:
        """Get comprehensive text statistics.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary of text statistics
        """
        if not text:
            return {}
        
        words = text.split()
        sentences = self.sentence_endings.split(text)
        paragraphs = self.paragraph_breaks.split(text)
        
        # Calculate averages
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        avg_paragraph_length = len(words) / len(paragraphs) if paragraphs else 0
        
        return {
            'total_characters': len(text),
            'total_words': len(words),
            'total_sentences': len(sentences),
            'total_paragraphs': len(paragraphs),
            'avg_word_length': round(avg_word_length, 2),
            'avg_sentence_length': round(avg_sentence_length, 2),
            'avg_paragraph_length': round(avg_paragraph_length, 2),
            'readability_score': self._calculate_readability_score(text, words, sentences)
        }
    
    def _calculate_readability_score(self, text: str, words: List[str], sentences: List[str]) -> float:
        """Calculate a simple readability score.
        
        Args:
            text: Original text
            words: List of words
            sentences: List of sentences
            
        Returns:
            Readability score (0-100, higher is more readable)
        """
        if not words or not sentences:
            return 0.0
        
        # Simple Flesch-like formula
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Simplified score (not actual Flesch)
        score = 100 - (avg_sentence_length * 1.5) - (avg_word_length * 2)
        
        return max(0.0, min(100.0, score))