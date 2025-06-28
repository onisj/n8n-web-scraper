#!/usr/bin/env python3
"""
n8n Documentation Data Analyzer

Analyzes the scraped n8n documentation data to extract insights,
generate reports, and export data in various formats.
"""

import json
import os
import csv
import re
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class N8nDataAnalyzer:
    """Analyzer for scraped n8n documentation data"""
    
    def __init__(self, data_directory: str = "/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs"):
        self.data_dir = data_directory
        self.pages_data = []
        self.summary_data = None
        self.load_data()
    
    def load_data(self):
        """Load all scraped data from JSON files"""
        if not os.path.exists(self.data_dir):
            raise FileNotFoundError(f"Data directory {self.data_dir} not found")
        
        # Load summary
        summary_path = os.path.join(self.data_dir, 'scraping_summary.json')
        if os.path.exists(summary_path):
            with open(summary_path, 'r', encoding='utf-8') as f:
                self.summary_data = json.load(f)
        
        # Load individual pages
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json') and filename != 'scraping_summary.json':
                filepath = os.path.join(self.data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        page_data = json.load(f)
                        self.pages_data.append(page_data)
                except Exception as e:
                    logger.error(f"Error loading {filepath}: {e}")
        
        logger.info(f"Loaded {len(self.pages_data)} pages")
    
    def generate_content_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive content statistics"""
        stats = {
            'total_pages': len(self.pages_data),
            'total_words': sum(page['word_count'] for page in self.pages_data),
            'total_headings': sum(len(page['headings']) for page in self.pages_data),
            'total_links': sum(len(page['links']) for page in self.pages_data),
            'total_code_blocks': sum(len(page['code_blocks']) for page in self.pages_data),
            'total_images': sum(len(page['images']) for page in self.pages_data),
        }
        
        # Word count distribution
        word_counts = [page['word_count'] for page in self.pages_data]
        stats['word_count_stats'] = {
            'min': min(word_counts) if word_counts else 0,
            'max': max(word_counts) if word_counts else 0,
            'avg': sum(word_counts) / len(word_counts) if word_counts else 0
        }
        
        # Page categories (based on URL structure)
        categories = defaultdict(int)
        for page in self.pages_data:
            url_parts = page['url'].replace('https://docs.n8n.io/', '').split('/')
            category = url_parts[0] if url_parts[0] else 'root'
            categories[category] += 1
        
        stats['page_categories'] = dict(categories)
        
        return stats
    
    def analyze_headings(self) -> Dict[str, Any]:
        """Analyze heading structure and content"""
        all_headings = []
        heading_levels = defaultdict(int)
        
        for page in self.pages_data:
            for heading in page['headings']:
                all_headings.append(heading['text'])
                heading_levels[heading['level']] += 1
        
        # Most common headings
        heading_counter = Counter(all_headings)
        
        return {
            'total_headings': len(all_headings),
            'unique_headings': len(set(all_headings)),
            'heading_levels': dict(heading_levels),
            'most_common_headings': heading_counter.most_common(20),
            'heading_patterns': self._analyze_heading_patterns(all_headings)
        }
    
    def _analyze_heading_patterns(self, headings: List[str]) -> Dict[str, int]:
        """Analyze common patterns in headings"""
        patterns = {
            'contains_node': sum(1 for h in headings if 'node' in h.lower()),
            'contains_workflow': sum(1 for h in headings if 'workflow' in h.lower()),
            'contains_api': sum(1 for h in headings if 'api' in h.lower()),
            'contains_integration': sum(1 for h in headings if 'integration' in h.lower()),
            'contains_setup': sum(1 for h in headings if any(word in h.lower() for word in ['setup', 'install', 'configure'])),
            'contains_example': sum(1 for h in headings if 'example' in h.lower()),
        }
        return patterns
    
    def analyze_code_blocks(self) -> Dict[str, Any]:
        """Analyze code blocks and programming languages"""
        all_code_blocks = []
        languages = defaultdict(int)
        code_types = defaultdict(int)
        
        for page in self.pages_data:
            for code_block in page['code_blocks']:
                all_code_blocks.append(code_block['content'])
                
                # Count languages
                lang = code_block.get('language', 'unknown').lower()
                if lang:
                    languages[lang] += 1
                
                # Count types
                code_type = code_block.get('type', 'unknown')
                code_types[code_type] += 1
        
        # Analyze code content patterns
        code_patterns = self._analyze_code_patterns(all_code_blocks)
        
        return {
            'total_code_blocks': len(all_code_blocks),
            'languages': dict(languages),
            'code_types': dict(code_types),
            'code_patterns': code_patterns,
            'avg_code_length': sum(len(code) for code in all_code_blocks) / len(all_code_blocks) if all_code_blocks else 0
        }
    
    def _analyze_code_patterns(self, code_blocks: List[str]) -> Dict[str, int]:
        """Analyze patterns in code blocks"""
        patterns = {
            'contains_npm': sum(1 for code in code_blocks if 'npm' in code.lower()),
            'contains_docker': sum(1 for code in code_blocks if 'docker' in code.lower()),
            'contains_curl': sum(1 for code in code_blocks if 'curl' in code.lower()),
            'contains_json': sum(1 for code in code_blocks if any(char in code for char in ['{', '}', '[', ']'])),
            'contains_url': sum(1 for code in code_blocks if 'http' in code.lower()),
            'contains_api_key': sum(1 for code in code_blocks if any(word in code.lower() for word in ['api_key', 'apikey', 'token'])),
        }
        return patterns
    
    def analyze_links(self) -> Dict[str, Any]:
        """Analyze internal and external links"""
        internal_links = []
        external_links = []
        
        for page in self.pages_data:
            for link in page['links']:
                url = link['url']
                if 'docs.n8n.io' in url:
                    internal_links.append(url)
                else:
                    external_links.append(url)
        
        # Most linked pages
        internal_counter = Counter(internal_links)
        external_domains = Counter([url.split('/')[2] if len(url.split('/')) > 2 else url for url in external_links])
        
        return {
            'total_internal_links': len(internal_links),
            'total_external_links': len(external_links),
            'unique_internal_links': len(set(internal_links)),
            'unique_external_links': len(set(external_links)),
            'most_linked_pages': internal_counter.most_common(10),
            'external_domains': external_domains.most_common(10)
        }
    
    def find_n8n_nodes(self) -> List[Dict[str, Any]]:
        """Extract information about n8n nodes mentioned in documentation"""
        nodes = []
        node_pattern = re.compile(r'\b([A-Z][a-zA-Z]*\s*[Nn]ode)\b')
        
        for page in self.pages_data:
            # Look for node mentions in content
            content = page['content']
            node_matches = node_pattern.findall(content)
            
            # Look for node-specific pages
            if '/integrations/' in page['url'] or '/nodes/' in page['url']:
                node_name = page['title'].replace(' | n8n Docs', '').strip()
                nodes.append({
                    'name': node_name,
                    'url': page['url'],
                    'word_count': page['word_count'],
                    'code_blocks': len(page['code_blocks']),
                    'type': 'integration_page'
                })
            
            # Add nodes found in content
            for match in set(node_matches):
                nodes.append({
                    'name': match,
                    'url': page['url'],
                    'context': 'mentioned_in_content',
                    'type': 'content_mention'
                })
        
        return nodes
    
    def export_to_csv(self, output_file: str = "data/exports/n8n_docs_export.csv"):
        """Export page data to CSV format"""
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['url', 'title', 'word_count', 'headings_count', 'links_count', 'code_blocks_count', 'images_count']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for page in self.pages_data:
                writer.writerow({
                    'url': page['url'],
                    'title': page['title'],
                    'word_count': page['word_count'],
                    'headings_count': len(page['headings']),
                    'links_count': len(page['links']),
                    'code_blocks_count': len(page['code_blocks']),
                    'images_count': len(page['images'])
                })
        
        logger.info(f"Data exported to {output_file}")
    
    def export_content_text(self, output_file: str = "data/analysis/n8n_docs_content.txt"):
        """Export all content as plain text"""
        with open(output_file, 'w', encoding='utf-8') as f:
            for page in self.pages_data:
                f.write(f"\n{'='*80}\n")
                f.write(f"URL: {page['url']}\n")
                f.write(f"Title: {page['title']}\n")
                f.write(f"{'='*80}\n\n")
                f.write(page['content'])
                f.write("\n\n")
        
        logger.info(f"Content exported to {output_file}")
    
    def generate_report(self, output_file: str = "data/analysis/n8n_docs_analysis_report.json"):
        """Generate comprehensive analysis report"""
        report = {
            'analysis_date': datetime.now().isoformat(),
            'data_source': self.data_dir,
            'content_statistics': self.generate_content_statistics(),
            'heading_analysis': self.analyze_headings(),
            'code_analysis': self.analyze_code_blocks(),
            'link_analysis': self.analyze_links(),
            'n8n_nodes': self.find_n8n_nodes()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Analysis report saved to {output_file}")
        return report
    
    def print_summary(self):
        """Print a summary of the analysis"""
        stats = self.generate_content_statistics()
        heading_analysis = self.analyze_headings()
        code_analysis = self.analyze_code_blocks()
        link_analysis = self.analyze_links()
        
        print("\n" + "="*60)
        print("n8n Documentation Analysis Summary")
        print("="*60)
        
        print(f"\nContent Statistics:")
        print(f"  Total Pages: {stats['total_pages']:,}")
        print(f"  Total Words: {stats['total_words']:,}")
        print(f"  Average Words per Page: {stats['word_count_stats']['avg']:.0f}")
        print(f"  Total Headings: {stats['total_headings']:,}")
        print(f"  Total Code Blocks: {stats['total_code_blocks']:,}")
        print(f"  Total Links: {stats['total_links']:,}")
        
        print(f"\nPage Categories:")
        for category, count in sorted(stats['page_categories'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {category}: {count}")
        
        print(f"\nMost Common Headings:")
        for heading, count in heading_analysis['most_common_headings'][:5]:
            print(f"  '{heading}': {count}")
        
        print(f"\nCode Languages:")
        for lang, count in sorted(code_analysis['languages'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {lang}: {count}")
        
        print(f"\nExternal Domains:")
        for domain, count in link_analysis['external_domains'][:5]:
            print(f"  {domain}: {count}")
        
        print("\n" + "="*60)

def main():
    """Main function to run the analyzer"""
    analyzer = N8nDataAnalyzer()
    
    # Print summary
    analyzer.print_summary()
    
    # Generate comprehensive report
    report = analyzer.generate_report()
    
    # Export data in different formats
    analyzer.export_to_csv()
    analyzer.export_content_text()
    
    print("\nAnalysis complete! Check the generated files:")
    print("- n8n_docs_analysis_report.json (comprehensive analysis)")
    print("- n8n_docs_export.csv (structured data)")
    print("- n8n_docs_content.txt (all content as text)")

if __name__ == "__main__":
    main()