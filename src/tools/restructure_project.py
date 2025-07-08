#!/usr/bin/env python3
"""
Project Restructuring Script

This script reorganizes the current n8n AI Knowledge System to follow
the proper directory structure as outlined in the architecture plan.
"""

import os
import shutil
from pathlib import Path

def create_directory_structure():
    """Create the proper directory structure"""
    base_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper")
    
    # Define the target structure
    directories = [
        "agents",
        "automation", 
        "web_interface",
        "web_interface/components",
        "web_interface/static",
        "database",
        "database/schemas",
        "database/migrations",
        "api",
        "api/routes",
        "api/middleware",
        "config",
        "tests",
        "docs",
        "data",  # For scraped data
        "logs",  # For system logs
        "backups"  # For data backups
    ]
    
    print("Creating directory structure...")
    for directory in directories:
        dir_path = base_dir / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {directory}/")
    
    # Create __init__.py files for Python packages
    python_packages = [
        "agents",
        "automation",
        "web_interface",
        "database",
        "api",
        "api/routes",
        "api/middleware",
        "config",
        "tests"
    ]
    
    for package in python_packages:
        init_file = base_dir / package / "__init__.py"
        if not init_file.exists():
            init_file.write_text(f'"""\n{package.replace("/", ".")} package\n"""\n')
            print(f"✓ Created: {package}/__init__.py")

def move_existing_files():
    """Move existing files to their proper locations"""
    base_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper")
    
    # File mappings: current_file -> new_location
    file_mappings = {
        "ai_agent.py": "agents/n8n_agent.py",
        "knowledge_processor.py": "agents/knowledge_processor.py",
        "api_server.py": "api/main.py",
        "automated_updater.py": "automation/update_scheduler.py",
        "streamlit_app.py": "web_interface/streamlit_app.py",
        "n8n_docs_scraper.py": "automation/knowledge_updater.py",
        "data_analyzer.py": "automation/change_detector.py",
        "config.json": "config/scraper.json",
        "requirements.txt": "requirements.txt",  # Keep at root
        "streamlit_requirements.txt": "web_interface/requirements.txt",
        "docker-compose.yml": "docker-compose.yml",  # Keep at root
        "Dockerfile": "Dockerfile",  # Keep at root
        "start_system.py": "start_system.py",  # Keep at root
    }
    
    print("\nMoving existing files...")
    for current_file, new_location in file_mappings.items():
        current_path = base_dir / current_file
        new_path = base_dir / new_location
        
        if current_path.exists():
            # Create parent directory if it doesn't exist
            new_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move the file
            shutil.move(str(current_path), str(new_path))
            print(f"✓ Moved: {current_file} -> {new_location}")
        else:
            print(f"⚠ File not found: {current_file}")
    
    # Move data directory
    data_src = base_dir / "n8n_docs_data"
    data_dst = base_dir / "data" / "scraped_docs"
    if data_src.exists():
        data_dst.parent.mkdir(parents=True, exist_ok=True)
        if data_dst.exists():
            shutil.rmtree(data_dst)
        shutil.move(str(data_src), str(data_dst))
        print(f"✓ Moved: n8n_docs_data/ -> data/scraped_docs/")
    
    # Move documentation files
    doc_files = [
        "README_AI_SYSTEM.md",
        "README_COMPLETE_SYSTEM.md", 
        "TRAE_INTEGRATION_GUIDE.md",
        "ai_knowledge_system_plan.md"
    ]
    
    for doc_file in doc_files:
        src_path = base_dir / doc_file
        dst_path = base_dir / "docs" / doc_file
        if src_path.exists():
            shutil.move(str(src_path), str(dst_path))
            print(f"✓ Moved: {doc_file} -> docs/{doc_file}")

def create_config_files():
    """Create configuration files"""
    base_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper")
    
    # Create settings.py
    settings_content = '''"""\nConfiguration settings for n8n AI Knowledge System\n"""\n\nimport os\nfrom pathlib import Path\nfrom typing import Optional\n\n# Base paths\nBASE_DIR = Path(__file__).parent.parent\nDATA_DIR = BASE_DIR / "data"\nLOGS_DIR = BASE_DIR / "logs"\nBACKUPS_DIR = BASE_DIR / "backups"\n\n# API Configuration\nAPI_HOST = os.getenv("API_HOST", "0.0.0.0")\nAPI_PORT = int(os.getenv("API_PORT", "8000"))\nAPI_WORKERS = int(os.getenv("API_WORKERS", "1"))\n\n# Streamlit Configuration\nSTREAMLIT_HOST = os.getenv("STREAMLIT_HOST", "0.0.0.0")\nSTREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))\n\n# AI Configuration\nOPENAI_API_KEY = os.getenv("OPENAI_API_KEY")\nAI_MODEL = os.getenv("AI_MODEL", "gpt-4")\nAI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "500"))\nAI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.7"))\n\n# Database Configuration\nVECTOR_DB_PATH = DATA_DIR / "vector_db"\nKNOWLEDGE_DB_PATH = DATA_DIR / "knowledge.db"\n\n# Scraping Configuration\nSCRAPER_BASE_URL = "https://docs.n8n.io"\nSCRAPER_MAX_PAGES = int(os.getenv("SCRAPER_MAX_PAGES", "1000"))\nSCRAPER_DELAY = float(os.getenv("SCRAPER_DELAY", "1.0"))\nSCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", "30"))\n\n# Update Configuration\nUPDATE_FREQUENCY = os.getenv("UPDATE_FREQUENCY", "daily")\nFULL_SCRAPE_FREQUENCY = os.getenv("FULL_SCRAPE_FREQUENCY", "weekly")\nBACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))\n\n# Logging Configuration\nLOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")\nLOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"\nLOG_FILE = LOGS_DIR / "system.log"\n\n# Security Configuration\nAPI_KEY: Optional[str] = os.getenv("API_KEY")\nCORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")\n\n# Performance Configuration\nCACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour\nMAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))\n\n# Ensure directories exist\nfor directory in [DATA_DIR, LOGS_DIR, BACKUPS_DIR, VECTOR_DB_PATH.parent]:\n    directory.mkdir(parents=True, exist_ok=True)\n'''
    
    settings_file = base_dir / "config" / "settings.py"
    settings_file.write_text(settings_content)
    print(f"✓ Created: config/settings.py")
    
    # Create database.yaml
    database_yaml = '''# Database Configuration\nvector_db:\n  provider: "chromadb"\n  path: "../data/vector_db"\n  collection_name: "n8n_knowledge"\n  embedding_model: "text-embedding-ada-002"\n\nknowledge_db:\n  provider: "sqlite"\n  path: "../data/knowledge.db"\n  tables:\n    - documents\n    - chunks\n    - metadata\n    - updates\n\ncache:\n  provider: "redis"\n  host: "localhost"\n  port: 6379\n  db: 0\n  ttl: 3600\n'''
    
    db_config_file = base_dir / "config" / "database.yaml"
    db_config_file.write_text(database_yaml)
    print(f"✓ Created: config/database.yaml")
    
    # Create scheduler.yaml
    scheduler_yaml = '''# Scheduler Configuration\nschedules:\n  daily_update:\n    cron: "0 2 * * *"  # 2 AM daily\n    job: "incremental_update"\n    enabled: true\n\n  weekly_full_scrape:\n    cron: "0 3 * * 0"  # 3 AM every Sunday\n    job: "full_scrape"\n    enabled: true\n\n  monthly_cleanup:\n    cron: "0 4 1 * *"  # 4 AM first day of month\n    job: "cleanup_old_data"\n    enabled: true\n\n  backup:\n    cron: "0 1 * * *"  # 1 AM daily\n    job: "backup_data"\n    enabled: true\n\njobs:\n  incremental_update:\n    description: "Check for documentation updates"\n    timeout: 1800  # 30 minutes\n    retry_count: 3\n\n  full_scrape:\n    description: "Complete documentation scrape"\n    timeout: 7200  # 2 hours\n    retry_count: 2\n\n  cleanup_old_data:\n    description: "Clean up old backups and logs"\n    timeout: 600  # 10 minutes\n    retry_count: 1\n\n  backup_data:\n    description: "Backup knowledge base"\n    timeout: 1200  # 20 minutes\n    retry_count: 2\n'''
    
    scheduler_config_file = base_dir / "config" / "scheduler.yaml"
    scheduler_config_file.write_text(scheduler_yaml)
    print(f"✓ Created: config/scheduler.yaml")

def create_api_structure():
    """Create API route structure"""
    base_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper")
    
    # Create routes/__init__.py
    routes_init = '''"""\nAPI Routes package\n"""\n\nfrom .ai_routes import router as ai_router\nfrom .knowledge_routes import router as knowledge_router\nfrom .system_routes import router as system_router\n\n__all__ = ["ai_router", "knowledge_router", "system_router"]\n'''
    
    routes_init_file = base_dir / "api" / "routes" / "__init__.py"
    routes_init_file.write_text(routes_init)
    print(f"✓ Created: api/routes/__init__.py")
    
    # Create middleware/__init__.py
    middleware_init = '''"""\nAPI Middleware package\n"""\n\nfrom .auth import AuthMiddleware\nfrom .cors import CORSMiddleware\nfrom .rate_limit import RateLimitMiddleware\n\n__all__ = ["AuthMiddleware", "CORSMiddleware", "RateLimitMiddleware"]\n'''
    
    middleware_init_file = base_dir / "api" / "middleware" / "__init__.py"
    middleware_init_file.write_text(middleware_init)
    print(f"✓ Created: api/middleware/__init__.py")

def create_database_structure():
    """Create database structure files"""
    base_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper")
    
    # Create vector_db.py
    vector_db_content = '''"""\nVector Database Management\n"""\n\nfrom typing import List, Dict, Any, Optional\nfrom pathlib import Path\nimport chromadb\nfrom chromadb.config import Settings\n\nclass VectorDatabase:\n    """Vector database for storing and retrieving knowledge embeddings"""\n    \n    def __init__(self, db_path: Path, collection_name: str = "n8n_knowledge"):\n        self.db_path = db_path\n        self.collection_name = collection_name\n        self.client = None\n        self.collection = None\n        \n    def initialize(self):\n        """Initialize the vector database"""\n        self.db_path.mkdir(parents=True, exist_ok=True)\n        \n        self.client = chromadb.PersistentClient(\n            path=str(self.db_path),\n            settings=Settings(anonymized_telemetry=False)\n        )\n        \n        self.collection = self.client.get_or_create_collection(\n            name=self.collection_name\n        )\n        \n    def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str]):\n        """Add documents to the vector database"""\n        if not self.collection:\n            raise RuntimeError("Database not initialized")\n            \n        self.collection.add(\n            documents=documents,\n            metadatas=metadatas,\n            ids=ids\n        )\n        \n    def search(self, query: str, n_results: int = 10) -> List[Dict[str, Any]]:\n        """Search for similar documents"""\n        if not self.collection:\n            raise RuntimeError("Database not initialized")\n            \n        results = self.collection.query(\n            query_texts=[query],\n            n_results=n_results\n        )\n        \n        return results\n        \n    def get_stats(self) -> Dict[str, Any]:\n        """Get database statistics"""\n        if not self.collection:\n            return {"error": "Database not initialized"}\n            \n        count = self.collection.count()\n        return {\n            "total_documents": count,\n            "collection_name": self.collection_name\n        }\n'''
    
    vector_db_file = base_dir / "database" / "vector_db.py"
    vector_db_file.write_text(vector_db_content)
    print(f"✓ Created: database/vector_db.py")

def update_imports_and_references():
    """Update import statements in moved files"""
    print("\nUpdating import statements...")
    
    # This would require parsing and updating Python files
    # For now, just create a note file
    base_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper")
    
    update_notes = '''# Import Updates Required\n\nAfter restructuring, the following files need import updates:\n\n## api/main.py (formerly api_server.py)\n- Update imports to use new structure:\n  ```python\n  from agents.n8n_agent import N8nExpertAgent\n  from agents.knowledge_processor import N8nKnowledgeProcessor\n  from automation.update_scheduler import AutomatedUpdater\n  from automation.change_detector import N8nDocsAnalyzer\n  ```\n\n## web_interface/streamlit_app.py\n- Update imports:\n  ```python\n  from agents.n8n_agent import N8nExpertAgent\n  from agents.knowledge_processor import N8nKnowledgeProcessor\n  from automation.update_scheduler import AutomatedUpdater\n  from automation.change_detector import N8nDocsAnalyzer\n  ```\n\n## start_system.py\n- Update module paths in subprocess calls\n- Update file paths for moved components\n\n## Docker and deployment files\n- Update COPY commands in Dockerfile\n- Update volume mounts in docker-compose.yml\n'''
    
    notes_file = base_dir / "RESTRUCTURE_NOTES.md"
    notes_file.write_text(update_notes)
    print(f"✓ Created: RESTRUCTURE_NOTES.md")

def main():
    """Main restructuring function"""
    print("🚀 Starting project restructuring...\n")
    
    try:
        create_directory_structure()
        move_existing_files()
        create_config_files()
        create_api_structure()
        create_database_structure()
        update_imports_and_references()
        
        print("\n✅ Project restructuring completed successfully!")
        print("\n📁 New structure:")
        print("n8n-ai-knowledge-system/")
        print("├── agents/")
        print("├── automation/")
        print("├── web_interface/")
        print("├── database/")
        print("├── api/")
        print("├── config/")
        print("├── tests/")
        print("├── docs/")
        print("├── data/")
        print("├── logs/")
        print("└── backups/")
        
        print("\n⚠️  Next steps:")
        print("1. Review RESTRUCTURE_NOTES.md for required import updates")
        print("2. Update import statements in moved files")
        print("3. Test the system after restructuring")
        print("4. Update documentation with new structure")
        
    except Exception as e:
        print(f"\n❌ Error during restructuring: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())