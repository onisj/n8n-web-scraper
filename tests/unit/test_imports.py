#!/usr/bin/env python3
"""
Import Tests for n8n Web Scraper

This module tests that all imports in the project work correctly,
helping to identify missing dependencies or incorrect import paths.
"""

import pytest
import sys
import importlib
from pathlib import Path

# Add src to path for testing
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

class TestCoreImports:
    """Test core module imports"""
    
    def test_n8n_scraper_package(self):
        """Test that the main n8n_scraper package can be imported"""
        try:
            import n8n_scraper
            assert n8n_scraper is not None
        except ImportError as e:
            pytest.fail(f"Failed to import n8n_scraper package: {e}")
    
    def test_config_imports(self):
        """Test configuration module imports"""
        try:
            from config import settings
            assert settings is not None
        except ImportError as e:
            pytest.fail(f"Failed to import config.settings: {e}")

class TestScraperImports:
    """Test scraper-related imports"""
    
    def test_scraper_modules(self):
        """Test scraper module imports"""
        modules_to_test = [
            "n8n_scraper.scrapers.base_scraper",
            "n8n_scraper.scrapers.docs_scraper",
            "n8n_scraper.scrapers.community_scraper"
        ]
        
        for module_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")
    
    def test_scraper_classes(self):
        """Test that scraper classes can be imported"""
        try:
            from n8n_scraper.scrapers.base_scraper import BaseScraper
            from n8n_scraper.scrapers.docs_scraper import N8nDocsScraper
            from n8n_scraper.scrapers.community_scraper import CommunityScraper
            
            assert BaseScraper is not None
            assert N8nDocsScraper is not None
            assert CommunityScraper is not None
        except ImportError as e:
            pytest.fail(f"Failed to import scraper classes: {e}")

class TestAgentImports:
    """Test AI agent-related imports"""
    
    def test_agent_modules(self):
        """Test agent module imports"""
        modules_to_test = [
            "n8n_scraper.agents.n8n_agent",
            "n8n_scraper.agents.knowledge_processor"
        ]
        
        for module_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")
    
    def test_agent_classes(self):
        """Test that agent classes can be imported"""
        try:
            from n8n_scraper.agents.n8n_agent import N8nExpertAgent
            from n8n_scraper.agents.knowledge_processor import N8nKnowledgeProcessor
            
            assert N8nExpertAgent is not None
            assert N8nKnowledgeProcessor is not None
        except ImportError as e:
            pytest.fail(f"Failed to import agent classes: {e}")

class TestAutomationImports:
    """Test automation-related imports"""
    
    def test_automation_modules(self):
        """Test automation module imports"""
        modules_to_test = [
            "n8n_scraper.automation.update_scheduler",
            "n8n_scraper.automation.knowledge_updater",
            "n8n_scraper.automation.change_detector"
        ]
        
        for module_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")
    
    def test_automation_classes(self):
        """Test that automation classes can be imported"""
        try:
            from n8n_scraper.automation.update_scheduler import AutomatedUpdater
            from n8n_scraper.automation.knowledge_updater import N8nDocsScraper
            from n8n_scraper.automation.change_detector import N8nDataAnalyzer
            
            assert AutomatedUpdater is not None
            assert N8nDocsScraper is not None
            assert N8nDataAnalyzer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import automation classes: {e}")

class TestAPIImports:
    """Test API-related imports"""
    
    def test_api_modules(self):
        """Test API module imports"""
        modules_to_test = [
            "n8n_scraper.api.main",
            "n8n_scraper.api.routes.scraper",
            "n8n_scraper.api.routes.analysis",
            "n8n_scraper.api.routes.knowledge"
        ]
        
        for module_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")
    
    def test_fastapi_app(self):
        """Test that FastAPI app can be imported"""
        try:
            from n8n_scraper.api.main import app
            assert app is not None
        except ImportError as e:
            pytest.fail(f"Failed to import FastAPI app: {e}")

class TestUtilityImports:
    """Test utility module imports"""
    
    def test_utility_modules(self):
        """Test utility module imports"""
        modules_to_test = [
            "n8n_scraper.utils.file_handler",
            "n8n_scraper.utils.data_processor",
            "n8n_scraper.utils.logger"
        ]
        
        for module_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

class TestExternalDependencies:
    """Test external dependency imports"""
    
    def test_web_scraping_dependencies(self):
        """Test web scraping related dependencies"""
        dependencies = [
            "requests",
            "bs4",  # beautifulsoup4
            "selenium",
            "aiohttp"
        ]
        
        for dep in dependencies:
            try:
                module = importlib.import_module(dep)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {dep}: {e}")
    
    def test_data_processing_dependencies(self):
        """Test data processing dependencies"""
        dependencies = [
            "pandas",
            "numpy",
            "json",
            "yaml",  # pyyaml
            "sqlite3"
        ]
        
        for dep in dependencies:
            try:
                module = importlib.import_module(dep)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {dep}: {e}")
    
    def test_web_framework_dependencies(self):
        """Test web framework dependencies"""
        dependencies = [
            "fastapi",
            "uvicorn",
            # "streamlit",  # Removed - replaced by Next.js frontend
            "pydantic"
        ]
        
        for dep in dependencies:
            try:
                module = importlib.import_module(dep)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {dep}: {e}")
    
    def test_ai_ml_dependencies(self):
        """Test AI/ML dependencies (optional)"""
        optional_dependencies = [
            "openai",
            "langchain",
            "nltk"
        ]
        
        for dep in optional_dependencies:
            try:
                module = importlib.import_module(dep)
                assert module is not None
            except ImportError:
                # These are optional, so we just warn
                print(f"Warning: Optional dependency {dep} not available")
    
    def test_scheduling_dependencies(self):
        """Test scheduling and automation dependencies"""
        dependencies = [
            "schedule",
            "threading",
            "subprocess",
            "datetime"
        ]
        
        for dep in dependencies:
            try:
                module = importlib.import_module(dep)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {dep}: {e}")

class TestScriptImports:
    """Test script imports"""
    
    def test_script_modules(self):
        """Test that script modules can be imported"""
        # Test scripts that should be importable
        script_modules = [
            "scripts.start_system"
        ]
        
        for module_name in script_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

class TestToolImports:
    """Test tool imports"""
    
    def test_tool_modules(self):
        """Test that tool modules can be imported"""
        tool_modules = [
            "tools.system_check"
        ]
        
        for module_name in tool_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])