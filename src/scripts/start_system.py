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
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging

class ComponentType(Enum):
    """Types of system components"""
    SERVICE = "service"  # Long-running services that should stay alive
    TASK = "task"       # One-time tasks that complete and exit
    PERIODIC = "periodic"  # Tasks that run periodically
    CRITICAL_SERVICE = "critical_service"  # Critical services that cause system shutdown if they fail

class ComponentStatus(Enum):
    """Status of system components"""
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"
    RESTARTING = "restarting"

@dataclass
class ComponentInfo:
    """Information about a system component"""
    name: str
    process: subprocess.Popen
    component_type: ComponentType
    start_time: datetime
    expected_duration: Optional[int] = None  # Expected duration in seconds for tasks
    restart_on_failure: bool = True
    max_restarts: int = 3
    restart_count: int = 0
    original_command: Optional[List[str]] = None
    original_cwd: Optional[str] = None
    status: ComponentStatus = ComponentStatus.STARTING
    health_check_url: Optional[str] = None  # URL for health checks
    health_check_interval: int = 30  # Health check interval in seconds
    last_health_check: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)  # Component dependencies
    graceful_shutdown_timeout: int = 10  # Timeout for graceful shutdown
    failure_threshold: int = 3  # Number of consecutive health check failures before restart
    consecutive_failures: int = 0
    last_restart_time: Optional[datetime] = None
    total_runtime: float = 0.0  # Total runtime across all restarts

class SystemManager:
    """Manages the startup and shutdown of system components"""
    
    def __init__(self):
        self.components: Dict[str, ComponentInfo] = {}
        self.running = False
        self.base_dir = Path(__file__).parent.parent.parent  # Go up from src/scripts to project root
        self.startup_order: List[str] = []  # Track startup order for dependencies
        self.shutdown_order: List[str] = []  # Track shutdown order (reverse of startup)
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging for the system manager"""
        log_dir = self.base_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "system_manager.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("SystemManager")
    
    def check_dependencies(self, component_name: str, dependencies: List[str]) -> bool:
        """Check if all dependencies are running"""
        for dep in dependencies:
            if dep not in self.components:
                self.logger.warning(f"Dependency '{dep}' not found for component '{component_name}'")
                return False
            
            dep_component = self.components[dep]
            if dep_component.status not in [ComponentStatus.RUNNING, ComponentStatus.COMPLETED]:
                self.logger.warning(f"Dependency '{dep}' is not ready (status: {dep_component.status.value})")
                return False
        
        return True
        
    def start_component(self, name: str, command: List[str], component_type: ComponentType = ComponentType.SERVICE, 
                       cwd: Optional[str] = None, expected_duration: Optional[int] = None, 
                       restart_on_failure: bool = True, health_check_url: Optional[str] = None,
                       dependencies: Optional[List[str]] = None, graceful_shutdown_timeout: int = 10) -> bool:
        """Start a system component with enhanced monitoring and dependency management"""
        try:
            dependencies = dependencies or []
            
            # Check dependencies first
            if dependencies and not self.check_dependencies(name, dependencies):
                self.logger.error(f"Cannot start {name}: dependencies not satisfied")
                return False
            
            self.logger.info(f"Starting {name} ({component_type.value})...")
            print(f"Starting {name} ({component_type.value})...")
            
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
            
            # Create component info with enhanced monitoring
            component_info = ComponentInfo(
                name=name,
                process=process,
                component_type=component_type,
                start_time=datetime.now(),
                expected_duration=expected_duration,
                restart_on_failure=restart_on_failure,
                original_command=command.copy(),
                original_cwd=work_dir,
                health_check_url=health_check_url,
                dependencies=dependencies,
                graceful_shutdown_timeout=graceful_shutdown_timeout,
                status=ComponentStatus.STARTING
            )
            
            self.components[name] = component_info
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                component_info.status = ComponentStatus.RUNNING
                self.startup_order.append(name)
                self.shutdown_order.insert(0, name)  # Reverse order for shutdown
                
                self.logger.info(f"{name} started successfully (PID: {process.pid})")
                print(f"✓ {name} started successfully (PID: {process.pid})")
                print(f"  Type: {component_type.value}")
                print(f"  Logs: {stdout_log} | {stderr_log}")
                if expected_duration:
                    print(f"  Expected duration: {expected_duration}s")
                if health_check_url:
                    print(f"  Health check: {health_check_url}")
                if dependencies:
                    print(f"  Dependencies: {', '.join(dependencies)}")
                return True
            else:
                component_info.status = ComponentStatus.FAILED
                self.logger.error(f"{name} failed to start")
                print(f"✗ {name} failed to start")
                # Read error from log file
                try:
                    with open(stderr_log, 'r') as f:
                        stderr_content = f.read().strip()
                    if stderr_content:
                        self.logger.error(f"{name} error: {stderr_content}")
                        print(f"Error: {stderr_content}")
                except:
                    pass
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start {name}: {str(e)}")
            print(f"✗ Failed to start {name}: {str(e)}")
            return False
    
    def perform_health_check(self, component: ComponentInfo) -> bool:
        """Perform health check on a component"""
        if not component.health_check_url:
            return True  # No health check configured
        
        try:
            import requests
            response = requests.get(component.health_check_url, timeout=5)
            component.last_health_check = datetime.now()
            
            if response.status_code == 200:
                component.consecutive_failures = 0
                return True
            else:
                component.consecutive_failures += 1
                self.logger.warning(f"Health check failed for {component.name}: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            component.consecutive_failures += 1
            self.logger.warning(f"Health check failed for {component.name}: {str(e)}")
            return False
    
    def should_restart_component(self, component: ComponentInfo) -> bool:
        """Determine if a component should be restarted based on health checks and failures"""
        if not component.restart_on_failure:
            return False
        
        if component.restart_count >= component.max_restarts:
            return False
        
        # For services with health checks, restart if failure threshold is reached
        if (component.component_type in [ComponentType.SERVICE, ComponentType.CRITICAL_SERVICE] and 
            component.health_check_url and 
            component.consecutive_failures >= component.failure_threshold):
            return True
        
        # For services that stopped unexpectedly
        if (component.component_type in [ComponentType.SERVICE, ComponentType.CRITICAL_SERVICE] and 
            component.process.poll() is not None and 
            component.status == ComponentStatus.RUNNING):
            return True
        
        return False
    
    def stop_component(self, name: str, graceful: bool = True) -> bool:
        """Stop a system component with graceful shutdown support"""
        if name not in self.components:
            return True
            
        try:
            component = self.components[name]
            process = component.process
            
            if process.poll() is None:  # Process is still running
                component.status = ComponentStatus.STOPPED
                self.logger.info(f"Stopping {name}...")
                print(f"Stopping {name}...")
                
                if graceful:
                    # Try graceful shutdown first
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=component.graceful_shutdown_timeout)
                        self.logger.info(f"{name} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        self.logger.warning(f"Graceful shutdown timeout for {name}, force killing...")
                        print(f"Force killing {name}...")
                        process.kill()
                        process.wait()
                else:
                    # Force kill immediately
                    process.kill()
                    process.wait()
                
                # Update total runtime
                runtime = (datetime.now() - component.start_time).total_seconds()
                component.total_runtime += runtime
                
                self.logger.info(f"{name} stopped (total runtime: {component.total_runtime:.0f}s)")
                print(f"✓ {name} stopped")
            
            # Remove from startup/shutdown order
            if name in self.startup_order:
                self.startup_order.remove(name)
            if name in self.shutdown_order:
                self.shutdown_order.remove(name)
            
            del self.components[name]
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping {name}: {str(e)}")
            print(f"✗ Error stopping {name}: {str(e)}")
            return False
    
    def stop_all(self):
        """Stop all running components"""
        print("\nShutting down system...")
        for name in list(self.components.keys()):
            self.stop_component(name)
        self.running = False
    
    def check_system_dependencies(self) -> bool:
        """Check if required system dependencies are available"""
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
        """Start the FastAPI server with health monitoring"""
        command = [
            sys.executable, "-m", "uvicorn", 
            "src.n8n_scraper.api.main:app",
            "--host", host,
            "--port", str(port)
        ]
        
        if reload:
            command.append("--reload")
        
        health_check_url = f"http://{host if host != '0.0.0.0' else 'localhost'}:{port}/health"
        
        return self.start_component(
            "API Server", 
            command, 
            ComponentType.CRITICAL_SERVICE,  # API Server is critical
            health_check_url=health_check_url,
            graceful_shutdown_timeout=15
        )
    
    # def start_streamlit_app(self, port: int = 8501):
    #     """Start the Streamlit web interface - DEPRECATED"""
    #     # Streamlit has been replaced by Next.js frontend
    #     print("⚠ Streamlit has been replaced by Next.js frontend")
    #     print("  Please use the Next.js frontend at http://localhost:3000")
    #     return False
    
    def start_scraper(self, mode: str = "analyze"):
        """Start the documentation scraper with appropriate component type"""
        if mode == "scrape":
            command = [sys.executable, "src/scripts/run_scraper.py", "--scrape"]
            expected_duration = 1800  # 30 minutes for scraping
            component_type = ComponentType.TASK
        elif mode == "analyze":
            command = [sys.executable, "src/scripts/run_scraper.py", "--analyze"]
            expected_duration = 300   # 5 minutes for analysis
            component_type = ComponentType.TASK
        elif mode == "full":
            command = [sys.executable, "src/scripts/run_scraper.py", "--scrape", "--analyze"]
            expected_duration = 2100  # 35 minutes for full operation
            component_type = ComponentType.TASK
        else:
            self.logger.error(f"Unknown scraper mode: {mode}")
            print(f"✗ Unknown scraper mode: {mode}")
            return False
        
        return self.start_component(
            f"Scraper ({mode})", 
            command, 
            component_type, 
            expected_duration=expected_duration,
            restart_on_failure=False,  # Don't restart completed tasks
            dependencies=["API Server"] if mode in ["scrape", "full"] else []  # Scraping may need API
        )
    
    def start_updater(self):
        """Start the automated updater as a service"""
        command = [sys.executable, "src/n8n_scraper/automation/update_scheduler.py", "--start"]
        return self.start_component(
            "Automated Updater", 
            command, 
            ComponentType.SERVICE,
            dependencies=["API Server"],  # Updater depends on API Server
            graceful_shutdown_timeout=20
        )
    
    def wait_for_services(self):
        """Wait for services to be ready"""
        print("\nWaiting for services to be ready...")
        
        # Wait for API server
        if "API Server" in self.components:
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
        
        if not self.components:
            print("No components running")
            return
        
        # Group components by type
        services = []
        tasks = []
        
        for name, component in self.components.items():
            process = component.process
            runtime = (datetime.now() - component.start_time).total_seconds()
            
            if process.poll() is None:
                status = f"✓ Running (PID: {process.pid}, {runtime:.0f}s)"
            else:
                exit_code = process.returncode
                if component.component_type == ComponentType.TASK and exit_code == 0:
                    status = f"✓ Completed successfully ({runtime:.0f}s)"
                else:
                    status = f"✗ Stopped (exit: {exit_code}, {runtime:.0f}s)"
            
            component_info = {
                'name': name,
                'status': status,
                'type': component.component_type.value,
                'expected_duration': component.expected_duration
            }
            
            if component.component_type == ComponentType.SERVICE:
                services.append(component_info)
            else:
                tasks.append(component_info)
        
        # Display services
        if services:
            print("\nServices (should run continuously):")
            for service in services:
                print(f"  {service['name']:25} {service['status']}")
        
        # Display tasks
        if tasks:
            print("\nTasks (run once and complete):")
            for task in tasks:
                duration_info = f" (expected: {task['expected_duration']}s)" if task['expected_duration'] else ""
                print(f"  {task['name']:25} {task['status']}{duration_info}")
        
        print("\nAccess URLs:")
        if "API Server" in self.components:
            print("  API Server:     http://localhost:8000")
            print("  API Docs:       http://localhost:8000/docs")
        # Streamlit removed - Next.js frontend available at http://localhost:3000
        print("  Next.js Frontend: http://localhost:3000 (start separately)")
        
        print("\nMonitoring Features:")
        print("  • Intelligent monitoring distinguishes between services and tasks")
        print("  • Tasks that complete successfully are not flagged as errors")
        print("  • Services are automatically restarted if they fail unexpectedly")
        print("  • Runtime tracking with expected duration comparisons")
        print("\nPress Ctrl+C to stop all services")
    
    def monitor_processes(self):
        """Enhanced monitoring with health checks and intelligent component handling"""
        self.logger.info("Starting enhanced process monitoring")
        
        while self.running:
            try:
                time.sleep(10)  # Check every 10 seconds
                
                for name, component in list(self.components.items()):
                    process = component.process
                    current_time = datetime.now()
                    
                    # Perform health checks for running services
                    if (process.poll() is None and 
                        component.health_check_url and 
                        component.component_type in [ComponentType.SERVICE, ComponentType.CRITICAL_SERVICE]):
                        
                        # Check if it's time for a health check
                        if (not component.last_health_check or 
                            (current_time - component.last_health_check).total_seconds() >= component.health_check_interval):
                            
                            if not self.perform_health_check(component):
                                self.logger.warning(f"Health check failed for {name} ({component.consecutive_failures}/{component.failure_threshold})")
                                
                                # Check if we should restart due to health check failures
                                if self.should_restart_component(component):
                                    self.logger.warning(f"Restarting {name} due to health check failures")
                                    print(f"\n⚠ Restarting '{name}' due to health check failures ({component.consecutive_failures} consecutive failures)")
                                    self._restart_component(name, component.restart_count + 1)
                                    continue
                    
                    # Handle stopped processes
                    if process.poll() is not None:  # Process has stopped
                        exit_code = process.returncode
                        runtime = (current_time - component.start_time).total_seconds()
                        component.total_runtime += runtime
                        
                        if component.component_type == ComponentType.TASK:
                            # Tasks are expected to complete and exit
                            if exit_code == 0:
                                component.status = ComponentStatus.COMPLETED
                                self.logger.info(f"Task '{name}' completed successfully after {runtime:.0f}s")
                                print(f"\n✓ Task '{name}' completed successfully after {runtime:.0f}s")
                                if component.expected_duration:
                                    if runtime < component.expected_duration * 0.5:
                                        print(f"  Note: Completed faster than expected ({component.expected_duration}s)")
                                    elif runtime > component.expected_duration * 1.5:
                                        print(f"  Note: Took longer than expected ({component.expected_duration}s)")
                            else:
                                component.status = ComponentStatus.FAILED
                                self.logger.error(f"Task '{name}' failed with exit code {exit_code} after {runtime:.0f}s")
                                print(f"\n⚠ Task '{name}' failed with exit code {exit_code} after {runtime:.0f}s")
                                if self.should_restart_component(component):
                                    print(f"  Attempting restart ({component.restart_count + 1}/{component.max_restarts})...")
                                    self._restart_component(name, component.restart_count + 1)
                        
                        elif component.component_type in [ComponentType.SERVICE, ComponentType.CRITICAL_SERVICE]:
                            # Services should keep running
                            component.status = ComponentStatus.FAILED
                            self.logger.error(f"Service '{name}' stopped unexpectedly (exit: {exit_code}, runtime: {runtime:.0f}s)")
                            print(f"\n⚠ Service '{name}' stopped unexpectedly (exit: {exit_code}, runtime: {runtime:.0f}s)")
                            
                            if component.component_type == ComponentType.CRITICAL_SERVICE:
                                self.logger.critical(f"Critical service '{name}' failed - initiating system shutdown")
                                print(f"\n🚨 Critical service '{name}' failed - shutting down system")
                                self.running = False
                                break
                            
                            if self.should_restart_component(component):
                                print(f"  Attempting restart ({component.restart_count + 1}/{component.max_restarts})...")
                                self._restart_component(name, component.restart_count + 1)
                            else:
                                print(f"  Max restarts reached or restart disabled for {name}")
                        
                        elif component.component_type == ComponentType.PERIODIC:
                            # Periodic tasks are expected to exit and will be restarted by scheduler
                            if exit_code == 0:
                                component.status = ComponentStatus.COMPLETED
                                self.logger.info(f"Periodic task '{name}' completed cycle after {runtime:.0f}s")
                                print(f"\n✓ Periodic task '{name}' completed cycle after {runtime:.0f}s")
                            else:
                                component.status = ComponentStatus.FAILED
                                self.logger.warning(f"Periodic task '{name}' failed with exit code {exit_code}")
                                print(f"\n⚠ Periodic task '{name}' failed with exit code {exit_code}")
                        
            except KeyboardInterrupt:
                self.logger.info("Monitoring interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Error in process monitoring: {e}")
                print(f"Error in process monitoring: {e}")
    
    def _restart_component(self, name: str, new_restart_count: int = 0) -> bool:
        """Restart a failed component"""
        if name not in self.components:
            return False
        
        component = self.components[name]
        
        # Store restart information
        original_command = component.original_command
        original_cwd = component.original_cwd
        component_type = component.component_type
        expected_duration = component.expected_duration
        restart_on_failure = component.restart_on_failure
        max_restarts = component.max_restarts
        
        # Stop the current process if it's still running
        if component.process.poll() is None:
            try:
                component.process.terminate()
                component.process.wait(timeout=5)
            except:
                component.process.kill()
        
        # Remove the old component
        del self.components[name]
        
        # Wait a moment before restart
        time.sleep(2)
        
        # Restart with original parameters and updated restart count
        success = self.start_component(
            name=name,
            command=original_command,
            component_type=component_type,
            cwd=original_cwd,
            expected_duration=expected_duration,
            restart_on_failure=restart_on_failure
        )
        
        # Update restart count if successful
        if success and name in self.components:
            self.components[name].restart_count = new_restart_count
            self.components[name].max_restarts = max_restarts
        
        return success
    
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
    if not manager.check_system_dependencies():
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