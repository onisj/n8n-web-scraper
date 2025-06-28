#!/usr/bin/env python3
"""
Setup and Installation Script for n8n Documentation Automation System

This script helps configure and deploy the automated scraping system
with proper dependencies, database setup, and service configuration.
"""

import os
import sys
import json
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import argparse

class AutomationSetup:
    """Setup and configuration manager for automation system"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.system = platform.system().lower()
        self.python_executable = sys.executable
        
        print(f"Setting up n8n Documentation Automation System")
        print(f"Project root: {self.project_root}")
        print(f"System: {self.system}")
        print(f"Python: {self.python_executable}")
    
    def check_prerequisites(self) -> Dict[str, bool]:
        """Check system prerequisites"""
        print("\n=== Checking Prerequisites ===")
        
        checks = {}
        
        # Python version check
        python_version = sys.version_info
        python_ok = python_version >= (3, 8)
        checks['python'] = python_ok
        print(f"✓ Python {python_version.major}.{python_version.minor}.{python_version.micro}: {'OK' if python_ok else 'FAIL (requires 3.8+)'}")
        
        # PostgreSQL check
        try:
            result = subprocess.run(['psql', '--version'], capture_output=True, text=True)
            pg_ok = result.returncode == 0
            checks['postgresql'] = pg_ok
            if pg_ok:
                version = result.stdout.strip().split()[-1]
                print(f"✓ PostgreSQL {version}: OK")
            else:
                print("✗ PostgreSQL: NOT FOUND")
        except FileNotFoundError:
            checks['postgresql'] = False
            print("✗ PostgreSQL: NOT FOUND")
        
        # Git check
        try:
            result = subprocess.run(['git', '--version'], capture_output=True, text=True)
            git_ok = result.returncode == 0
            checks['git'] = git_ok
            if git_ok:
                version = result.stdout.strip().split()[-1]
                print(f"✓ Git {version}: OK")
            else:
                print("✗ Git: NOT FOUND")
        except FileNotFoundError:
            checks['git'] = False
            print("✗ Git: NOT FOUND")
        
        # pip check
        try:
            result = subprocess.run([self.python_executable, '-m', 'pip', '--version'], capture_output=True, text=True)
            pip_ok = result.returncode == 0
            checks['pip'] = pip_ok
            if pip_ok:
                print(f"✓ pip: OK")
            else:
                print("✗ pip: NOT FOUND")
        except FileNotFoundError:
            checks['pip'] = False
            print("✗ pip: NOT FOUND")
        
        return checks
    
    def install_dependencies(self) -> bool:
        """Install Python dependencies"""
        print("\n=== Installing Dependencies ===")
        
        try:
            # Install main requirements
            if (self.project_root / "requirements.txt").exists():
                print("Installing main requirements...")
                result = subprocess.run([
                    self.python_executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
                ], check=True)
            
            # Install automation requirements
            if (self.project_root / "requirements_automation.txt").exists():
                print("Installing automation requirements...")
                result = subprocess.run([
                    self.python_executable, '-m', 'pip', 'install', '-r', 'requirements_automation.txt'
                ], check=True)
            
            print("✓ Dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install dependencies: {e}")
            return False
        except Exception as e:
            print(f"✗ Error installing dependencies: {e}")
            return False
    
    def setup_directories(self) -> bool:
        """Create necessary directories"""
        print("\n=== Setting Up Directories ===")
        
        directories = [
            "data",
            "data/scraped_docs",
            "data/cache",
            "data/chroma_db",
            "data/exports",
            "data/analysis",
            "logs",
            "data/backups",
            "config"
        ]
        
        try:
            for directory in directories:
                dir_path = self.project_root / directory
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"✓ Created directory: {directory}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error creating directories: {e}")
            return False
    
    def configure_environment(self) -> bool:
        """Configure environment variables"""
        print("\n=== Configuring Environment ===")
        
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"
        
        if not env_file.exists():
            if env_example.exists():
                print("Copying .env.example to .env...")
                shutil.copy2(env_example, env_file)
                print("✓ Environment file created from template")
                print("⚠️  Please edit .env file with your specific configuration")
            else:
                print("✗ No .env.example file found")
                return False
        else:
            print("✓ Environment file already exists")
        
        return True
    
    def setup_database(self) -> bool:
        """Setup database schema"""
        print("\n=== Setting Up Database ===")
        
        try:
            # Check if database setup scripts exist in scripts directory
            scripts_dir = self.project_root / "scripts"
            setup_scripts = [
                "create_database.sql",
                "fix_foreign_keys.sql"
            ]
            
            available_scripts = []
            for script in setup_scripts:
                if (scripts_dir / script).exists():
                    available_scripts.append(script)
            
            if available_scripts:
                print(f"Found database setup scripts: {', '.join(available_scripts)}")
                print("⚠️  Please run these scripts manually against your PostgreSQL database")
                print("   Example: psql -d n8n_scraper -f scripts/create_database.sql")
            else:
                print("⚠️  No database setup scripts found")
                print("   Please ensure your PostgreSQL database is properly configured")
            
            return True
            
        except Exception as e:
            print(f"✗ Error setting up database: {e}")
            return False
    
    def setup_service(self) -> bool:
        """Setup system service"""
        print("\n=== Setting Up System Service ===")
        
        if self.system == "linux":
            return self._setup_systemd_service()
        elif self.system == "darwin":
            return self._setup_launchd_service()
        else:
            print(f"⚠️  System service setup not supported for {self.system}")
            print("   You can run the automation manually using:")
            print(f"   {self.python_executable} src/automation/src/automation/automated_scraper.py --mode schedule")
            return True
    
    def _setup_systemd_service(self) -> bool:
        """Setup systemd service on Linux"""
        service_file = self.project_root / "systemd" / "n8n-automation.service"
        
        if not service_file.exists():
            print("✗ Systemd service file not found")
            return False
        
        print("To install the systemd service:")
        print(f"1. sudo cp {service_file} /etc/systemd/system/")
        print("2. sudo systemctl daemon-reload")
        print("3. sudo systemctl enable n8n-automation.service")
        print("4. sudo systemctl start n8n-automation.service")
        print("")
        print("To check service status:")
        print("   sudo systemctl status n8n-automation.service")
        
        return True
    
    def _setup_launchd_service(self) -> bool:
        """Setup launchd service on macOS"""
        plist_file = self.project_root / "launchd" / "com.n8n.automation.plist"
        
        if not plist_file.exists():
            print("✗ Launchd plist file not found")
            return False
        
        user_agents_dir = Path.home() / "Library" / "LaunchAgents"
        user_agents_dir.mkdir(exist_ok=True)
        
        target_plist = user_agents_dir / "com.n8n.automation.plist"
        
        print("To install the launchd service:")
        print(f"1. cp {plist_file} {target_plist}")
        print("2. launchctl load ~/Library/LaunchAgents/com.n8n.automation.plist")
        print("3. launchctl start com.n8n.automation")
        print("")
        print("To check service status:")
        print("   launchctl list | grep com.n8n.automation")
        print("")
        print("To stop the service:")
        print("   launchctl stop com.n8n.automation")
        print("   launchctl unload ~/Library/LaunchAgents/com.n8n.automation.plist")
        
        return True
    
    def test_automation(self) -> bool:
        """Test the automation system"""
        print("\n=== Testing Automation System ===")
        
        try:
            # Test health check
            print("Running health check...")
            result = subprocess.run([
                self.python_executable, "src/automation/src/automation/automated_scraper.py", "--mode", "health"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✓ Health check passed")
                
                # Parse and display health status
                try:
                    health_data = json.loads(result.stdout)
                    if health_data.get('overall_healthy'):
                        print("✓ System is healthy")
                    else:
                        print("⚠️  System has health issues:")
                        for check_name, check_result in health_data.get('checks', {}).items():
                            if not check_result.get('healthy'):
                                print(f"   - {check_name}: {check_result.get('message')}")
                except json.JSONDecodeError:
                    print("⚠️  Could not parse health check output")
                
                return True
            else:
                print(f"✗ Health check failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("✗ Health check timed out")
            return False
        except Exception as e:
            print(f"✗ Error running health check: {e}")
            return False
    
    def run_full_setup(self) -> bool:
        """Run complete setup process"""
        print("Starting full automation system setup...\n")
        
        # Check prerequisites
        prereqs = self.check_prerequisites()
        if not all(prereqs.values()):
            print("\n✗ Prerequisites check failed. Please install missing components.")
            return False
        
        # Install dependencies
        if not self.install_dependencies():
            print("\n✗ Dependency installation failed.")
            return False
        
        # Setup directories
        if not self.setup_directories():
            print("\n✗ Directory setup failed.")
            return False
        
        # Configure environment
        if not self.configure_environment():
            print("\n✗ Environment configuration failed.")
            return False
        
        # Setup database
        if not self.setup_database():
            print("\n✗ Database setup failed.")
            return False
        
        # Setup service
        if not self.setup_service():
            print("\n✗ Service setup failed.")
            return False
        
        # Test automation
        if not self.test_automation():
            print("\n⚠️  Automation test failed, but setup is complete.")
            print("   Please check your configuration and try again.")
        
        print("\n=== Setup Complete ===")
        print("✓ n8n Documentation Automation System setup completed successfully!")
        print("")
        print("Next steps:")
        print("1. Edit .env file with your specific configuration")
        print("2. Setup your PostgreSQL database")
        print("3. Run initial scraping: python src/automation/src/automation/automated_scraper.py --mode run --force")
        print("4. Start the scheduler: python src/automation/src/automation/automated_scraper.py --mode schedule")
        print("")
        print("For more information, see the README.md file.")
        
        return True

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Setup n8n Documentation Automation System")
    parser.add_argument("--action", choices=[
        "full", "prereqs", "deps", "dirs", "env", "db", "service", "test"
    ], default="full", help="Setup action to perform")
    
    args = parser.parse_args()
    
    setup = AutomationSetup()
    
    if args.action == "full":
        success = setup.run_full_setup()
    elif args.action == "prereqs":
        prereqs = setup.check_prerequisites()
        success = all(prereqs.values())
    elif args.action == "deps":
        success = setup.install_dependencies()
    elif args.action == "dirs":
        success = setup.setup_directories()
    elif args.action == "env":
        success = setup.configure_environment()
    elif args.action == "db":
        success = setup.setup_database()
    elif args.action == "service":
        success = setup.setup_service()
    elif args.action == "test":
        success = setup.test_automation()
    else:
        print(f"Unknown action: {args.action}")
        success = False
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()