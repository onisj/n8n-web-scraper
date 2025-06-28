#!/usr/bin/env python3
"""
Startup Script for n8n AI Knowledge System

This script provides an easy way to start the entire n8n AI Knowledge System
with different configurations and modes.
"""

import os
import sys
import time
import signal
import argparse
import subprocess
import threading
from pathlib import Path
from typing import List, Dict, Optional

class SystemManager:
    """Manages the startup and shutdown of system components"""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = False
        self.base_dir = Path(__file__).parent.parent.parent  # Go up from src/scripts to project root
        
    def start_component(self, name: str, command: List[str], cwd: Optional[str] = None) -> bool:
        """Start a system component"""
        try:
            print(f"Starting {name}...")
            
            # Set working directory
            work_dir = cwd or str(self.base_dir)
            
            # Create log files for output
            log_dir = self.base_dir / "logs"
            log_dir.mkdir(exist_ok=True)
            
            # Use log files instead of PIPE to prevent buffer overflow
            stdout_log = log_dir / f"{name.lower().replace(' ', '_')}_stdout.log"
            stderr_log = log_dir / f"{name.lower().replace(' ', '_')}_stderr.log"
            
            # Start process with file output instead of PIPE
            with open(stdout_log, 'w') as stdout_file, open(stderr_log, 'w') as stderr_file:
                process = subprocess.Popen(
                    command,
                    cwd=work_dir,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    text=True
                )
            
            self.processes[name] = process
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                print(f"✓ {name} started successfully (PID: {process.pid})")
                print(f"  Logs: {stdout_log} | {stderr_log}")
                return True
            else:
                print(f"✗ {name} failed to start")
                # Read error from log file
                try:
                    with open(stderr_log, 'r') as f:
                        stderr_content = f.read().strip()
                    if stderr_content:
                        print(f"Error: {stderr_content}")
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"✗ Failed to start {name}: {str(e)}")
            return False
    
    def stop_component(self, name: str) -> bool:
        """Stop a system component"""
        if name not in self.processes:
            return True
            
        try:
            process = self.processes[name]
            if process.poll() is None:  # Process is still running
                print(f"Stopping {name}...")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    print(f"Force killing {name}...")
                    process.kill()
                    process.wait()
                
                print(f"✓ {name} stopped")
            
            del self.processes[name]
            return True
            
        except Exception as e:
            print(f"✗ Error stopping {name}: {str(e)}")
            return False
    
    def stop_all(self):
        """Stop all running components"""
        print("\nShutting down system...")
        for name in list(self.processes.keys()):
            self.stop_component(name)
        self.running = False
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        print("Checking dependencies...")
        
        # Check Python packages
        required_packages = [
            'fastapi', 'uvicorn', 'requests',  # Removed streamlit
            'beautifulsoup4', 'pandas', 'numpy'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                # Handle package name variations
                import_name = package
                if package == "beautifulsoup4":
                    import_name = "bs4"
                __import__(import_name)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"✗ Missing packages: {', '.join(missing_packages)}")
            print("Install with: pip install -r requirements.txt")
            return False
        
        # Check required files
        required_files = [
            'src/n8n_scraper/api/main.py',
            'src/n8n_scraper/automation/update_scheduler.py',
            'requirements.txt'
        ]
        
        missing_files = []
        for file in required_files:
            if not (self.base_dir / file).exists():
                missing_files.append(file)
        
        if missing_files:
            print(f"✗ Missing files: {', '.join(missing_files)}")
            return False
        
        print("✓ All dependencies satisfied")
        return True
    
    def setup_data_directory(self):
        """Ensure data directories exist"""
        directories = [
            self.base_dir / "data" / "scraped_docs",
            self.base_dir / "data" / "vector_db",
            self.base_dir / "logs",
            self.base_dir / "data" / "exports",
            self.base_dir / "data" / "backups",
            self.base_dir / "config"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        print(f"✓ Data directories ready")
    
    def start_api_server(self, host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
        """Start the FastAPI server"""
        command = [
            sys.executable, "-m", "uvicorn", "src.n8n_scraper.api.main:app",
            "--host", host,
            "--port", str(port),
            "--log-level", "info"
        ]
        
        if reload:
            command.append("--reload")
        
        return self.start_component("API Server", command)
    
    # def start_streamlit_app(self, port: int = 8501):
    #     """Start the Streamlit web interface - DEPRECATED"""
    #     # Streamlit has been replaced by Next.js frontend
    #     print("⚠ Streamlit has been replaced by Next.js frontend")
    #     print("  Please use the Next.js frontend at http://localhost:3000")
    #     return False
    
    def start_scraper(self, mode: str = "analyze"):
        """Start the documentation scraper"""
        if mode == "scrape":
            command = [sys.executable, "src/scripts/run_scraper.py", "--scrape"]
        elif mode == "analyze":
            command = [sys.executable, "src/scripts/run_scraper.py", "--analyze"]
        elif mode == "full":
            command = [sys.executable, "src/scripts/run_scraper.py", "--scrape", "--analyze"]
        else:
            print(f"✗ Unknown scraper mode: {mode}")
            return False
        
        return self.start_component(f"Scraper ({mode})", command)
    
    def start_updater(self):
        """Start the automated updater"""
        command = [sys.executable, "src/n8n_scraper/automation/update_scheduler.py", "--start"]
        return self.start_component("Automated Updater", command)
    
    def wait_for_services(self):
        """Wait for services to be ready"""
        print("\nWaiting for services to be ready...")
        
        # Wait for API server
        if "API Server" in self.processes:
            for i in range(30):  # Wait up to 30 seconds
                try:
                    import requests
                    response = requests.get("http://localhost:8000/health", timeout=2)
                    if response.status_code == 200:
                        print("✓ API Server is ready")
                        break
                except:
                    time.sleep(1)
            else:
                print("⚠ API Server may not be ready")
        
        # Streamlit removed - replaced by Next.js frontend
        # Next.js frontend should be started separately
    
    def show_status(self):
        """Show status of all components"""
        print("\n" + "="*50)
        print("n8n AI Knowledge System Status")
        print("="*50)
        
        if not self.processes:
            print("No components running")
            return
        
        for name, process in self.processes.items():
            if process.poll() is None:
                status = f"✓ Running (PID: {process.pid})"
            else:
                status = "✗ Stopped"
            print(f"{name:20} {status}")
        
        print("\nAccess URLs:")
        if "API Server" in self.processes:
            print("  API Server:     http://localhost:8000")
            print("  API Docs:       http://localhost:8000/docs")
        # Streamlit removed - Next.js frontend available at http://localhost:3000
        print("  Next.js Frontend: http://localhost:3000 (start separately)")
        
        print("\nPress Ctrl+C to stop all services")
    
    def monitor_processes(self):
        """Monitor running processes and restart if needed"""
        while self.running:
            time.sleep(10)
            
            # Check each process
            for name, process in list(self.processes.items()):
                if process.poll() is not None:  # Process has stopped
                    print(f"\n⚠ {name} has stopped unexpectedly")
                    # Could implement auto-restart here
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\nReceived shutdown signal...")
        self.stop_all()
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(
        description="n8n AI Knowledge System Startup Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_system.py --mode full                    # Start everything
  python start_system.py --mode api-only               # API server only
  python start_system.py --mode web-only               # Web mode (Next.js separate)
  python start_system.py --mode development            # Development mode
  python start_system.py --scraper-mode scrape         # Include scraping
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["full", "api-only", "development", "minimal"],  # Removed web-only
        default="full",
        help="System startup mode"
    )
    
    parser.add_argument(
        "--api-port",
        type=int,
        default=8000,
        help="API server port (default: 8000)"
    )
    
    # parser.add_argument(
    #     "--web-port",
    #     type=int,
    #     default=8501,
    #     help="Streamlit port (default: 8501) - DEPRECATED"
    # )
    
    parser.add_argument(
        "--scraper-mode",
        choices=["analyze", "scrape", "full", "none"],
        default="analyze",
        help="Scraper mode (default: analyze)"
    )
    
    parser.add_argument(
        "--no-updater",
        action="store_true",
        help="Don't start the automated updater"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check dependencies and exit"
    )
    
    args = parser.parse_args()
    
    # Create system manager
    manager = SystemManager()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, manager.signal_handler)
    signal.signal(signal.SIGTERM, manager.signal_handler)
    
    # Check dependencies
    if not manager.check_dependencies():
        sys.exit(1)
    
    if args.check_only:
        print("✓ All dependencies satisfied")
        sys.exit(0)
    
    # Setup data directory
    manager.setup_data_directory()
    
    print(f"\nStarting n8n AI Knowledge System in '{args.mode}' mode...")
    
    success = True
    manager.running = True
    
    # Start components based on mode
    if args.mode in ["full", "api-only", "development", "minimal"]:
        success &= manager.start_api_server(
            port=args.api_port,
            reload=args.reload
        )
    
    # Streamlit removed - Next.js frontend should be started separately
    if args.mode in ["full", "development"]:
        print("ℹ Next.js frontend should be started separately:")
        print("  cd frontend && npm run dev")
    
    if args.mode == "full" and args.scraper_mode != "none":
        success &= manager.start_scraper(mode=args.scraper_mode)
    
    if args.mode == "full" and not args.no_updater:
        success &= manager.start_updater()
    
    if not success:
        print("\n✗ Failed to start some components")
        manager.stop_all()
        sys.exit(1)
    
    # Wait for services to be ready
    manager.wait_for_services()
    
    # Show status
    manager.show_status()
    
    # Start monitoring thread
    monitor_thread = threading.Thread(target=manager.monitor_processes, daemon=True)
    monitor_thread.start()
    
    # Keep running until interrupted
    try:
        while manager.running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop_all()

if __name__ == "__main__":
    main()