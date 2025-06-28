#!/usr/bin/env python3
"""
Performance Benchmark Script

Benchmarks the knowledge base loading performance with and without optimizations.
"""

import time
import sys
import os
from pathlib import Path
import logging
from typing import Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from n8n_scraper.optimization.knowledge_cache import KnowledgeCache
from n8n_scraper.optimization.agent_manager import get_agent_manager
from n8n_scraper.optimization.agent_manager import get_expert_agent, get_knowledge_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def benchmark_original_loading(data_directory: str = "data/scraped_docs") -> Dict[str, Any]:
    """Benchmark original loading without optimizations"""
    logger.info("Benchmarking original loading method...")
    
    start_time = time.time()
    
    try:
        # Create agent without optimizations
        agent = get_expert_agent(data_directory)
        
        end_time = time.time()
        loading_time = end_time - start_time
        
        return {
            'method': 'original',
            'loading_time': loading_time,
            'chunks_loaded': len(agent.knowledge_chunks),
            'categories': len(agent.categories),
            'success': True
        }
        
    except Exception as e:
        end_time = time.time()
        return {
            'method': 'original',
            'loading_time': end_time - start_time,
            'error': str(e),
            'success': False
        }

def benchmark_optimized_loading(data_directory: str = "data/scraped_docs", force_refresh: bool = False) -> Dict[str, Any]:
    """Benchmark optimized loading with caching"""
    logger.info(f"Benchmarking optimized loading method (force_refresh={force_refresh})...")
    
    start_time = time.time()
    
    try:
        # Clear cache if force refresh
        if force_refresh:
            cache = KnowledgeCache(data_directory)
            cache.invalidate_cache()
        
        # Use optimized agent manager
        agent_manager = get_agent_manager()
        agent = agent_manager.get_expert_agent(data_directory)
        
        end_time = time.time()
        loading_time = end_time - start_time
        
        return {
            'method': 'optimized',
            'loading_time': loading_time,
            'chunks_loaded': len(agent.knowledge_chunks),
            'categories': len(agent.categories),
            'force_refresh': force_refresh,
            'success': True
        }
        
    except Exception as e:
        end_time = time.time()
        return {
            'method': 'optimized',
            'loading_time': end_time - start_time,
            'force_refresh': force_refresh,
            'error': str(e),
            'success': False
        }

def benchmark_cache_performance(data_directory: str = "data/scraped_docs") -> Dict[str, Any]:
    """Benchmark cache performance specifically"""
    logger.info("Benchmarking cache performance...")
    
    cache = KnowledgeCache(data_directory)
    
    # First load (cache miss)
    cache.invalidate_cache()
    start_time = time.time()
    knowledge_base_1 = cache.get_knowledge_base(force_refresh=True)
    first_load_time = time.time() - start_time
    
    # Second load (cache hit)
    start_time = time.time()
    knowledge_base_2 = cache.get_knowledge_base(force_refresh=False)
    second_load_time = time.time() - start_time
    
    return {
        'method': 'cache_comparison',
        'first_load_time': first_load_time,
        'second_load_time': second_load_time,
        'speedup_factor': first_load_time / second_load_time if second_load_time > 0 else float('inf'),
        'chunks_loaded': len(knowledge_base_1.chunks) if knowledge_base_1 else 0,
        'cache_working': knowledge_base_1 is not None and knowledge_base_2 is not None,
        'success': True
    }

def run_comprehensive_benchmark(data_directory: str = "data/scraped_docs") -> Dict[str, Any]:
    """Run comprehensive performance benchmark"""
    logger.info("Starting comprehensive performance benchmark...")
    
    results = {
        'benchmark_start': time.time(),
        'data_directory': data_directory,
        'tests': []
    }
    
    # Test 1: Cache performance
    logger.info("\n=== Test 1: Cache Performance ===")
    cache_results = benchmark_cache_performance(data_directory)
    results['tests'].append(cache_results)
    
    if cache_results['success']:
        logger.info(f"First load (cache miss): {cache_results['first_load_time']:.2f}s")
        logger.info(f"Second load (cache hit): {cache_results['second_load_time']:.2f}s")
        logger.info(f"Speedup factor: {cache_results['speedup_factor']:.1f}x")
    
    # Test 2: Optimized loading (fresh)
    logger.info("\n=== Test 2: Optimized Loading (Fresh) ===")
    optimized_fresh = benchmark_optimized_loading(data_directory, force_refresh=True)
    results['tests'].append(optimized_fresh)
    
    if optimized_fresh['success']:
        logger.info(f"Optimized fresh load: {optimized_fresh['loading_time']:.2f}s")
        logger.info(f"Chunks loaded: {optimized_fresh['chunks_loaded']}")
    
    # Test 3: Optimized loading (cached)
    logger.info("\n=== Test 3: Optimized Loading (Cached) ===")
    optimized_cached = benchmark_optimized_loading(data_directory, force_refresh=False)
    results['tests'].append(optimized_cached)
    
    if optimized_cached['success']:
        logger.info(f"Optimized cached load: {optimized_cached['loading_time']:.2f}s")
        logger.info(f"Chunks loaded: {optimized_cached['chunks_loaded']}")
    
    # Test 4: Multiple agent instances (singleton test)
    logger.info("\n=== Test 4: Singleton Pattern Test ===")
    start_time = time.time()
    
    agent_manager = get_agent_manager()
    agent1 = agent_manager.get_expert_agent(data_directory)
    agent2 = agent_manager.get_expert_agent(data_directory)
    agent3 = agent_manager.get_expert_agent(data_directory)
    
    singleton_time = time.time() - start_time
    
    singleton_results = {
        'method': 'singleton_test',
        'loading_time': singleton_time,
        'agents_identical': agent1 is agent2 is agent3,
        'success': True
    }
    results['tests'].append(singleton_results)
    
    logger.info(f"Multiple agent creation: {singleton_time:.2f}s")
    logger.info(f"Agents are identical (singleton): {singleton_results['agents_identical']}")
    
    results['benchmark_end'] = time.time()
    results['total_benchmark_time'] = results['benchmark_end'] - results['benchmark_start']
    
    return results

def print_summary(results: Dict[str, Any]):
    """Print benchmark summary"""
    print("\n" + "="*60)
    print("PERFORMANCE BENCHMARK SUMMARY")
    print("="*60)
    
    print(f"Data Directory: {results['data_directory']}")
    print(f"Total Benchmark Time: {results['total_benchmark_time']:.2f}s")
    print()
    
    for test in results['tests']:
        if test['success']:
            method = test['method']
            if method == 'cache_comparison':
                print(f"Cache Performance:")
                print(f"  - First load: {test['first_load_time']:.2f}s")
                print(f"  - Second load: {test['second_load_time']:.2f}s")
                print(f"  - Speedup: {test['speedup_factor']:.1f}x")
                print(f"  - Chunks: {test['chunks_loaded']}")
            elif method == 'optimized':
                cache_status = "(fresh)" if test['force_refresh'] else "(cached)"
                print(f"Optimized Loading {cache_status}: {test['loading_time']:.2f}s")
            elif method == 'singleton_test':
                print(f"Singleton Pattern: {test['loading_time']:.2f}s (multiple instances)")
                print(f"  - Singleton working: {test['agents_identical']}")
        else:
            print(f"Test {test['method']} failed: {test.get('error', 'Unknown error')}")
        print()
    
    # Performance recommendations
    print("RECOMMENDATIONS:")
    print("- First startup will be slower as cache is built")
    print("- Subsequent startups should be significantly faster")
    print("- Use singleton pattern to prevent duplicate loading")
    print("- Monitor cache validity with /optimization/status endpoint")
    print("- Clear cache if data changes: /optimization/cache (DELETE)")

def main():
    """Main benchmark function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark n8n knowledge base performance")
    parser.add_argument(
        "--data-dir", 
        default="data/scraped_docs",
        help="Path to scraped data directory"
    )
    parser.add_argument(
        "--quick", 
        action="store_true",
        help="Run quick benchmark (cache only)"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.data_dir):
        logger.error(f"Data directory not found: {args.data_dir}")
        sys.exit(1)
    
    if args.quick:
        logger.info("Running quick benchmark...")
        results = benchmark_cache_performance(args.data_dir)
        print(f"\nQuick Benchmark Results:")
        print(f"First load: {results['first_load_time']:.2f}s")
        print(f"Second load: {results['second_load_time']:.2f}s")
        print(f"Speedup: {results['speedup_factor']:.1f}x")
    else:
        results = run_comprehensive_benchmark(args.data_dir)
        print_summary(results)

if __name__ == "__main__":
    main()