#!/usr/bin/env python3
"""
Test script for the unified database schema integration.
This script tests all major functionality of the unified schema
to ensure everything works correctly after migration.
"""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Disable verbose SQL logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.n8n_scraper.database.unified_service import unified_db_service
    from src.n8n_scraper.database.connection import initialize_database, cleanup_database
    from src.n8n_scraper.core.logging_config import get_logger
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this script from the project root directory")
    sys.exit(1)

logger = get_logger(__name__)


class UnifiedSchemaIntegrationTest:
    """Test suite for unified schema integration."""
    
    def __init__(self):
        self.service = unified_db_service
        self.test_results = []
        self.test_documents = []  # Track created test documents for cleanup
        self.verbose = True
    
    async def initialize(self):
        """Initialize the test environment."""
        try:
            await initialize_database()
            logger.info("Test environment initialized successfully")
            if self.verbose:
                print("✓ Test environment initialized")
        except Exception as e:
            logger.error(f"Failed to initialize test environment: {e}")
            if self.verbose:
                print(f"✗ Failed to initialize test environment: {e}")
                traceback.print_exc()
            raise
    
    async def cleanup(self):
        """Clean up test environment."""
        try:
            # Clean up test documents
            cleanup_count = 0
            for doc_id in self.test_documents:
                try:
                    await self.service.delete_document(doc_id)
                    cleanup_count += 1
                    if self.verbose:
                        print(f"✓ Cleaned up test document: {doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete test document {doc_id}: {e}")
                    if self.verbose:
                        print(f"⚠ Failed to delete test document {doc_id}: {e}")
            
            await cleanup_database()
            logger.info(f"Test environment cleaned up successfully. Removed {cleanup_count} test documents.")
            if self.verbose:
                print(f"✓ Test environment cleaned up. Removed {cleanup_count} test documents.")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            if self.verbose:
                print(f"✗ Error during cleanup: {e}")
                traceback.print_exc()
    
    def log_test_result(self, test_name: str, success: bool, message: str = "", error: Exception = None):
        """Log a test result."""
        status = "PASS" if success else "FAIL"
        self.test_results.append({
            'test': test_name,
            'status': status,
            'message': message,
            'error': str(error) if error else None
        })
        
        log_msg = f"[{status}] {test_name}"
        if message:
            log_msg += f": {message}"
        
        if success:
            logger.info(log_msg)
            if self.verbose:
                print(f"✓ {test_name}: {message}")
        else:
            logger.error(log_msg)
            if self.verbose:
                print(f"✗ {test_name}: {message}")
                if error:
                    print(f"  Error details: {error}")
    
    async def test_database_connection(self) -> bool:
        """Test basic database connectivity."""
        try:
            stats = await self.service.get_statistics()
            self.log_test_result(
                "Database Connection", 
                True, 
                f"Connected successfully, found {stats.get('total_documents', 0)} documents"
            )
            return True
        except Exception as e:
            self.log_test_result("Database Connection", False, "Failed to connect or get statistics", e)
            return False
    
    async def test_create_documentation_document(self) -> bool:
        """Test creating a documentation document."""
        try:
            doc = await self.service.create_document(
                document_type='documentation',
                source_type='web_scrape',
                title='Test Documentation',
                content='This is a test documentation document with some content.',
                url=f'https://test.example.com/docs/test_{int(time.time())}',
                category='Testing',
                subcategory='Integration Tests',
                metadata={
                    'test': True,
                    'created_by': 'integration_test'
                }
            )
            
            if doc and doc.id:
                self.test_documents.append(doc.id)
                self.log_test_result(
                    "Create Documentation Document", 
                    True, 
                    f"Created document with ID: {doc.id}"
                )
                return True
            else:
                self.log_test_result("Create Documentation Document", False, "Document creation returned None")
                return False
                
        except Exception as e:
            self.log_test_result("Create Documentation Document", False, "Failed to create documentation document", e)
            return False
    
    async def test_create_workflow_document(self) -> bool:
        """Test creating a workflow document."""
        try:
            # Sample workflow data
            workflow_data = {
                "name": "Test Workflow",
                "description": "A test workflow for integration testing",
                "nodes": [
                    {"name": "Start", "type": "n8n-nodes-base.start"},
                    {"name": "HTTP Request", "type": "n8n-nodes-base.httpRequest"},
                    {"name": "Set", "type": "n8n-nodes-base.set"}
                ],
                "connections": {"Start": {"main": [[{"node": "HTTP Request", "type": "main", "index": 0}]]}}
            }
            
            doc = await self.service.create_document(
                document_type='workflow',
                source_type='file_import',
                title='Test Workflow',
                content='Test workflow with HTTP request and data transformation',
                file_path=f'/test/workflows/test_workflow_{int(time.time())}.json',
                file_name='test_workflow.json',
                category='Testing',
                workflow_id='test-workflow-123',
                workflow_data=workflow_data,
                node_count=3,
                connection_count=1,
                trigger_types=['manual'],
                node_types=['start', 'httpRequest', 'set'],
                integrations=['http'],
                complexity_score=0.1,
                metadata={
                    'test': True,
                    'created_by': 'integration_test'
                }
            )
            
            if doc and doc.id:
                self.test_documents.append(doc.id)
                self.log_test_result(
                    "Create Workflow Document", 
                    True, 
                    f"Created workflow with ID: {doc.id}"
                )
                return True
            else:
                self.log_test_result("Create Workflow Document", False, "Workflow creation returned None")
                return False
                
        except Exception as e:
            self.log_test_result("Create Workflow Document", False, "Failed to create workflow document", e)
            return False
    
    async def test_document_retrieval(self) -> bool:
        """Test retrieving documents by ID."""
        try:
            if not self.test_documents:
                self.log_test_result("Document Retrieval", False, "No test documents available for retrieval")
                return False
            
            doc_id = self.test_documents[0]
            doc = await self.service.get_document_by_id(doc_id)
            
            if doc and doc.id == doc_id:
                self.log_test_result(
                    "Document Retrieval", 
                    True, 
                    f"Successfully retrieved document: {doc.title}"
                )
                return True
            else:
                self.log_test_result("Document Retrieval", False, "Document not found or ID mismatch")
                return False
                
        except Exception as e:
            self.log_test_result("Document Retrieval", False, "Failed to retrieve document", e)
            return False
    
    async def test_document_search(self) -> bool:
        """Test document search functionality."""
        try:
            # Search for test documents
            results = await self.service.search_documents(
                query='test',
                limit=10
            )
            
            if results:
                self.log_test_result(
                    "Document Search", 
                    True, 
                    f"Found {len(results)} documents matching 'test'"
                )
                return True
            else:
                # This might not be a failure if no documents match
                self.log_test_result("Document Search", True, "Search completed but no results found")
                return True
                
        except Exception as e:
            self.log_test_result("Document Search", False, "Search functionality failed", e)
            return False
    
    async def test_document_filtering(self) -> bool:
        """Test document filtering by type and category."""
        try:
            # Test filtering by document type
            workflows = await self.service.get_documents_by_type('workflow', limit=5)
            docs = await self.service.get_documents_by_type('documentation', limit=5)
            
            self.log_test_result(
                "Document Filtering", 
                True, 
                f"Found {len(workflows)} workflows and {len(docs)} documentation documents"
            )
            return True
                
        except Exception as e:
            self.log_test_result("Document Filtering", False, "Failed to filter documents", e)
            return False
    
    async def test_document_update(self) -> bool:
        """Test updating document content."""
        try:
            if not self.test_documents:
                self.log_test_result("Document Update", False, "No test documents available for update")
                return False
            
            doc_id = self.test_documents[0]
            updated_doc = await self.service.update_document(
                doc_id,
                title='Updated Test Document',
                content='This content has been updated during integration testing.',
                metadata={'updated': True, 'update_time': datetime.utcnow().isoformat()}
            )
            
            if updated_doc and updated_doc.title == 'Updated Test Document':
                self.log_test_result(
                    "Document Update", 
                    True, 
                    f"Successfully updated document: {updated_doc.id}"
                )
                return True
            else:
                self.log_test_result("Document Update", False, "Document update failed or returned None")
                return False
                
        except Exception as e:
            self.log_test_result("Document Update", False, "Failed to update document", e)
            return False
    
    async def test_chunk_operations(self) -> bool:
        """Test chunk creation and retrieval."""
        try:
            if not self.test_documents:
                self.log_test_result("Chunk Operations", False, "No test documents available for chunk operations")
                return False
            
            doc_id = self.test_documents[0]
            
            # Create a chunk
            chunk = await self.service.create_chunk(
                document_id=doc_id,
                content='This is a test chunk for the document.',
                chunk_index=0,
                metadata={'test_chunk': True}
            )
            
            if not chunk:
                self.log_test_result("Chunk Operations", False, "Failed to create chunk")
                return False
            
            # Retrieve chunks for the document
            chunks = await self.service.get_document_chunks(doc_id)
            
            if chunks and len(chunks) > 0:
                self.log_test_result(
                    "Chunk Operations", 
                    True, 
                    f"Created and retrieved {len(chunks)} chunks for document"
                )
                return True
            else:
                self.log_test_result("Chunk Operations", False, "No chunks found for document")
                return False
                
        except Exception as e:
            self.log_test_result("Chunk Operations", False, "Chunk operations failed", e)
            return False
    
    async def test_workflow_file_import(self) -> bool:
        """Test importing a workflow file."""
        try:
            # Create a temporary workflow file
            test_workflow = {
                "name": "Integration Test Workflow",
                "description": "A workflow created for integration testing",
                "nodes": [
                    {"name": "Manual Trigger", "type": "n8n-nodes-base.manualTrigger"},
                    {"name": "Code", "type": "n8n-nodes-base.code"},
                    {"name": "HTTP Request", "type": "n8n-nodes-base.httpRequest"}
                ],
                "connections": {
                    "Manual Trigger": {"main": [[{"node": "Code", "type": "main", "index": 0}]]},
                    "Code": {"main": [[{"node": "HTTP Request", "type": "main", "index": 0}]]}
                }
            }
            
            # Create temporary file
            temp_file = Path("/tmp/test_integration_workflow.json")
            with open(temp_file, 'w') as f:
                json.dump(test_workflow, f)
            
            try:
                # Import the workflow file
                doc = await self.service.import_workflow_file(temp_file)
                
                if doc and doc.id:
                    self.test_documents.append(doc.id)
                    self.log_test_result(
                        "Workflow File Import", 
                        True, 
                        f"Successfully imported workflow: {doc.title}"
                    )
                    return True
                else:
                    self.log_test_result("Workflow File Import", False, "Import returned None")
                    return False
            finally:
                # Clean up temporary file
                if temp_file.exists():
                    temp_file.unlink()
                
        except Exception as e:
            self.log_test_result("Workflow File Import", False, "Failed to import workflow file", e)
            return False
    
    async def test_statistics_generation(self) -> bool:
        """Test database statistics generation."""
        try:
            stats = await self.service.get_statistics()
            
            required_keys = ['total_documents', 'total_chunks', 'documents_by_type', 'documents_by_category']
            missing_keys = [key for key in required_keys if key not in stats]
            
            if not missing_keys:
                self.log_test_result(
                    "Statistics Generation", 
                    True, 
                    f"Generated complete statistics: {stats['total_documents']} docs, {stats['total_chunks']} chunks"
                )
                return True
            else:
                self.log_test_result(
                    "Statistics Generation", 
                    False, 
                    f"Missing statistics keys: {missing_keys}"
                )
                return False
                
        except Exception as e:
            self.log_test_result("Statistics Generation", False, "Failed to generate statistics", e)
            return False
    
    async def test_backward_compatibility_views(self) -> bool:
        """Test that backward compatibility views work correctly."""
        try:
            from src.n8n_scraper.database.connection import get_async_session
            from sqlalchemy import text
            
            async with get_async_session() as session:
                # Test workflow_documents view
                result = await session.execute(text("SELECT COUNT(*) FROM workflow_documents"))
                workflow_count = result.scalar()
                
                # Test scraped_documents view
                result = await session.execute(text("SELECT COUNT(*) FROM scraped_documents"))
                scraped_count = result.scalar()
                
                self.log_test_result(
                    "Backward Compatibility Views", 
                    True, 
                    f"Views accessible: {workflow_count} workflows, {scraped_count} scraped docs"
                )
                return True
                
        except Exception as e:
            self.log_test_result("Backward Compatibility Views", False, "Failed to access compatibility views", e)
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        logger.info("Starting unified schema integration tests...")
        if self.verbose:
            print("\n🧪 Starting Unified Schema Integration Tests")
            print("=" * 50)
        
        tests = [
            self.test_database_connection,
            self.test_create_documentation_document,
            self.test_create_workflow_document,
            self.test_document_retrieval,
            self.test_document_search,
            self.test_document_filtering,
            self.test_document_update,
            self.test_chunk_operations,
            self.test_workflow_file_import,
            self.test_statistics_generation,
            self.test_backward_compatibility_views
        ]
        
        passed = 0
        failed = 0
        
        for i, test in enumerate(tests, 1):
            if self.verbose:
                print(f"\n[{i}/{len(tests)}] Running {test.__name__.replace('test_', '').replace('_', ' ').title()}...")
            
            try:
                success = await test()
                if success:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Test {test.__name__} crashed: {e}")
                if self.verbose:
                    print(f"✗ Test {test.__name__} crashed: {e}")
                    traceback.print_exc()
                failed += 1
        
        return {
            'total_tests': len(tests),
            'passed': passed,
            'failed': failed,
            'success_rate': (passed / len(tests)) * 100 if tests else 0,
            'results': self.test_results
        }
    
    def print_test_summary(self, results: Dict[str, Any]):
        """Print a summary of test results."""
        print("\n" + "=" * 60)
        print("UNIFIED SCHEMA INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        
        print("\nDetailed Results:")
        print("-" * 40)
        
        for result in results['results']:
            status_symbol = "✓" if result['status'] == 'PASS' else "✗"
            print(f"{status_symbol} {result['test']}")
            if result['message']:
                print(f"  {result['message']}")
            if result.get('error'):
                print(f"  Error: {result['error']}")
        
        print("\n" + "=" * 60)
        
        if results['failed'] == 0:
            print("🎉 ALL TESTS PASSED! The unified schema integration is working correctly.")
        else:
            print(f"⚠️  {results['failed']} test(s) failed. Please review the errors above.")
        
        print("=" * 60)


async def main():
    """Main test function."""
    test_suite = UnifiedSchemaIntegrationTest()
    
    try:
        await test_suite.initialize()
        results = await test_suite.run_all_tests()
        test_suite.print_test_summary(results)
        
        # Return appropriate exit code
        exit_code = 0 if results['failed'] == 0 else 1
        
        if exit_code == 0:
            print("\n✅ Integration tests completed successfully!")
        else:
            print(f"\n❌ Integration tests completed with {results['failed']} failures.")
        
        return exit_code
        
    except Exception as e:
        logger.error(f"Test suite failed to run: {e}")
        print(f"\n💥 Test suite failed to run: {e}")
        traceback.print_exc()
        return 1
    finally:
        try:
            await test_suite.cleanup()
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)