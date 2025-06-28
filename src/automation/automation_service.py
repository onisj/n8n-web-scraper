#!/usr/bin/env python3
"""
Service wrapper for the automated scraper

This script provides a simple service interface for running the automation
system with proper error handling, logging, and restart capabilities.
"""

import os
import sys
import time
import signal
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

class AutomationService:
    """Service wrapper for automated scraper"""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.restart_count = 0
        self.max_restarts = 5
        self.restart_delay = 60  # seconds
        
        # Setup logging
        log_dir = Path("./logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "automation_service.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start the automation service"""
        self.logger.info("Starting automation service")
        self.running = True
        
        while self.running and self.restart_count < self.max_restarts:
            try:
                self._start_automation_process()
                
                if self.process:
                    # Wait for process to complete
                    return_code = self.process.wait()
                    
                    if return_code == 0:
                        self.logger.info("Automation process completed successfully")
                        self.restart_count = 0  # Reset restart count on success
                    else:
                        self.logger.error(f"Automation process failed with code {return_code}")
                        self.restart_count += 1
                        
                        if self.running and self.restart_count < self.max_restarts:
                            self.logger.info(f"Restarting in {self.restart_delay} seconds (attempt {self.restart_count}/{self.max_restarts})")
                            time.sleep(self.restart_delay)
                
            except Exception as e:
                self.logger.error(f"Error in automation service: {e}")
                self.restart_count += 1
                
                if self.running and self.restart_count < self.max_restarts:
                    self.logger.info(f"Restarting in {self.restart_delay} seconds (attempt {self.restart_count}/{self.max_restarts})")
                    time.sleep(self.restart_delay)
        
        if self.restart_count >= self.max_restarts:
            self.logger.error(f"Maximum restart attempts ({self.max_restarts}) reached. Service stopping.")
        
        self.logger.info("Automation service stopped")
    
    def _start_automation_process(self):
        """Start the automation process"""
        try:
            cmd = [sys.executable, "src/automation/src/automation/automated_scraper.py", "--mode", "schedule"]
            
            self.logger.info(f"Starting automation process: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.logger.info(f"Automation process started with PID {self.process.pid}")
            
        except Exception as e:
            self.logger.error(f"Failed to start automation process: {e}")
            self.process = None
    
    def stop(self):
        """Stop the automation service"""
        self.logger.info("Stopping automation service")
        self.running = False
        
        if self.process:
            try:
                self.logger.info(f"Terminating automation process (PID {self.process.pid})")
                self.process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    self.logger.warning("Process did not terminate gracefully, killing...")
                    self.process.kill()
                    self.process.wait()
                
                self.logger.info("Automation process stopped")
                
            except Exception as e:
                self.logger.error(f"Error stopping automation process: {e}")
    
    def status(self):
        """Get service status"""
        if self.process and self.process.poll() is None:
            return {
                "status": "running",
                "pid": self.process.pid,
                "restart_count": self.restart_count
            }
        else:
            return {
                "status": "stopped",
                "restart_count": self.restart_count
            }

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="n8n Documentation Automation Service")
    parser.add_argument("action", choices=["start", "stop", "status", "restart"],
                       help="Service action to perform")
    
    args = parser.parse_args()
    
    service = AutomationService()
    
    if args.action == "start":
        service.start()
    elif args.action == "stop":
        service.stop()
    elif args.action == "status":
        status = service.status()
        print(f"Service status: {status['status']}")
        if status['status'] == 'running':
            print(f"PID: {status['pid']}")
        print(f"Restart count: {status['restart_count']}")
    elif args.action == "restart":
        service.stop()
        time.sleep(2)
        service.start()

if __name__ == "__main__":
    main()