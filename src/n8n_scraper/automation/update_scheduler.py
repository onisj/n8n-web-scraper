#!/usr/bin/env python3
"""
Automated N8n Knowledge Base Updater

This module handles automated updates of the n8n knowledge base by scheduling
regular scraping operations and processing the collected data.
"""

import schedule
import time
import logging
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess
import threading
from dataclasses import dataclass, asdict

# Import our existing components
from n8n_scraper.automation.knowledge_updater import N8nDocsScraper
from n8n_scraper.automation.change_detector import N8nDataAnalyzer
from n8n_scraper.optimization.agent_manager import get_knowledge_processor, get_expert_agent

@dataclass
class UpdateConfig:
    """Configuration for automated updates"""
    schedule_time: str = "02:00"  # Daily at 2 AM
    max_pages: int = 500  # Maximum pages to scrape
    delay_between_requests: float = 1.0  # Delay between requests
    backup_retention_days: int = 7  # Keep backups for 7 days
    enable_notifications: bool = True
    webhook_url: Optional[str] = None  # For notifications
    data_directory: str = "/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs"
    backup_directory: str = "backups"
    logs_directory: str = "logs"

class AutomatedUpdater:
    """
    Manages automated updates of the n8n knowledge base.
    
    Features:
    - Scheduled scraping operations
    - Data backup and versioning
    - Change detection and notifications
    - Health monitoring
    - Integration with AI agent
    """
    
    def __init__(self, config: UpdateConfig = None):
        """
        Initialize the automated updater.
        
        Args:
            config: Configuration for the updater
        """
        self.config = config or UpdateConfig()
        self.logger = self._setup_logging()
        self.is_running = False
        self.last_update = None
        self.update_stats = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "last_error": None
        }
        
        # Initialize components
        self.scraper = N8nDocsScraper()
        self.analyzer = N8nDataAnalyzer()
        self.knowledge_processor = get_knowledge_processor()
        self.ai_agent = get_expert_agent()
        
        # Create necessary directories
        self._create_directories()
        
        # Load existing stats
        self._load_stats()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the updater"""
        logger = logging.getLogger('automated_updater')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # Create logs directory if it doesn't exist
            os.makedirs(self.config.logs_directory, exist_ok=True)
            
            # File handler
            log_file = os.path.join(self.config.logs_directory, 'automated_updater.log')
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def _create_directories(self):
        """Create necessary directories"""
        directories = [
            self.config.data_directory,
            self.config.backup_directory,
            self.config.logs_directory
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            self.logger.info(f"Ensured directory exists: {directory}")
    
    def _load_stats(self):
        """Load existing update statistics"""
        stats_file = os.path.join(self.config.logs_directory, 'update_stats.json')
        
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r') as f:
                    self.update_stats.update(json.load(f))
                self.logger.info("Loaded existing update statistics")
            except Exception as e:
                self.logger.error(f"Error loading stats: {e}")
    
    def _save_stats(self):
        """Save update statistics"""
        stats_file = os.path.join(self.config.logs_directory, 'update_stats.json')
        
        try:
            with open(stats_file, 'w') as f:
                json.dump(self.update_stats, f, indent=2, default=str)
            self.logger.info("Saved update statistics")
        except Exception as e:
            self.logger.error(f"Error saving stats: {e}")
    
    def _create_backup(self) -> str:
        """Create a backup of current data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"n8n_docs_backup_{timestamp}"
        backup_path = os.path.join(self.config.backup_directory, backup_name)
        
        try:
            # Create backup directory
            os.makedirs(backup_path, exist_ok=True)
            
            # Copy data files
            data_path = Path(self.config.data_directory)
            if data_path.exists():
                import shutil
                shutil.copytree(
                    data_path, 
                    os.path.join(backup_path, 'data'),
                    dirs_exist_ok=True
                )
            
            # Save metadata
            metadata = {
                "timestamp": timestamp,
                "backup_date": datetime.now().isoformat(),
                "data_files_count": len(list(data_path.glob('*.json'))) if data_path.exists() else 0,
                "config": asdict(self.config)
            }
            
            with open(os.path.join(backup_path, 'metadata.json'), 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Created backup: {backup_name}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            return None
    
    def _cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        try:
            backup_path = Path(self.config.backup_directory)
            if not backup_path.exists():
                return
            
            cutoff_date = datetime.now() - timedelta(days=self.config.backup_retention_days)
            
            for backup_dir in backup_path.iterdir():
                if backup_dir.is_dir() and backup_dir.name.startswith('n8n_docs_backup_'):
                    # Extract timestamp from directory name
                    try:
                        timestamp_str = backup_dir.name.replace('n8n_docs_backup_', '')
                        backup_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                        
                        if backup_date < cutoff_date:
                            import shutil
                            shutil.rmtree(backup_dir)
                            self.logger.info(f"Removed old backup: {backup_dir.name}")
                    except ValueError:
                        # Skip directories with invalid timestamp format
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error cleaning up old backups: {e}")
    
    def _detect_changes(self, old_data_path: str, new_data_path: str) -> Dict[str, Any]:
        """Detect changes between old and new data"""
        changes = {
            "new_files": [],
            "modified_files": [],
            "deleted_files": [],
            "total_changes": 0
        }
        
        try:
            old_path = Path(old_data_path)
            new_path = Path(new_data_path)
            
            if not old_path.exists():
                # First run, all files are new
                if new_path.exists():
                    changes["new_files"] = [f.name for f in new_path.glob('*.json')]
                return changes
            
            old_files = {f.name: f.stat().st_mtime for f in old_path.glob('*.json')}
            new_files = {f.name: f.stat().st_mtime for f in new_path.glob('*.json') if new_path.exists()}
            
            # Detect new files
            changes["new_files"] = [f for f in new_files if f not in old_files]
            
            # Detect deleted files
            changes["deleted_files"] = [f for f in old_files if f not in new_files]
            
            # Detect modified files (simplified - based on modification time)
            for filename in new_files:
                if filename in old_files and new_files[filename] > old_files[filename]:
                    changes["modified_files"].append(filename)
            
            changes["total_changes"] = (
                len(changes["new_files"]) + 
                len(changes["modified_files"]) + 
                len(changes["deleted_files"])
            )
            
        except Exception as e:
            self.logger.error(f"Error detecting changes: {e}")
        
        return changes
    
    def _send_notification(self, message: str, is_error: bool = False):
        """Send notification about update status"""
        if not self.config.enable_notifications:
            return
        
        try:
            # Log the notification
            if is_error:
                self.logger.error(f"NOTIFICATION: {message}")
            else:
                self.logger.info(f"NOTIFICATION: {message}")
            
            # Send webhook notification if configured
            if self.config.webhook_url:
                import requests
                payload = {
                    "text": f"N8n Knowledge Base Update: {message}",
                    "timestamp": datetime.now().isoformat(),
                    "is_error": is_error
                }
                
                response = requests.post(
                    self.config.webhook_url,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.logger.info("Notification sent successfully")
                else:
                    self.logger.warning(f"Notification failed: {response.status_code}")
                    
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
    
    def perform_update(self) -> bool:
        """
        Perform a complete update cycle.
        
        Returns:
            bool: True if update was successful, False otherwise
        """
        update_start_time = datetime.now()
        self.logger.info("Starting automated update cycle")
        
        try:
            # Update statistics
            self.update_stats["total_updates"] += 1
            
            # Create backup before update
            backup_path = self._create_backup()
            if not backup_path:
                raise Exception("Failed to create backup")
            
            # Store old data path for change detection
            old_data_path = os.path.join(backup_path, 'data')
            
            # Perform scraping
            self.logger.info("Starting documentation scraping")
            scrape_result = self.scraper.run(
                max_pages=self.config.max_pages,
                delay=self.config.delay_between_requests
            )
            
            if not scrape_result:
                raise Exception("Scraping failed")
            
            # Analyze the scraped data
            self.logger.info("Analyzing scraped data")
            analysis_result = self.analyzer.analyze_all_data()
            
            # Process knowledge for AI agent
            self.logger.info("Processing knowledge for AI agent")
            knowledge = self.knowledge_processor.process_directory(self.config.data_directory)
            
            # Reload AI agent with new data
            self.ai_agent._load_knowledge_base()
            
            # Detect changes
            changes = self._detect_changes(old_data_path, self.config.data_directory)
            
            # Update statistics
            self.update_stats["successful_updates"] += 1
            self.last_update = update_start_time
            
            # Clean up old backups
            self._cleanup_old_backups()
            
            # Save statistics
            self._save_stats()
            
            # Send success notification
            update_duration = datetime.now() - update_start_time
            message = (
                f"Update completed successfully in {update_duration.total_seconds():.1f}s. "
                f"Changes: {changes['total_changes']} "
                f"(New: {len(changes['new_files'])}, "
                f"Modified: {len(changes['modified_files'])}, "
                f"Deleted: {len(changes['deleted_files'])})"
            )
            self._send_notification(message)
            
            self.logger.info(f"Update cycle completed successfully: {message}")
            return True
            
        except Exception as e:
            # Update error statistics
            self.update_stats["failed_updates"] += 1
            self.update_stats["last_error"] = str(e)
            
            # Save statistics
            self._save_stats()
            
            # Send error notification
            error_message = f"Update failed: {str(e)}"
            self._send_notification(error_message, is_error=True)
            
            self.logger.error(f"Update cycle failed: {e}")
            return False
    
    def start_scheduler(self):
        """Start the automated scheduler"""
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.logger.info(f"Starting scheduler with daily updates at {self.config.schedule_time}")
        
        # Schedule daily updates
        schedule.every().day.at(self.config.schedule_time).do(self.perform_update)
        
        # Schedule weekly cleanup
        schedule.every().sunday.at("03:00").do(self._cleanup_old_backups)
        
        self.is_running = True
        
        # Send startup notification
        self._send_notification(f"Automated updater started. Next update scheduled for {self.config.schedule_time}")
        
        # Run scheduler in a separate thread
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        self.logger.info("Scheduler started successfully")
    
    def stop_scheduler(self):
        """Stop the automated scheduler"""
        if not self.is_running:
            self.logger.warning("Scheduler is not running")
            return
        
        self.is_running = False
        schedule.clear()
        
        self._send_notification("Automated updater stopped")
        self.logger.info("Scheduler stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the updater"""
        return {
            "is_running": self.is_running,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "next_update": self.config.schedule_time,
            "statistics": self.update_stats,
            "config": asdict(self.config)
        }
    
    def force_update(self) -> bool:
        """Force an immediate update"""
        self.logger.info("Forcing immediate update")
        return self.perform_update()

# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='N8n Knowledge Base Automated Updater')
    parser.add_argument('--start', action='store_true', help='Start the scheduler')
    parser.add_argument('--stop', action='store_true', help='Stop the scheduler')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--update', action='store_true', help='Force immediate update')
    parser.add_argument('--schedule-time', default='02:00', help='Daily update time (HH:MM)')
    parser.add_argument('--max-pages', type=int, default=500, help='Maximum pages to scrape')
    parser.add_argument('--webhook-url', help='Webhook URL for notifications')
    
    args = parser.parse_args()
    
    # Create configuration
    config = UpdateConfig(
        schedule_time=args.schedule_time,
        max_pages=args.max_pages,
        webhook_url=args.webhook_url
    )
    
    # Initialize updater
    updater = AutomatedUpdater(config)
    
    if args.start:
        updater.start_scheduler()
        print(f"Scheduler started. Daily updates at {config.schedule_time}")
        print("Press Ctrl+C to stop")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            updater.stop_scheduler()
            print("\nScheduler stopped")
    
    elif args.stop:
        updater.stop_scheduler()
        print("Scheduler stopped")
    
    elif args.status:
        status = updater.get_status()
        print("=== Automated Updater Status ===")
        for key, value in status.items():
            print(f"{key}: {value}")
    
    elif args.update:
        print("Starting immediate update...")
        success = updater.force_update()
        if success:
            print("Update completed successfully")
        else:
            print("Update failed")
    
    else:
        parser.print_help()