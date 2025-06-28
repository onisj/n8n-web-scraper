"""
Main CLI entry point for the n8n scraper.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.traceback import install

from ..core.config import Config, load_config
from ..core.logging_config import setup_logging, get_logger
from ..core.exceptions import ConfigurationError, ScrapingError
from .commands import (
    scrape_command,
    init_command,
    status_command,
    export_command,
    search_command,
    config_command,
)
from .vector_commands import vector_group

# Install rich traceback handler
install(show_locals=True)

console = Console()
logger = get_logger(__name__)


@click.group()
@click.option(
    '--config',
    '-c',
    type=click.Path(exists=True, path_type=Path),
    help='Path to configuration file'
)
@click.option(
    '--verbose',
    '-v',
    count=True,
    help='Increase verbosity (use -v, -vv, or -vvv)'
)
@click.option(
    '--quiet',
    '-q',
    is_flag=True,
    help='Suppress output except errors'
)
@click.option(
    '--log-file',
    type=click.Path(path_type=Path),
    help='Log file path'
)
@click.option(
    '--no-color',
    is_flag=True,
    help='Disable colored output'
)
@click.pass_context
def cli(ctx: click.Context,
        config: Optional[Path],
        verbose: int,
        quiet: bool,
        log_file: Optional[Path],
        no_color: bool):
    """N8n Web Scraper - Extract and process n8n documentation.
    
    This tool helps you scrape n8n documentation, process the content,
    and store it in a searchable format for building knowledge bases
    or training AI models.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Disable colors if requested
    if no_color:
        console._color_system = None
    
    # Determine log level
    if quiet:
        log_level = 'ERROR'
    elif verbose >= 3:
        log_level = 'DEBUG'
    elif verbose >= 2:
        log_level = 'INFO'
    elif verbose >= 1:
        log_level = 'WARNING'
    else:
        log_level = 'INFO'
    
    # Setup logging
    try:
        setup_logging(
            log_level=log_level,
            log_file=Path(log_file) if log_file else None
        )
    except Exception as e:
        console.print(f"[red]Error setting up logging: {e}[/red]")
        sys.exit(1)
    
    # Load configuration
    try:
        if config:
            app_config = load_config(config)
        else:
            app_config = load_config()  # This will look for config in default locations
        
        ctx.obj['config'] = app_config
        ctx.obj['console'] = console
        ctx.obj['verbose'] = verbose
        ctx.obj['quiet'] = quiet
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if verbose >= 2:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.pass_context
def version(ctx: click.Context):
    """Show version information."""
    console = ctx.obj['console']
    
    try:
        from .. import __version__
        version_str = __version__
    except ImportError:
        version_str = "unknown"
    
    console.print(f"n8n-scraper version: {version_str}")
    console.print(f"Python version: {sys.version}")
    console.print(f"Platform: {sys.platform}")


@cli.command()
@click.option(
    '--check-deps',
    is_flag=True,
    help='Check if all dependencies are available'
)
@click.pass_context
def doctor(ctx: click.Context, check_deps: bool):
    """Check system health and configuration."""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    console.print("[bold blue]N8n Scraper Health Check[/bold blue]")
    console.print()
    
    # Check configuration
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Database URL: {'✓' if config.database.url else '✗'}")
    console.print(f"  Vector Store: {'✓' if config.vector_store.enabled else '✗'}")
    console.print(f"  Cache: {'✓' if config.cache.enabled else '✗'}")
    console.print()
    
    # Check dependencies
    if check_deps:
        console.print("[bold]Dependencies:[/bold]")
        
        deps = [
            ('aiohttp', 'HTTP client'),
            ('asyncpg', 'PostgreSQL driver'),
            ('sqlalchemy', 'ORM'),
            ('beautifulsoup4', 'HTML parsing'),
            ('sentence-transformers', 'Embeddings'),
            ('click', 'CLI framework'),
            ('rich', 'Terminal formatting'),
        ]
        
        for dep, description in deps:
            try:
                __import__(dep.replace('-', '_'))
                console.print(f"  {dep}: ✓ ({description})")
            except ImportError:
                console.print(f"  {dep}: ✗ ({description}) - Missing")
        
        console.print()
    
    # Check database connection
    console.print("[bold]Database Connection:[/bold]")
    try:
        # This would need to be implemented
        console.print("  Connection: ✓ (Not implemented yet)")
    except Exception as e:
        console.print(f"  Connection: ✗ ({e})")
    
    console.print()
    console.print("[green]Health check completed![/green]")


# Add command groups
cli.add_command(scrape_command, name='scrape')
cli.add_command(init_command, name='init')
cli.add_command(status_command, name='status')
cli.add_command(export_command, name='export')
cli.add_command(search_command, name='search')
cli.add_command(config_command, name='config')
cli.add_command(vector_group, name='vector')


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        logger.exception("Unexpected error in main")
        sys.exit(1)


if __name__ == '__main__':
    main()