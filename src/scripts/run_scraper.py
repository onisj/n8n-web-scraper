#!/usr/bin/env python3
"""
n8n Documentation Scraper Runner

A simple script to run the n8n documentation scraper with various options.
"""

import argparse
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from n8n_scraper.automation.knowledge_updater import N8nDocsScraper
from n8n_scraper.automation.change_detector import N8nDataAnalyzer

def run_scraper(max_pages=None, delay=1.0, base_url="https://docs.n8n.io/"):
    """Run the scraper with specified parameters"""
    print(f"Starting n8n documentation scraper...")
    print(f"Base URL: {base_url}")
    print(f"Delay: {delay} seconds")
    print(f"Max pages: {max_pages if max_pages else 'Unlimited'}")
    print("-" * 50)
    
    scraper = N8nDocsScraper(base_url=base_url, delay=delay)
    scraper.run(max_pages=max_pages)
    
    print("\nScraping completed successfully!")
    print(f"Data saved to: {scraper.output_dir}")
    return scraper.output_dir

def run_analyzer(data_dir="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs"):
    """Run the data analyzer"""
    print(f"\nStarting data analysis...")
    print(f"Data directory: {data_dir}")
    print("-" * 50)
    
    if not os.path.exists(data_dir):
        print(f"Error: Data directory '{data_dir}' not found.")
        print("Please run the scraper first.")
        return False
    
    analyzer = N8nDataAnalyzer(data_dir)
    analyzer.print_summary()
    analyzer.generate_report()
    analyzer.export_to_csv()
    analyzer.export_content_text()
    
    print("\nAnalysis completed successfully!")
    return True

def main():
    parser = argparse.ArgumentParser(
        description="n8n Documentation Scraper and Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full scrape (unlimited pages)
  python run_scraper.py --scrape
  
  # Run limited scrape for testing
  python run_scraper.py --scrape --max-pages 50
  
  # Run scrape with custom delay
  python run_scraper.py --scrape --delay 2.0
  
  # Analyze existing data
  python run_scraper.py --analyze
  
  # Run both scrape and analyze
  python run_scraper.py --scrape --analyze
  
  # Quick test run
  python run_scraper.py --test
"""
    )
    
    # Main actions
    parser.add_argument('--scrape', action='store_true',
                       help='Run the web scraper')
    parser.add_argument('--analyze', action='store_true',
                       help='Run the data analyzer')
    parser.add_argument('--test', action='store_true',
                       help='Run a quick test (scrape 10 pages + analyze)')
    
    # Scraper options
    parser.add_argument('--max-pages', type=int, default=None,
                       help='Maximum number of pages to scrape (default: unlimited)')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between requests in seconds (default: 1.0)')
    parser.add_argument('--base-url', default="https://docs.n8n.io/",
                       help='Base URL to start scraping (default: https://docs.n8n.io/)')
    
    # Data options
    parser.add_argument('--data-dir', default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs",
                       help='Directory containing scraped data (default: /Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs)')
    
    args = parser.parse_args()
    
    # If no action specified, show help
    if not any([args.scrape, args.analyze, args.test]):
        parser.print_help()
        return
    
    # Handle test mode
    if args.test:
        print("Running in TEST mode (10 pages + analysis)")
        data_dir = run_scraper(max_pages=10, delay=args.delay, base_url=args.base_url)
        run_analyzer(data_dir)
        return
    
    # Run scraper if requested
    data_dir = args.data_dir
    if args.scrape:
        data_dir = run_scraper(
            max_pages=args.max_pages,
            delay=args.delay,
            base_url=args.base_url
        )
    
    # Run analyzer if requested
    if args.analyze:
        run_analyzer(data_dir)
    
    print("\n" + "="*60)
    print("All operations completed successfully!")
    print("="*60)

if __name__ == "__main__":
    main()