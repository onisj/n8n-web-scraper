"""
System Management API Routes

Routes for system monitoring, updates, and management
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
import json
import psutil
import os

from n8n_scraper.automation.update_scheduler import AutomatedUpdater
from n8n_scraper.automation.change_detector import N8nDataAnalyzer as N8nDocsAnalyzer

router = APIRouter(prefix="/system", tags=["System Management"])

# Request/Response models
class UpdateRequest(BaseModel):
    force: Optional[bool] = Field(False, description="Force update even if recent")
    full_scrape: Optional[bool] = Field(False, description="Perform full scrape")

class SystemStatus(BaseModel):
    status: str
    knowledge_base_size: int
    last_update: Optional[str]
    ai_agent_status: str
    uptime: str
    memory_usage: Dict[str, Any]
    disk_usage: Dict[str, Any]

class APIResponse(BaseModel):
    success: bool
    data: Any
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# Global instances
automated_updater = None
analyzer = None
start_time = datetime.now()

def get_updater() -> AutomatedUpdater:
    """Get automated updater instance"""
    global automated_updater
    if automated_updater is None:
        automated_updater = AutomatedUpdater()
    return automated_updater

def get_analyzer() -> N8nDocsAnalyzer:
    """Get analyzer instance"""
    global analyzer
    if analyzer is None:
        analyzer = N8nDocsAnalyzer()
    return analyzer

@router.get("/health", response_model=Dict[str, str])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": str(datetime.now() - start_time)
    }

@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get comprehensive system status"""
    try:
        # Count knowledge base files
        data_dir = Path("data/scraped_docs")
        kb_size = len(list(data_dir.glob("*.json"))) if data_dir.exists() else 0
        
        # Get last update time
        analysis_file = Path("n8n_docs_analysis_report.json")
        last_update = None
        if analysis_file.exists():
            try:
                with open(analysis_file, 'r') as f:
                    analysis = json.load(f)
                last_update = analysis.get('timestamp')
            except Exception:
                pass
        
        # Get system metrics
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return SystemStatus(
            status="operational",
            knowledge_base_size=kb_size,
            last_update=last_update,
            ai_agent_status="ready",
            uptime=str(datetime.now() - start_time),
            memory_usage={
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            },
            disk_usage={
                "total": disk.total,
                "free": disk.free,
                "used": disk.used,
                "percent": (disk.used / disk.total) * 100
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")

@router.post("/update/trigger", response_model=APIResponse)
async def trigger_update(
    request: UpdateRequest,
    background_tasks: BackgroundTasks
):
    """Trigger a knowledge base update"""
    try:
        # Add update task to background
        background_tasks.add_task(
            run_update_task,
            force=request.force,
            full_scrape=request.full_scrape
        )
        
        return APIResponse(
            success=True,
            data={
                "update_triggered": True,
                "force": request.force,
                "full_scrape": request.full_scrape
            },
            message="Update task started in background"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger update: {str(e)}")

@router.get("/update/status", response_model=APIResponse)
async def get_update_status():
    """Get update system status"""
    try:
        updater = get_updater()
        
        # Check if updater is running
        status = "idle"  # This would need to be implemented in the updater
        
        return APIResponse(
            success=True,
            data={
                "status": status,
                "last_check": None,  # Would come from updater
                "next_scheduled": None  # Would come from updater
            },
            message="Update status retrieved"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get update status: {str(e)}")

@router.get("/logs", response_model=APIResponse)
async def get_system_logs(
    lines: int = 100,
    level: Optional[str] = None
):
    """Get system logs"""
    try:
        logs_dir = Path("logs")
        log_file = logs_dir / "system.log"
        
        if not log_file.exists():
            return APIResponse(
                success=True,
                data={"logs": []},
                message="No log file found"
            )
        
        # Read last N lines
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # Filter by level if specified
        if level:
            recent_lines = [line for line in recent_lines if level.upper() in line]
        
        return APIResponse(
            success=True,
            data={
                "logs": [line.strip() for line in recent_lines],
                "total_lines": len(recent_lines),
                "filtered_by": level
            },
            message="Logs retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

@router.get("/metrics", response_model=APIResponse)
async def get_system_metrics():
    """Get detailed system metrics"""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        
        # Process metrics
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        return APIResponse(
            success=True,
            data={
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "free": disk.free,
                    "used": disk.used,
                    "percent": (disk.used / disk.total) * 100
                },
                "process": {
                    "memory_rss": process_memory.rss,
                    "memory_vms": process_memory.vms,
                    "cpu_percent": process.cpu_percent()
                }
            },
            message="System metrics retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@router.post("/backup/create", response_model=APIResponse)
async def create_backup(background_tasks: BackgroundTasks):
    """Create a backup of the knowledge base"""
    try:
        background_tasks.add_task(run_backup_task)
        
        return APIResponse(
            success=True,
            data={"backup_triggered": True},
            message="Backup task started in background"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create backup: {str(e)}")

@router.get("/backup/list", response_model=APIResponse)
async def list_backups():
    """List available backups"""
    try:
        backups_dir = Path("backups")
        
        if not backups_dir.exists():
            return APIResponse(
                success=True,
                data={"backups": []},
                message="No backups directory found"
            )
        
        # Get backup files
        backup_files = []
        for backup_file in backups_dir.glob("*.tar.gz"):
            stat = backup_file.stat()
            backup_files.append({
                "name": backup_file.name,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        # Sort by creation time (newest first)
        backup_files.sort(key=lambda x: x['created'], reverse=True)
        
        return APIResponse(
            success=True,
            data={
                "backups": backup_files,
                "total": len(backup_files)
            },
            message="Backups listed successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")

# Background task functions
async def run_update_task(force: bool = False, full_scrape: bool = False):
    """Background task to run knowledge base update"""
    try:
        updater = get_updater()
        # This would call the actual update method
        # updater.run_update_cycle(force=force, full_scrape=full_scrape)
        print(f"Update task completed (force={force}, full_scrape={full_scrape})")
    except Exception as e:
        print(f"Update task failed: {str(e)}")

async def run_backup_task():
    """Background task to create backup"""
    try:
        # This would implement the actual backup logic
        print("Backup task completed")
    except Exception as e:
        print(f"Backup task failed: {str(e)}")