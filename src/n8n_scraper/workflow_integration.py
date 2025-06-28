#!/usr/bin/env python3
"""
Workflow Integration Module
Integrates the standalone workflow system into the main n8n scraper backend.
"""

import os
import sys
import sqlite3
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

# Import from the new location
try:
    from .database.workflow_db import WorkflowDatabase
except ImportError:
    print("Warning: Could not import WorkflowDatabase. Workflow features may not work.")
    WorkflowDatabase = None


class WorkflowIntegration:
    """Handles integration of workflow system with main backend."""
    
    def __init__(self, main_db_path: str = None, workflow_db_path: str = None):
        self.main_db_path = main_db_path or "data/knowledge_base.db"
        self.workflow_db_path = workflow_db_path or "data/workflows/database/workflows.db"
        self.workflows_json_dir = "data/workflows/files"
        
    def ensure_workflow_db_exists(self) -> bool:
        """Ensure the workflow database exists and is initialized."""
        try:
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(self.workflow_db_path), exist_ok=True)
            os.makedirs(self.workflows_json_dir, exist_ok=True)
            
            # Initialize workflow database if it doesn't exist
            if not os.path.exists(self.workflow_db_path):
                if WorkflowDatabase:
                    db = WorkflowDatabase(self.workflow_db_path)
                    print(f"✅ Initialized workflow database at {self.workflow_db_path}")
                    return True
                else:
                    print("❌ Cannot initialize workflow database - WorkflowDatabase not available")
                    return False
            else:
                print(f"✅ Workflow database already exists at {self.workflow_db_path}")
                return True
                
        except Exception as e:
            print(f"❌ Error ensuring workflow database exists: {e}")
            return False
    
    def import_workflows_to_db(self) -> Dict[str, Any]:
        """Import all workflow JSON files into the database."""
        if not WorkflowDatabase:
            return {"success": False, "error": "WorkflowDatabase not available"}
            
        try:
            # Create a temporary WorkflowDatabase instance with the correct workflows directory
            db = WorkflowDatabase(self.workflow_db_path)
            # Set the workflows directory to our JSON files location
            db.workflows_dir = self.workflows_json_dir
            
            # Check if workflows directory exists
            if not os.path.exists(self.workflows_json_dir):
                return {
                    "success": False, 
                    "error": f"Workflows directory not found: {self.workflows_json_dir}"
                }
            
            # Index workflows using the correct method
            result = db.index_all_workflows(force_reindex=False)
            return {
                "success": True,
                "imported": result.get('processed', 0),
                "skipped": result.get('skipped', 0),
                "errors": result.get('errors', 0),
                "details": result
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_workflow_stats(self) -> Dict[str, Any]:
        """Get workflow statistics."""
        if not WorkflowDatabase:
            return {"success": False, "error": "WorkflowDatabase not available"}
            
        try:
            db = WorkflowDatabase(self.workflow_db_path)
            stats = db.get_stats()
            return {"success": True, "data": stats}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_workflows(self, query: str = "", category: str = None, 
                        integration: str = None, limit: int = 20, 
                        offset: int = 0) -> Dict[str, Any]:
        """Search workflows with filters."""
        if not WorkflowDatabase:
            return {"success": False, "error": "WorkflowDatabase not available"}
            
        try:
            db = WorkflowDatabase(self.workflow_db_path)
            # Use the correct parameter name for WorkflowDatabase.search_workflows
            results = db.search_workflows(
                query=query,
                trigger_filter=category or "all",
                limit=limit,
                offset=offset
            )
            return {"success": True, "data": results}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_workflow_by_id(self, workflow_id: int) -> Dict[str, Any]:
        """Get detailed workflow information by ID."""
        if not WorkflowDatabase:
            return {"success": False, "error": "WorkflowDatabase not available"}
            
        try:
            db = WorkflowDatabase(self.workflow_db_path)
            workflow = db.get_workflow_by_id(workflow_id)
            if workflow:
                return {"success": True, "data": workflow}
            else:
                return {"success": False, "error": "Workflow not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_categories(self) -> Dict[str, Any]:
        """Get all workflow categories (trigger types)."""
        if not WorkflowDatabase:
            return {"success": False, "error": "WorkflowDatabase not available"}
            
        try:
            db = WorkflowDatabase(self.workflow_db_path)
            # Use get_service_categories which exists in WorkflowDatabase
            service_categories = db.get_service_categories()
            return {"success": True, "data": service_categories}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_integrations(self) -> Dict[str, Any]:
        """Get all workflow integrations."""
        if not WorkflowDatabase:
            return {"success": False, "error": "WorkflowDatabase not available"}
            
        try:
            db = WorkflowDatabase(self.workflow_db_path)
            # Use get_service_categories to get integrations data
            service_categories = db.get_service_categories()
            # Flatten all services from all categories
            all_integrations = []
            for category, services in service_categories.items():
                all_integrations.extend(services)
            return {"success": True, "data": list(set(all_integrations))}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_mermaid_diagram(self, workflow_id: int) -> Dict[str, Any]:
        """Generate Mermaid diagram for a workflow."""
        if not WorkflowDatabase:
            return {"success": False, "error": "WorkflowDatabase not available"}
            
        try:
            db = WorkflowDatabase(self.workflow_db_path)
            
            # Get workflow details
            workflow = db.get_workflow_by_id(workflow_id)
            if not workflow:
                return {"success": False, "error": "Workflow not found"}
            
            # Load the actual workflow JSON
            workflow_file = os.path.join(self.workflows_json_dir, workflow['filename'])
            if not os.path.exists(workflow_file):
                return {"success": False, "error": "Workflow file not found"}
            
            import json
            with open(workflow_file, 'r') as f:
                workflow_data = json.load(f)
            
            # Generate Mermaid diagram
            mermaid_code = self._generate_mermaid_from_workflow(workflow_data)
            
            return {
                "success": True, 
                "data": {
                    "mermaid_code": mermaid_code,
                    "workflow_name": workflow['name']
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_mermaid_from_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """Generate Mermaid flowchart from workflow data."""
        nodes = workflow_data.get('nodes', [])
        connections = workflow_data.get('connections', {})
        
        mermaid_lines = ['flowchart TD']
        
        # Add nodes
        for node in nodes:
            node_id = node.get('name', '').replace(' ', '_').replace('-', '_')
            node_type = node.get('type', '').split('.')[-1] if '.' in node.get('type', '') else node.get('type', '')
            node_label = f"{node.get('name', 'Unknown')}\n({node_type})"
            
            # Determine node shape based on type
            if 'trigger' in node_type.lower():
                mermaid_lines.append(f'    {node_id}([{node_label}])')
            elif 'webhook' in node_type.lower():
                mermaid_lines.append(f'    {node_id}{{{{{{node_label}}}}}}')
            elif 'if' in node_type.lower() or 'switch' in node_type.lower():
                mermaid_lines.append(f'    {node_id}{{{node_label}}}')
            else:
                mermaid_lines.append(f'    {node_id}[{node_label}]')
        
        # Add connections
        for source_node, targets in connections.items():
            source_id = source_node.replace(' ', '_').replace('-', '_')
            
            if isinstance(targets, dict):
                for output_name, target_list in targets.items():
                    if isinstance(target_list, list):
                        for target in target_list:
                            target_node = target.get('node', '')
                            target_id = target_node.replace(' ', '_').replace('-', '_')
                            if target_id:
                                mermaid_lines.append(f'    {source_id} --> {target_id}')
        
        return '\n'.join(mermaid_lines)
    
    def download_workflow(self, workflow_id: int) -> Dict[str, Any]:
        """Get workflow JSON for download."""
        if not WorkflowDatabase:
            return {"success": False, "error": "WorkflowDatabase not available"}
            
        try:
            db = WorkflowDatabase(self.workflow_db_path)
            
            # Get workflow details
            workflow = db.get_workflow_by_id(workflow_id)
            if not workflow:
                return {"success": False, "error": "Workflow not found"}
            
            # Load the actual workflow JSON
            workflow_file = os.path.join(self.workflows_json_dir, workflow['filename'])
            if not os.path.exists(workflow_file):
                return {"success": False, "error": "Workflow file not found"}
            
            import json
            with open(workflow_file, 'r') as f:
                workflow_data = json.load(f)
            
            return {
                "success": True,
                "data": {
                    "filename": workflow['filename'],
                    "content": workflow_data
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_similar_workflows(self, workflow_id: int, limit: int = 5) -> Dict[str, Any]:
        """Get workflows similar to the given workflow."""
        if not WorkflowDatabase:
            return {"success": False, "error": "WorkflowDatabase not available"}
            
        try:
            db = WorkflowDatabase(self.workflow_db_path)
            similar = db.get_similar_workflows(workflow_id, limit)
            return {"success": True, "data": {"similar_workflows": similar}}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def setup_integration(self) -> Dict[str, Any]:
        """Complete setup of workflow integration."""
        results = []
        
        # Step 1: Ensure database exists
        if self.ensure_workflow_db_exists():
            results.append("✅ Workflow database initialized")
        else:
            results.append("❌ Failed to initialize workflow database")
            return {"success": False, "results": results}
        
        # Step 2: Import workflows
        import_result = self.import_workflows_to_db()
        if import_result.get("success"):
            imported = import_result.get("imported", 0)
            results.append(f"✅ Imported {imported} workflows")
        else:
            error = import_result.get("error", "Unknown error")
            results.append(f"⚠️ Workflow import issue: {error}")
        
        # Step 3: Verify integration
        stats_result = self.get_workflow_stats()
        if stats_result.get("success"):
            stats = stats_result.get("data", {})
            total = stats.get("total_workflows", 0)
            results.append(f"✅ Integration verified: {total} workflows available")
        else:
            results.append("⚠️ Could not verify integration")
        
        return {
            "success": True,
            "results": results,
            "stats": stats_result.get("data", {})
        }


# Global instance for use in routes
workflow_integration = WorkflowIntegration()


def get_workflow_integration() -> WorkflowIntegration:
    """Get the global workflow integration instance."""
    return workflow_integration