"""Unit tests for search service.

These tests validate the search functionality including
vector search, text search, and search result processing.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List, Dict, Any
from datetime import datetime
import numpy as np

from src.n8n_scraper.search.search_service import SearchService
from src.n8n_scraper.search.vector_search import VectorSearchEngine
from src.n8n_scraper.search.text_search import TextSearchEngine
from src.n8n_scraper.database.models import Document, SearchResult
from src.n8n_scraper.config import settings


class TestSearchService:
    """Test suite for SearchService."""

    @pytest.fixture
    def mock_vector_engine(self):
        """Mock vector search engine."""
        engine = Mock(spec=VectorSearchEngine)
        engine.search.return_value = [
            {
                "id": "doc1",
                "score": 0.95,
                "content": "Test content 1",
                "metadata": {"category": "tutorial"}
            },
            {
                "id": "doc2",
                "score": 0.87,
                "content": "Test content 2",
                "metadata": {"category": "guide"}
            }
        ]
        return engine

    @pytest.fixture
    def mock_text_engine(self):
        """Mock text search engine."""
        engine = Mock(spec=TextSearchEngine)
        engine.search.return_value = [
            {
                "id": "doc1",
                "score": 0.92,
                "content": "Test content 1",
                "highlights": ["<em>test</em> content"]
            },
            {
                "id": "doc3",
                "score": 0.78,
                "content": "Test content 3",
                "highlights": ["<em>test</em> content"]
            }
        ]
        return engine

    @pytest.fixture
    def mock_database(self):
        """Mock database connection."""
        db = Mock()
        db.get_documents_by_ids.return_value = [
            {
                "id": "doc1",
                "title": "Test Document 1",
                "content": "Test content 1",
                "url": "https://example.com/doc1",
                "category": "tutorial",
                "tags": ["test", "api"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "id": "doc2",
                "title": "Test Document 2",
                "content": "Test content 2",
                "url": "https://example.com/doc2",
                "category": "guide",
                "tags": ["test", "integration"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        return db

    @pytest.fixture
    def search_service(self, mock_vector_engine, mock_text_engine, mock_database):
        """Create SearchService instance with mocked dependencies."""
        service = SearchService(
            vector_engine=mock_vector_engine,
            text_engine=mock_text_engine,
            database=mock_database
        )
        return service

    def test_vector_search_basic(self, search_service, mock_vector_engine):
        """Test basic vector search functionality."""
        query = "test automation"
        limit = 10
        
        results = search_service.vector_search(query, limit=limit)
        
        mock_vector_engine.search.assert_called_once_with(query, limit=limit)
        assert len(results) == 2
        assert results[0]["score"] == 0.95
        assert results[1]["score"] == 0.87

    def test_vector_search_with_filters(self, search_service, mock_vector_engine):
        """Test vector search with category and tag filters."""
        query = "test automation"
        filters = {
            "category": "tutorial",
            "tags": ["api", "test"]
        }
        
        results = search_service.vector_search(query, filters=filters)
        
        mock_vector_engine.search.assert_called_once_with(
            query, 
            limit=20, 
            filters=filters
        )
        assert len(results) == 2

    def test_text_search_basic(self, search_service, mock_text_engine):
        """Test basic text search functionality."""
        query = "test content"
        limit = 10
        
        results = search_service.text_search(query, limit=limit)
        
        mock_text_engine.search.assert_called_once_with(query, limit=limit)
        assert len(results) == 2
        assert "highlights" in results[0]

    def test_text_search_with_boost(self, search_service, mock_text_engine):
        """Test text search with field boosting."""
        query = "test content"
        boost_fields = {"title": 2.0, "content": 1.0}
        
        results = search_service.text_search(query, boost_fields=boost_fields)
        
        mock_text_engine.search.assert_called_once_with(
            query, 
            limit=20, 
            boost_fields=boost_fields
        )
        assert len(results) == 2

    def test_hybrid_search(self, search_service, mock_vector_engine, mock_text_engine):
        """Test hybrid search combining vector and text search."""
        query = "test automation"
        
        results = search_service.hybrid_search(query)
        
        # Both engines should be called
        mock_vector_engine.search.assert_called_once()
        mock_text_engine.search.assert_called_once()
        
        # Results should be merged and deduplicated
        assert len(results) >= 2
        
        # Check that scores are properly combined
        for result in results:
            assert "combined_score" in result
            assert result["combined_score"] > 0

    def test_hybrid_search_score_combination(self, search_service):
        """Test score combination in hybrid search."""
        # Mock different results from vector and text search
        with patch.object(search_service, 'vector_search') as mock_vector:
            with patch.object(search_service, 'text_search') as mock_text:
                mock_vector.return_value = [
                    {"id": "doc1", "score": 0.9, "content": "content1"}
                ]
                mock_text.return_value = [
                    {"id": "doc1", "score": 0.8, "content": "content1"}
                ]
                
                results = search_service.hybrid_search("test")
                
                assert len(results) == 1
                # Combined score should be weighted average
                expected_score = (0.9 * 0.7) + (0.8 * 0.3)  # Default weights
                assert abs(results[0]["combined_score"] - expected_score) < 0.01

    def test_search_with_pagination(self, search_service, mock_vector_engine):
        """Test search with pagination parameters."""
        query = "test"
        limit = 5
        offset = 10
        
        results = search_service.vector_search(query, limit=limit, offset=offset)
        
        mock_vector_engine.search.assert_called_once_with(
            query, 
            limit=limit, 
            offset=offset
        )

    def test_search_result_enrichment(self, search_service, mock_database):
        """Test enrichment of search results with document metadata."""
        raw_results = [
            {"id": "doc1", "score": 0.9},
            {"id": "doc2", "score": 0.8}
        ]
        
        enriched = search_service.enrich_results(raw_results)
        
        mock_database.get_documents_by_ids.assert_called_once_with(["doc1", "doc2"])
        
        assert len(enriched) == 2
        assert enriched[0]["title"] == "Test Document 1"
        assert enriched[0]["url"] == "https://example.com/doc1"
        assert enriched[0]["score"] == 0.9

    def test_search_result_filtering(self, search_service):
        """Test filtering of search results."""
        results = [
            {"id": "doc1", "score": 0.9, "category": "tutorial"},
            {"id": "doc2", "score": 0.8, "category": "guide"},
            {"id": "doc3", "score": 0.7, "category": "tutorial"}
        ]
        
        filters = {"category": "tutorial"}
        filtered = search_service.filter_results(results, filters)
        
        assert len(filtered) == 2
        assert all(result["category"] == "tutorial" for result in filtered)

    def test_search_result_sorting(self, search_service):
        """Test sorting of search results."""
        results = [
            {"id": "doc1", "score": 0.7, "created_at": "2024-01-01"},
            {"id": "doc2", "score": 0.9, "created_at": "2024-01-02"},
            {"id": "doc3", "score": 0.8, "created_at": "2024-01-03"}
        ]
        
        # Sort by score (default)
        sorted_by_score = search_service.sort_results(results, "score")
        assert sorted_by_score[0]["score"] == 0.9
        assert sorted_by_score[1]["score"] == 0.8
        assert sorted_by_score[2]["score"] == 0.7
        
        # Sort by date
        sorted_by_date = search_service.sort_results(results, "created_at")
        assert sorted_by_date[0]["created_at"] == "2024-01-03"

    def test_search_suggestions(self, search_service):
        """Test search suggestion generation."""
        query = "test"
        
        with patch.object(search_service, '_get_popular_queries') as mock_popular:
            with patch.object(search_service, '_get_related_terms') as mock_related:
                mock_popular.return_value = ["test automation", "test api"]
                mock_related.return_value = ["testing", "tests"]
                
                suggestions = search_service.get_suggestions(query)
                
                assert len(suggestions) > 0
                assert "test automation" in suggestions
                assert "testing" in suggestions

    def test_search_analytics_tracking(self, search_service):
        """Test search analytics tracking."""
        query = "test query"
        user_id = "user123"
        
        with patch.object(search_service, '_track_search') as mock_track:
            search_service.vector_search(query, user_id=user_id)
            
            mock_track.assert_called_once_with(
                query=query,
                user_id=user_id,
                search_type="vector",
                result_count=2
            )

    def test_search_caching(self, search_service):
        """Test search result caching."""
        query = "cached query"
        
        with patch.object(search_service, '_get_cached_results') as mock_get_cache:
            with patch.object(search_service, '_cache_results') as mock_set_cache:
                # First call - cache miss
                mock_get_cache.return_value = None
                results1 = search_service.vector_search(query)
                
                mock_set_cache.assert_called_once()
                
                # Second call - cache hit
                cached_results = [{"id": "cached1", "score": 0.9}]
                mock_get_cache.return_value = cached_results
                results2 = search_service.vector_search(query)
                
                assert results2 == cached_results

    def test_search_error_handling(self, search_service, mock_vector_engine):
        """Test error handling in search operations."""
        query = "test query"
        
        # Test vector search engine failure
        mock_vector_engine.search.side_effect = Exception("Vector search failed")
        
        with pytest.raises(Exception) as exc_info:
            search_service.vector_search(query)
        
        assert "Vector search failed" in str(exc_info.value)

    def test_search_with_empty_query(self, search_service):
        """Test search behavior with empty query."""
        empty_queries = ["", "   ", None]
        
        for query in empty_queries:
            with pytest.raises(ValueError) as exc_info:
                search_service.vector_search(query)
            
            assert "Query cannot be empty" in str(exc_info.value)

    def test_search_result_deduplication(self, search_service):
        """Test deduplication of search results."""
        results_with_duplicates = [
            {"id": "doc1", "score": 0.9},
            {"id": "doc2", "score": 0.8},
            {"id": "doc1", "score": 0.85},  # Duplicate
            {"id": "doc3", "score": 0.7}
        ]
        
        deduplicated = search_service.deduplicate_results(results_with_duplicates)
        
        assert len(deduplicated) == 3
        # Should keep the result with higher score
        doc1_result = next(r for r in deduplicated if r["id"] == "doc1")
        assert doc1_result["score"] == 0.9

    def test_search_performance_monitoring(self, search_service):
        """Test performance monitoring for search operations."""
        query = "performance test"
        
        with patch.object(search_service, '_log_performance') as mock_log:
            search_service.vector_search(query)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]
            assert "query" in call_args
            assert "duration" in call_args
            assert "result_count" in call_args

    def test_search_with_custom_weights(self, search_service):
        """Test hybrid search with custom weight configuration."""
        query = "test"
        custom_weights = {"vector": 0.8, "text": 0.2}
        
        with patch.object(search_service, 'vector_search') as mock_vector:
            with patch.object(search_service, 'text_search') as mock_text:
                mock_vector.return_value = [{"id": "doc1", "score": 0.9}]
                mock_text.return_value = [{"id": "doc1", "score": 0.7}]
                
                results = search_service.hybrid_search(query, weights=custom_weights)
                
                expected_score = (0.9 * 0.8) + (0.7 * 0.2)
                assert abs(results[0]["combined_score"] - expected_score) < 0.01

    def test_search_result_highlighting(self, search_service):
        """Test search result highlighting functionality."""
        query = "test automation"
        content = "This is a test document about automation workflows."
        
        highlighted = search_service.highlight_content(content, query)
        
        assert "<em>test</em>" in highlighted
        assert "<em>automation</em>" in highlighted

    def test_search_faceted_results(self, search_service):
        """Test faceted search results."""
        query = "test"
        
        results = [
            {"id": "doc1", "category": "tutorial", "tags": ["api", "test"]},
            {"id": "doc2", "category": "guide", "tags": ["test", "integration"]},
            {"id": "doc3", "category": "tutorial", "tags": ["webhook", "test"]}
        ]
        
        facets = search_service.generate_facets(results)
        
        assert "category" in facets
        assert facets["category"]["tutorial"] == 2
        assert facets["category"]["guide"] == 1
        
        assert "tags" in facets
        assert facets["tags"]["test"] == 3
        assert facets["tags"]["api"] == 1

    def test_search_spell_correction(self, search_service):
        """Test spell correction for search queries."""
        misspelled_query = "automaton workflo"
        
        with patch.object(search_service, '_spell_check') as mock_spell:
            mock_spell.return_value = "automation workflow"
            
            corrected = search_service.correct_spelling(misspelled_query)
            
            assert corrected == "automation workflow"
            mock_spell.assert_called_once_with(misspelled_query)

    def test_search_query_expansion(self, search_service):
        """Test query expansion with synonyms."""
        query = "API"
        
        with patch.object(search_service, '_get_synonyms') as mock_synonyms:
            mock_synonyms.return_value = ["interface", "endpoint", "service"]
            
            expanded = search_service.expand_query(query)
            
            assert "API" in expanded
            assert "interface" in expanded
            assert "endpoint" in expanded

    def test_search_result_clustering(self, search_service):
        """Test clustering of search results."""
        results = [
            {"id": "doc1", "content": "API tutorial", "category": "tutorial"},
            {"id": "doc2", "content": "API guide", "category": "guide"},
            {"id": "doc3", "content": "webhook tutorial", "category": "tutorial"},
            {"id": "doc4", "content": "webhook guide", "category": "guide"}
        ]
        
        clusters = search_service.cluster_results(results)
        
        assert len(clusters) > 1
        assert all("documents" in cluster for cluster in clusters)
        assert all("label" in cluster for cluster in clusters)

    def test_search_personalization(self, search_service):
        """Test personalized search results."""
        query = "automation"
        user_profile = {
            "preferred_categories": ["tutorial"],
            "skill_level": "beginner",
            "interests": ["api", "webhook"]
        }
        
        with patch.object(search_service, '_personalize_results') as mock_personalize:
            mock_personalize.return_value = [{"id": "doc1", "score": 0.95}]
            
            results = search_service.personalized_search(query, user_profile)
            
            mock_personalize.assert_called_once()
            assert len(results) == 1
            assert results[0]["score"] == 0.95

    def test_search_multilingual_support(self, search_service):
        """Test multilingual search support."""
        queries = {
            "en": "automation workflow",
            "es": "flujo de automatización",
            "fr": "flux d'automatisation"
        }
        
        for lang, query in queries.items():
            with patch.object(search_service, '_detect_language') as mock_detect:
                with patch.object(search_service, '_translate_query') as mock_translate:
                    mock_detect.return_value = lang
                    mock_translate.return_value = queries["en"]
                    
                    results = search_service.multilingual_search(query)
                    
                    if lang != "en":
                        mock_translate.assert_called_once()
                    
                    assert isinstance(results, list)

    def test_search_real_time_indexing(self, search_service):
        """Test real-time indexing of new documents."""
        new_document = {
            "id": "new_doc",
            "title": "New Document",
            "content": "This is new content",
            "category": "tutorial"
        }
        
        with patch.object(search_service, '_index_document') as mock_index:
            search_service.index_document(new_document)
            
            mock_index.assert_called_once_with(new_document)

    def test_search_bulk_operations(self, search_service):
        """Test bulk search operations."""
        queries = ["automation", "webhook", "api integration"]
        
        with patch.object(search_service, 'vector_search') as mock_search:
            mock_search.return_value = [{"id": "doc1", "score": 0.9}]
            
            results = search_service.bulk_search(queries)
            
            assert len(results) == len(queries)
            assert mock_search.call_count == len(queries)

    def test_search_configuration_validation(self, search_service):
        """Test validation of search configuration."""
        invalid_configs = [
            {"limit": -1},  # Negative limit
            {"limit": 1001},  # Limit too high
            {"weights": {"vector": 1.5, "text": -0.5}},  # Invalid weights
        ]
        
        for config in invalid_configs:
            with pytest.raises(ValueError):
                search_service.validate_config(config)

    def test_search_memory_management(self, search_service):
        """Test memory management for large result sets."""
        # Simulate large result set
        large_results = [{"id": f"doc{i}", "score": 0.9} for i in range(10000)]
        
        with patch.object(search_service, '_process_results_in_batches') as mock_batch:
            mock_batch.return_value = large_results[:100]  # Return first 100
            
            processed = search_service.process_large_results(large_results)
            
            mock_batch.assert_called_once()
            assert len(processed) == 100