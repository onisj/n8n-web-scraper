"""Performance tests for the n8n scraper application.

These tests validate system performance under various load conditions
including API endpoints, search functionality, and database operations.
"""

import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable
from unittest.mock import patch, Mock
import psutil
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.n8n_scraper.api.main import app
from src.n8n_scraper.search.search_service import SearchService
from src.n8n_scraper.database.connection import DatabaseManager
from src.n8n_scraper.config import settings


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    response_times: List[float]
    success_rate: float
    throughput: float
    error_count: int
    memory_usage: float
    cpu_usage: float
    
    @property
    def avg_response_time(self) -> float:
        return statistics.mean(self.response_times) if self.response_times else 0
    
    @property
    def p95_response_time(self) -> float:
        return statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) >= 20 else 0
    
    @property
    def p99_response_time(self) -> float:
        return statistics.quantiles(self.response_times, n=100)[98] if len(self.response_times) >= 100 else 0


class PerformanceTestBase:
    """Base class for performance tests."""
    
    def __init__(self):
        self.client = TestClient(app)
        self.metrics = PerformanceMetrics(
            response_times=[],
            success_rate=0.0,
            throughput=0.0,
            error_count=0,
            memory_usage=0.0,
            cpu_usage=0.0
        )
    
    def measure_performance(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Measure performance of a function call."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        start_cpu = psutil.Process().cpu_percent()
        
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        end_cpu = psutil.Process().cpu_percent()
        
        return {
            "result": result,
            "success": success,
            "error": error,
            "response_time": end_time - start_time,
            "memory_delta": end_memory - start_memory,
            "cpu_usage": (start_cpu + end_cpu) / 2
        }
    
    def run_load_test(self, func: Callable, num_requests: int, 
                     concurrent_users: int = 1, *args, **kwargs) -> PerformanceMetrics:
        """Run load test with specified parameters."""
        results = []
        start_time = time.time()
        
        if concurrent_users == 1:
            # Sequential execution
            for _ in range(num_requests):
                result = self.measure_performance(func, *args, **kwargs)
                results.append(result)
        else:
            # Concurrent execution
            with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = []
                for _ in range(num_requests):
                    future = executor.submit(self.measure_performance, func, *args, **kwargs)
                    futures.append(future)
                
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate metrics
        response_times = [r["response_time"] for r in results]
        successful_requests = [r for r in results if r["success"]]
        error_count = len([r for r in results if not r["success"]])
        
        metrics = PerformanceMetrics(
            response_times=response_times,
            success_rate=len(successful_requests) / len(results) * 100,
            throughput=len(successful_requests) / total_time,
            error_count=error_count,
            memory_usage=statistics.mean([r["memory_delta"] for r in results]),
            cpu_usage=statistics.mean([r["cpu_usage"] for r in results])
        )
        
        return metrics


class TestAPIPerformance(PerformanceTestBase):
    """Performance tests for API endpoints."""
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers for testing."""
        return {"Authorization": "Bearer test_token"}
    
    def test_health_endpoint_performance(self):
        """Test health endpoint performance under load."""
        def make_health_request():
            response = self.client.get("/api/v1/health")
            assert response.status_code == 200
            return response
        
        # Test with increasing load
        load_scenarios = [
            {"requests": 100, "concurrent": 1},
            {"requests": 100, "concurrent": 10},
            {"requests": 100, "concurrent": 50},
        ]
        
        for scenario in load_scenarios:
            metrics = self.run_load_test(
                make_health_request,
                scenario["requests"],
                scenario["concurrent"]
            )
            
            # Performance assertions
            assert metrics.success_rate >= 99.0, f"Success rate too low: {metrics.success_rate}%"
            assert metrics.avg_response_time < 0.1, f"Average response time too high: {metrics.avg_response_time}s"
            assert metrics.p95_response_time < 0.2, f"P95 response time too high: {metrics.p95_response_time}s"
            assert metrics.throughput > 100, f"Throughput too low: {metrics.throughput} req/s"
    
    def test_search_endpoint_performance(self, auth_headers):
        """Test search endpoint performance."""
        search_queries = [
            "automation workflow",
            "webhook integration",
            "API documentation",
            "n8n tutorial",
            "data processing"
        ]
        
        def make_search_request():
            query = search_queries[int(time.time() * 1000) % len(search_queries)]
            response = self.client.get(
                f"/api/v1/search?query={query}&limit=10",
                headers=auth_headers
            )
            return response
        
        with patch('src.n8n_scraper.search.search_service.search_documents') as mock_search:
            mock_search.return_value = {
                "results": [{"id": f"doc{i}", "score": 0.9} for i in range(10)],
                "total": 100,
                "query": "test"
            }
            
            metrics = self.run_load_test(make_search_request, 50, 10)
            
            # Performance assertions for search
            assert metrics.success_rate >= 95.0
            assert metrics.avg_response_time < 0.5  # Search can be slower
            assert metrics.p95_response_time < 1.0
    
    def test_chat_endpoint_performance(self, auth_headers):
        """Test chat endpoint performance."""
        chat_messages = [
            "How do I create an automation?",
            "What is a webhook?",
            "How to integrate with APIs?",
            "Explain n8n workflows",
            "Help with data transformation"
        ]
        
        def make_chat_request():
            message = chat_messages[int(time.time() * 1000) % len(chat_messages)]
            response = self.client.post(
                "/api/v1/chat",
                json={"message": message, "model": "gpt-3.5-turbo"},
                headers=auth_headers
            )
            return response
        
        with patch('src.n8n_scraper.chat.chat_service.generate_response') as mock_chat:
            mock_chat.return_value = {
                "response": "This is a test response",
                "sources": ["doc1"],
                "model": "gpt-3.5-turbo"
            }
            
            metrics = self.run_load_test(make_chat_request, 20, 5)
            
            # Chat endpoints can be slower due to AI processing
            assert metrics.success_rate >= 90.0
            assert metrics.avg_response_time < 2.0
            assert metrics.p95_response_time < 5.0
    
    def test_document_retrieval_performance(self, auth_headers):
        """Test document retrieval performance."""
        document_ids = [f"doc{i}" for i in range(1, 21)]
        
        def make_document_request():
            doc_id = document_ids[int(time.time() * 1000) % len(document_ids)]
            response = self.client.get(
                f"/api/v1/documents/{doc_id}",
                headers=auth_headers
            )
            return response
        
        with patch('src.n8n_scraper.database.document_service.get_document') as mock_get_doc:
            mock_get_doc.return_value = {
                "id": "doc1",
                "title": "Test Document",
                "content": "Test content"
            }
            
            metrics = self.run_load_test(make_document_request, 100, 20)
            
            assert metrics.success_rate >= 99.0
            assert metrics.avg_response_time < 0.05
            assert metrics.throughput > 200
    
    def test_authentication_performance(self):
        """Test authentication endpoint performance."""
        def make_login_request():
            response = self.client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "password"}
            )
            return response
        
        with patch('src.n8n_scraper.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "email": "test@example.com"}
            
            metrics = self.run_load_test(make_login_request, 50, 10)
            
            assert metrics.success_rate >= 95.0
            assert metrics.avg_response_time < 0.2
    
    def test_concurrent_user_simulation(self, auth_headers):
        """Test system behavior with concurrent users performing mixed operations."""
        operations = [
            lambda: self.client.get("/api/v1/health"),
            lambda: self.client.get("/api/v1/search?query=test", headers=auth_headers),
            lambda: self.client.get("/api/v1/documents/doc1", headers=auth_headers),
            lambda: self.client.post("/api/v1/chat", json={"message": "test"}, headers=auth_headers)
        ]
        
        def simulate_user_session():
            """Simulate a user session with multiple operations."""
            session_results = []
            for _ in range(5):  # 5 operations per session
                operation = operations[int(time.time() * 1000) % len(operations)]
                result = self.measure_performance(operation)
                session_results.append(result)
                time.sleep(0.1)  # Small delay between operations
            return session_results
        
        with patch('src.n8n_scraper.search.search_service.search_documents') as mock_search:
            with patch('src.n8n_scraper.chat.chat_service.generate_response') as mock_chat:
                with patch('src.n8n_scraper.database.document_service.get_document') as mock_doc:
                    mock_search.return_value = {"results": [], "total": 0}
                    mock_chat.return_value = {"response": "test", "sources": []}
                    mock_doc.return_value = {"id": "doc1", "title": "Test"}
                    
                    # Simulate 20 concurrent users
                    with ThreadPoolExecutor(max_workers=20) as executor:
                        futures = [executor.submit(simulate_user_session) for _ in range(20)]
                        all_results = []
                        
                        for future in as_completed(futures):
                            session_results = future.result()
                            all_results.extend(session_results)
                    
                    # Analyze overall system performance
                    successful_ops = [r for r in all_results if r["success"]]
                    success_rate = len(successful_ops) / len(all_results) * 100
                    avg_response_time = statistics.mean([r["response_time"] for r in all_results])
                    
                    assert success_rate >= 90.0
                    assert avg_response_time < 1.0


class TestSearchPerformance(PerformanceTestBase):
    """Performance tests for search functionality."""
    
    @pytest.fixture
    def mock_search_service(self):
        """Mock search service for testing."""
        service = Mock(spec=SearchService)
        service.vector_search.return_value = [
            {"id": f"doc{i}", "score": 0.9 - i * 0.1} for i in range(10)
        ]
        service.text_search.return_value = [
            {"id": f"doc{i}", "score": 0.8 - i * 0.1} for i in range(10)
        ]
        return service
    
    def test_vector_search_performance(self, mock_search_service):
        """Test vector search performance."""
        queries = [
            "automation workflow setup",
            "webhook integration guide",
            "API documentation examples",
            "data transformation tutorial",
            "n8n node configuration"
        ]
        
        def perform_vector_search():
            query = queries[int(time.time() * 1000) % len(queries)]
            return mock_search_service.vector_search(query, limit=20)
        
        metrics = self.run_load_test(perform_vector_search, 100, 10)
        
        assert metrics.success_rate >= 99.0
        assert metrics.avg_response_time < 0.1
        assert metrics.throughput > 50
    
    def test_text_search_performance(self, mock_search_service):
        """Test text search performance."""
        def perform_text_search():
            return mock_search_service.text_search("test query", limit=20)
        
        metrics = self.run_load_test(perform_text_search, 100, 10)
        
        assert metrics.success_rate >= 99.0
        assert metrics.avg_response_time < 0.05
        assert metrics.throughput > 100
    
    def test_hybrid_search_performance(self, mock_search_service):
        """Test hybrid search performance."""
        mock_search_service.hybrid_search.return_value = [
            {"id": f"doc{i}", "combined_score": 0.9 - i * 0.1} for i in range(10)
        ]
        
        def perform_hybrid_search():
            return mock_search_service.hybrid_search("test query")
        
        metrics = self.run_load_test(perform_hybrid_search, 50, 5)
        
        # Hybrid search can be slower as it combines multiple search types
        assert metrics.success_rate >= 95.0
        assert metrics.avg_response_time < 0.2
    
    def test_search_with_large_result_sets(self, mock_search_service):
        """Test search performance with large result sets."""
        # Mock large result set
        large_results = [{"id": f"doc{i}", "score": 0.9} for i in range(1000)]
        mock_search_service.vector_search.return_value = large_results
        
        def perform_large_search():
            return mock_search_service.vector_search("test", limit=1000)
        
        metrics = self.run_load_test(perform_large_search, 10, 2)
        
        assert metrics.success_rate >= 95.0
        assert metrics.avg_response_time < 0.5
    
    def test_concurrent_search_operations(self, mock_search_service):
        """Test concurrent search operations."""
        search_types = [
            lambda: mock_search_service.vector_search("test"),
            lambda: mock_search_service.text_search("test"),
            lambda: mock_search_service.hybrid_search("test")
        ]
        
        def perform_mixed_search():
            search_func = search_types[int(time.time() * 1000) % len(search_types)]
            return search_func()
        
        metrics = self.run_load_test(perform_mixed_search, 60, 20)
        
        assert metrics.success_rate >= 90.0
        assert metrics.avg_response_time < 0.3


class TestDatabasePerformance(PerformanceTestBase):
    """Performance tests for database operations."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager for testing."""
        manager = Mock(spec=DatabaseManager)
        manager.get_document.return_value = {
            "id": "doc1",
            "title": "Test Document",
            "content": "Test content"
        }
        manager.list_documents.return_value = {
            "documents": [{"id": f"doc{i}"} for i in range(20)],
            "total": 100
        }
        return manager
    
    def test_document_retrieval_performance(self, mock_db_manager):
        """Test document retrieval performance."""
        def get_document():
            return mock_db_manager.get_document("doc1")
        
        metrics = self.run_load_test(get_document, 200, 20)
        
        assert metrics.success_rate >= 99.0
        assert metrics.avg_response_time < 0.01
        assert metrics.throughput > 500
    
    def test_document_listing_performance(self, mock_db_manager):
        """Test document listing performance."""
        def list_documents():
            return mock_db_manager.list_documents(limit=20, offset=0)
        
        metrics = self.run_load_test(list_documents, 100, 10)
        
        assert metrics.success_rate >= 99.0
        assert metrics.avg_response_time < 0.05
        assert metrics.throughput > 100
    
    def test_bulk_operations_performance(self, mock_db_manager):
        """Test bulk database operations performance."""
        document_ids = [f"doc{i}" for i in range(100)]
        mock_db_manager.get_documents_by_ids.return_value = [
            {"id": doc_id, "title": f"Document {doc_id}"} for doc_id in document_ids
        ]
        
        def bulk_get_documents():
            return mock_db_manager.get_documents_by_ids(document_ids[:50])
        
        metrics = self.run_load_test(bulk_get_documents, 20, 5)
        
        assert metrics.success_rate >= 95.0
        assert metrics.avg_response_time < 0.1
    
    def test_connection_pool_performance(self, mock_db_manager):
        """Test database connection pool performance under load."""
        def db_operation():
            # Simulate various database operations
            operations = [
                lambda: mock_db_manager.get_document("doc1"),
                lambda: mock_db_manager.list_documents(limit=10),
                lambda: mock_db_manager.search_documents("test")
            ]
            op = operations[int(time.time() * 1000) % len(operations)]
            return op()
        
        # Test with high concurrency to stress connection pool
        metrics = self.run_load_test(db_operation, 100, 50)
        
        assert metrics.success_rate >= 90.0
        assert metrics.avg_response_time < 0.1


class TestMemoryPerformance(PerformanceTestBase):
    """Performance tests for memory usage."""
    
    def test_memory_usage_under_load(self):
        """Test memory usage under sustained load."""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        def memory_intensive_operation():
            # Simulate memory-intensive operation
            large_data = [f"data_{i}" * 1000 for i in range(1000)]
            processed = [item.upper() for item in large_data]
            return len(processed)
        
        # Run operations and monitor memory
        memory_samples = []
        for i in range(50):
            memory_intensive_operation()
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            
            if i % 10 == 0:  # Check every 10 operations
                time.sleep(0.1)  # Allow garbage collection
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 100MB for this test)
        assert memory_growth < 100, f"Memory growth too high: {memory_growth}MB"
        
        # Memory usage should stabilize (not continuously growing)
        recent_memory = statistics.mean(memory_samples[-10:])
        early_memory = statistics.mean(memory_samples[:10])
        growth_rate = (recent_memory - early_memory) / early_memory
        
        assert growth_rate < 0.5, f"Memory growth rate too high: {growth_rate * 100}%"
    
    def test_garbage_collection_efficiency(self):
        """Test garbage collection efficiency."""
        import gc
        
        initial_objects = len(gc.get_objects())
        
        def create_temporary_objects():
            temp_objects = []
            for i in range(1000):
                temp_objects.append({"id": i, "data": f"temp_data_{i}" * 100})
            return len(temp_objects)
        
        # Create and destroy objects multiple times
        for _ in range(10):
            create_temporary_objects()
            gc.collect()  # Force garbage collection
        
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects
        
        # Object count should not grow significantly
        assert object_growth < 1000, f"Too many objects not garbage collected: {object_growth}"


class TestConcurrencyPerformance(PerformanceTestBase):
    """Performance tests for concurrency handling."""
    
    def test_thread_safety_performance(self):
        """Test thread safety under concurrent access."""
        shared_counter = {"value": 0}
        lock = threading.Lock()
        
        def thread_safe_increment():
            with lock:
                current = shared_counter["value"]
                time.sleep(0.001)  # Simulate some processing
                shared_counter["value"] = current + 1
            return shared_counter["value"]
        
        # Run concurrent increments
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(thread_safe_increment) for _ in range(100)]
            results = [future.result() for future in as_completed(futures)]
        
        # Final value should be exactly 100 (no race conditions)
        assert shared_counter["value"] == 100
        assert len(set(results)) == 100  # All results should be unique
    
    def test_async_performance(self):
        """Test async operation performance."""
        async def async_operation(delay: float = 0.01):
            await asyncio.sleep(delay)
            return f"completed_{time.time()}"
        
        async def run_concurrent_async_ops():
            tasks = [async_operation() for _ in range(100)]
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            return results, end_time - start_time
        
        # Run async operations
        results, duration = asyncio.run(run_concurrent_async_ops())
        
        assert len(results) == 100
        # Should complete much faster than sequential execution (100 * 0.01 = 1s)
        assert duration < 0.5, f"Async operations too slow: {duration}s"
    
    def test_resource_contention(self):
        """Test performance under resource contention."""
        shared_resource = {"data": []}
        resource_lock = threading.Lock()
        
        def contended_operation(worker_id: int):
            results = []
            for i in range(10):
                with resource_lock:
                    # Simulate resource access
                    shared_resource["data"].append(f"worker_{worker_id}_item_{i}")
                    time.sleep(0.001)  # Simulate processing time
                results.append(f"worker_{worker_id}_completed_{i}")
            return results
        
        start_time = time.time()
        
        # Run with high contention
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(contended_operation, i) for i in range(20)]
            all_results = []
            for future in as_completed(futures):
                worker_results = future.result()
                all_results.extend(worker_results)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify correctness
        assert len(shared_resource["data"]) == 200  # 20 workers * 10 items
        assert len(all_results) == 200
        
        # Performance should be reasonable despite contention
        assert duration < 5.0, f"Resource contention caused excessive delay: {duration}s"


class TestScalabilityPerformance(PerformanceTestBase):
    """Performance tests for scalability."""
    
    def test_linear_scalability(self):
        """Test if performance scales linearly with load."""
        def simple_operation():
            # Simple CPU-bound operation
            result = sum(i * i for i in range(1000))
            return result
        
        # Test with different load levels
        load_levels = [10, 20, 50, 100]
        throughputs = []
        
        for load in load_levels:
            metrics = self.run_load_test(simple_operation, load, 1)
            throughputs.append(metrics.throughput)
        
        # Throughput should scale reasonably with load
        # (allowing for some overhead and system limitations)
        for i in range(1, len(throughputs)):
            ratio = throughputs[i] / throughputs[0]
            expected_ratio = load_levels[i] / load_levels[0]
            
            # Allow 50% deviation from perfect linear scaling
            assert ratio > expected_ratio * 0.5, f"Poor scalability at load {load_levels[i]}"
    
    def test_breaking_point_analysis(self):
        """Test to find system breaking point."""
        def stress_operation():
            # Moderately intensive operation
            data = [i for i in range(10000)]
            processed = [x * 2 for x in data if x % 2 == 0]
            return len(processed)
        
        # Gradually increase load until performance degrades
        concurrent_levels = [1, 5, 10, 20, 50, 100]
        performance_data = []
        
        for concurrent in concurrent_levels:
            try:
                metrics = self.run_load_test(stress_operation, 50, concurrent)
                performance_data.append({
                    "concurrent": concurrent,
                    "throughput": metrics.throughput,
                    "avg_response_time": metrics.avg_response_time,
                    "success_rate": metrics.success_rate
                })
            except Exception as e:
                # System reached breaking point
                performance_data.append({
                    "concurrent": concurrent,
                    "throughput": 0,
                    "avg_response_time": float('inf'),
                    "success_rate": 0,
                    "error": str(e)
                })
                break
        
        # Analyze performance degradation
        peak_throughput = max(data["throughput"] for data in performance_data)
        acceptable_performance = [data for data in performance_data 
                                if data["success_rate"] >= 95 and data["throughput"] >= peak_throughput * 0.8]
        
        # System should handle at least 10 concurrent operations effectively
        max_acceptable_concurrent = max(data["concurrent"] for data in acceptable_performance)
        assert max_acceptable_concurrent >= 10, f"System breaks down too early: {max_acceptable_concurrent}"


@pytest.mark.performance
class TestEndToEndPerformance(PerformanceTestBase):
    """End-to-end performance tests."""
    
    def test_complete_user_workflow_performance(self):
        """Test performance of complete user workflows."""
        def complete_workflow():
            """Simulate a complete user workflow."""
            workflow_steps = []
            
            # Step 1: Health check
            start = time.time()
            health_response = self.client.get("/api/v1/health")
            workflow_steps.append({"step": "health", "time": time.time() - start, "success": health_response.status_code == 200})
            
            # Step 2: Authentication (mocked)
            start = time.time()
            with patch('src.n8n_scraper.auth.auth_service.authenticate_user') as mock_auth:
                mock_auth.return_value = {"id": "user1", "email": "test@example.com"}
                auth_response = self.client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "password"})
                workflow_steps.append({"step": "auth", "time": time.time() - start, "success": auth_response.status_code == 200})
            
            # Step 3: Search (mocked)
            start = time.time()
            with patch('src.n8n_scraper.search.search_service.search_documents') as mock_search:
                mock_search.return_value = {"results": [{"id": "doc1"}], "total": 1}
                search_response = self.client.get("/api/v1/search?query=test", headers={"Authorization": "Bearer token"})
                workflow_steps.append({"step": "search", "time": time.time() - start, "success": search_response.status_code == 200})
            
            # Step 4: Get document (mocked)
            start = time.time()
            with patch('src.n8n_scraper.database.document_service.get_document') as mock_doc:
                mock_doc.return_value = {"id": "doc1", "title": "Test"}
                doc_response = self.client.get("/api/v1/documents/doc1", headers={"Authorization": "Bearer token"})
                workflow_steps.append({"step": "document", "time": time.time() - start, "success": doc_response.status_code == 200})
            
            # Step 5: Chat (mocked)
            start = time.time()
            with patch('src.n8n_scraper.chat.chat_service.generate_response') as mock_chat:
                mock_chat.return_value = {"response": "Test response", "sources": []}
                chat_response = self.client.post("/api/v1/chat", json={"message": "test"}, headers={"Authorization": "Bearer token"})
                workflow_steps.append({"step": "chat", "time": time.time() - start, "success": chat_response.status_code == 200})
            
            return workflow_steps
        
        # Run complete workflows
        metrics = self.run_load_test(complete_workflow, 10, 3)
        
        assert metrics.success_rate >= 90.0
        assert metrics.avg_response_time < 2.0  # Complete workflow should finish in 2 seconds
    
    def test_system_stability_under_sustained_load(self):
        """Test system stability under sustained load over time."""
        def mixed_operations():
            operations = [
                lambda: self.client.get("/api/v1/health"),
                lambda: self.client.get("/api/v1/search?query=test", headers={"Authorization": "Bearer token"}),
            ]
            
            with patch('src.n8n_scraper.search.search_service.search_documents') as mock_search:
                mock_search.return_value = {"results": [], "total": 0}
                
                op = operations[int(time.time() * 1000) % len(operations)]
                return op()
        
        # Run sustained load for 30 seconds
        start_time = time.time()
        results = []
        
        while time.time() - start_time < 30:  # 30 seconds
            batch_metrics = self.run_load_test(mixed_operations, 20, 5)
            results.append({
                "timestamp": time.time(),
                "success_rate": batch_metrics.success_rate,
                "avg_response_time": batch_metrics.avg_response_time,
                "throughput": batch_metrics.throughput
            })
            time.sleep(1)  # 1 second between batches
        
        # Analyze stability
        success_rates = [r["success_rate"] for r in results]
        response_times = [r["avg_response_time"] for r in results]
        throughputs = [r["throughput"] for r in results]
        
        # System should maintain stable performance
        assert min(success_rates) >= 90.0, "Success rate dropped too low during sustained load"
        assert max(response_times) < 1.0, "Response time spiked too high during sustained load"
        
        # Performance should not degrade significantly over time
        early_throughput = statistics.mean(throughputs[:5])
        late_throughput = statistics.mean(throughputs[-5:])
        degradation = (early_throughput - late_throughput) / early_throughput
        
        assert degradation < 0.3, f"Performance degraded too much over time: {degradation * 100}%"


if __name__ == "__main__":
    # Run performance tests
    pytest.main(["-v", "-m", "performance", __file__])