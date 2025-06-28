"""
Content quality assessment utilities.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any
from enum import Enum

from ..core.logging_config import get_logger
from ..core.metrics import metrics, timing_decorator
from .content_extractor import ExtractedContent

logger = get_logger(__name__)


class QualityLevel(Enum):
    """Content quality levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    VERY_POOR = "very_poor"


@dataclass
class QualityMetrics:
    """Content quality metrics."""
    overall_score: float = 0.0
    overall_level: QualityLevel = QualityLevel.POOR
    
    # Individual metric scores (0-100)
    content_length_score: float = 0.0
    readability_score: float = 0.0
    structure_score: float = 0.0
    uniqueness_score: float = 0.0
    completeness_score: float = 0.0
    technical_quality_score: float = 0.0
    
    # Detailed metrics
    word_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    avg_sentence_length: float = 0.0
    avg_paragraph_length: float = 0.0
    
    # Structure metrics
    has_title: bool = False
    has_headings: bool = False
    has_description: bool = False
    heading_hierarchy_score: float = 0.0
    
    # Content type indicators
    has_code_blocks: bool = False
    has_tables: bool = False
    has_lists: bool = False
    has_images: bool = False
    has_links: bool = False
    
    # Quality indicators
    duplicate_content_ratio: float = 0.0
    boilerplate_ratio: float = 0.0
    noise_ratio: float = 0.0
    
    # Issues found
    issues: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        """Initialize lists if None."""
        if self.issues is None:
            self.issues = []
        if self.warnings is None:
            self.warnings = []


class QualityChecker:
    """Assesses the quality of extracted content."""
    
    def __init__(self):
        """Initialize quality checker."""
        # Common boilerplate patterns
        self.boilerplate_patterns = [
            r'copyright\s+\d{4}',
            r'all\s+rights\s+reserved',
            r'privacy\s+policy',
            r'terms\s+of\s+service',
            r'cookie\s+policy',
            r'subscribe\s+to\s+newsletter',
            r'follow\s+us\s+on',
            r'share\s+this\s+article',
            r'related\s+articles',
            r'you\s+might\s+also\s+like',
            r'advertisement',
            r'sponsored\s+content',
        ]
        
        # Noise patterns
        self.noise_patterns = [
            r'\b(click|tap)\s+here\b',
            r'\bread\s+more\b',
            r'\blearn\s+more\b',
            r'\bsee\s+also\b',
            r'\bview\s+all\b',
            r'\bshow\s+more\b',
            r'\bload\s+more\b',
            r'\bnext\s+page\b',
            r'\bprevious\s+page\b',
        ]
        
        # Technical content indicators
        self.technical_indicators = [
            r'\bapi\b',
            r'\bfunction\b',
            r'\bmethod\b',
            r'\bclass\b',
            r'\bvariable\b',
            r'\bparameter\b',
            r'\breturn\b',
            r'\bexample\b',
            r'\btutorial\b',
            r'\bguide\b',
            r'\bdocumentation\b',
            r'\binstall\b',
            r'\bconfigure\b',
            r'\bsetup\b',
        ]
        
        # Quality thresholds
        self.quality_thresholds = {
            QualityLevel.EXCELLENT: 85.0,
            QualityLevel.GOOD: 70.0,
            QualityLevel.FAIR: 55.0,
            QualityLevel.POOR: 40.0,
            QualityLevel.VERY_POOR: 0.0,
        }
    
    @timing_decorator("quality_checker_assess")
    def assess_quality(self, content: ExtractedContent) -> QualityMetrics:
        """Assess content quality.
        
        Args:
            content: Extracted content to assess
        
        Returns:
            Quality metrics
        """
        metrics_obj = QualityMetrics()
        
        try:
            # Basic content metrics
            self._calculate_basic_metrics(content, metrics_obj)
            
            # Individual quality scores
            metrics_obj.content_length_score = self._assess_content_length(content)
            metrics_obj.readability_score = self._assess_readability(content)
            metrics_obj.structure_score = self._assess_structure(content, metrics_obj)
            metrics_obj.uniqueness_score = self._assess_uniqueness(content, metrics_obj)
            metrics_obj.completeness_score = self._assess_completeness(content, metrics_obj)
            metrics_obj.technical_quality_score = self._assess_technical_quality(content)
            
            # Calculate overall score
            metrics_obj.overall_score = self._calculate_overall_score(metrics_obj)
            metrics_obj.overall_level = self._determine_quality_level(metrics_obj.overall_score)
            
            # Identify issues and warnings
            self._identify_issues(content, metrics_obj)
            
            metrics.increment_counter("quality_checker_success")
            return metrics_obj
            
        except Exception as e:
            metrics.increment_counter("quality_checker_errors")
            logger.error(f"Quality assessment failed: {e}")
            return metrics_obj  # Return partial results
    
    def _calculate_basic_metrics(self, content: ExtractedContent, metrics_obj: QualityMetrics) -> None:
        """Calculate basic content metrics.
        
        Args:
            content: Extracted content
            metrics_obj: Metrics object to update
        """
        text = content.main_content
        
        # Word and sentence counts
        metrics_obj.word_count = len(text.split()) if text else 0
        
        sentences = re.split(r'[.!?]+', text) if text else []
        metrics_obj.sentence_count = len([s for s in sentences if s.strip()])
        
        paragraphs = text.split('\n\n') if text else []
        metrics_obj.paragraph_count = len([p for p in paragraphs if p.strip()])
        
        # Average lengths
        if metrics_obj.sentence_count > 0:
            metrics_obj.avg_sentence_length = metrics_obj.word_count / metrics_obj.sentence_count
        
        if metrics_obj.paragraph_count > 0:
            metrics_obj.avg_paragraph_length = metrics_obj.sentence_count / metrics_obj.paragraph_count
        
        # Structure indicators
        metrics_obj.has_title = bool(content.title.strip())
        metrics_obj.has_headings = len(content.headings) > 0
        metrics_obj.has_description = bool(content.description.strip())
        
        # Content type indicators
        metrics_obj.has_code_blocks = len(content.code_blocks) > 0
        metrics_obj.has_tables = len(content.tables) > 0
        metrics_obj.has_lists = len(content.lists) > 0
        metrics_obj.has_images = len(content.images) > 0
        metrics_obj.has_links = len(content.links) > 0
    
    def _assess_content_length(self, content: ExtractedContent) -> float:
        """Assess content length quality.
        
        Args:
            content: Extracted content
        
        Returns:
            Content length score (0-100)
        """
        word_count = len(content.main_content.split()) if content.main_content else 0
        
        # Optimal range: 300-2000 words
        if word_count < 50:
            return 10.0  # Too short
        elif word_count < 150:
            return 30.0  # Short but acceptable
        elif word_count < 300:
            return 60.0  # Good minimum
        elif word_count <= 2000:
            return 100.0  # Optimal range
        elif word_count <= 5000:
            return 80.0  # Long but good
        else:
            return 60.0  # Very long, might be overwhelming
    
    def _assess_readability(self, content: ExtractedContent) -> float:
        """Assess content readability.
        
        Args:
            content: Extracted content
        
        Returns:
            Readability score (0-100)
        """
        text = content.main_content
        if not text:
            return 0.0
        
        score = 0.0
        
        # Sentence length assessment
        sentences = re.split(r'[.!?]+', text)
        valid_sentences = [s.strip() for s in sentences if s.strip()]
        
        if valid_sentences:
            avg_sentence_length = sum(len(s.split()) for s in valid_sentences) / len(valid_sentences)
            
            # Optimal sentence length: 15-20 words
            if 10 <= avg_sentence_length <= 25:
                score += 30.0
            elif 8 <= avg_sentence_length <= 30:
                score += 20.0
            else:
                score += 10.0
        
        # Paragraph structure
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if paragraphs:
            avg_paragraph_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs)
            
            # Optimal paragraph length: 50-150 words
            if 30 <= avg_paragraph_length <= 200:
                score += 25.0
            elif 20 <= avg_paragraph_length <= 300:
                score += 15.0
            else:
                score += 5.0
        
        # Text complexity indicators
        complex_words = len(re.findall(r'\b\w{10,}\b', text))
        total_words = len(text.split())
        
        if total_words > 0:
            complexity_ratio = complex_words / total_words
            if complexity_ratio < 0.1:
                score += 25.0  # Good balance
            elif complexity_ratio < 0.2:
                score += 15.0  # Acceptable
            else:
                score += 5.0   # Too complex
        
        # Formatting indicators
        if content.headings:
            score += 20.0  # Well-structured with headings
        
        return min(score, 100.0)
    
    def _assess_structure(self, content: ExtractedContent, metrics_obj: QualityMetrics) -> float:
        """Assess content structure quality.
        
        Args:
            content: Extracted content
            metrics_obj: Metrics object
        
        Returns:
            Structure score (0-100)
        """
        score = 0.0
        
        # Title presence and quality
        if content.title:
            score += 20.0
            if 10 <= len(content.title.split()) <= 15:
                score += 10.0  # Good title length
        
        # Description presence
        if content.description:
            score += 15.0
        
        # Heading hierarchy
        if content.headings:
            score += 20.0
            
            # Check heading hierarchy
            heading_levels = [h['level'] for h in content.headings]
            if self._has_good_heading_hierarchy(heading_levels):
                score += 15.0
                metrics_obj.heading_hierarchy_score = 100.0
            else:
                metrics_obj.heading_hierarchy_score = 50.0
        
        # Content organization
        if content.lists:
            score += 10.0  # Lists improve readability
        
        if content.tables:
            score += 10.0  # Tables for structured data
        
        # Metadata completeness
        if content.author:
            score += 5.0
        
        if content.published_date:
            score += 5.0
        
        if content.tags:
            score += 5.0
        
        return min(score, 100.0)
    
    def _has_good_heading_hierarchy(self, levels: List[int]) -> bool:
        """Check if heading hierarchy is well-structured.
        
        Args:
            levels: List of heading levels
        
        Returns:
            True if hierarchy is good
        """
        if not levels:
            return False
        
        # Should start with h1 or h2
        if levels[0] > 2:
            return False
        
        # Check for logical progression
        for i in range(1, len(levels)):
            # Don't skip more than one level
            if levels[i] - levels[i-1] > 1:
                return False
        
        return True
    
    def _assess_uniqueness(self, content: ExtractedContent, metrics_obj: QualityMetrics) -> float:
        """Assess content uniqueness (detect boilerplate/duplicate content).
        
        Args:
            content: Extracted content
            metrics_obj: Metrics object to update
        
        Returns:
            Uniqueness score (0-100)
        """
        text = content.main_content.lower() if content.main_content else ""
        if not text:
            return 0.0
        
        total_chars = len(text)
        boilerplate_chars = 0
        
        # Check for boilerplate patterns
        for pattern in self.boilerplate_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            boilerplate_chars += sum(len(match) for match in matches)
        
        # Check for repetitive content
        sentences = re.split(r'[.!?]+', text)
        unique_sentences = set(s.strip() for s in sentences if s.strip())
        
        if sentences:
            duplicate_ratio = 1 - (len(unique_sentences) / len(sentences))
            metrics_obj.duplicate_content_ratio = duplicate_ratio
        
        # Calculate boilerplate ratio
        if total_chars > 0:
            metrics_obj.boilerplate_ratio = boilerplate_chars / total_chars
        
        # Calculate uniqueness score
        score = 100.0
        score -= metrics_obj.boilerplate_ratio * 50  # Penalize boilerplate
        score -= metrics_obj.duplicate_content_ratio * 30  # Penalize duplicates
        
        return max(score, 0.0)
    
    def _assess_completeness(self, content: ExtractedContent, metrics_obj: QualityMetrics) -> float:
        """Assess content completeness.
        
        Args:
            content: Extracted content
            metrics_obj: Metrics object
        
        Returns:
            Completeness score (0-100)
        """
        score = 0.0
        
        # Essential elements
        if content.title:
            score += 25.0
        
        if content.main_content and len(content.main_content.split()) >= 100:
            score += 40.0  # Substantial content
        elif content.main_content:
            score += 20.0  # Some content
        
        # Additional elements
        if content.description:
            score += 10.0
        
        if content.headings:
            score += 10.0
        
        if content.author:
            score += 5.0
        
        if content.published_date:
            score += 5.0
        
        if content.tags:
            score += 5.0
        
        return min(score, 100.0)
    
    def _assess_technical_quality(self, content: ExtractedContent) -> float:
        """Assess technical content quality.
        
        Args:
            content: Extracted content
        
        Returns:
            Technical quality score (0-100)
        """
        text = content.main_content.lower() if content.main_content else ""
        if not text:
            return 0.0
        
        score = 50.0  # Base score
        
        # Check for technical indicators
        technical_matches = 0
        for pattern in self.technical_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                technical_matches += 1
        
        # Bonus for technical content
        if technical_matches >= 5:
            score += 30.0
        elif technical_matches >= 3:
            score += 20.0
        elif technical_matches >= 1:
            score += 10.0
        
        # Code blocks indicate technical content
        if content.code_blocks:
            score += 20.0
        
        # Tables often contain technical data
        if content.tables:
            score += 10.0
        
        # Check for noise patterns
        noise_chars = 0
        total_chars = len(text)
        
        for pattern in self.noise_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            noise_chars += sum(len(match) for match in matches)
        
        if total_chars > 0:
            noise_ratio = noise_chars / total_chars
            score -= noise_ratio * 30  # Penalize noise
        
        return max(min(score, 100.0), 0.0)
    
    def _calculate_overall_score(self, metrics_obj: QualityMetrics) -> float:
        """Calculate overall quality score.
        
        Args:
            metrics_obj: Quality metrics
        
        Returns:
            Overall score (0-100)
        """
        # Weighted average of individual scores
        weights = {
            'content_length': 0.15,
            'readability': 0.25,
            'structure': 0.20,
            'uniqueness': 0.15,
            'completeness': 0.15,
            'technical_quality': 0.10,
        }
        
        weighted_score = (
            metrics_obj.content_length_score * weights['content_length'] +
            metrics_obj.readability_score * weights['readability'] +
            metrics_obj.structure_score * weights['structure'] +
            metrics_obj.uniqueness_score * weights['uniqueness'] +
            metrics_obj.completeness_score * weights['completeness'] +
            metrics_obj.technical_quality_score * weights['technical_quality']
        )
        
        return round(weighted_score, 2)
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level from score.
        
        Args:
            score: Overall quality score
        
        Returns:
            Quality level
        """
        for level, threshold in self.quality_thresholds.items():
            if score >= threshold:
                return level
        
        return QualityLevel.VERY_POOR
    
    def _identify_issues(self, content: ExtractedContent, metrics_obj: QualityMetrics) -> None:
        """Identify content issues and warnings.
        
        Args:
            content: Extracted content
            metrics_obj: Metrics object to update
        """
        issues = []
        warnings = []
        
        # Critical issues
        if not content.title:
            issues.append("Missing title")
        
        if not content.main_content or len(content.main_content.split()) < 50:
            issues.append("Insufficient content length")
        
        if metrics_obj.boilerplate_ratio > 0.3:
            issues.append("High boilerplate content ratio")
        
        if metrics_obj.duplicate_content_ratio > 0.5:
            issues.append("High duplicate content ratio")
        
        # Warnings
        if not content.description:
            warnings.append("Missing description")
        
        if not content.headings:
            warnings.append("No headings found - poor structure")
        
        if metrics_obj.avg_sentence_length > 30:
            warnings.append("Sentences too long - poor readability")
        
        if metrics_obj.avg_sentence_length < 8:
            warnings.append("Sentences too short - choppy reading")
        
        if not content.author:
            warnings.append("Missing author information")
        
        if not content.published_date:
            warnings.append("Missing publication date")
        
        metrics_obj.issues = issues
        metrics_obj.warnings = warnings
    
    def is_high_quality(self, metrics_obj: QualityMetrics) -> bool:
        """Check if content meets high quality standards.
        
        Args:
            metrics_obj: Quality metrics
        
        Returns:
            True if high quality
        """
        return metrics_obj.overall_level in [QualityLevel.EXCELLENT, QualityLevel.GOOD]
    
    def get_quality_summary(self, metrics_obj: QualityMetrics) -> str:
        """Get human-readable quality summary.
        
        Args:
            metrics_obj: Quality metrics
        
        Returns:
            Quality summary text
        """
        summary_parts = [
            f"Overall Quality: {metrics_obj.overall_level.value.title()} ({metrics_obj.overall_score:.1f}/100)",
            f"Word Count: {metrics_obj.word_count}",
            f"Structure Score: {metrics_obj.structure_score:.1f}/100",
            f"Readability Score: {metrics_obj.readability_score:.1f}/100",
        ]
        
        if metrics_obj.issues:
            summary_parts.append(f"Issues: {', '.join(metrics_obj.issues)}")
        
        if metrics_obj.warnings:
            summary_parts.append(f"Warnings: {', '.join(metrics_obj.warnings)}")
        
        return " | ".join(summary_parts)