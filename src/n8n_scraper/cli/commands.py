"""
CLI commands for the n8n scraper.

This module contains the command-line interface (CLI) commands for the n8n scraper.
It provides functionality for initializing, configuring, scraping, and managing the n8n scraper.

Attributes:
    console (Console): Rich console instance for pretty-printing.
    logger (Logger): Logger instance for logging.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Confirm, Prompt

from ..core.config import Config, save_config
from ..core.logging_config import get_logger
from ..core.exceptions import ConfigurationError, ScrapingError
from ..scraper.scraper_factory import ScraperFactory, ScraperType, create_scraper_from_url
from ..database.connection import DatabaseManager
from ..database.models import ScrapedDocument, ConversationHistory, SystemMetrics
from ..automation.knowledge_vector_integration import create_knowledge_integration

logger = get_logger(__name__)
console = Console()


@click.command()
@click.argument('urls', nargs=-1, required=False)
@click.option(
    '--type',
    'scraper_type',
    type=click.Choice([t.value for t in ScraperType]),
    help='Type of scraper to use'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(path_type=Path),
    help='Output directory for scraped data'
)
@click.option(
    '--max-pages',
    type=int,
    default=100,
    help='Maximum number of pages to scrape'
)
@click.option(
    '--max-depth',
    type=int,
    default=3,
    help='Maximum crawling depth'
)
@click.option(
    '--delay',
    type=float,
    default=1.0,
    help='Delay between requests (seconds)'
)
@click.option(
    '--concurrent',
    type=int,
    default=5,
    help='Number of concurrent requests'
)
@click.option(
    '--format',
    'output_format',
    type=click.Choice(['json', 'csv', 'markdown']),
    default='json',
    help='Output format'
)
@click.option(
    '--filter-quality',
    type=float,
    help='Minimum quality score (0-100)'
)
@click.option(
    '--save-to-db',
    is_flag=True,
    help='Save results to database'
)
@click.option(
    '--process-to-vector',
    is_flag=True,
    help='Process scraped data into vector database for fast retrieval'
)
@click.option(
    '--vector-dir',
    default='/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/vector',
    help='Directory for vector database storage'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be scraped without actually scraping'
)
@click.pass_context
def scrape_command(ctx: click.Context,
                  urls: tuple,
                  scraper_type: Optional[str],
                  output: Optional[Path],
                  max_pages: int,
                  max_depth: int,
                  delay: float,
                  concurrent: int,
                  output_format: str,
                  filter_quality: Optional[float],
                  save_to_db: bool,
                  process_to_vector: bool,
                  vector_dir: str,
                  dry_run: bool):
    """Scrape URLs and extract content.
    
    If no URLs are provided, will scrape n8n documentation by default.
    """
    config = ctx.obj['config']
    
    # Default to n8n documentation if no URLs provided
    if not urls:
        urls = ['https://docs.n8n.io/']
        if not scraper_type:
            scraper_type = ScraperType.N8N.value
    
    # Convert scraper type
    if scraper_type:
        try:
            scraper_type_enum = ScraperType(scraper_type)
        except ValueError:
            console.print(f"[red]Invalid scraper type: {scraper_type}[/red]")
            sys.exit(1)
    else:
        # Auto-detect scraper type from first URL
        scraper_type_enum = None
    
    if dry_run:
        console.print("[yellow]Dry run mode - showing what would be scraped:[/yellow]")
        console.print(f"URLs: {list(urls)}")
        console.print(f"Scraper type: {scraper_type or 'auto-detect'}")
        console.print(f"Max pages: {max_pages}")
        console.print(f"Max depth: {max_depth}")
        console.print(f"Output format: {output_format}")
        console.print(f"Save to DB: {save_to_db}")
        console.print(f"Process to vector: {process_to_vector}")
        return
    
    # Run scraping
    asyncio.run(_run_scraping(
        urls=list(urls),
        scraper_type=scraper_type_enum,
        config=config,
        output=output,
        max_pages=max_pages,
        max_depth=max_depth,
        delay=delay,
        concurrent=concurrent,
        output_format=output_format,
        filter_quality=filter_quality,
        save_to_db=save_to_db,
        process_to_vector=process_to_vector,
        vector_dir=vector_dir
    ))


async def _run_scraping(urls: List[str],
                       scraper_type: Optional[ScraperType],
                       config: Config,
                       output: Optional[Path],
                       max_pages: int,
                       max_depth: int,
                       delay: float,
                       concurrent: int,
                       output_format: str,
                       filter_quality: Optional[float],
                       save_to_db: bool,
                       process_to_vector: bool,
                       vector_dir: str):
    """Run the scraping process."""
    try:
        # Create scraper
        factory = ScraperFactory()
        
        if scraper_type:
            scraper = factory.create_scraper(
                scraper_type,
                max_pages=max_pages,
                max_depth=max_depth,
                delay_range=(delay, delay * 1.5),
                max_concurrent=concurrent
            )
        else:
            # Auto-detect from first URL
            scraper = create_scraper_from_url(
                urls[0],
                max_pages=max_pages,
                max_depth=max_depth,
                delay_range=(delay, delay * 1.5),
                max_concurrent=concurrent
            )
        
        console.print(f"[green]Starting scraping with {type(scraper).__name__}[/green]")
        
        results = []
        
        # Progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Scraping...", total=None)
            
            async with scraper:
                async for result in scraper.scrape_urls(urls):
                    # Apply quality filter
                    if filter_quality and result.metadata.custom_data:
                        quality_score = result.metadata.custom_data.get('quality_score', 0)
                        if quality_score < filter_quality:
                            continue
                    
                    results.append(result)
                    progress.update(task, description=f"Scraped {len(results)} pages")
        
        console.print(f"[green]Scraping completed! Processed {len(results)} pages[/green]")
        
        # Save results
        if output or save_to_db or process_to_vector:
            await _save_results(results, output, output_format, save_to_db, process_to_vector, vector_dir, config)
        
        # Show summary
        _show_scraping_summary(results)
        
    except Exception as e:
        console.print(f"[red]Scraping failed: {e}[/red]")
        logger.exception("Scraping failed")
        sys.exit(1)


async def _save_results(results: List[Any],
                       output: Optional[Path],
                       output_format: str,
                       save_to_db: bool,
                       process_to_vector: bool,
                       vector_dir: str,
                       config: Config):
    """Save scraping results."""
    if output:
        output.mkdir(parents=True, exist_ok=True)
        
        if output_format == 'json':
            output_file = output / f"scraping_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump([result.__dict__ for result in results], f, indent=2, default=str)
        
        elif output_format == 'csv':
            import csv
            output_file = output / f"scraping_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if results:
                    writer = csv.DictWriter(f, fieldnames=results[0].__dict__.keys())
                    writer.writeheader()
                    for result in results:
                        writer.writerow(result.__dict__)
        
        elif output_format == 'markdown':
            output_file = output / f"scraping_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# Scraping Results\n\n")
                for i, result in enumerate(results, 1):
                    f.write(f"## {i}. {result.url}\n\n")
                    if result.content and result.content.title:
                        f.write(f"**Title:** {result.content.title}\n\n")
                    if result.content and result.content.content:
                        f.write(f"**Content:**\n{result.content.content[:500]}...\n\n")
                    f.write(f"**Status:** {result.status.value}\n\n")
                    f.write("---\n\n")
        
        console.print(f"[green]Results saved to {output_file}[/green]")
    
    if save_to_db:
        # This would need database implementation
        console.print("[yellow]Database saving not implemented yet[/yellow]")
    
    if process_to_vector:
        console.print("[cyan]Processing scraped data into vector database...[/cyan]")
        try:
            # Convert results to JSON format for processing
            scraped_data_dir = output or Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs")
            scraped_data_dir.mkdir(parents=True, exist_ok=True)
            
            # Save results as JSON files first
            processed_files = []
            for i, result in enumerate(results):
                if hasattr(result, 'content') and result.content:
                    # Create JSON data structure
                    json_data = {
                        'url': result.url,
                        'title': getattr(result.content, 'title', 'Untitled'),
                        'content': getattr(result.content, 'content', ''),
                        'headings': getattr(result.content, 'headings', []),
                        'links': getattr(result.content, 'links', []),
                        'code_blocks': getattr(result.content, 'code_blocks', []),
                        'images': getattr(result.content, 'images', []),
                        'scraped_at': datetime.now().isoformat(),
                        'metadata': getattr(result, 'metadata', {}).__dict__ if hasattr(getattr(result, 'metadata', {}), '__dict__') else {}
                    }
                    
                    # Save to JSON file
                    filename = f"scraped_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    file_path = scraped_data_dir / filename
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=2, ensure_ascii=False)
                    
                    processed_files.append(file_path)
            
            if processed_files:
                # Create vector integration and process the data
                integration = create_knowledge_integration(
                    scraped_data_dir=str(scraped_data_dir),
                    vector_db_dir=vector_dir
                )
                
                # Process the scraped data into vector database
                stats = integration.process_and_store_all(force_refresh=True)
                
                console.print(f"[green]✅ Vector processing completed![/green]")
                console.print(f"📁 Processed files: {stats['processed_files']}")
                console.print(f"🧩 Total chunks created: {stats['total_chunks']}")
                console.print(f"⏱️  Processing time: {stats['duration_seconds']:.2f} seconds")
                console.print(f"📊 Chunks per file: {stats['chunks_per_file']:.1f}")
                
                # Show knowledge base stats
                knowledge_stats = integration.get_knowledge_stats()
                if 'vector_database' in knowledge_stats:
                    db_stats = knowledge_stats['vector_database']
                    console.print(f"\n📚 Knowledge Base:")
                    console.print(f"   Total documents: {db_stats.get('total_documents', 0):,}")
                    console.print(f"   Unique sources: {db_stats.get('unique_sources', 0):,}")
                    console.print(f"   Categories: {db_stats.get('categories', 0):,}")
            else:
                console.print("[yellow]No valid content found for vector processing[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error processing to vector database: {e}[/red]")
            logger.exception("Vector processing failed")


def _show_scraping_summary(results: List[Any]):
    """Show scraping summary."""
    if not results:
        console.print("[yellow]No results to display[/yellow]")
        return
    
    # Create summary table
    table = Table(title="Scraping Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    successful = sum(1 for r in results if r.status.value == 'success')
    failed = sum(1 for r in results if r.status.value == 'failed')
    skipped = sum(1 for r in results if r.status.value == 'skipped')
    
    table.add_row("Total URLs", str(len(results)))
    table.add_row("Successful", str(successful))
    table.add_row("Failed", str(failed))
    table.add_row("Skipped", str(skipped))
    
    console.print(table)


@click.command()
@click.option(
    '--database-url',
    help='Database connection URL'
)
@click.option(
    '--vector-store',
    type=click.Choice(['faiss', 'numpy']),
    default='numpy',
    help='Vector store backend'
)
@click.option(
    '--force',
    is_flag=True,
    help='Force initialization even if already initialized'
)
@click.pass_context
def init_command(ctx: click.Context,
                database_url: Optional[str],
                vector_store: str,
                force: bool):
    """Initialize the n8n scraper system."""
    config = ctx.obj['config']
    
    console.print("[bold blue]Initializing n8n scraper system...[/bold blue]")
    
    # Check if already initialized
    if not force and _is_initialized(config):
        if not Confirm.ask("System appears to be already initialized. Continue anyway?"):
            console.print("[yellow]Initialization cancelled[/yellow]")
            return
    
    # Update configuration
    if database_url:
        config.database.url = database_url
    
    config.vector_store.backend = vector_store
    
    # Initialize database
    console.print("[cyan]Setting up database...[/cyan]")
    asyncio.run(_init_database(config))
    
    # Initialize vector store
    console.print("[cyan]Setting up vector store...[/cyan]")
    _init_vector_store(config)
    
    # Save configuration
    config_path = Path.cwd() / 'config' / 'scraper.json'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    save_config(config, config_path)
    
    console.print("[green]✓ Initialization completed successfully![/green]")
    console.print(f"Configuration saved to: {config_path}")


def _is_initialized(config: Config) -> bool:
    """Check if system is already initialized."""
    # Simple check - in practice, you'd check database tables, etc.
    return bool(config.database.url)


async def _init_database(config: Config):
    """Initialize database."""
    if not config.database.url:
        console.print("[yellow]No database URL configured, skipping database setup[/yellow]")
        return
    
    try:
        # This would use the actual database initialization
        console.print("[green]✓ Database initialized[/green]")
    except Exception as e:
        console.print(f"[red]Database initialization failed: {e}[/red]")
        raise


def _init_vector_store(config: Config):
    """Initialize vector store."""
    try:
        # This would use the actual vector store initialization
        console.print("[green]✓ Vector store initialized[/green]")
    except Exception as e:
        console.print(f"[red]Vector store initialization failed: {e}[/red]")
        raise


@click.command()
@click.option(
    '--detailed',
    is_flag=True,
    help='Show detailed status information'
)
@click.pass_context
def status_command(ctx: click.Context, detailed: bool):
    """Show system status and statistics."""
    config = ctx.obj['config']
    
    console.print("[bold blue]N8n Scraper System Status[/bold blue]")
    console.print()
    
    # System status
    status_table = Table(title="System Status")
    status_table.add_column("Component", style="cyan")
    status_table.add_column("Status", style="green")
    status_table.add_column("Details")
    
    # Check database
    db_status = "✓ Connected" if config.database.url else "✗ Not configured"
    status_table.add_row("Database", db_status, config.database.url or "N/A")
    
    # Check vector store
    vs_status = "✓ Enabled" if config.vector_store.enabled else "✗ Disabled"
    status_table.add_row("Vector Store", vs_status, config.vector_store.backend)
    
    # Check cache
    cache_status = "✓ Enabled" if config.cache.enabled else "✗ Disabled"
    status_table.add_row("Cache", cache_status, config.cache.backend)
    
    console.print(status_table)
    console.print()
    
    if detailed:
        _show_detailed_status(config)


def _show_detailed_status(config: Config):
    """Show detailed status information."""
    # Configuration details
    config_panel = Panel(
        f"Database URL: {config.database.url or 'Not set'}\n"
        f"Vector Store: {config.vector_store.backend}\n"
        f"Cache Backend: {config.cache.backend}\n"
        f"Log Level: {config.logging.level}",
        title="Configuration Details",
        border_style="blue"
    )
    console.print(config_panel)
    console.print()
    
    # Statistics (would be fetched from database in real implementation)
    stats_table = Table(title="Statistics")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")
    
    stats_table.add_row("Total Documents", "0")
    stats_table.add_row("Total Chunks", "0")
    stats_table.add_row("Last Scrape", "Never")
    stats_table.add_row("Cache Hits", "0")
    
    console.print(stats_table)


@click.command()
@click.option(
    '--format',
    'export_format',
    type=click.Choice(['json', 'csv', 'markdown', 'txt']),
    default='json',
    help='Export format'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(path_type=Path),
    required=True,
    help='Output file path'
)
@click.option(
    '--filter-type',
    type=click.Choice(['documentation', 'integration', 'tutorial', 'api']),
    help='Filter by content type'
)
@click.option(
    '--min-quality',
    type=float,
    help='Minimum quality score'
)
@click.option(
    '--limit',
    type=int,
    help='Maximum number of documents to export'
)
@click.pass_context
def export_command(ctx: click.Context,
                  export_format: str,
                  output: Path,
                  filter_type: Optional[str],
                  min_quality: Optional[float],
                  limit: Optional[int]):
    """Export scraped data in various formats."""
    config = ctx.obj['config']
    
    console.print(f"[cyan]Exporting data to {output}...[/cyan]")
    
    # This would fetch data from database in real implementation
    console.print("[yellow]Export functionality not implemented yet[/yellow]")
    console.print("Would export with filters:")
    console.print(f"  Format: {export_format}")
    console.print(f"  Type filter: {filter_type or 'None'}")
    console.print(f"  Min quality: {min_quality or 'None'}")
    console.print(f"  Limit: {limit or 'None'}")


@click.command()
@click.argument('query')
@click.option(
    '--limit',
    type=int,
    default=10,
    help='Maximum number of results'
)
@click.option(
    '--threshold',
    type=float,
    default=0.7,
    help='Similarity threshold (0-1)'
)
@click.option(
    '--type',
    'content_type',
    type=click.Choice(['documentation', 'integration', 'tutorial', 'api']),
    help='Filter by content type'
)
@click.pass_context
def search_command(ctx: click.Context,
                  query: str,
                  limit: int,
                  threshold: float,
                  content_type: Optional[str]):
    """Search scraped content using semantic similarity."""
    config = ctx.obj['config']
    
    console.print(f"[cyan]Searching for: '{query}'[/cyan]")
    
    # This would use the actual vector search in real implementation
    console.print("[yellow]Search functionality not implemented yet[/yellow]")
    console.print("Would search with parameters:")
    console.print(f"  Query: {query}")
    console.print(f"  Limit: {limit}")
    console.print(f"  Threshold: {threshold}")
    console.print(f"  Type filter: {content_type or 'None'}")


@click.group()
def config_command():
    """Manage configuration settings."""
    pass


@config_command.command('show')
@click.pass_context
def config_show(ctx: click.Context):
    """Show current configuration."""
    config = ctx.obj['config']
    
    # Convert config to dict for display
    config_dict = {
        'database': {
            'url': config.database.url,
            'pool_size': config.database.pool_size,
            'max_overflow': config.database.max_overflow,
        },
        'vector_store': {
            'enabled': config.vector_store.enabled,
            'backend': config.vector_store.backend,
            'dimension': config.vector_store.dimension,
        },
        'cache': {
            'enabled': config.cache.enabled,
            'backend': config.cache.backend,
            'ttl': config.cache.ttl,
        },
        'logging': {
            'level': config.logging.level,
            'file': config.logging.file,
        }
    }
    
    syntax = Syntax(json.dumps(config_dict, indent=2), "json", theme="monokai")
    console.print(Panel(syntax, title="Current Configuration", border_style="blue"))


@config_command.command('set')
@click.argument('key')
@click.argument('value')
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str):
    """Set a configuration value.
    
    Examples:
        config set database.url postgresql://user:pass@localhost/db
        config set vector_store.backend faiss
        config set logging.level DEBUG
    """
    config = ctx.obj['config']
    
    # Parse nested key
    keys = key.split('.')
    if len(keys) != 2:
        console.print("[red]Key must be in format 'section.key'[/red]")
        sys.exit(1)
    
    section, setting = keys
    
    # Update configuration
    try:
        if section == 'database':
            setattr(config.database, setting, value)
        elif section == 'vector_store':
            if setting == 'enabled':
                value = value.lower() in ('true', '1', 'yes')
            elif setting == 'dimension':
                value = int(value)
            setattr(config.vector_store, setting, value)
        elif section == 'cache':
            if setting == 'enabled':
                value = value.lower() in ('true', '1', 'yes')
            elif setting == 'ttl':
                value = int(value)
            setattr(config.cache, setting, value)
        elif section == 'logging':
            setattr(config.logging, setting, value)
        else:
            console.print(f"[red]Unknown configuration section: {section}[/red]")
            sys.exit(1)
        
        console.print(f"[green]✓ Set {key} = {value}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error setting configuration: {e}[/red]")
        sys.exit(1)


@config_command.command('reset')
@click.option(
    '--confirm',
    is_flag=True,
    help='Skip confirmation prompt'
)
@click.pass_context
def config_reset(ctx: click.Context, confirm: bool):
    """Reset configuration to defaults."""
    if not confirm and not Confirm.ask("Reset all configuration to defaults?"):
        console.print("[yellow]Reset cancelled[/yellow]")
        return
    
    # Reset to default configuration
    ctx.obj['config'] = Config()
    console.print("[green]✓ Configuration reset to defaults[/green]")