"""
Intelligent content processing with AI/ML capabilities.

This module provides intelligent processing of content using AI models and machine learning algorithms.
It includes functionalities for sentiment analysis, summarization, named entity recognition,
category classification, and topic modeling.

Attributes:
    TRANSFORMERS_AVAILABLE (bool): Flag indicating if the Transformers library is available.
    SKLEARN_AVAILABLE (bool): Flag indicating if the scikit-learn library is available.

Note:
    This module requires the Transformers and scikit-learn libraries to be installed.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel

try:
    from transformers import pipeline, AutoTokenizer, AutoModel
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from ..config.settings import settings
from ..database.models import ScrapedDocument
from ..database.vector_store import VectorStore

logger = logging.getLogger(__name__)


class ContentAnalysis(BaseModel):
    """Content analysis results."""
    sentiment: float
    complexity_score: float
    readability_score: float
    key_topics: List[str]
    entities: List[Dict[str, Any]]
    summary: str
    category: str
    quality_score: float


class SmartCategorization(BaseModel):
    """Smart categorization results."""
    primary_category: str
    secondary_categories: List[str]
    confidence: float
    tags: List[str]
    difficulty_level: str
    content_type: str


class IntelligentProcessor:
    """AI-powered content processor for enhanced analysis."""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self._sentiment_analyzer = None
        self._summarizer = None
        self._ner_pipeline = None
        self._classifier = None
        self._topic_model = None
        self._is_initialized = False
        
        # Category mapping for n8n documentation
        self.category_mapping = {
            'getting-started': ['introduction', 'setup', 'installation', 'quickstart'],
            'nodes': ['node', 'integration', 'service', 'api', 'webhook'],
            'workflows': ['workflow', 'automation', 'trigger', 'execution'],
            'advanced': ['code', 'expression', 'function', 'custom'],
            'hosting': ['deployment', 'docker', 'kubernetes', 'cloud'],
            'troubleshooting': ['error', 'debug', 'issue', 'problem', 'fix']
        }
    
    async def initialize(self) -> None:
        """Initialize AI models and components."""
        if self._is_initialized:
            return
            
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Transformers not available, using basic processing")
            self._is_initialized = True
            return
        
        try:
            logger.info("Initializing AI models...")
            
            # Initialize sentiment analysis
            self._sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                device=0 if torch.cuda.is_available() else -1
            )
            
            # Initialize summarization
            self._summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=0 if torch.cuda.is_available() else -1
            )
            
            # Initialize NER
            self._ner_pipeline = pipeline(
                "ner",
                model="dbmdz/bert-large-cased-finetuned-conll03-english",
                aggregation_strategy="simple",
                device=0 if torch.cuda.is_available() else -1
            )
            
            # Initialize vector store
            await self.vector_store.initialize()
            
            self._is_initialized = True
            logger.info("AI models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI models: {e}")
            self._is_initialized = True  # Continue with basic processing
    
    async def analyze_content(self, content: str, metadata: Dict[str, Any] = None) -> ContentAnalysis:
        """Perform comprehensive content analysis."""
        await self.initialize()
        
        try:
            # Sentiment analysis
            sentiment = await self._analyze_sentiment(content)
            
            # Complexity and readability
            complexity = self._calculate_complexity(content)
            readability = self._calculate_readability(content)
            
            # Extract entities
            entities = await self._extract_entities(content)
            
            # Generate summary
            summary = await self._generate_summary(content)
            
            # Extract key topics
            topics = await self._extract_topics(content)
            
            # Categorize content
            category = self._categorize_content(content, metadata or {})
            
            # Calculate quality score
            quality = self._calculate_quality_score(
                content, sentiment, complexity, readability, len(entities)
            )
            
            return ContentAnalysis(
                sentiment=sentiment,
                complexity_score=complexity,
                readability_score=readability,
                key_topics=topics,
                entities=entities,
                summary=summary,
                category=category,
                quality_score=quality
            )
            
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            # Return basic analysis
            return ContentAnalysis(
                sentiment=0.0,
                complexity_score=0.5,
                readability_score=0.5,
                key_topics=[],
                entities=[],
                summary=content[:200] + "..." if len(content) > 200 else content,
                category="general",
                quality_score=0.5
            )
    
    async def smart_categorize(self, content: str, metadata: Dict[str, Any] = None) -> SmartCategorization:
        """Perform smart categorization with confidence scoring."""
        await self.initialize()
        
        try:
            # Primary categorization
            primary_category, confidence = self._classify_primary_category(content, metadata or {})
            
            # Secondary categories
            secondary_categories = self._identify_secondary_categories(content)
            
            # Extract tags
            tags = self._extract_tags(content)
            
            # Determine difficulty level
            difficulty = self._assess_difficulty(content)
            
            # Identify content type
            content_type = self._identify_content_type(content, metadata or {})
            
            return SmartCategorization(
                primary_category=primary_category,
                secondary_categories=secondary_categories,
                confidence=confidence,
                tags=tags,
                difficulty_level=difficulty,
                content_type=content_type
            )
            
        except Exception as e:
            logger.error(f"Smart categorization failed: {e}")
            return SmartCategorization(
                primary_category="general",
                secondary_categories=[],
                confidence=0.5,
                tags=[],
                difficulty_level="intermediate",
                content_type="documentation"
            )
    
    async def _analyze_sentiment(self, content: str) -> float:
        """Analyze sentiment of content."""
        if not self._sentiment_analyzer:
            return 0.0
        
        try:
            # Truncate content for analysis
            text = content[:512]  # BERT limit
            result = self._sentiment_analyzer(text)[0]
            
            # Convert to numerical score (-1 to 1)
            if result['label'] == 'POSITIVE':
                return result['score']
            elif result['label'] == 'NEGATIVE':
                return -result['score']
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return 0.0
    
    def _calculate_complexity(self, content: str) -> float:
        """Calculate content complexity score."""
        try:
            words = content.split()
            sentences = content.split('.')
            
            # Average words per sentence
            avg_words_per_sentence = len(words) / max(len(sentences), 1)
            
            # Average characters per word
            avg_chars_per_word = sum(len(word) for word in words) / max(len(words), 1)
            
            # Technical terms count
            technical_terms = ['api', 'webhook', 'node', 'workflow', 'json', 'http', 'authentication']
            tech_count = sum(1 for word in words if word.lower() in technical_terms)
            tech_ratio = tech_count / max(len(words), 1)
            
            # Normalize to 0-1 scale
            complexity = min(1.0, (
                (avg_words_per_sentence / 20) * 0.4 +
                (avg_chars_per_word / 10) * 0.3 +
                tech_ratio * 0.3
            ))
            
            return complexity
            
        except Exception as e:
            logger.error(f"Complexity calculation failed: {e}")
            return 0.5
    
    def _calculate_readability(self, content: str) -> float:
        """Calculate readability score (Flesch Reading Ease approximation)."""
        try:
            words = content.split()
            sentences = content.split('.')
            syllables = sum(self._count_syllables(word) for word in words)
            
            if len(sentences) == 0 or len(words) == 0:
                return 0.5
            
            # Simplified Flesch Reading Ease
            score = 206.835 - (1.015 * (len(words) / len(sentences))) - (84.6 * (syllables / len(words)))
            
            # Normalize to 0-1 scale (higher = more readable)
            normalized = max(0, min(1, score / 100))
            
            return normalized
            
        except Exception as e:
            logger.error(f"Readability calculation failed: {e}")
            return 0.5
    
    def _count_syllables(self, word: str) -> int:
        """Estimate syllable count in a word."""
        word = word.lower()
        vowels = 'aeiouy'
        syllable_count = 0
        previous_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel
        
        # Handle silent 'e'
        if word.endswith('e'):
            syllable_count -= 1
        
        return max(1, syllable_count)
    
    async def _extract_entities(self, content: str) -> List[Dict[str, Any]]:
        """Extract named entities from content."""
        if not self._ner_pipeline:
            return []
        
        try:
            # Truncate content for NER
            text = content[:512]
            entities = self._ner_pipeline(text)
            
            return [
                {
                    'text': entity['word'],
                    'label': entity['entity_group'],
                    'confidence': entity['score'],
                    'start': entity['start'],
                    'end': entity['end']
                }
                for entity in entities
                if entity['score'] > 0.8  # High confidence only
            ]
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []
    
    async def _generate_summary(self, content: str) -> str:
        """Generate content summary."""
        if not self._summarizer:
            # Fallback to first 200 characters
            return content[:200] + "..." if len(content) > 200 else content
        
        try:
            # Ensure content is long enough for summarization
            if len(content) < 100:
                return content
            
            # Truncate if too long
            text = content[:1024]  # Model limit
            
            summary = self._summarizer(
                text,
                max_length=150,
                min_length=30,
                do_sample=False
            )[0]['summary_text']
            
            return summary
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return content[:200] + "..." if len(content) > 200 else content
    
    async def _extract_topics(self, content: str) -> List[str]:
        """Extract key topics from content."""
        try:
            # Simple keyword extraction based on frequency and relevance
            words = content.lower().split()
            
            # Filter out common words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
            
            # Count frequency
            word_freq = {}
            for word in filtered_words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get top topics
            topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return [topic[0] for topic in topics]
            
        except Exception as e:
            logger.error(f"Topic extraction failed: {e}")
            return []
    
    def _categorize_content(self, content: str, metadata: Dict[str, Any]) -> str:
        """Categorize content based on keywords and metadata."""
        content_lower = content.lower()
        url = metadata.get('url', '').lower()
        title = metadata.get('title', '').lower()
        
        # Check URL patterns first
        if '/getting-started' in url or '/quickstart' in url:
            return 'getting-started'
        elif '/nodes/' in url or '/integrations/' in url:
            return 'nodes'
        elif '/workflows/' in url or '/automation/' in url:
            return 'workflows'
        elif '/code/' in url or '/expressions/' in url:
            return 'advanced'
        elif '/hosting/' in url or '/deployment/' in url:
            return 'hosting'
        
        # Check content keywords
        for category, keywords in self.category_mapping.items():
            if any(keyword in content_lower or keyword in title for keyword in keywords):
                return category
        
        return 'general'
    
    def _classify_primary_category(self, content: str, metadata: Dict[str, Any]) -> Tuple[str, float]:
        """Classify primary category with confidence."""
        category = self._categorize_content(content, metadata)
        
        # Calculate confidence based on keyword matches
        content_lower = content.lower()
        keywords = self.category_mapping.get(category, [])
        matches = sum(1 for keyword in keywords if keyword in content_lower)
        confidence = min(1.0, matches / max(len(keywords), 1) + 0.3)
        
        return category, confidence
    
    def _identify_secondary_categories(self, content: str) -> List[str]:
        """Identify secondary categories."""
        content_lower = content.lower()
        secondary = []
        
        for category, keywords in self.category_mapping.items():
            matches = sum(1 for keyword in keywords if keyword in content_lower)
            if matches > 0:
                secondary.append(category)
        
        return secondary[:3]  # Limit to top 3
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extract relevant tags from content."""
        content_lower = content.lower()
        
        # Predefined tag patterns
        tag_patterns = {
            'webhook': ['webhook', 'http trigger'],
            'api': ['api', 'rest', 'endpoint'],
            'database': ['database', 'sql', 'mongodb'],
            'email': ['email', 'smtp', 'mail'],
            'automation': ['automation', 'trigger', 'schedule'],
            'javascript': ['javascript', 'js', 'code node'],
            'json': ['json', 'data transformation'],
            'error-handling': ['error', 'try', 'catch', 'exception']
        }
        
        tags = []
        for tag, patterns in tag_patterns.items():
            if any(pattern in content_lower for pattern in patterns):
                tags.append(tag)
        
        return tags
    
    def _assess_difficulty(self, content: str) -> str:
        """Assess content difficulty level."""
        complexity = self._calculate_complexity(content)
        
        if complexity < 0.3:
            return 'beginner'
        elif complexity < 0.7:
            return 'intermediate'
        else:
            return 'advanced'
    
    def _identify_content_type(self, content: str, metadata: Dict[str, Any]) -> str:
        """Identify the type of content."""
        content_lower = content.lower()
        title = metadata.get('title', '').lower()
        
        if 'tutorial' in title or 'how to' in title:
            return 'tutorial'
        elif 'reference' in title or 'api' in title:
            return 'reference'
        elif 'example' in content_lower or 'sample' in content_lower:
            return 'example'
        elif 'troubleshoot' in content_lower or 'error' in content_lower:
            return 'troubleshooting'
        else:
            return 'documentation'
    
    def _calculate_quality_score(self, content: str, sentiment: float, complexity: float, 
                                readability: float, entity_count: int) -> float:
        """Calculate overall content quality score."""
        try:
            # Length factor (optimal around 500-2000 words)
            word_count = len(content.split())
            length_factor = min(1.0, word_count / 500) if word_count < 500 else min(1.0, 2000 / word_count)
            
            # Entity richness (more entities = more informative)
            entity_factor = min(1.0, entity_count / 10)
            
            # Sentiment factor (neutral to positive is better for documentation)
            sentiment_factor = max(0.5, (sentiment + 1) / 2)
            
            # Combine factors
            quality = (
                length_factor * 0.3 +
                readability * 0.25 +
                entity_factor * 0.2 +
                sentiment_factor * 0.15 +
                (1 - abs(complexity - 0.5)) * 0.1  # Moderate complexity is ideal
            )
            
            return min(1.0, max(0.0, quality))
            
        except Exception as e:
            logger.error(f"Quality score calculation failed: {e}")
            return 0.5


# Factory function
def create_intelligent_processor() -> IntelligentProcessor:
    """Create and return an intelligent processor instance."""
    return IntelligentProcessor()