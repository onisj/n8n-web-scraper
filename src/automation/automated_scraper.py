#!/usr/bin/env python3
"""
Unified Automation Script for n8n Documentation Scraping System

This script combines scraping, database import, and export generation
with configurable scheduling based on environment variables.

Features:
- Automated scraping with configurable intervals
- Database import and export generation
- Comprehensive error handling and notifications
- Health monitoring and data freshness tracking
- Backup management
"""

import os
import sys
import json
import time
import logging
import schedule
import asyncio
import psycopg2
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
    handlers=[
        logging.FileHandler(os.path.join(os.getenv('LOGS_DIRECTORY', './logs'), 'automation.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class AutomationConfig:
    """Configuration for automated scraping system"""
    # Scheduling
    scrape_interval_days: int = int(os.getenv('SCRAPE_INTERVAL_DAYS', '2'))
    scrape_interval_hours: int = int(os.getenv('SCRAPE_INTERVAL_HOURS', '0'))
    scrape_schedule_time: str = os.getenv('SCRAPE_SCHEDULE_TIME', '02:00')
    scrape_enabled: bool = os.getenv('SCRAPE_ENABLED', 'true').lower() == 'true'
    
    # Data Processing
    auto_import_to_database: bool = os.getenv('AUTO_IMPORT_TO_DATABASE', 'true').lower() == 'true'
    auto_export_formats: bool = os.getenv('AUTO_EXPORT_FORMATS', 'true').lower() == 'true'
    auto_backup_enabled: bool = os.getenv('AUTO_BACKUP_ENABLED', 'true').lower() == 'true'
    
    # Database
    database_url: str = os.getenv('DATABASE_URL', '')
    database_host: str = os.getenv('DATABASE_HOST', 'localhost')
    database_port: int = int(os.getenv('DATABASE_PORT', '5432'))
    database_name: str = os.getenv('DATABASE_NAME', 'n8n_scraper')
    database_user: str = os.getenv('DATABASE_USER', '')
    database_password: str = os.getenv('DATABASE_PASSWORD', '')
    
    # Directories
    data_directory: str = os.getenv('DATA_DIRECTORY', './data')
    scraped_docs_directory: str = os.getenv('SCRAPED_DOCS_DIRECTORY', './data/scraped_docs')
    backups_directory: str = os.getenv('BACKUPS_DIRECTORY', './backups')
    exports_directory: str = os.getenv('EXPORTS_DIRECTORY', './data/exports')
    logs_directory: str = os.getenv('LOGS_DIRECTORY', './logs')
    
    # Scraping
    scraper_max_pages: int = int(os.getenv('SCRAPER_MAX_PAGES', '500'))
    scraper_delay: float = float(os.getenv('SCRAPER_DELAY_BETWEEN_REQUESTS', '1.0'))
    scraper_max_retries: int = int(os.getenv('SCRAPER_MAX_RETRIES', '3'))
    
    # Notifications
    notifications_enabled: bool = os.getenv('NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
    webhook_url: str = os.getenv('WEBHOOK_URL', '')
    slack_webhook_url: str = os.getenv('SLACK_WEBHOOK_URL', '')
    discord_webhook_url: str = os.getenv('DISCORD_WEBHOOK_URL', '')
    
    # Backup
    backup_retention_days: int = int(os.getenv('BACKUP_RETENTION_DAYS', '7'))

class DatabaseManager:
    """Manages database operations and health checks"""
    
    def __init__(self, config: AutomationConfig):
        self.config = config
        self.connection_string = (
            config.database_url or 
            f"postgresql://{config.database_user}:{config.database_password}@"
            f"{config.database_host}:{config.database_port}/{config.database_name}"
        )
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = psycopg2.connect(self.connection_string)
            conn.close()
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            stats = {}
            
            # Get total documents
            cursor.execute("SELECT COUNT(*) FROM documentation_pages")
            stats['total_documents'] = cursor.fetchone()[0]
            
            # Get latest scrape time
            cursor.execute("SELECT MAX(scraped_at) FROM documentation_pages")
            latest_scrape = cursor.fetchone()[0]
            stats['latest_scrape'] = latest_scrape.isoformat() if latest_scrape else None
            
            # Get category counts
            cursor.execute("""
                SELECT category, COUNT(*) 
                FROM documentation_pages 
                GROUP BY category 
                ORDER BY COUNT(*) DESC
            """)
            stats['category_counts'] = dict(cursor.fetchall())
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

class NotificationManager:
    """Manages notifications for automation events"""
    
    def __init__(self, config: AutomationConfig):
        self.config = config
    
    def send_notification(self, title: str, message: str, level: str = "info") -> None:
        """Send notification via configured channels"""
        if not self.config.notifications_enabled:
            return
        
        notification_data = {
            "title": title,
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to Slack
        if self.config.slack_webhook_url:
            self._send_slack_notification(notification_data)
        
        # Send to Discord
        if self.config.discord_webhook_url:
            self._send_discord_notification(notification_data)
        
        # Send to generic webhook
        if self.config.webhook_url:
            self._send_webhook_notification(notification_data)
    
    def _send_slack_notification(self, data: Dict[str, Any]) -> None:
        """Send notification to Slack"""
        try:
            color = {"info": "good", "warning": "warning", "error": "danger"}.get(data["level"], "good")
            payload = {
                "attachments": [{
                    "color": color,
                    "title": data["title"],
                    "text": data["message"],
                    "ts": int(datetime.fromisoformat(data["timestamp"]).timestamp())
                }]
            }
            requests.post(self.config.slack_webhook_url, json=payload, timeout=10)
            logger.debug("Slack notification sent")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    def _send_discord_notification(self, data: Dict[str, Any]) -> None:
        """Send notification to Discord"""
        try:
            color = {"info": 0x00ff00, "warning": 0xffff00, "error": 0xff0000}.get(data["level"], 0x00ff00)
            payload = {
                "embeds": [{
                    "title": data["title"],
                    "description": data["message"],
                    "color": color,
                    "timestamp": data["timestamp"]
                }]
            }
            requests.post(self.config.discord_webhook_url, json=payload, timeout=10)
            logger.debug("Discord notification sent")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
    
    def _send_webhook_notification(self, data: Dict[str, Any]) -> None:
        """Send notification to generic webhook"""
        try:
            requests.post(self.config.webhook_url, json=data, timeout=10)
            logger.debug("Webhook notification sent")
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")

class AutomatedScraper:
    """Main automation class that orchestrates scraping, import, and export"""
    
    def __init__(self):
        self.config = AutomationConfig()
        self.db_manager = DatabaseManager(self.config)
        self.notification_manager = NotificationManager(self.config)
        self.last_run_file = Path(self.config.data_directory) / "logs/last_automation_run.json"
        
        # Ensure directories exist
        self._create_directories()
        
        logger.info("Automated scraper initialized")
        logger.info(f"Configuration: {asdict(self.config)}")
    
    def _create_directories(self) -> None:
        """Create necessary directories"""
        directories = [
            self.config.data_directory,
            self.config.scraped_docs_directory,
            self.config.backups_directory,
            self.config.exports_directory,
            self.config.logs_directory
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def should_run_scraping(self) -> bool:
        """Check if scraping should run based on schedule"""
        if not self.config.scrape_enabled:
            return False
        
        if not self.last_run_file.exists():
            return True
        
        try:
            with open(self.last_run_file, 'r') as f:
                last_run_data = json.load(f)
            
            last_run = datetime.fromisoformat(last_run_data['timestamp'])
            interval = timedelta(
                days=self.config.scrape_interval_days,
                hours=self.config.scrape_interval_hours
            )
            
            return datetime.now() >= last_run + interval
            
        except Exception as e:
            logger.error(f"Error checking last run: {e}")
            return True
    
    def update_last_run(self, success: bool, stats: Dict[str, Any] = None) -> None:
        """Update last run information"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'success': success,
                'stats': stats or {}
            }
            
            with open(self.last_run_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error updating last run: {e}")
    
    def run_scraping(self) -> Dict[str, Any]:
        """Execute the scraping process"""
        logger.info("Starting scraping process")
        
        try:
            # Run the scraper
            cmd = [
                sys.executable, "src/scripts/run_scraper.py",
                "--max-pages", str(self.config.scraper_max_pages),
                "--delay", str(self.config.scraper_delay)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logger.info("Scraping completed successfully")
                return {"success": True, "output": result.stdout}
            else:
                logger.error(f"Scraping failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            logger.error("Scraping process timed out")
            return {"success": False, "error": "Process timed out"}
        except Exception as e:
            logger.error(f"Error running scraping: {e}")
            return {"success": False, "error": str(e)}
    
    def import_to_database(self) -> Dict[str, Any]:
        """Import scraped data to database"""
        if not self.config.auto_import_to_database:
            return {"success": True, "message": "Database import disabled"}
        
        logger.info("Starting database import")
        
        try:
            # Check if import script exists
            import_script = "src/scripts/import_docs_data.py"
            if not Path(import_script).exists():
                logger.error(f"Import script {import_script} not found")
                return {"success": False, "error": "Import script not found"}
            
            # Run the import script
            result = subprocess.run(
                [sys.executable, import_script],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info("Database import completed successfully")
                return {"success": True, "output": result.stdout}
            else:
                logger.error(f"Database import failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            logger.error("Database import process timed out")
            return {"success": False, "error": "Process timed out"}
        except Exception as e:
            logger.error(f"Error running database import: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_exports(self) -> Dict[str, Any]:
        """Generate export files"""
        if not self.config.auto_export_formats:
            return {"success": True, "message": "Export generation disabled"}
        
        logger.info("Starting export generation")
        
        try:
            # Generate CSV export
            export_file = Path(self.config.exports_directory) / f"n8n_docs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # Ensure export directory exists
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Connect to database
            conn = psycopg2.connect(self.db_manager.connection_string)
            cursor = conn.cursor()
            
            try:
                # Use copy_expert to export data to CSV file
                with open(export_file, 'w', encoding='utf-8') as f:
                    cursor.copy_expert(
                        "COPY (SELECT url, title, category, subcategory, content_length, word_count, scraped_at FROM documentation_pages ORDER BY category, subcategory, title) TO STDOUT WITH CSV HEADER",
                        f
                    )
                
                logger.info(f"Export generated: {export_file}")
                return {"success": True, "export_file": str(export_file)}
                
            finally:
                cursor.close()
                conn.close()
            
        except Exception as e:
            logger.error(f"Error generating exports: {e}")
            return {"success": False, "error": str(e)} 
    
    def create_backup(self) -> Dict[str, Any]:
        """Create backup of current data"""
        if not self.config.auto_backup_enabled:
            return {"success": True, "message": "Backup disabled"}
        
        logger.info("Starting backup creation")
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = Path(self.config.backups_directory) / f"n8n_scraper_backup_{timestamp}.sql"
            
            # Create database backup using pg_dump
            cmd = [
                "pg_dump",
                "--host", self.config.database_host,
                "--port", str(self.config.database_port),
                "--username", self.config.database_user,
                "--dbname", self.config.database_name,
                "--file", str(backup_file),
                "--verbose"
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.config.database_password
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Backup created: {backup_file}")
                self._cleanup_old_backups()
                return {"success": True, "backup_file": str(backup_file)}
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            logger.error("Backup process timed out")
            return {"success": False, "error": "Process timed out"}
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return {"success": False, "error": str(e)}
    
    def _cleanup_old_backups(self) -> None:
        """Remove old backup files"""
        try:
            backup_dir = Path(self.config.backups_directory)
            cutoff_date = datetime.now() - timedelta(days=self.config.backup_retention_days)
            
            for backup_file in backup_dir.glob("n8n_scraper_backup_*.sql"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    logger.info(f"Removed old backup: {backup_file}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
    
    def run_full_automation(self) -> Dict[str, Any]:
        """Run the complete automation process"""
        logger.info("Starting full automation process")
        
        start_time = datetime.now()
        results = {
            "start_time": start_time.isoformat(),
            "steps": {},
            "overall_success": True
        }
        
        try:
            # Check database connection
            if not self.db_manager.test_connection():
                raise Exception("Database connection failed")
            
            # Step 1: Run scraping
            scraping_result = self.run_scraping()
            results["steps"]["scraping"] = scraping_result
            
            if not scraping_result["success"]:
                results["overall_success"] = False
                self.notification_manager.send_notification(
                    "Scraping Failed",
                    f"Scraping process failed: {scraping_result.get('error', 'Unknown error')}",
                    "error"
                )
                return results
            
            # Step 2: Import to database
            import_result = self.import_to_database()
            results["steps"]["database_import"] = import_result
            
            if not import_result["success"]:
                results["overall_success"] = False
                self.notification_manager.send_notification(
                    "Database Import Failed",
                    f"Database import failed: {import_result.get('error', 'Unknown error')}",
                    "error"
                )
            
            # Step 3: Generate exports
            export_result = self.generate_exports()
            results["steps"]["export_generation"] = export_result
            
            if not export_result["success"]:
                results["overall_success"] = False
                self.notification_manager.send_notification(
                    "Export Generation Failed",
                    f"Export generation failed: {export_result.get('error', 'Unknown error')}",
                    "warning"
                )
            
            # Step 4: Create backup
            backup_result = self.create_backup()
            results["steps"]["backup"] = backup_result
            
            if not backup_result["success"]:
                self.notification_manager.send_notification(
                    "Backup Failed",
                    f"Backup creation failed: {backup_result.get('error', 'Unknown error')}",
                    "warning"
                )
            
            # Get final database stats
            db_stats = self.db_manager.get_stats()
            results["database_stats"] = db_stats
            
            # Calculate duration
            end_time = datetime.now()
            results["end_time"] = end_time.isoformat()
            results["duration_seconds"] = (end_time - start_time).total_seconds()
            
            # Update last run
            self.update_last_run(results["overall_success"], results)
            
            # Send success notification
            if results["overall_success"]:
                self.notification_manager.send_notification(
                    "Automation Completed Successfully",
                    f"Full automation completed in {results['duration_seconds']:.1f} seconds. "
                    f"Total documents: {db_stats.get('total_documents', 'Unknown')}",
                    "info"
                )
            
            logger.info(f"Full automation completed. Success: {results['overall_success']}")
            return results
            
        except Exception as e:
            logger.error(f"Error in full automation: {e}")
            results["overall_success"] = False
            results["error"] = str(e)
            
            self.notification_manager.send_notification(
                "Automation Failed",
                f"Full automation failed: {str(e)}",
                "error"
            )
            
            return results
    
    def run_health_check(self) -> Dict[str, Any]:
        """Run health check on the system"""
        logger.info("Running health check")
        
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_healthy": True,
            "checks": {}
        }
        
        # Database connection check
        db_healthy = self.db_manager.test_connection()
        health_status["checks"]["database_connection"] = {
            "healthy": db_healthy,
            "message": "Database connection successful" if db_healthy else "Database connection failed"
        }
        
        if not db_healthy:
            health_status["overall_healthy"] = False
        
        # Directory checks
        directories = [
            self.config.data_directory,
            self.config.scraped_docs_directory,
            self.config.backups_directory,
            self.config.exports_directory,
            self.config.logs_directory
        ]
        
        for directory in directories:
            dir_exists = Path(directory).exists()
            health_status["checks"][f"directory_{Path(directory).name}"] = {
                "healthy": dir_exists,
                "message": f"Directory {directory} exists" if dir_exists else f"Directory {directory} missing"
            }
            
            if not dir_exists:
                health_status["overall_healthy"] = False
        
        # Data freshness check
        try:
            db_stats = self.db_manager.get_stats()
            latest_scrape = db_stats.get('latest_scrape')
            
            if latest_scrape:
                latest_scrape_dt = datetime.fromisoformat(latest_scrape.replace('Z', '+00:00'))
                age_hours = (datetime.now() - latest_scrape_dt.replace(tzinfo=None)).total_seconds() / 3600
                
                # Consider data stale if older than 3 days
                data_fresh = age_hours < 72
                health_status["checks"]["data_freshness"] = {
                    "healthy": data_fresh,
                    "message": f"Data is {age_hours:.1f} hours old",
                    "latest_scrape": latest_scrape
                }
                
                if not data_fresh:
                    health_status["overall_healthy"] = False
            else:
                health_status["checks"]["data_freshness"] = {
                    "healthy": False,
                    "message": "No data found in database"
                }
                health_status["overall_healthy"] = False
                
        except Exception as e:
            health_status["checks"]["data_freshness"] = {
                "healthy": False,
                "message": f"Error checking data freshness: {e}"
            }
            health_status["overall_healthy"] = False
        
        logger.info(f"Health check completed. Overall healthy: {health_status['overall_healthy']}")
        return health_status
    
    def start_scheduler(self) -> None:
        """Start the scheduled automation"""
        if not self.config.scrape_enabled:
            logger.info("Scraping is disabled, scheduler not started")
            return
        
        logger.info(f"Starting scheduler with time: {self.config.scrape_schedule_time}")
        
        # Schedule the automation
        schedule.every(self.config.scrape_interval_days).days.at(self.config.scrape_schedule_time).do(
            self._scheduled_run
        )
        
        # Schedule health checks every 6 hours
        schedule.every(6).hours.do(self._scheduled_health_check)
        
        logger.info("Scheduler started. Waiting for scheduled runs...")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            self.notification_manager.send_notification(
                "Scheduler Error",
                f"Scheduler encountered an error: {str(e)}",
                "error"
            )
    
    def _scheduled_run(self) -> None:
        """Wrapper for scheduled automation runs"""
        logger.info("Starting scheduled automation run")
        
        if self.should_run_scraping():
            self.run_full_automation()
        else:
            logger.info("Skipping scheduled run - not yet time")
    
    def _scheduled_health_check(self) -> None:
        """Wrapper for scheduled health checks"""
        health_status = self.run_health_check()
        
        if not health_status["overall_healthy"]:
            failed_checks = []
            for check_name, check_result in health_status["checks"].items():
                if not check_result["healthy"]:
                    failed_checks.append(f"{check_name}: {check_result['message']}")
            
            self.notification_manager.send_notification(
                "Health Check Failed",
                f"System health check failed:\n" + "\n".join(failed_checks),
                "warning"
            )

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="n8n Documentation Automation System")
    parser.add_argument("--mode", choices=["run", "schedule", "health"], default="run",
                       help="Mode to run: 'run' for one-time execution, 'schedule' for continuous scheduling, 'health' for health check")
    parser.add_argument("--force", action="store_true",
                       help="Force run even if not scheduled")
    
    args = parser.parse_args()
    
    scraper = AutomatedScraper()
    
    if args.mode == "health":
        health_status = scraper.run_health_check()
        print(json.dumps(health_status, indent=2))
        sys.exit(0 if health_status["overall_healthy"] else 1)
    
    elif args.mode == "schedule":
        scraper.start_scheduler()
    
    elif args.mode == "run":
        if args.force or scraper.should_run_scraping():
            results = scraper.run_full_automation()
            print(json.dumps(results, indent=2))
            sys.exit(0 if results["overall_success"] else 1)
        else:
            logger.info("Skipping run - not yet time. Use --force to override.")
            print(json.dumps({"message": "Not yet time to run", "success": True}, indent=2))

if __name__ == "__main__":
    main()