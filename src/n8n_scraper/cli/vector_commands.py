#!/usr/bin/env python3
"""
Vector Database CLI Commands

Provides command-line interface for managing the knowledge vector database,
including processing scraped data, searching knowledge, and managing the vector store.
"""

import click
import json
import asyncio
from pathlib import Path
from typing import Optional

from ..automation.knowledge_vector_integration import (
    KnowledgeVectorIntegration,
    create_knowledge_integration,
    process_knowledge_async
)
from ..core.config import load_config
from ..core.exceptions import VectorDatabaseError, ProcessingError


@click.group(name='vector')
def vector_group():
    """Manage knowledge vector database operations."""
    pass


@vector_group.command('process')
@click.option(
    '--scraped-dir',
    default='/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs',
    help='Directory containing scraped JSON files'
)
@click.option(
    '--vector-dir',
    default='/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/vector',
    help='Directory for vector database storage'
)
@click.option(
    '--force-refresh',
    is_flag=True,
    help='Force reprocessing of all files'
)
@click.option(
    '--chunk-size',
    default=1000,
    type=int,
    help='Maximum size of text chunks in characters'
)
@click.option(
    '--chunk-overlap',
    default=200,
    type=int,
    help='Overlap between chunks in characters'
)
@click.option(
    '--async-mode',
    is_flag=True,
    help='Run processing asynchronously'
)
def process_command(
    scraped_dir: str,
    vector_dir: str,
    force_refresh: bool,
    chunk_size: int,
    chunk_overlap: int,
    async_mode: bool
):
    """
    Process scraped data and store in vector database for fast retrieval.
    
    This command takes scraped n8n documentation and processes it into
    semantic chunks that are stored in a vector database for AI-powered
    search and retrieval.
    """
    try:
        click.echo("🚀 Starting knowledge vector processing...")
        
        # Create integration instance
        integration = KnowledgeVectorIntegration(
            scraped_data_dir=scraped_dir,
            vector_db_dir=vector_dir,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Check if scraped data exists
        scraped_path = Path(scraped_dir)
        if not scraped_path.exists() or not list(scraped_path.glob("*.json")):
            click.echo(f"❌ No scraped data found in {scraped_dir}")
            click.echo("💡 Run 'n8n-scraper scrape' first to collect data")
            return
        
        # Process data
        if async_mode:
            click.echo("⚡ Running in async mode...")
            stats = asyncio.run(process_knowledge_async(integration, force_refresh))
        else:
            stats = integration.process_and_store_all(force_refresh)
        
        # Display results
        click.echo("\n✅ Processing completed successfully!")
        click.echo(f"📁 Processed files: {stats['processed_files']}")
        click.echo(f"🧩 Total chunks created: {stats['total_chunks']}")
        click.echo(f"⏱️  Duration: {stats['duration_seconds']:.2f} seconds")
        click.echo(f"📊 Chunks per file: {stats['chunks_per_file']:.1f}")
        click.echo(f"🚄 Processing rate: {stats['processing_rate']:.1f} files/sec")
        
        # Show knowledge base stats
        knowledge_stats = integration.get_knowledge_stats()
        if 'vector_database' in knowledge_stats:
            db_stats = knowledge_stats['vector_database']
            click.echo(f"\n📚 Knowledge Base Statistics:")
            click.echo(f"   Total documents: {db_stats.get('total_documents', 0)}")
            click.echo(f"   Unique sources: {db_stats.get('unique_sources', 0)}")
            click.echo(f"   Categories: {db_stats.get('categories', 0)}")
        
    except ProcessingError as e:
        click.echo(f"❌ Processing error: {e}")
        raise click.ClickException(str(e))
    except VectorDatabaseError as e:
        click.echo(f"❌ Vector database error: {e}")
        raise click.ClickException(str(e))
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}")
        raise click.ClickException(str(e))


@vector_group.command('search')
@click.argument('query')
@click.option(
    '--vector-dir',
    default='/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/vector',
    help='Directory for vector database storage'
)
@click.option(
    '--top-k',
    default=5,
    type=int,
    help='Number of results to return'
)
@click.option(
    '--score-threshold',
    default=0.7,
    type=float,
    help='Minimum similarity score (0.0-1.0)'
)
@click.option(
    '--category',
    help='Filter by category'
)
@click.option(
    '--output-format',
    type=click.Choice(['table', 'json', 'detailed']),
    default='table',
    help='Output format'
)
def search_command(
    query: str,
    vector_dir: str,
    top_k: int,
    score_threshold: float,
    category: Optional[str],
    output_format: str
):
    """
    Search the knowledge vector database using semantic similarity.
    
    QUERY: The search query to find relevant documentation
    """
    try:
        click.echo(f"🔍 Searching for: '{query}'")
        
        # Create integration instance
        integration = create_knowledge_integration(vector_db_dir=vector_dir)
        
        # Perform search
        results = integration.search_knowledge(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            category_filter=category
        )
        
        if not results:
            click.echo("❌ No results found matching your query")
            click.echo("💡 Try adjusting the score threshold or using different keywords")
            return
        
        # Display results based on format
        if output_format == 'json':
            click.echo(json.dumps(results, indent=2))
        elif output_format == 'detailed':
            _display_detailed_results(results)
        else:  # table format
            _display_table_results(results)
        
        click.echo(f"\n✅ Found {len(results)} relevant results")
        
    except Exception as e:
        click.echo(f"❌ Search error: {e}")
        raise click.ClickException(str(e))


@vector_group.command('stats')
@click.option(
    '--vector-dir',
    default='/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/vector',
    help='Directory for vector database storage'
)
@click.option(
    '--scraped-dir',
    default='/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs',
    help='Directory containing scraped JSON files'
)
@click.option(
    '--output-format',
    type=click.Choice(['table', 'json']),
    default='table',
    help='Output format'
)
def stats_command(
    vector_dir: str,
    scraped_dir: str,
    output_format: str
):
    """
    Display comprehensive statistics about the knowledge vector database.
    """
    try:
        click.echo("📊 Gathering knowledge base statistics...")
        
        # Create integration instance
        integration = create_knowledge_integration(
            scraped_data_dir=scraped_dir,
            vector_db_dir=vector_dir
        )
        
        # Get statistics
        stats = integration.get_knowledge_stats()
        
        if output_format == 'json':
            click.echo(json.dumps(stats, indent=2))
        else:
            _display_stats_table(stats)
        
    except Exception as e:
        click.echo(f"❌ Error getting statistics: {e}")
        raise click.ClickException(str(e))


@vector_group.command('update')
@click.option(
    '--scraped-dir',
    default='/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs',
    help='Directory containing scraped JSON files'
)
@click.option(
    '--vector-dir', 
    default='/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/vector',
    help='Directory for vector database storage'
)
def update_command(
    scraped_dir: str,
    vector_dir: str
):
    """
    Incrementally update the vector database with new or modified files.
    
    This command only processes files that are new or have been modified
    since the last update, making it efficient for regular updates.
    """
    try:
        click.echo("🔄 Starting incremental knowledge update...")
        
        # Create integration instance
        integration = create_knowledge_integration(
            scraped_data_dir=scraped_dir,
            vector_db_dir=vector_dir
        )
        
        # Perform incremental update
        stats = integration.process_incremental_update()
        
        if stats['processed_files'] == 0:
            click.echo("✅ Knowledge base is up to date - no new files to process")
        else:
            click.echo("\n✅ Incremental update completed!")
            click.echo(f"📁 Updated files: {stats['processed_files']}")
            click.echo(f"🧩 New chunks: {stats['total_chunks']}")
            click.echo(f"⏱️  Duration: {stats['duration_seconds']:.2f} seconds")
        
    except Exception as e:
        click.echo(f"❌ Update error: {e}")
        raise click.ClickException(str(e))


@vector_group.command('reset')
@click.option(
    '--vector-dir',
    default='/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/vector',
    help='Directory for vector database storage'
)
@click.option(
    '--confirm',
    is_flag=True,
    help='Skip confirmation prompt'
)
def reset_command(
    vector_dir: str,
    confirm: bool
):
    """
    Reset the vector database by removing all stored knowledge.
    
    WARNING: This will permanently delete all processed knowledge chunks.
    """
    try:
        if not confirm:
            click.confirm(
                "⚠️  This will permanently delete all knowledge from the vector database. Continue?",
                abort=True
            )
        
        click.echo("🗑️  Resetting vector database...")
        
        # Create integration instance
        integration = create_knowledge_integration(vector_db_dir=vector_dir)
        
        # Reset the database
        integration.vector_db.reset_collection()
        
        # Clear processed files cache
        cache_file = Path(vector_dir) / "processed_files_cache.json"
        if cache_file.exists():
            cache_file.unlink()
        
        click.echo("✅ Vector database reset successfully")
        
    except Exception as e:
        click.echo(f"❌ Reset error: {e}")
        raise click.ClickException(str(e))


def _display_table_results(results):
    """
    Display search results in table format.
    """
    click.echo("\n📋 Search Results:")
    click.echo("=" * 80)
    
    for i, result in enumerate(results, 1):
        metadata = result.get('metadata', {})
        score = result.get('score', 0)
        content = result.get('content', '')[:200] + '...' if len(result.get('content', '')) > 200 else result.get('content', '')
        
        click.echo(f"\n{i}. {metadata.get('title', 'Untitled')} (Score: {score:.3f})")
        click.echo(f"   Category: {metadata.get('category', 'Unknown')} > {metadata.get('subcategory', 'Unknown')}")
        click.echo(f"   URL: {metadata.get('url', 'N/A')}")
        click.echo(f"   Content: {content}")
        click.echo("-" * 80)


def _display_detailed_results(results):
    """
    Display search results in detailed format.
    """
    click.echo("\n📋 Detailed Search Results:")
    click.echo("=" * 100)
    
    for i, result in enumerate(results, 1):
        metadata = result.get('metadata', {})
        score = result.get('score', 0)
        content = result.get('content', '')
        
        click.echo(f"\n🔍 Result {i}")
        click.echo(f"Title: {metadata.get('title', 'Untitled')}")
        click.echo(f"Score: {score:.3f}")
        click.echo(f"Category: {metadata.get('category', 'Unknown')} > {metadata.get('subcategory', 'Unknown')}")
        click.echo(f"URL: {metadata.get('url', 'N/A')}")
        click.echo(f"Source: {metadata.get('source_file', 'Unknown')}")
        click.echo(f"Word Count: {metadata.get('word_count', 0)}")
        click.echo(f"Has Code: {'Yes' if metadata.get('has_code') else 'No'}")
        click.echo(f"Has Images: {'Yes' if metadata.get('has_images') else 'No'}")
        click.echo(f"\nContent:")
        click.echo(content)
        click.echo("=" * 100)


def _display_stats_table(stats):
    """
    Display statistics in table format.
    """
    click.echo("\n📊 Knowledge Base Statistics")
    click.echo("=" * 50)
    
    # Vector Database Stats
    if 'vector_database' in stats:
        db_stats = stats['vector_database']
        click.echo("\n🗄️  Vector Database:")
        click.echo(f"   Total Documents: {db_stats.get('total_documents', 0):,}")
        click.echo(f"   Unique Sources: {db_stats.get('unique_sources', 0):,}")
        click.echo(f"   Categories: {db_stats.get('categories', 0):,}")
    
    # File Processing Stats
    if 'file_processing' in stats:
        file_stats = stats['file_processing']
        click.echo("\n📁 File Processing:")
        click.echo(f"   Total Scraped Files: {file_stats.get('total_scraped_files', 0):,}")
        click.echo(f"   Processed Files: {file_stats.get('processed_files', 0):,}")
        click.echo(f"   Pending Files: {file_stats.get('pending_files', 0):,}")
        click.echo(f"   Last Update: {file_stats.get('last_update', 'Never')}")
    
    # Chunking Stats
    if 'chunking' in stats:
        chunk_stats = stats['chunking']
        click.echo("\n🧩 Chunking Configuration:")
        click.echo(f"   Chunk Size: {chunk_stats.get('chunk_size', 0):,} characters")
        click.echo(f"   Chunk Overlap: {chunk_stats.get('chunk_overlap', 0):,} characters")
    
    click.echo("\n" + "=" * 50)


# Add vector commands to the main CLI
def add_vector_commands(cli_group):
    """
    Add vector database commands to the main CLI group.
    
    Args:
        cli_group: The main Click CLI group
    """
    cli_group.add_command(vector_group)


if __name__ == '__main__':
    vector_group()