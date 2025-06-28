"""
Content processing pipeline for scraped data.
"""

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Callable, Awaitable
from enum import Enum

from ..core.exceptions import ContentProcessingError
from ..core.logging_config import get_logger
from ..core.metrics import metrics, timing_decorator
from .content_extractor import ContentExtractor, ExtractedContent
from .quality_checker import QualityChecker, QualityMetrics, QualityLevel

logger = get_logger(__name__)


class ProcessingStage(Enum):
    """Content processing stages."""
    EXTRACTION = "extraction"
    QUALITY_CHECK = "quality_check"
    CLEANING = "cleaning"
    ENRICHMENT = "enrichment"
    VALIDATION = "validation"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORAGE = "storage"


class ProcessingStatus(Enum):
    """Processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProcessingConfig:
    """Configuration for content processing."""
    # Quality thresholds
    min_quality_score: float = 40.0
    min_word_count: int = 50
    max_word_count: int = 50000
    
    # Processing options
    enable_quality_check: bool = True
    enable_content_cleaning: bool = True
    enable_enrichment: bool = True
    enable_chunking: bool = True
    enable_embedding: bool = True
    
    # Chunking settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_chunks_per_document: int = 100
    
    # Processing limits
    max_concurrent_processes: int = 5
    processing_timeout: int = 300  # seconds
    
    # Content filters
    blocked_content_types: Set[str] = field(default_factory=lambda: {
        'advertisement', 'popup', 'cookie-notice', 'newsletter'
    })
    required_elements: Set[str] = field(default_factory=lambda: {
        'title', 'main_content'
    })


@dataclass
class ProcessingResult:
    """Result of content processing."""
    url: str
    status: ProcessingStatus = ProcessingStatus.PENDING
    extracted_content: Optional[ExtractedContent] = None
    quality_metrics: Optional[QualityMetrics] = None
    processed_content: Optional[str] = None
    chunks: List[str] = field(default_factory=list)
    embeddings: List[List[float]] = field(default_factory=list)
    
    # Processing metadata
    processing_time: float = 0.0
    stages_completed: List[ProcessingStage] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Content metadata
    content_hash: Optional[str] = None
    processing_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        logger.error(f"Processing error for {self.url}: {error}")
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
        logger.warning(f"Processing warning for {self.url}: {warning}")
    
    def mark_stage_completed(self, stage: ProcessingStage) -> None:
        """Mark a processing stage as completed."""
        if stage not in self.stages_completed:
            self.stages_completed.append(stage)


class ContentProcessor:
    """Processes scraped content through various stages."""
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        """Initialize content processor.
        
        Args:
            config: Processing configuration
        """
        self.config = config or ProcessingConfig()
        self.extractor = ContentExtractor()
        self.quality_checker = QualityChecker()
        
        # Processing hooks
        self.pre_processing_hooks: List[Callable[[str, str], Awaitable[None]]] = []
        self.post_processing_hooks: List[Callable[[ProcessingResult], Awaitable[None]]] = []
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'avg_processing_time': 0.0,
            'quality_distribution': {level.value: 0 for level in QualityLevel},
        }
    
    async def process_content(self, html: str, url: str) -> ProcessingResult:
        """Process content through the complete pipeline.
        
        Args:
            html: Raw HTML content
            url: Source URL
        
        Returns:
            Processing result
        """
        result = ProcessingResult(url=url)
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Run pre-processing hooks
            await self._run_pre_processing_hooks(html, url)
            
            result.status = ProcessingStatus.PROCESSING
            
            # Stage 1: Content Extraction
            if not await self._extract_content(html, url, result):
                return result
            
            # Stage 2: Quality Check
            if self.config.enable_quality_check:
                if not await self._check_quality(result):
                    return result
            
            # Stage 3: Content Cleaning
            if self.config.enable_content_cleaning:
                await self._clean_content(result)
            
            # Stage 4: Content Enrichment
            if self.config.enable_enrichment:
                await self._enrich_content(result)
            
            # Stage 5: Content Validation
            if not await self._validate_content(result):
                return result
            
            # Stage 6: Content Chunking
            if self.config.enable_chunking:
                await self._chunk_content(result)
            
            # Stage 7: Generate Embeddings
            if self.config.enable_embedding:
                await self._generate_embeddings(result)
            
            result.status = ProcessingStatus.COMPLETED
            
            # Run post-processing hooks
            await self._run_post_processing_hooks(result)
            
            # Update statistics
            self._update_stats(result, success=True)
            
        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.add_error(f"Processing failed: {str(e)}")
            self._update_stats(result, success=False)
            logger.error(f"Content processing failed for {url}: {e}")
        
        finally:
            result.processing_time = asyncio.get_event_loop().time() - start_time
            metrics.record_histogram("content_processor_duration", result.processing_time)
        
        return result
    
    async def process_multiple(self, content_items: List[tuple[str, str]]) -> List[ProcessingResult]:
        """Process multiple content items concurrently.
        
        Args:
            content_items: List of (html, url) tuples
        
        Returns:
            List of processing results
        """
        semaphore = asyncio.Semaphore(self.config.max_concurrent_processes)
        
        async def process_with_semaphore(html: str, url: str) -> ProcessingResult:
            async with semaphore:
                return await self.process_content(html, url)
        
        tasks = [
            process_with_semaphore(html, url)
            for html, url in content_items
        ]
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.processing_timeout
            )
            
            # Handle exceptions in results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    url = content_items[i][1]
                    error_result = ProcessingResult(url=url)
                    error_result.status = ProcessingStatus.FAILED
                    error_result.add_error(f"Processing exception: {str(result)}")
                    processed_results.append(error_result)
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except asyncio.TimeoutError:
            logger.error(f"Batch processing timed out after {self.config.processing_timeout}s")
            # Return partial results with timeout errors
            return [
                ProcessingResult(
                    url=url,
                    status=ProcessingStatus.FAILED,
                    errors=["Processing timed out"]
                )
                for _, url in content_items
            ]
    
    async def _extract_content(self, html: str, url: str, result: ProcessingResult) -> bool:
        """Extract content from HTML.
        
        Args:
            html: Raw HTML
            url: Source URL
            result: Processing result to update
        
        Returns:
            True if successful
        """
        try:
            result.extracted_content = self.extractor.extract(html, url)
            result.mark_stage_completed(ProcessingStage.EXTRACTION)
            
            # Check for required elements
            for element in self.config.required_elements:
                if not getattr(result.extracted_content, element, None):
                    result.status = ProcessingStatus.FAILED
                    result.add_error(f"Missing required element: {element}")
                    return False
            
            metrics.increment_counter("content_processor_extraction_success")
            return True
            
        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.add_error(f"Content extraction failed: {str(e)}")
            metrics.increment_counter("content_processor_extraction_errors")
            return False
    
    async def _check_quality(self, result: ProcessingResult) -> bool:
        """Check content quality.
        
        Args:
            result: Processing result to update
        
        Returns:
            True if quality is acceptable
        """
        try:
            result.quality_metrics = self.quality_checker.assess_quality(result.extracted_content)
            result.mark_stage_completed(ProcessingStage.QUALITY_CHECK)
            
            # Check quality thresholds
            if result.quality_metrics.overall_score < self.config.min_quality_score:
                result.status = ProcessingStatus.SKIPPED
                result.add_warning(f"Quality score {result.quality_metrics.overall_score} below threshold {self.config.min_quality_score}")
                return False
            
            # Check word count
            word_count = result.quality_metrics.word_count
            if word_count < self.config.min_word_count:
                result.status = ProcessingStatus.SKIPPED
                result.add_warning(f"Word count {word_count} below minimum {self.config.min_word_count}")
                return False
            
            if word_count > self.config.max_word_count:
                result.add_warning(f"Word count {word_count} exceeds maximum {self.config.max_word_count}")
            
            metrics.increment_counter("content_processor_quality_check_success")
            return True
            
        except Exception as e:
            result.add_error(f"Quality check failed: {str(e)}")
            metrics.increment_counter("content_processor_quality_check_errors")
            return True  # Continue processing even if quality check fails
    
    async def _clean_content(self, result: ProcessingResult) -> None:
        """Clean and normalize content.
        
        Args:
            result: Processing result to update
        """
        try:
            content = result.extracted_content.main_content
            
            # Remove excessive whitespace
            content = ' '.join(content.split())
            
            # Remove blocked content patterns
            for blocked_type in self.config.blocked_content_types:
                # Simple pattern matching - could be enhanced
                content = content.replace(blocked_type, '')
            
            # Normalize unicode
            import unicodedata
            content = unicodedata.normalize('NFKC', content)
            
            # Update processed content
            result.processed_content = content
            result.content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
            
            result.mark_stage_completed(ProcessingStage.CLEANING)
            metrics.increment_counter("content_processor_cleaning_success")
            
        except Exception as e:
            result.add_error(f"Content cleaning failed: {str(e)}")
            metrics.increment_counter("content_processor_cleaning_errors")
    
    async def _enrich_content(self, result: ProcessingResult) -> None:
        """Enrich content with additional metadata.
        
        Args:
            result: Processing result to update
        """
        try:
            # Add processing metadata
            if result.extracted_content:
                # Extract keywords from content
                keywords = self._extract_keywords(result.processed_content or result.extracted_content.main_content)
                result.extracted_content.metadata['extracted_keywords'] = keywords
                
                # Add content statistics
                result.extracted_content.metadata['processing_stats'] = {
                    'stages_completed': [stage.value for stage in result.stages_completed],
                    'processing_timestamp': result.processing_timestamp.isoformat(),
                    'content_hash': result.content_hash,
                }
            
            result.mark_stage_completed(ProcessingStage.ENRICHMENT)
            metrics.increment_counter("content_processor_enrichment_success")
            
        except Exception as e:
            result.add_error(f"Content enrichment failed: {str(e)}")
            metrics.increment_counter("content_processor_enrichment_errors")
    
    def _extract_keywords(self, content: str, max_keywords: int = 20) -> List[str]:
        """Extract keywords from content.
        
        Args:
            content: Content text
            max_keywords: Maximum number of keywords
        
        Returns:
            List of keywords
        """
        if not content:
            return []
        
        # Simple keyword extraction - could be enhanced with NLP
        import re
        from collections import Counter
        
        # Extract words (alphanumeric, 3+ chars)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        
        # Common stop words to filter out
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our',
            'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way',
            'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'this', 'that', 'with', 'have',
            'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come',
            'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well',
            'were', 'will', 'would', 'there', 'could', 'other', 'after', 'first', 'little', 'only', 'right',
            'think', 'where', 'being', 'every', 'great', 'might', 'shall', 'still', 'those', 'under', 'while'
        }
        
        # Filter stop words and count
        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
        word_counts = Counter(filtered_words)
        
        # Return most common keywords
        return [word for word, _ in word_counts.most_common(max_keywords)]
    
    async def _validate_content(self, result: ProcessingResult) -> bool:
        """Validate processed content.
        
        Args:
            result: Processing result to update
        
        Returns:
            True if validation passes
        """
        try:
            # Check if we have content to work with
            content = result.processed_content or (result.extracted_content.main_content if result.extracted_content else None)
            
            if not content or len(content.strip()) < 10:
                result.status = ProcessingStatus.FAILED
                result.add_error("Insufficient content after processing")
                return False
            
            # Validate content hash
            if not result.content_hash:
                result.content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
            
            result.mark_stage_completed(ProcessingStage.VALIDATION)
            metrics.increment_counter("content_processor_validation_success")
            return True
            
        except Exception as e:
            result.add_error(f"Content validation failed: {str(e)}")
            metrics.increment_counter("content_processor_validation_errors")
            return False
    
    async def _chunk_content(self, result: ProcessingResult) -> None:
        """Split content into chunks.
        
        Args:
            result: Processing result to update
        """
        try:
            content = result.processed_content or (result.extracted_content.main_content if result.extracted_content else "")
            
            if not content:
                result.add_warning("No content to chunk")
                return
            
            # Simple word-based chunking
            words = content.split()
            chunks = []
            
            for i in range(0, len(words), self.config.chunk_size - self.config.chunk_overlap):
                chunk_words = words[i:i + self.config.chunk_size]
                chunk_text = ' '.join(chunk_words)
                
                if len(chunk_text.strip()) > 50:  # Minimum chunk size
                    chunks.append(chunk_text)
                
                # Limit number of chunks
                if len(chunks) >= self.config.max_chunks_per_document:
                    result.add_warning(f"Reached maximum chunks limit ({self.config.max_chunks_per_document})")
                    break
            
            result.chunks = chunks
            result.mark_stage_completed(ProcessingStage.CHUNKING)
            metrics.increment_counter("content_processor_chunking_success")
            metrics.record_histogram("content_processor_chunks_count", len(chunks))
            
        except Exception as e:
            result.add_error(f"Content chunking failed: {str(e)}")
            metrics.increment_counter("content_processor_chunking_errors")
    
    async def _generate_embeddings(self, result: ProcessingResult) -> None:
        """Generate embeddings for content chunks.
        
        Args:
            result: Processing result to update
        """
        try:
            if not result.chunks:
                result.add_warning("No chunks available for embedding generation")
                return
            
            # Placeholder for embedding generation
            # In a real implementation, this would use a sentence transformer or API
            embeddings = []
            
            for chunk in result.chunks:
                # Simulate embedding generation
                # In practice, use sentence-transformers, OpenAI embeddings, etc.
                embedding = [0.0] * 384  # Placeholder 384-dimensional embedding
                embeddings.append(embedding)
            
            result.embeddings = embeddings
            result.mark_stage_completed(ProcessingStage.EMBEDDING)
            metrics.increment_counter("content_processor_embedding_success")
            
        except Exception as e:
            result.add_error(f"Embedding generation failed: {str(e)}")
            metrics.increment_counter("content_processor_embedding_errors")
    
    async def _run_pre_processing_hooks(self, html: str, url: str) -> None:
        """Run pre-processing hooks.
        
        Args:
            html: Raw HTML content
            url: Source URL
        """
        for hook in self.pre_processing_hooks:
            try:
                await hook(html, url)
            except Exception as e:
                logger.warning(f"Pre-processing hook failed for {url}: {e}")
    
    async def _run_post_processing_hooks(self, result: ProcessingResult) -> None:
        """Run post-processing hooks.
        
        Args:
            result: Processing result
        """
        for hook in self.post_processing_hooks:
            try:
                await hook(result)
            except Exception as e:
                logger.warning(f"Post-processing hook failed for {result.url}: {e}")
    
    def _update_stats(self, result: ProcessingResult, success: bool) -> None:
        """Update processing statistics.
        
        Args:
            result: Processing result
            success: Whether processing was successful
        """
        self.stats['total_processed'] += 1
        
        if success:
            self.stats['successful'] += 1
        elif result.status == ProcessingStatus.SKIPPED:
            self.stats['skipped'] += 1
        else:
            self.stats['failed'] += 1
        
        # Update average processing time
        total = self.stats['total_processed']
        current_avg = self.stats['avg_processing_time']
        self.stats['avg_processing_time'] = ((current_avg * (total - 1)) + result.processing_time) / total
        
        # Update quality distribution
        if result.quality_metrics:
            level = result.quality_metrics.overall_level.value
            self.stats['quality_distribution'][level] += 1
    
    def add_pre_processing_hook(self, hook: Callable[[str, str], Awaitable[None]]) -> None:
        """Add a pre-processing hook.
        
        Args:
            hook: Async function that takes (html, url) and returns None
        """
        self.pre_processing_hooks.append(hook)
    
    def add_post_processing_hook(self, hook: Callable[[ProcessingResult], Awaitable[None]]) -> None:
        """Add a post-processing hook.
        
        Args:
            hook: Async function that takes ProcessingResult and returns None
        """
        self.post_processing_hooks.append(hook)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics.
        
        Returns:
            Statistics dictionary
        """
        return self.stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset processing statistics."""
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'avg_processing_time': 0.0,
            'quality_distribution': {level.value: 0 for level in QualityLevel},
        }