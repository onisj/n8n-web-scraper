#!/usr/bin/env python3
"""
Monitoring Dashboard for n8n Documentation Automation System

This script provides a comprehensive monitoring interface for tracking
automation health, data freshness, system performance, and historical metrics.
"""

import os
import sys
import json
import time
import psutil
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv()

@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    disk_free_gb: float
    load_average: List[float]
    uptime_hours: float
    timestamp: str

@dataclass
class DatabaseMetrics:
    """Database performance and content metrics"""
    total_documents: int
    latest_scrape: Optional[str]
    data_age_hours: Optional[float]
    category_counts: Dict[str, int]
    avg_content_length: float
    total_content_size_mb: float
    database_size_mb: float
    connection_count: int
    timestamp: str

@dataclass
class AutomationMetrics:
    """Automation system metrics"""
    last_run_time: Optional[str]
    last_run_success: bool
    last_run_duration: Optional[float]
    total_runs: int
    success_rate: float
    avg_duration: float
    next_scheduled_run: Optional[str]
    automation_enabled: bool
    timestamp: str

class MonitoringDashboard:
    """Comprehensive monitoring dashboard for automation system"""
    
    def __init__(self):
        self.db_connection_string = self._get_db_connection_string()
        self.data_dir = Path(os.getenv('DATA_DIRECTORY', '/Users/user/Projects/n8n-projects/n8n-web-scrapper/data'))
        self.logs_dir = Path(os.getenv('LOGS_DIRECTORY', '/Users/user/Projects/n8n-projects/n8n-web-scrapper/logs'))
        self.last_run_file = self.data_dir / "last_automation_run.json"
        
    def _get_db_connection_string(self) -> str:
        """Get database connection string from environment"""
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url
        
        return (
            f"postgresql://{os.getenv('DATABASE_USER')}:{os.getenv('DATABASE_PASSWORD')}@"
            f"{os.getenv('DATABASE_HOST', 'localhost')}:{os.getenv('DATABASE_PORT', '5432')}/"
            f"{os.getenv('DATABASE_NAME', 'n8n_scraper')}"
        )
    
    def get_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024**3)
            
            # Load average (Unix-like systems)
            try:
                load_avg = list(os.getloadavg())
            except (OSError, AttributeError):
                load_avg = [0.0, 0.0, 0.0]
            
            # System uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = uptime_seconds / 3600
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                load_average=load_avg,
                uptime_hours=uptime_hours,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            print(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                load_average=[0.0, 0.0, 0.0],
                uptime_hours=0.0,
                timestamp=datetime.now().isoformat()
            )
    
    def get_database_metrics(self) -> DatabaseMetrics:
        """Collect database metrics"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            cursor = conn.cursor()
            
            # Total documents
            cursor.execute("SELECT COUNT(*) FROM documentation_pages")
            total_documents = cursor.fetchone()[0]
            
            # Latest scrape time
            cursor.execute("SELECT MAX(scraped_at) FROM documentation_pages")
            latest_scrape_result = cursor.fetchone()[0]
            latest_scrape = latest_scrape_result.isoformat() if latest_scrape_result else None
            
            # Data age
            data_age_hours = None
            if latest_scrape_result:
                age_delta = datetime.now() - latest_scrape_result.replace(tzinfo=None)
                data_age_hours = age_delta.total_seconds() / 3600
            
            # Category counts
            cursor.execute("""
                SELECT category, COUNT(*) 
                FROM documentation_pages 
                GROUP BY category 
                ORDER BY COUNT(*) DESC
            """)
            category_counts = dict(cursor.fetchall())
            
            # Content statistics
            cursor.execute("""
                SELECT 
                    AVG(content_length) as avg_length,
                    SUM(content_length) / (1024.0 * 1024.0) as total_size_mb
                FROM documentation_pages
            """)
            content_stats = cursor.fetchone()
            avg_content_length = float(content_stats[0] or 0)
            total_content_size_mb = float(content_stats[1] or 0)
            
            # Database size
            cursor.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)
            db_size_str = cursor.fetchone()[0]
            
            # Extract numeric value from size string (e.g., "15 MB" -> 15.0)
            try:
                db_size_parts = db_size_str.split()
                db_size_value = float(db_size_parts[0])
                db_size_unit = db_size_parts[1].upper()
                
                if db_size_unit == 'GB':
                    database_size_mb = db_size_value * 1024
                elif db_size_unit == 'KB':
                    database_size_mb = db_size_value / 1024
                else:  # MB
                    database_size_mb = db_size_value
            except (IndexError, ValueError):
                database_size_mb = 0.0
            
            # Active connections
            cursor.execute("""
                SELECT COUNT(*) 
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """)
            connection_count = cursor.fetchone()[0]
            
            conn.close()
            
            return DatabaseMetrics(
                total_documents=total_documents,
                latest_scrape=latest_scrape,
                data_age_hours=data_age_hours,
                category_counts=category_counts,
                avg_content_length=avg_content_length,
                total_content_size_mb=total_content_size_mb,
                database_size_mb=database_size_mb,
                connection_count=connection_count,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            print(f"Error collecting database metrics: {e}")
            return DatabaseMetrics(
                total_documents=0,
                latest_scrape=None,
                data_age_hours=None,
                category_counts={},
                avg_content_length=0.0,
                total_content_size_mb=0.0,
                database_size_mb=0.0,
                connection_count=0,
                timestamp=datetime.now().isoformat()
            )
    
    def get_automation_metrics(self) -> AutomationMetrics:
        """Collect automation system metrics"""
        try:
            # Read last run information
            last_run_time = None
            last_run_success = False
            last_run_duration = None
            
            if self.last_run_file.exists():
                with open(self.last_run_file, 'r') as f:
                    last_run_data = json.load(f)
                
                last_run_time = last_run_data.get('timestamp')
                last_run_success = last_run_data.get('success', False)
                
                if 'stats' in last_run_data and 'duration_seconds' in last_run_data['stats']:
                    last_run_duration = last_run_data['stats']['duration_seconds']
            
            # Calculate automation statistics from log files
            total_runs = 0
            successful_runs = 0
            total_duration = 0.0
            
            # Parse automation logs to get historical data
            automation_log = self.logs_dir / "automation.log"
            if automation_log.exists():
                try:
                    with open(automation_log, 'r') as f:
                        for line in f:
                            if "Full automation completed" in line:
                                total_runs += 1
                                if "Success: True" in line:
                                    successful_runs += 1
                except Exception:
                    pass  # Continue if log parsing fails
            
            # Calculate success rate and average duration
            success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0.0
            avg_duration = total_duration / total_runs if total_runs > 0 else 0.0
            
            # Calculate next scheduled run
            next_scheduled_run = None
            automation_enabled = os.getenv('SCRAPE_ENABLED', 'true').lower() == 'true'
            
            if automation_enabled and last_run_time:
                try:
                    last_run_dt = datetime.fromisoformat(last_run_time)
                    interval_days = int(os.getenv('SCRAPE_INTERVAL_DAYS', '2'))
                    interval_hours = int(os.getenv('SCRAPE_INTERVAL_HOURS', '0'))
                    
                    next_run_dt = last_run_dt + timedelta(days=interval_days, hours=interval_hours)
                    next_scheduled_run = next_run_dt.isoformat()
                except Exception:
                    pass
            
            return AutomationMetrics(
                last_run_time=last_run_time,
                last_run_success=last_run_success,
                last_run_duration=last_run_duration,
                total_runs=total_runs,
                success_rate=success_rate,
                avg_duration=avg_duration,
                next_scheduled_run=next_scheduled_run,
                automation_enabled=automation_enabled,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            print(f"Error collecting automation metrics: {e}")
            return AutomationMetrics(
                last_run_time=None,
                last_run_success=False,
                last_run_duration=None,
                total_runs=0,
                success_rate=0.0,
                avg_duration=0.0,
                next_scheduled_run=None,
                automation_enabled=False,
                timestamp=datetime.now().isoformat()
            )
    
    def get_log_summary(self, lines: int = 50) -> Dict[str, List[str]]:
        """Get recent log entries"""
        logs = {
            'automation': [],
            'system': [],
            'error': []
        }
        
        log_files = {
            'automation': self.logs_dir / "automation.log",
            'system': self.logs_dir / "system.log",
            'error': self.logs_dir / "error_system.log"
        }
        
        for log_type, log_file in log_files.items():
            if log_file.exists():
                try:
                    with open(log_file, 'r') as f:
                        log_lines = f.readlines()
                        logs[log_type] = [line.strip() for line in log_lines[-lines:]]
                except Exception as e:
                    logs[log_type] = [f"Error reading log: {e}"]
        
        return logs
    
    def generate_dashboard_report(self) -> Dict[str, Any]:
        """Generate comprehensive dashboard report"""
        print("Collecting system metrics...")
        system_metrics = self.get_system_metrics()
        
        print("Collecting database metrics...")
        database_metrics = self.get_database_metrics()
        
        print("Collecting automation metrics...")
        automation_metrics = self.get_automation_metrics()
        
        print("Collecting log summary...")
        log_summary = self.get_log_summary()
        
        return {
            'report_timestamp': datetime.now().isoformat(),
            'system': asdict(system_metrics),
            'database': asdict(database_metrics),
            'automation': asdict(automation_metrics),
            'logs': log_summary,
            'health_status': self._calculate_health_status(
                system_metrics, database_metrics, automation_metrics
            )
        }
    
    def _calculate_health_status(self, system: SystemMetrics, 
                               database: DatabaseMetrics, 
                               automation: AutomationMetrics) -> Dict[str, Any]:
        """Calculate overall health status"""
        issues = []
        warnings = []
        
        # System health checks
        if system.cpu_percent > 80:
            issues.append(f"High CPU usage: {system.cpu_percent:.1f}%")
        elif system.cpu_percent > 60:
            warnings.append(f"Elevated CPU usage: {system.cpu_percent:.1f}%")
        
        if system.memory_percent > 85:
            issues.append(f"High memory usage: {system.memory_percent:.1f}%")
        elif system.memory_percent > 70:
            warnings.append(f"Elevated memory usage: {system.memory_percent:.1f}%")
        
        if system.disk_usage_percent > 90:
            issues.append(f"Low disk space: {system.disk_usage_percent:.1f}% used")
        elif system.disk_usage_percent > 80:
            warnings.append(f"Disk space getting low: {system.disk_usage_percent:.1f}% used")
        
        # Database health checks
        if database.data_age_hours and database.data_age_hours > 72:
            issues.append(f"Data is stale: {database.data_age_hours:.1f} hours old")
        elif database.data_age_hours and database.data_age_hours > 48:
            warnings.append(f"Data is aging: {database.data_age_hours:.1f} hours old")
        
        if database.total_documents == 0:
            issues.append("No documents in database")
        
        # Automation health checks
        if not automation.automation_enabled:
            warnings.append("Automation is disabled")
        
        if automation.success_rate < 80 and automation.total_runs > 5:
            issues.append(f"Low automation success rate: {automation.success_rate:.1f}%")
        elif automation.success_rate < 95 and automation.total_runs > 5:
            warnings.append(f"Automation success rate could be better: {automation.success_rate:.1f}%")
        
        if not automation.last_run_success and automation.last_run_time:
            issues.append("Last automation run failed")
        
        # Overall health status
        if issues:
            overall_status = "unhealthy"
        elif warnings:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            'overall_status': overall_status,
            'issues': issues,
            'warnings': warnings,
            'score': max(0, 100 - len(issues) * 20 - len(warnings) * 5)
        }
    
    def print_dashboard(self, report: Dict[str, Any]) -> None:
        """Print formatted dashboard to console"""
        print("\n" + "=" * 80)
        print("n8n DOCUMENTATION AUTOMATION SYSTEM - MONITORING DASHBOARD")
        print("=" * 80)
        print(f"Report generated: {report['report_timestamp']}")
        
        # Health Status
        health = report['health_status']
        status_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'unhealthy': '❌'
        }
        
        print(f"\n🏥 OVERALL HEALTH: {status_emoji.get(health['overall_status'], '❓')} {health['overall_status'].upper()} (Score: {health['score']}/100)")
        
        if health['issues']:
            print("\n❌ CRITICAL ISSUES:")
            for issue in health['issues']:
                print(f"   • {issue}")
        
        if health['warnings']:
            print("\n⚠️  WARNINGS:")
            for warning in health['warnings']:
                print(f"   • {warning}")
        
        # System Metrics
        system = report['system']
        print(f"\n🖥️  SYSTEM METRICS")
        print(f"   CPU Usage:      {system['cpu_percent']:.1f}%")
        print(f"   Memory Usage:   {system['memory_percent']:.1f}%")
        print(f"   Disk Usage:     {system['disk_usage_percent']:.1f}% ({system['disk_free_gb']:.1f} GB free)")
        print(f"   Load Average:   {system['load_average'][0]:.2f}, {system['load_average'][1]:.2f}, {system['load_average'][2]:.2f}")
        print(f"   Uptime:         {system['uptime_hours']:.1f} hours")
        
        # Database Metrics
        database = report['database']
        print(f"\n🗄️  DATABASE METRICS")
        print(f"   Total Documents:    {database['total_documents']:,}")
        print(f"   Latest Scrape:      {database['latest_scrape'] or 'Never'}")
        if database['data_age_hours']:
            print(f"   Data Age:           {database['data_age_hours']:.1f} hours")
        print(f"   Avg Content Length: {database['avg_content_length']:.0f} chars")
        print(f"   Total Content Size: {database['total_content_size_mb']:.1f} MB")
        print(f"   Database Size:      {database['database_size_mb']:.1f} MB")
        print(f"   Active Connections: {database['connection_count']}")
        
        if database['category_counts']:
            print(f"\n   📊 CATEGORY BREAKDOWN:")
            for category, count in list(database['category_counts'].items())[:5]:
                print(f"      {category}: {count:,} documents")
        
        # Automation Metrics
        automation = report['automation']
        print(f"\n🤖 AUTOMATION METRICS")
        print(f"   Enabled:            {'Yes' if automation['automation_enabled'] else 'No'}")
        print(f"   Last Run:           {automation['last_run_time'] or 'Never'}")
        print(f"   Last Run Success:   {'Yes' if automation['last_run_success'] else 'No'}")
        if automation['last_run_duration']:
            print(f"   Last Run Duration:  {automation['last_run_duration']:.1f} seconds")
        print(f"   Total Runs:         {automation['total_runs']}")
        if automation['total_runs'] > 0:
            print(f"   Success Rate:       {automation['success_rate']:.1f}%")
        if automation['next_scheduled_run']:
            print(f"   Next Scheduled:     {automation['next_scheduled_run']}")
        
        print("\n" + "=" * 80)
    
    def save_report(self, report: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Save dashboard report to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"dashboard_report_{timestamp}.json"
        
        reports_dir = self.data_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        report_file = reports_dir / filename
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return str(report_file)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="n8n Documentation Automation Monitoring Dashboard")
    parser.add_argument("--format", choices=["console", "json", "both"], default="console",
                       help="Output format")
    parser.add_argument("--save", action="store_true",
                       help="Save report to file")
    parser.add_argument("--watch", type=int, metavar="SECONDS",
                       help="Watch mode - refresh every N seconds")
    
    args = parser.parse_args()
    
    dashboard = MonitoringDashboard()
    
    def generate_and_display():
        report = dashboard.generate_dashboard_report()
        
        if args.format in ["console", "both"]:
            dashboard.print_dashboard(report)
        
        if args.format in ["json", "both"]:
            print(json.dumps(report, indent=2))
        
        if args.save:
            report_file = dashboard.save_report(report)
            print(f"\nReport saved to: {report_file}")
        
        return report
    
    if args.watch:
        print(f"Starting dashboard in watch mode (refresh every {args.watch} seconds)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                if args.format == "console":
                    os.system('clear' if os.name == 'posix' else 'cls')
                
                generate_and_display()
                
                if args.format == "console":
                    print(f"\nRefreshing in {args.watch} seconds... (Press Ctrl+C to stop)")
                
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\nDashboard stopped.")
    else:
        report = generate_and_display()
        
        # Exit with appropriate code based on health status
        health_status = report['health_status']['overall_status']
        if health_status == "unhealthy":
            sys.exit(2)
        elif health_status == "warning":
            sys.exit(1)
        else:
            sys.exit(0)

if __name__ == "__main__":
    main()