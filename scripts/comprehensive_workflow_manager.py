#!/usr/bin/env python3
"""
Comprehensive Workflow Management Script

This script consolidates all workflow import processes:
1. Validation of workflow files
2. Automatic error fixing
3. Enhanced import with detailed logging
4. Comprehensive error reporting

Usage:
    python3 scripts/comprehensive_workflow_manager.py [--validate-only] [--fix-only] [--import-only]
"""

import os
import sys
import json
import logging
import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.n8n_scraper.database.connection import DatabaseManager
from src.n8n_scraper.database.unified_models import UnifiedDocument, UnifiedChunk
from sqlalchemy import text
import hashlib
import re

class ComprehensiveWorkflowManager:
    """Unified workflow management system"""
    
    def __init__(self, base_path: str = "data/workflows"):
        self.base_path = Path(base_path)
        self.setup_logging()
        self.stats = {
            'validation': {'total': 0, 'valid': 0, 'invalid': 0, 'warnings': 0},
            'fixing': {'processed': 0, 'fixed': 0, 'failed': 0},
            'import': {'processed': 0, 'errors': 0, 'skipped': 0}
        }
        self.validation_errors = []
        self.fix_results = []
        self.import_errors = []
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('workflow_management.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def find_workflow_files(self) -> List[Path]:
        """Find all workflow files"""
        files = []
        for pattern in ['**/*.json', '**/*.txt']:
            files.extend(self.base_path.glob(pattern))
        return sorted(files)
    
    def validate_workflows(self) -> Dict[str, Any]:
        """Validate all workflow files"""
        self.logger.info("Starting workflow validation...")
        
        files = self.find_workflow_files()
        self.stats['validation']['total'] = len(files)
        
        validation_results = {
            'timestamp': datetime.now().isoformat(),
            'summary': {'total_files': len(files), 'valid': 0, 'invalid': 0, 'errors': 0, 'warnings': 0},
            'errors': [],
            'warnings': [],
            'invalid_files': []
        }
        
        for file_path in files:
            try:
                result = self._validate_single_file(file_path)
                if result['valid']:
                    validation_results['summary']['valid'] += 1
                    self.stats['validation']['valid'] += 1
                else:
                    validation_results['summary']['invalid'] += 1
                    validation_results['invalid_files'].append(str(file_path))
                    self.stats['validation']['invalid'] += 1
                    
                if result['errors']:
                    validation_results['summary']['errors'] += len(result['errors'])
                    validation_results['errors'].extend(result['errors'])
                    
                if result['warnings']:
                    validation_results['summary']['warnings'] += len(result['warnings'])
                    validation_results['warnings'].extend(result['warnings'])
                    self.stats['validation']['warnings'] += len(result['warnings'])
                    
            except Exception as e:
                self.logger.error(f"Error validating {file_path}: {e}")
                validation_results['summary']['invalid'] += 1
                validation_results['errors'].append({
                    'file': str(file_path),
                    'error': f"Validation failed: {str(e)}"
                })
        
        # Save validation report
        self._save_validation_report(validation_results)
        
        self.logger.info(f"Validation complete: {validation_results['summary']['valid']} valid, "
                        f"{validation_results['summary']['invalid']} invalid files")
        
        return validation_results
    
    def _validate_single_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate a single workflow file"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        # Check if file exists and is readable
        if not file_path.exists():
            result['valid'] = False
            result['errors'].append({'file': str(file_path), 'error': 'File does not exist'})
            return result
            
        # Check file size
        file_size = file_path.stat().st_size
        if file_size == 0:
            result['valid'] = False
            result['errors'].append({'file': str(file_path), 'error': 'Empty file'})
            return result
            
        if file_size > 1024 * 1024:  # 1MB
            result['warnings'].append({'file': str(file_path), 'warning': f'Large file ({file_size} bytes)'})
        
        # For JSON files, validate JSON structure
        if file_path.suffix.lower() == '.json':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Check for required fields in workflow JSON
                if isinstance(data, dict):
                    if not data.get('nodes'):
                        result['errors'].append({'file': str(file_path), 'error': 'Missing required field: nodes'})
                        result['valid'] = False
                        
                    if not data.get('connections'):
                        result['errors'].append({'file': str(file_path), 'error': 'Missing required field: connections'})
                        result['valid'] = False
                        
                    # Check for default/empty names
                    name = data.get('name', '')
                    if not name or name in ['My workflow', 'New workflow', '']:
                        result['warnings'].append({'file': str(file_path), 'warning': 'Default or empty workflow name'})
                        
            except json.JSONDecodeError as e:
                result['valid'] = False
                result['errors'].append({'file': str(file_path), 'error': f'Invalid JSON: {str(e)}'})
            except UnicodeDecodeError as e:
                result['valid'] = False
                result['errors'].append({'file': str(file_path), 'error': f'Encoding error: {str(e)}'})
                
        return result
    
    def fix_workflow_errors(self) -> Dict[str, Any]:
        """Fix common workflow file errors"""
        self.logger.info("Starting workflow error fixing...")
        
        files = self.find_workflow_files()
        
        fix_results = {
            'timestamp': datetime.now().isoformat(),
            'summary': {'processed': 0, 'fixed': 0, 'failed': 0},
            'fixes_applied': defaultdict(int),
            'fixed_files': [],
            'failed_files': []
        }
        
        # Create backup directory
        backup_dir = self.base_path / 'backups' / datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        duplicates = self._find_duplicates(files)
        
        for i, file_path in enumerate(files, 1):
            if i % 100 == 0:
                self.logger.info(f"Processing file {i}/{len(files)}: {file_path.name}")
                
            try:
                fix_results['summary']['processed'] += 1
                self.stats['fixing']['processed'] += 1
                
                fixed = False
                
                # Handle duplicates
                if str(file_path) in duplicates and len(duplicates[str(file_path)]) > 1:
                    # Keep the first occurrence, remove others
                    if file_path != duplicates[str(file_path)][0]:
                        self._backup_file(file_path, backup_dir)
                        file_path.unlink()
                        fix_results['fixes_applied']['duplicate_files_removed'] += 1
                        fixed = True
                        continue
                
                # Check if file is empty
                if file_path.stat().st_size == 0:
                    self.logger.warning(f"Removing empty file: {file_path}")
                    self._backup_file(file_path, backup_dir)
                    file_path.unlink()
                    fix_results['fixes_applied']['empty_files_removed'] += 1
                    fixed = True
                    continue
                
                # Fix JSON files
                if file_path.suffix.lower() == '.json':
                    json_fixed = self._fix_json_file(file_path, backup_dir)
                    if json_fixed:
                        fix_results['fixes_applied']['json_repaired'] += 1
                        fixed = True
                        
                    # Add missing fields
                    fields_added = self._add_missing_fields(file_path, backup_dir)
                    if fields_added:
                        fix_results['fixes_applied']['missing_fields_added'] += 1
                        fixed = True
                
                if fixed:
                    fix_results['summary']['fixed'] += 1
                    fix_results['fixed_files'].append(str(file_path))
                    self.stats['fixing']['fixed'] += 1
                    
            except Exception as e:
                self.logger.error(f"Error fixing {file_path}: {e}")
                fix_results['summary']['failed'] += 1
                fix_results['failed_files'].append({'file': str(file_path), 'error': str(e)})
                self.stats['fixing']['failed'] += 1
        
        # Save fix report
        self._save_fix_report(fix_results)
        
        self.logger.info(f"Fixing complete: {fix_results['summary']['fixed']} files fixed, "
                        f"{fix_results['summary']['failed']} failed")
        
        return fix_results
    
    def _find_duplicates(self, files: List[Path]) -> Dict[str, List[Path]]:
        """Find duplicate files based on content hash"""
        hash_to_files = defaultdict(list)
        
        for file_path in files:
            try:
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                    hash_to_files[file_hash].append(file_path)
            except Exception as e:
                self.logger.warning(f"Could not hash {file_path}: {e}")
        
        return {h: paths for h, paths in hash_to_files.items() if len(paths) > 1}
    
    def _backup_file(self, file_path: Path, backup_dir: Path):
        """Create backup of file before modification"""
        backup_path = backup_dir / file_path.name
        counter = 1
        while backup_path.exists():
            backup_path = backup_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
            counter += 1
        shutil.copy2(file_path, backup_path)
    
    def _fix_json_file(self, file_path: Path, backup_dir: Path) -> bool:
        """Fix common JSON syntax errors"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Try to parse as-is first
            try:
                json.loads(content)
                return False  # Already valid
            except json.JSONDecodeError:
                pass
            
            # Common fixes
            original_content = content
            
            # Remove trailing commas
            content = re.sub(r',\s*}', '}', content)
            content = re.sub(r',\s*]', ']', content)
            
            # Fix unescaped quotes in strings
            content = re.sub(r'"([^"]*?)"([^"]*?)"([^"]*?)"', r'"\1\"\2\"\3"', content)
            
            # Try to parse fixed content
            try:
                json.loads(content)
                # Backup original and save fixed version
                self._backup_file(file_path, backup_dir)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.logger.info(f"Repaired JSON syntax in: {file_path}")
                return True
            except json.JSONDecodeError:
                return False
                
        except Exception as e:
            self.logger.error(f"Error fixing JSON in {file_path}: {e}")
            return False
    
    def _add_missing_fields(self, file_path: Path, backup_dir: Path) -> bool:
        """Add missing required fields to workflow JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                return False
                
            modified = False
            
            # Add missing nodes field
            if 'nodes' not in data:
                data['nodes'] = []
                modified = True
                
            # Add missing connections field
            if 'connections' not in data:
                data['connections'] = {}
                modified = True
            
            if modified:
                self._backup_file(file_path, backup_dir)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                self.logger.info(f"Added missing fields to: {file_path}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error adding fields to {file_path}: {e}")
            return False
    
    def import_workflows(self) -> Dict[str, Any]:
        """Import workflows with enhanced error handling"""
        self.logger.info("Starting workflow import...")
        
        try:
            db_manager = DatabaseManager()
            # Initialize sync engine for database operations
            if not db_manager._sync_engine:
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                from config.settings import settings
                
                db_manager._sync_engine = create_engine(
                    settings.database_url,
                    pool_size=settings.db_pool_size,
                    max_overflow=settings.db_max_overflow,
                    pool_timeout=settings.db_pool_timeout,
                    pool_recycle=3600,
                    echo=settings.is_development,
                )
                
                db_manager._sync_session_factory = sessionmaker(
                    bind=db_manager._sync_engine,
                    expire_on_commit=False,
                )
            
            # Clear existing workflows
            self.logger.info("Clearing existing workflow data...")
            session = db_manager.get_sync_session()
            try:
                session.execute(text("DELETE FROM unified_chunks WHERE document_id IN (SELECT id FROM unified_documents WHERE document_type = 'workflow')"))
                session.execute(text("DELETE FROM unified_documents WHERE document_type = 'workflow'"))
                session.commit()
            finally:
                session.close()
            
            files = self.find_workflow_files()
            
            import_results = {
                'timestamp': datetime.now().isoformat(),
                'summary': {'total_files': len(files), 'processed': 0, 'errors': 0, 'skipped': 0},
                'error_breakdown': defaultdict(int),
                'failed_files': [],
                'error_details': []
            }
            
            for i, file_path in enumerate(files, 1):
                if i % 100 == 0:
                    self.logger.info(f"Importing file {i}/{len(files)}: {file_path.name}")
                
                try:
                    result = self._import_single_workflow(file_path, db_manager)
                    if result['success']:
                        import_results['summary']['processed'] += 1
                        self.stats['import']['processed'] += 1
                    else:
                        import_results['summary']['errors'] += 1
                        import_results['error_breakdown'][result['error_type']] += 1
                        import_results['failed_files'].append(str(file_path))
                        import_results['error_details'].append({
                            'file_path': str(file_path),
                            'error_type': result['error_type'],
                            'error_message': result['error_message'],
                            'workflow_name': result.get('workflow_name', 'Unknown'),
                            'file_size': file_path.stat().st_size
                        })
                        self.stats['import']['errors'] += 1
                        
                except Exception as e:
                    self.logger.error(f"Unexpected error importing {file_path}: {e}")
                    import_results['summary']['errors'] += 1
                    import_results['error_breakdown']['unexpected_error'] += 1
                    self.stats['import']['errors'] += 1
            
            # Get final database statistics
            session = db_manager.get_sync_session()
            try:
                workflow_count = session.query(UnifiedDocument).filter_by(document_type='workflow').count()
                chunk_count = session.query(UnifiedChunk).join(UnifiedDocument).filter(UnifiedDocument.document_type == 'workflow').count()
                
                # Get category breakdown
                category_stats = session.execute(
                    text("SELECT category, COUNT(*) FROM unified_documents WHERE document_type = 'workflow' GROUP BY category")
                ).fetchall()
            finally:
                session.close()
            
            import_results['database_stats'] = {
                'total_documents': workflow_count,
                'total_chunks': chunk_count,
                'categories': dict(category_stats)
            }
            
            # Save import report
            self._save_import_report(import_results)
            
            self.logger.info(f"Import complete: {import_results['summary']['processed']} imported, "
                           f"{import_results['summary']['errors']} errors")
            
            return import_results
            
        except Exception as e:
            self.logger.error(f"Import failed: {e}")
            raise
    
    def _import_single_workflow(self, file_path: Path, db_manager: DatabaseManager) -> Dict[str, Any]:
        """Import a single workflow file"""
        try:
            # Read and analyze file
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                workflow_data = self._analyze_workflow_json(data, file_path)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                workflow_data = self._analyze_workflow_text(content, file_path)
            
            # Create workflow record
            session = db_manager.get_sync_session()
            try:
                workflow = UnifiedDocument(
                    title=workflow_data['name'],
                    content=workflow_data['content'],
                    category=workflow_data['category'],
                    file_path=str(file_path),
                    file_name=file_path.name,
                    content_hash=workflow_data['file_hash'],
                    cache_metadata=workflow_data.get('metadata', {}),
                    document_type='workflow',
                    source_type='file_import',
                    workflow_id=workflow_data['name'],
                    workflow_data=workflow_data.get('raw_data', {}),
                    node_count=workflow_data.get('metadata', {}).get('node_count', 0),
                    word_count=len(workflow_data['content'].split()),
                    content_length=len(workflow_data['content'])
                )
                
                session.add(workflow)
                session.flush()  # Get the ID
                
                # Create chunks
                chunks = self._create_workflow_chunks(workflow_data['content'], workflow.id)
                for chunk in chunks:
                    session.add(chunk)
                
                session.commit()
            finally:
                session.close()
                
            return {
                'success': True,
                'workflow_name': workflow_data['name']
            }
            
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error_type': 'json_decode_error',
                'error_message': f"JSON decode error: {str(e)}"
            }
        except UnicodeDecodeError as e:
            return {
                'success': False,
                'error_type': 'unicode_decode_error',
                'error_message': f"Unicode decode error: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'error_type': 'import_failed',
                'error_message': f"Failed to import workflow: {str(e)}"
            }
    
    def _analyze_workflow_json(self, data: dict, file_path: Path) -> Dict[str, Any]:
        """Analyze JSON workflow data"""
        # Extract content parts
        content_parts = []
        
        # Add workflow name - ensure it's not empty and not too long
        name = data.get('name', file_path.stem)
        if not name or name.strip() == '':
            name = file_path.stem
        if not name or name.strip() == '':
            name = 'Unnamed Workflow'
        
        # Truncate name if too long (max 120 chars to leave room for safety)
        if len(name) > 120:
            name = name[:120]
        
        content_parts.append(f"Workflow: {name}")
        
        # Add description if available
        if data.get('meta', {}).get('description'):
            content_parts.append(f"Description: {data['meta']['description']}")
        
        # Add node information
        nodes = data.get('nodes', [])
        if nodes:
            content_parts.append(f"Nodes ({len(nodes)}):")
            for node in nodes:
                node_type = node.get('type', 'Unknown')
                node_name = node.get('name', node.get('id', 'Unnamed'))
                content_parts.append(f"- {node_name} ({node_type})")
        
        # Add tags
        tags = data.get('tags', [])
        if tags:
            tag_names = []
            for tag in tags:
                if isinstance(tag, dict):
                    tag_names.append(tag.get('name', str(tag)))
                else:
                    tag_names.append(str(tag))
            content_parts.append(f"Tags: {', '.join(tag_names)}")
        
        # Ensure all parts are strings
        content_parts = [str(part) for part in content_parts]
        content = '\n'.join(content_parts)
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        return {
            'name': name,
            'content': content,
            'category': self._determine_category(data, content),
            'file_hash': file_hash,
            'raw_data': data,
            'metadata': {
                'node_count': len(nodes),
                'has_description': bool(data.get('meta', {}).get('description')),
                'tags': [str(tag) if not isinstance(tag, dict) else tag.get('name', str(tag)) for tag in tags]
            }
        }
    
    def _analyze_workflow_text(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Analyze text workflow content"""
        # Calculate file hash
        file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        # Handle name - ensure it's not empty and not too long
        name = file_path.stem
        if not name or name.strip() == '':
            name = 'Unnamed Workflow'
        
        # Truncate name if too long (max 120 chars to leave room for safety)
        if len(name) > 120:
            name = name[:120]
        
        return {
            'name': name,
            'content': content,
            'category': self._determine_category({}, content),
            'file_hash': file_hash,
            'raw_data': {'content': content, 'file_type': 'text'},
            'metadata': {
                'content_length': len(content),
                'is_text_file': True
            }
        }
    
    def _determine_category(self, data: dict, content: str) -> str:
        """Determine workflow category based on content"""
        content_lower = content.lower()
        
        # Category mapping based on keywords
        categories = {
            'email': ['email', 'gmail', 'outlook', 'smtp', 'imap'],
            'communication': ['slack', 'discord', 'telegram', 'whatsapp', 'teams'],
            'crm': ['hubspot', 'salesforce', 'pipedrive', 'zoho'],
            'ecommerce': ['shopify', 'woocommerce', 'stripe', 'paypal'],
            'cloud': ['aws', 'azure', 'gcp', 'google cloud'],
            'data': ['database', 'mysql', 'postgres', 'mongodb', 'airtable'],
            'monitoring': ['prometheus', 'grafana', 'datadog', 'newrelic'],
            'api': ['rest', 'graphql', 'webhook', 'http request'],
            'automation': ['cron', 'schedule', 'trigger', 'automation'],
            'social': ['twitter', 'facebook', 'linkedin', 'instagram'],
            'productivity': ['notion', 'trello', 'asana', 'jira']
        }
        
        for category, keywords in categories.items():
            if any(keyword in content_lower for keyword in keywords):
                return category.title()
        
        return 'General'
    
    def _create_workflow_chunks(self, content: str, workflow_id: int) -> List[UnifiedChunk]:
        """Create searchable chunks from workflow content"""
        chunks = []
        
        # Split content into chunks (max 500 chars per chunk)
        chunk_size = 500
        overlap = 50
        
        for i in range(0, len(content), chunk_size - overlap):
            chunk_content = content[i:i + chunk_size]
            if chunk_content.strip():
                chunk_hash = hashlib.md5(chunk_content.encode('utf-8')).hexdigest()
                chunk = UnifiedChunk(
                    document_id=workflow_id,
                    content=chunk_content,
                    chunk_index=len(chunks),
                    chunk_type='workflow',
                    content_hash=chunk_hash
                )
                chunks.append(chunk)
        
        return chunks
    
    def _save_validation_report(self, results: Dict[str, Any]):
        """Save validation report to files"""
        # JSON report
        with open('validation_report.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # Text report
        with open('validation_report.txt', 'w') as f:
            f.write(f"# Workflow Validation Report\n")
            f.write(f"Generated: {results['timestamp']}\n\n")
            f.write(f"## Summary\n")
            f.write(f"Total files: {results['summary']['total_files']}\n")
            f.write(f"Valid files: {results['summary']['valid']}\n")
            f.write(f"Invalid files: {results['summary']['invalid']}\n")
            f.write(f"Errors: {results['summary']['errors']}\n")
            f.write(f"Warnings: {results['summary']['warnings']}\n\n")
            
            if results['errors']:
                f.write(f"## Errors\n")
                for error in results['errors']:
                    f.write(f"- {error['file']}: {error['error']}\n")
                f.write("\n")
    
    def _save_fix_report(self, results: Dict[str, Any]):
        """Save fix report to files"""
        # JSON report
        with open('recovery_report.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # Text report
        with open('recovery_report.txt', 'w') as f:
            f.write(f"# Workflow Error Recovery Report\n")
            f.write(f"Generated: {results['timestamp']}\n\n")
            f.write(f"## Summary\n")
            f.write(f"Files processed: {results['summary']['processed']}\n")
            f.write(f"Files fixed: {results['summary']['fixed']}\n")
            f.write(f"Files failed: {results['summary']['failed']}\n\n")
            f.write(f"## Fixes Applied\n")
            for fix_type, count in results['fixes_applied'].items():
                f.write(f"  - {fix_type.replace('_', ' ').title()}: {count}\n")
    
    def _save_import_report(self, results: Dict[str, Any]):
        """Save import report to files"""
        # JSON report
        with open('import_error_report.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # Text report
        with open('import_error_report.txt', 'w') as f:
            f.write(f"# Workflow Import Error Report\n")
            f.write(f"Generated: {results['timestamp']}\n\n")
            f.write(f"## Summary\n")
            f.write(f"Total files: {results['summary']['total_files']}\n")
            f.write(f"Successfully processed: {results['summary']['processed']}\n")
            f.write(f"Errors: {results['summary']['errors']}\n")
            f.write(f"Skipped: {results['summary']['skipped']}\n\n")
            
            if results['error_breakdown']:
                f.write(f"## Error Breakdown\n")
                for error_type, count in results['error_breakdown'].items():
                    f.write(f"  - {error_type}: {count}\n")
                f.write("\n")
            
            if results['error_details']:
                f.write(f"## Detailed Errors\n\n")
                for i, error in enumerate(results['error_details'], 1):
                    f.write(f"{i}. {error['file_path']}\n")
                    f.write(f"   Error Type: {error['error_type']}\n")
                    f.write(f"   Message: {error['error_message']}\n")
                    f.write(f"   File Size: {error['file_size']} bytes\n")
                    f.write(f"   Workflow Name: {error['workflow_name']}\n\n")
    
    def run_complete_process(self) -> Dict[str, Any]:
        """Run the complete workflow management process"""
        self.logger.info("Starting complete workflow management process...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'validation': None,
            'fixing': None,
            'import': None,
            'overall_stats': self.stats
        }
        
        try:
            # Step 1: Validate workflows
            self.logger.info("=== Step 1: Validation ===")
            results['validation'] = self.validate_workflows()
            
            # Step 2: Fix errors
            self.logger.info("=== Step 2: Error Fixing ===")
            results['fixing'] = self.fix_workflow_errors()
            
            # Step 3: Import workflows
            self.logger.info("=== Step 3: Import ===")
            results['import'] = self.import_workflows()
            
            # Final summary
            self.logger.info("=== Complete Process Summary ===")
            self.logger.info(f"Validation: {self.stats['validation']['valid']} valid, {self.stats['validation']['invalid']} invalid")
            self.logger.info(f"Fixing: {self.stats['fixing']['fixed']} fixed, {self.stats['fixing']['failed']} failed")
            self.logger.info(f"Import: {self.stats['import']['processed']} imported, {self.stats['import']['errors']} errors")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Complete process failed: {e}")
            raise

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Comprehensive Workflow Management')
    parser.add_argument('--validate-only', action='store_true', help='Only run validation')
    parser.add_argument('--fix-only', action='store_true', help='Only run error fixing')
    parser.add_argument('--import-only', action='store_true', help='Only run import')
    parser.add_argument('--base-path', default='data/workflows', help='Base path for workflow files')
    
    args = parser.parse_args()
    
    manager = ComprehensiveWorkflowManager(args.base_path)
    
    try:
        if args.validate_only:
            manager.validate_workflows()
        elif args.fix_only:
            manager.fix_workflow_errors()
        elif args.import_only:
            manager.import_workflows()
        else:
            manager.run_complete_process()
            
        print("\n=== Process Complete ===")
        print(f"Check the generated report files for detailed results.")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()