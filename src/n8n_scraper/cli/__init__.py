"""
Command-line interface for the n8n scraper.
"""

from .main import main, cli
from .commands import (
    scrape_command,
    init_command,
    status_command,
    export_command,
    search_command,
    config_command,
)
from .vector_commands import vector_group

__all__ = [
    'main',
    'cli',
    'scrape_command',
    'init_command', 
    'status_command',
    'export_command',
    'search_command',
    'config_command',
    'vector_group',
]