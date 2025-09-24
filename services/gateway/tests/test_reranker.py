"""
Tests for cross-encoder reranker
"""

import pytest
from unittest.mock import Mock, patch
from app.rag.reranker import CEReranker

@pytest.fixture
def sample_candidates():
    """Sample candidates for reranking"""
    return [
        "This is a document about machine learning algorithms",
        "Machine learning is a subset of artificial intelligence", 
        "Deep learning uses neural networks for pattern recognition",
        "Natural language processing helps computers understand text"
    ]

@pytest.fixture
def mock_cross_encoder():
    """Mock cross-encoder model"""
    mock_model = Mock()
    mock_model.predict.return_value = [0.9, 0.8, 0.7, 0.6]  # Mock scores
    return mock_model

def test_reranker_initialization():
    """Test reranker initialization"""
    with patch('app.rag.reranker.CrossEncoder') as mock_ce:
        mock_model = Mock()
        mock_ce.return_value = mock_model
        
        reranker = CEReranker()
        
        assert reranker.model is not None
        mock_ce.assert_called_once()

def test_reranker_with_custom_model():
    """Test reranker with custom model name"""
    with patch('app.rag.reranker.CrossEncoder') as mock_ce:
        mock_model = Mock()
        mock_ce.return_value = mock_model
        
        custom_model = "custom/reranker-model"
        reranker = CEReranker(model_name=custom_model)
        
        mock_ce.assert_called_with(custom_model)

def test_rerank_success(sample_candidates, mock_cross_encoder):
    """Test successful reranking"""
    with patch('app.rag.reranker.CrossEncoder') as mock_ce:
        mock_ce.return_value = mock_cross_encoder
        
        reranker = CEReranker()
        query = "machine learning"
        
        result = reranker.rerank(query, sample_candidates, top_k=3)
        
        # Check that results are returned
        assert len(result) == 3
        assert all("text" in item for item in result)
        assert all("rerank_score" in item for item in result)
        
        # Check that scores are monotonic (descending)
        scores = [item["rerank_score"] for item in result]
        assert scores == sorted(scores, reverse=True)
        
        # Verify model was called with correct pairs
        mock_cross_encoder.predict.assert_called_once()
        pairs = mock_cross_encoder.predict.call_args[0][0]
        assert len(pairs) == len(sample_candidates)
        assert all(pair[0] == query for pair in pairs)

def test_rerank_empty_candidates():
    """Test reranking with empty candidates"""
    with patch('app.rag.reranker.CrossEncoder') as mock_ce:
        mock_model = Mock()
        mock_ce.return_value = mock_model
        
        reranker = CEReranker()
        result = reranker.rerank("test query", [], top_k=5)
        
        assert result == []

def test_rerank_model_failure():
    """Test reranking when model fails to load"""
    with patch('app.rag.reranker.CrossEncoder') as mock_ce:
        mock_ce.side_effect = Exception("Model loading failed")
        
        reranker = CEReranker()
        assert reranker.model is None
        
        # Should return original candidates when model is None
        candidates = ["doc1", "doc2", "doc3"]
        result = reranker.rerank("test", candidates, top_k=2)
        
        assert len(result) == 2
        assert all(item["rerank_score"] == 0.0 for item in result)

def test_rerank_predict_failure(sample_candidates):
    """Test reranking when model prediction fails"""
    with patch('app.rag.reranker.CrossEncoder') as mock_ce:
        mock_model = Mock()
        mock_model.predict.side_effect = Exception("Prediction failed")
        mock_ce.return_value = mock_model
        
        reranker = CEReranker()
        result = reranker.rerank("test", sample_candidates, top_k=3)
        
        # Should return fallback results with 0.0 scores
        assert len(result) == 3
        assert all(item["rerank_score"] == 0.0 for item in result)

def test_rerank_deterministic_order(sample_candidates):
    """Test that reranking produces deterministic order"""
    with patch('app.rag.reranker.CrossEncoder') as mock_ce:
        # Mock deterministic scores
        mock_model = Mock()
        mock_model.predict.return_value = [0.9, 0.8, 0.7, 0.6]
        mock_ce.return_value = mock_model
        
        reranker = CEReranker()
        query = "test query"
        
        # Run multiple times
        results1 = reranker.rerank(query, sample_candidates, top_k=4)
        results2 = reranker.rerank(query, sample_candidates, top_k=4)
        
        # Results should be identical
        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1["text"] == r2["text"]
            assert r1["rerank_score"] == r2["rerank_score"]
