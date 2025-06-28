#!/usr/bin/env python3
"""
System Health Check for n8n AI Knowledge System

This script performs comprehensive checks to verify that all components
of the system are properly configured and functional.
"""

import os
import sys
import json
import importlib
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import requests
from dataclasses import dataclass


@dataclass
class CheckResult:
    """Result of a system check"""
    name: str
    status: str  # 'pass', 'fail', 'warning', 'skip'
    message: str
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class SystemChecker:
    """Comprehensive system health checker"""
    
    def __init__(self):
        self.results: List[CheckResult] = []
        self.project_root = Path(__file__).parent.parent.parent  # Go up from src/tools to project root
        self.start_time = datetime.now()
    
    def add_result(self, name: str, status: str, message: str, details: Dict = None):
        """Add a check result"""
        self.results.append(CheckResult(name, status, message, details or {}))
    
    def check_python_version(self):
        """Check Python version compatibility"""
        version = sys.version_info
        if version >= (3, 11):
            self.add_result(
                "Python Version", "pass", 
                f"Python {version.major}.{version.minor}.{version.micro} (✓ >= 3.11)"
            )
        elif version >= (3, 9):
            self.add_result(
                "Python Version", "warning", 
                f"Python {version.major}.{version.minor}.{version.micro} (⚠ Recommended: >= 3.11)"
            )
        else:
            self.add_result(
                "Python Version", "fail", 
                f"Python {version.major}.{version.minor}.{version.micro} (✗ Required: >= 3.9)"
            )
    
    def check_required_files(self):
        """Check if all required files exist"""
        required_files = [
            # Core application files
            "requirements.txt",
            "README.md",
            ".env.example",
            "pyproject.toml",
            "Makefile",
            
            # Source package files
            "src/__init__.py",
            "src/n8n_scraper/__init__.py",
            "src/scripts/start_system.py",
            "src/scripts/run_scraper.py",
            "src/scripts/run_tests.py",
            "src/tools/system_check.py",
            
            # Docker files
            "Dockerfile",
            "docker-compose.yml",
        ]
        
        missing_files = []
        existing_files = []
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)
        
        if not missing_files:
            self.add_result(
                "Required Files", "pass", 
                f"All {len(required_files)} required files exist",
                {"existing_files": len(existing_files)}
            )
        else:
            self.add_result(
                "Required Files", "fail", 
                f"{len(missing_files)} files missing: {', '.join(missing_files[:5])}{'...' if len(missing_files) > 5 else ''}",
                {"missing_files": missing_files, "existing_files": len(existing_files)}
            )
    
    def check_required_directories(self):
        """Check if all required directories exist"""
        required_dirs = [
            "src",
            "src/n8n_scraper",
            "src/scripts",
            "src/tools",
            "data",
            "data/analysis",
            "data/exports",
            "data/logs",
            "docs",
            "tests",
            "config"
        ]
        
        missing_dirs = []
        existing_dirs = []
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists() and full_path.is_dir():
                existing_dirs.append(dir_path)
            else:
                missing_dirs.append(dir_path)
        
        if not missing_dirs:
            self.add_result(
                "Required Directories", "pass", 
                f"All {len(required_dirs)} required directories exist"
            )
        else:
            self.add_result(
                "Required Directories", "warning", 
                f"{len(missing_dirs)} directories missing (will be created): {', '.join(missing_dirs)}",
                {"missing_dirs": missing_dirs}
            )
    
    def check_python_dependencies(self):
        """Check if required Python packages are installed"""
        required_packages = [
            # Core dependencies
            "fastapi", "uvicorn", "pydantic",  # Removed streamlit
            
            # AI and ML
            "openai", "anthropic", "chromadb",
            
            # Data processing
            "pandas", "numpy", "requests", "beautifulsoup4",
            
            # Utilities
            "python-dotenv", "pyyaml", "schedule", "psutil",
            
            # Testing
            "pytest", "pytest-cov", "pytest-mock", "pytest-asyncio"
        ]
        
        installed_packages = []
        missing_packages = []
        
        for package in required_packages:
            try:
                # Handle package name variations
                import_name = package.replace("-", "_")
                if package == "beautifulsoup4":
                    import_name = "bs4"
                elif package == "python-dotenv":
                    import_name = "dotenv"
                elif package == "pyyaml":
                    import_name = "yaml"
                elif package == "sentence-transformers":
                    import_name = "sentence_transformers"
                
                importlib.import_module(import_name)
                installed_packages.append(package)
            except ImportError:
                missing_packages.append(package)
        
        if not missing_packages:
            self.add_result(
                "Python Dependencies", "pass", 
                f"All {len(required_packages)} required packages are installed"
            )
        else:
            self.add_result(
                "Python Dependencies", "fail", 
                f"{len(missing_packages)} packages missing: {', '.join(missing_packages[:5])}{'...' if len(missing_packages) > 5 else ''}",
                {"missing_packages": missing_packages, "installed_packages": len(installed_packages)}
            )
    
    def check_environment_variables(self):
        """Check environment variables"""
        env_file = self.project_root / ".env"
        
        if not env_file.exists():
            self.add_result(
                "Environment File", "warning", 
                ".env file not found. Copy .env.example to .env and configure."
            )
            return
        
        # Check for critical environment variables
        critical_vars = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY"
        ]
        
        optional_vars = [
            "N8N_API_KEY",
            "API_SECRET_KEY",
            "REDIS_URL"
        ]
        
        # Load .env file
        env_vars = {}
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value
        except Exception as e:
            self.add_result(
                "Environment Variables", "fail", 
                f"Error reading .env file: {e}"
            )
            return
        
        # Check if at least one AI provider key is set
        ai_keys = [var for var in critical_vars if env_vars.get(var) and env_vars[var] != 'your_api_key_here']
        
        if ai_keys:
            self.add_result(
                "AI API Keys", "pass", 
                f"AI provider keys configured: {', '.join(ai_keys)}"
            )
        else:
            self.add_result(
                "AI API Keys", "fail", 
                "No AI provider API keys configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY."
            )
        
        # Check optional variables
        configured_optional = [var for var in optional_vars if env_vars.get(var)]
        self.add_result(
            "Optional Configuration", "pass", 
            f"Optional variables configured: {len(configured_optional)}/{len(optional_vars)}",
            {"configured": configured_optional}
        )
    
    def check_docker_availability(self):
        """Check if Docker is available"""
        try:
            result = subprocess.run(
                ["docker", "--version"], 
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                self.add_result(
                    "Docker", "pass", 
                    f"Docker available: {version}"
                )
                
                # Check Docker Compose
                try:
                    result = subprocess.run(
                        ["docker-compose", "--version"], 
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        compose_version = result.stdout.strip()
                        self.add_result(
                            "Docker Compose", "pass", 
                            f"Docker Compose available: {compose_version}"
                        )
                    else:
                        self.add_result(
                            "Docker Compose", "warning", 
                            "Docker Compose not available (optional for development)"
                        )
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    self.add_result(
                        "Docker Compose", "warning", 
                        "Docker Compose not available (optional for development)"
                    )
            else:
                self.add_result(
                    "Docker", "warning", 
                    "Docker not available (optional for development)"
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.add_result(
                "Docker", "warning", 
                "Docker not available (optional for development)"
            )
    
    def check_api_endpoints(self):
        """Check if API endpoints are accessible (if running)"""
        endpoints = [
            ("http://localhost:8000/health", "API Health"),
            ("http://localhost:8000/docs", "API Documentation"),
            # ("http://localhost:8501", "Streamlit Interface")  # Removed - replaced by Next.js
        ("http://localhost:3000", "Next.js Frontend (if running)")
        ]
        
        for url, name in endpoints:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    self.add_result(
                        name, "pass", 
                        f"Accessible at {url}"
                    )
                else:
                    self.add_result(
                        name, "warning", 
                        f"Returned status {response.status_code} at {url}"
                    )
            except requests.exceptions.ConnectionError:
                self.add_result(
                    name, "skip", 
                    f"Not running (connection refused at {url})"
                )
            except requests.exceptions.Timeout:
                self.add_result(
                    name, "warning", 
                    f"Timeout accessing {url}"
                )
            except Exception as e:
                self.add_result(
                    name, "warning", 
                    f"Error accessing {url}: {e}"
                )
    
    def check_data_integrity(self):
        """Check data directory structure and content"""
        data_dir = self.project_root / "data"
        
        if not data_dir.exists():
            self.add_result(
                "Data Directory", "warning", 
                "Data directory doesn't exist (will be created on first run)"
            )
            return
        
        # Check subdirectories
        subdirs = ["scraped_docs", "vector_db"]
        existing_subdirs = []
        
        for subdir in subdirs:
            subdir_path = data_dir / subdir
            if subdir_path.exists():
                existing_subdirs.append(subdir)
        
        # Check for scraped data
        scraped_docs_dir = data_dir / "scraped_docs"
        if scraped_docs_dir.exists():
            json_files = list(scraped_docs_dir.glob("*.json"))
            if json_files:
                self.add_result(
                    "Scraped Data", "pass", 
                    f"Found {len(json_files)} scraped documentation files"
                )
            else:
                self.add_result(
                    "Scraped Data", "warning", 
                    "No scraped documentation files found (run scraper first)"
                )
        
        # Check vector database
        vector_db_dir = data_dir / "vector_db"
        if vector_db_dir.exists() and any(vector_db_dir.iterdir()):
            self.add_result(
                "Vector Database", "pass", 
                "Vector database directory contains data"
            )
        else:
            self.add_result(
                "Vector Database", "warning", 
                "Vector database not initialized (will be created on first use)"
            )
    
    def check_configuration_files(self):
        """Check configuration files"""
        config_files = {
            "config/settings.py": "Settings Configuration",
            "config/database.yaml": "Database Configuration",
            "config/scheduler.yaml": "Scheduler Configuration"
        }
        
        for file_path, name in config_files.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    if file_path.endswith('.py'):
                        # Try to import Python config
                        spec = importlib.util.spec_from_file_location("config", full_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        self.add_result(name, "pass", "Valid Python configuration")
                    elif file_path.endswith('.yaml'):
                        # Try to parse YAML config
                        import yaml
                        with open(full_path, 'r') as f:
                            yaml.safe_load(f)
                        self.add_result(name, "pass", "Valid YAML configuration")
                except Exception as e:
                    self.add_result(name, "fail", f"Invalid configuration: {e}")
            else:
                self.add_result(name, "fail", "Configuration file missing")
    
    def run_all_checks(self):
        """Run all system checks"""
        print("🔍 Running n8n AI Knowledge System Health Check...\n")
        
        # Core system checks
        self.check_python_version()
        self.check_required_files()
        self.check_required_directories()
        self.check_python_dependencies()
        
        # Configuration checks
        self.check_environment_variables()
        self.check_configuration_files()
        
        # Optional tools
        self.check_docker_availability()
        
        # Data and runtime checks
        self.check_data_integrity()
        self.check_api_endpoints()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive report"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        # Count results by status
        status_counts = {"pass": 0, "fail": 0, "warning": 0, "skip": 0}
        for result in self.results:
            status_counts[result.status] += 1
        
        # Determine overall health
        if status_counts["fail"] > 0:
            overall_status = "unhealthy"
        elif status_counts["warning"] > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "timestamp": end_time.isoformat(),
            "duration_seconds": duration,
            "overall_status": overall_status,
            "summary": status_counts,
            "total_checks": len(self.results),
            "results": [{
                "name": r.name,
                "status": r.status,
                "message": r.message,
                "details": r.details
            } for r in self.results]
        }
    
    def print_report(self):
        """Print human-readable report"""
        report = self.generate_report()
        
        # Print header
        print("\n" + "="*60)
        print("🏥 n8n AI Knowledge System Health Report")
        print("="*60)
        
        # Print summary
        status_icons = {
            "pass": "✅",
            "fail": "❌", 
            "warning": "⚠️",
            "skip": "⏭️"
        }
        
        overall_icon = {
            "healthy": "✅",
            "warning": "⚠️",
            "unhealthy": "❌"
        }[report["overall_status"]]
        
        print(f"\n{overall_icon} Overall Status: {report['overall_status'].upper()}")
        print(f"⏱️  Check Duration: {report['duration_seconds']:.2f} seconds")
        print(f"📊 Total Checks: {report['total_checks']}")
        
        print("\n📈 Summary:")
        for status, count in report["summary"].items():
            if count > 0:
                print(f"   {status_icons[status]} {status.title()}: {count}")
        
        # Print detailed results
        print("\n📋 Detailed Results:")
        print("-" * 60)
        
        for result in self.results:
            icon = status_icons[result.status]
            print(f"{icon} {result.name}: {result.message}")
            
            # Print details if available
            if result.details:
                for key, value in result.details.items():
                    if isinstance(value, list) and len(value) > 3:
                        print(f"     {key}: {value[:3]}... ({len(value)} total)")
                    else:
                        print(f"     {key}: {value}")
        
        # Print recommendations
        print("\n💡 Recommendations:")
        print("-" * 60)
        
        fail_results = [r for r in self.results if r.status == "fail"]
        warning_results = [r for r in self.results if r.status == "warning"]
        
        if fail_results:
            print("🚨 Critical Issues (must fix):")
            for result in fail_results:
                print(f"   • {result.name}: {result.message}")
        
        if warning_results:
            print("\n⚠️  Warnings (recommended to fix):")
            for result in warning_results:
                print(f"   • {result.name}: {result.message}")
        
        if not fail_results and not warning_results:
            print("🎉 All checks passed! Your system is ready to go.")
        
        print("\n" + "="*60)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="n8n AI Knowledge System Health Checker"
    )
    parser.add_argument(
        "--json", action="store_true", 
        help="Output results in JSON format"
    )
    parser.add_argument(
        "--output", type=str, 
        help="Save report to file"
    )
    
    args = parser.parse_args()
    
    # Run checks
    checker = SystemChecker()
    checker.run_all_checks()
    
    # Generate report
    if args.json:
        report = checker.generate_report()
        output = json.dumps(report, indent=2)
        print(output)
    else:
        checker.print_report()
    
    # Save to file if requested
    if args.output:
        report = checker.generate_report()
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Report saved to: {args.output}")
    
    # Exit with appropriate code
    report = checker.generate_report()
    if report["overall_status"] == "unhealthy":
        sys.exit(1)
    elif report["overall_status"] == "warning":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()