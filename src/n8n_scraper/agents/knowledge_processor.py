#!/usr/bin/env python3
"""
N8n Knowledge Processor

Transforms scraped n8n documentation into structured knowledge format
for AI agent consumption and vector database storage.
"""

import json
import os
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
import hashlib
from pathlib import Path

@dataclass
class KnowledgeChunk:
    """Represents a processed knowledge chunk"""
    id: str
    title: str
    content: str
    category: str
    subcategory: str
    url: str
    metadata: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    embeddings: Optional[List[float]] = None
    created_at: str = None
    updated_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at

@dataclass
class ProcessedKnowledge:
    """Container for all processed knowledge"""
    chunks: List[KnowledgeChunk]
    categories: Dict[str, int]
    total_chunks: int
    processing_date: str
    version: str = "1.0"

class N8nKnowledgeProcessor:
    """Processes n8n documentation into structured knowledge format"""
    
    def __init__(self, data_directory: str = "n8n_docs_data"):
        self.data_directory = Path(data_directory)
        self.processed_chunks = []
        self.categories = {}
        
        # Category mappings for better organization
        self.category_mappings = {
            'advanced-ai': 'AI & Machine Learning',
            'api': 'API & Integration',
            'code': 'Code & Development',
            'hosting': 'Hosting & Deployment',
            'integrations': 'Node Integrations',
            'data': 'Data Management',
            'flow-logic': 'Workflow Logic',
            'credentials': 'Authentication',
            'embed': 'Embedding',
            'courses': 'Learning Resources',
            'glossary': 'Reference',
            'help-community': 'Community & Support'
        }
    
    def process_all_files(self) -> ProcessedKnowledge:
        """Process all JSON files in the data directory"""
        print(f"Processing files from: {self.data_directory}")
        
        if not self.data_directory.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_directory}")
        
        json_files = list(self.data_directory.glob("*.json"))
        print(f"Found {len(json_files)} JSON files to process")
        
        for file_path in json_files:
            try:
                self._process_file(file_path)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
        
        # Count categories
        for chunk in self.processed_chunks:
            category = chunk.category
            self.categories[category] = self.categories.get(category, 0) + 1
        
        return ProcessedKnowledge(
            chunks=self.processed_chunks,
            categories=self.categories,
            total_chunks=len(self.processed_chunks),
            processing_date=datetime.now().isoformat()
        )
    
    def _process_file(self, file_path: Path) -> None:
        """Process a single JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract category and subcategory from filename
        filename = file_path.stem
        category, subcategory = self._extract_categories(filename)
        
        # Create knowledge chunk
        chunk = self._create_knowledge_chunk(data, category, subcategory, filename)
        if chunk:
            self.processed_chunks.append(chunk)
    
    def _extract_categories(self, filename: str) -> tuple[str, str]:
        """Extract category and subcategory from filename"""
        parts = filename.split('_')
        
        if len(parts) >= 2:
            main_category = parts[0]
            subcategory = '_'.join(parts[1:]) if len(parts) > 2 else parts[1]
        else:
            main_category = parts[0]
            subcategory = 'general'
        
        # Map to friendly category name
        friendly_category = self.category_mappings.get(main_category, main_category.title())
        
        return friendly_category, subcategory
    
    def _create_knowledge_chunk(self, data: Dict, category: str, subcategory: str, filename: str) -> Optional[KnowledgeChunk]:
        """Create a knowledge chunk from scraped data"""
        try:
            # Extract basic information
            title = data.get('title', 'Untitled')
            content = data.get('content', '')
            url = data.get('url', '')
            
            # Skip if no meaningful content
            if not content or len(content.strip()) < 50:
                return None
            
            # Clean and process content
            processed_content = self._clean_content(content)
            
            # Extract metadata
            metadata = self._extract_metadata(data)
            
            # Extract tags from content and metadata
            tags = self._extract_tags(data, category, subcategory)
            
            # Generate unique ID
            chunk_id = self._generate_chunk_id(url, title, content)
            
            return KnowledgeChunk(
                id=chunk_id,
                title=title,
                content=processed_content,
                category=category,
                subcategory=subcategory,
                url=url,
                metadata=metadata,
                tags=tags
            )
            
        except Exception as e:
            print(f"Error creating chunk for {filename}: {e}")
            return None
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content text"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove HTML tags if any
        content = re.sub(r'<[^>]+>', '', content)
        
        # Normalize quotes
        content = content.replace('"', '\"')
        
        # Remove extra spaces
        content = ' '.join(content.split())
        
        return content.strip()
    
    def _extract_metadata(self, data: Dict) -> Dict[str, Any]:
        """Extract metadata from scraped data"""
        metadata = {
            'scraped_at': data.get('scraped_at', ''),
            'last_modified': data.get('last_modified', ''),
            'word_count': len(data.get('content', '').split()),
            'has_code_examples': bool(re.search(r'```|<code>', data.get('content', ''))),
            'section_count': len(re.findall(r'#+\s', data.get('content', ''))),
        }
        
        # Add any additional metadata from the original data
        for key, value in data.items():
            if key not in ['title', 'content', 'url'] and not key.startswith('_'):
                metadata[key] = value
        
        return metadata
    
    def _extract_tags(self, data: Dict, category: str, subcategory: str) -> List[str]:
        """Extract tags from content and metadata"""
        tags = []
        
        # Add category and subcategory as tags
        tags.append(category.lower())
        tags.append(subcategory.lower())
        
        # Extract node names and technical terms from content
        content = data.get('content', '').lower()
        title = data.get('title', '').lower()
        
        # Common n8n node patterns
        node_patterns = [
            r'\b(\w+)\s+node\b',
            r'\b(http|webhook|code|function|if|switch|merge|split)\b',
            r'\b(gmail|slack|discord|telegram|twitter|facebook)\b',
            r'\b(mysql|postgres|mongodb|redis|elasticsearch)\b',
            r'\b(api|rest|graphql|json|xml|csv)\b'
        ]
        
        for pattern in node_patterns:
            matches = re.findall(pattern, content + ' ' + title)
            tags.extend(matches)
        
        # Remove duplicates and filter out common words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        tags = list(set([tag for tag in tags if tag not in stop_words and len(tag) > 2]))
        
        return tags[:10]  # Limit to 10 tags
    
    def _generate_chunk_id(self, url: str, title: str, content: str) -> str:
        """Generate a unique ID for the knowledge chunk"""
        # Create a hash from URL, title, and content snippet
        content_snippet = content[:200] if content else ''
        hash_input = f"{url}:{title}:{content_snippet}"
        return hashlib.md5(hash_input.encode('utf-8')).hexdigest()[:16]
    
    def save_processed_knowledge(self, processed_knowledge: ProcessedKnowledge, output_file: str = "processed_knowledge.json") -> None:
        """Save processed knowledge to a JSON file"""
        output_path = self.data_directory / output_file
        
        # Convert to dictionary for JSON serialization
        data = asdict(processed_knowledge)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Processed knowledge saved to: {output_path}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'total_chunks': len(self.processed_chunks),
            'categories': dict(self.categories),
            'avg_content_length': sum(len(chunk.content) for chunk in self.processed_chunks) / len(self.processed_chunks) if self.processed_chunks else 0,
            'chunks_with_code': sum(1 for chunk in self.processed_chunks if chunk.metadata.get('has_code_examples', False))
        }

if __name__ == "__main__":
    # Example usage - using agent manager to prevent duplicates
    from n8n_scraper.optimization.agent_manager import get_knowledge_processor
    
    processor = get_knowledge_processor()
    try:
        knowledge = processor.process_all_files()
        processor.save_processed_knowledge(knowledge)
        print(f"Processing complete! Generated {knowledge.total_chunks} knowledge chunks.")
        print(f"Categories: {list(knowledge.categories.keys())}")
    except Exception as e:
        print(f"Error during processing: {e}")