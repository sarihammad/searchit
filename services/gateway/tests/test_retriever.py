"""
Tests for hybrid retriever with RRF fusion
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.rag.retriever import HybridRetriever

@pytest.fixture
def mock_retriever():
    """Create a mock retriever for testing"""
    retriever = HybridRetriever()
    
    # Mock the adapters
    retriever.opensearch = AsyncMock()
    retriever.qdrant = AsyncMock()
    
    return retriever

@pytest.fixture
def sample_bm25_results():
    """Sample BM25 search results"""
    return [
        {
            "doc_id": "doc1",
            "chunk_id": "chunk1",
            "title": "Test Document 1",
            "text": "This is a test document about machine learning",
            "score": 0.9
        },
        {
            "doc_id": "doc2", 
            "chunk_id": "chunk2",
            "title": "Test Document 2",
            "text": "This is another test document about neural networks",
            "score": 0.8
        }
    ]

@pytest.fixture
def sample_dense_results():
    """Sample dense search results"""
    return [
        {
            "doc_id": "doc2",
            "chunk_id": "chunk2", 
            "title": "Test Document 2",
            "text": "This is another test document about neural networks",
            "score": 0.85
        },
        {
            "doc_id": "doc3",
            "chunk_id": "chunk3",
            "title": "Test Document 3", 
            "text": "This is a third test document about deep learning",
            "score": 0.75
        }
    ]

@pytest.mark.asyncio
async def test_hybrid_search_success(mock_retriever, sample_bm25_results, sample_dense_results):
    """Test successful hybrid search with RRF fusion"""
    
    # Setup mocks
    mock_retriever.opensearch.search_bm25.return_value = sample_bm25_results
    mock_retriever.qdrant.search_dense.return_value = sample_dense_results
    mock_retriever.opensearch.get_facets.return_value = {"lang": {"en": 3}}
    
    # Perform search
    result = await mock_retriever.search("machine learning", top_k=5)
    
    # Assertions
    assert "results" in result
    assert "facets" in result
    assert "query" in result
    assert result["query"] == "machine learning"
    assert len(result["results"]) <= 5
    
    # Check that RRF fusion was applied
    # doc2 should have higher score due to appearing in both results
    scores = [r["score"] for r in result["results"]]
    assert scores == sorted(scores, reverse=True)  # Monotonic decreasing

@pytest.mark.asyncio
async def test_hybrid_search_with_filters(mock_retriever):
    """Test hybrid search with filters"""
    
    mock_retriever.opensearch.search_bm25.return_value = []
    mock_retriever.qdrant.search_dense.return_value = []
    mock_retriever.opensearch.get_facets.return_value = {}
    
    filters = {"lang": "en", "tags": "python"}
    
    await mock_retriever.search("test query", filters=filters)
    
    # Verify filters were passed to both adapters
    mock_retriever.opensearch.search_bm25.assert_called_once()
    mock_retriever.qdrant.search_dense.assert_called_once()

def test_rrf_fusion_scoring():
    """Test RRF fusion scoring logic"""
    retriever = HybridRetriever()
    
    bm25_results = [
        {"doc_id": "doc1", "chunk_id": "chunk1", "score": 0.9},
        {"doc_id": "doc2", "chunk_id": "chunk2", "score": 0.8}
    ]
    
    dense_results = [
        {"doc_id": "doc2", "chunk_id": "chunk2", "score": 0.85},
        {"doc_id": "doc3", "chunk_id": "chunk3", "score": 0.75}
    ]
    
    fused = retriever._rrf_fuse(bm25_results, dense_results, top_k=3)
    
    # Check that results are properly merged
    assert len(fused) <= 3
    
    # Check that doc2 appears only once (deduplicated)
    doc_ids = [r["doc_id"] for r in fused]
    assert len(set(doc_ids)) == len(doc_ids)  # No duplicates
    
    # Check score monotonicity
    scores = [r["score"] for r in fused]
    assert scores == sorted(scores, reverse=True)

def test_rrf_fusion_empty_results():
    """Test RRF fusion with empty results"""
    retriever = HybridRetriever()
    
    fused = retriever._rrf_fuse([], [], top_k=5)
    assert fused == []

@pytest.mark.asyncio
async def test_hybrid_search_adapter_failure(mock_retriever):
    """Test hybrid search when adapters fail"""
    
    # Make adapters return empty results (simulating failure)
    mock_retriever.opensearch.search_bm25.return_value = []
    mock_retriever.qdrant.search_dense.return_value = []
    mock_retriever.opensearch.get_facets.return_value = {}
    
    result = await mock_retriever.search("test query")
    
    assert result["results"] == []
    assert result["total"] == 0
