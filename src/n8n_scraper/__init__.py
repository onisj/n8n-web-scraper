#!/usr/bin/env python3
"""
n8n Web Scraper - AI-powered documentation scraper and knowledge system

A comprehensive system for scraping, processing, and serving n8n documentation
through an intelligent knowledge base with vector search capabilities.
"""

__version__ = "1.0.0"
__author__ = "Oni Segun John"
__description__ = "AI-powered n8n documentation scraper and knowledge system"

# Core modules
# from . import agents  # Commented out - agents module structure updated
from . import api
from . import automation
from . import database
# from . import web_interface  # Commented out - module not found

__all__ = [
    "agents",
    "api", 
    "automation",
    "database",
    # "web_interface",
    "__version__",
    "__author__",
    "__description__"
]