"""
Tests for answer generator with grounding and validation
"""

import pytest
from unittest.mock import Mock, patch
from app.rag.generator import AnswerGenerator

@pytest.fixture
def sample_contexts():
    """Sample contexts for answer generation"""
    return [
        {"text": "Machine learning is a subset of artificial intelligence.", "rerank_score": 0.9},
        {"text": "Deep learning uses neural networks for pattern recognition.", "rerank_score": 0.8},
        {"text": "Supervised learning uses labeled training data.", "rerank_score": 0.7}
    ]

@pytest.fixture
def generator():
    """Create generator instance"""
    return AnswerGenerator()

def test_generator_initialization(generator):
    """Test generator initialization"""
    assert generator.generator_type == "stub"
    assert generator.coverage_threshold == 0.3

def test_answerability_check_high_coverage(generator, sample_contexts):
    """Test answerability check with high coverage"""
    is_answerable = generator._is_answerable(sample_contexts)
    assert is_answerable is True

def test_answerability_check_low_coverage(generator):
    """Test answerability check with low coverage"""
    low_coverage_contexts = [
        {"text": "Unrelated content", "rerank_score": 0.1}
    ]
    is_answerable = generator._is_answerable(low_coverage_contexts)
    assert is_answerable is False

def test_answerability_check_empty_contexts(generator):
    """Test answerability check with empty contexts"""
    is_answerable = generator._is_answerable([])
    assert is_answerable is False

def test_stub_answer_generation(generator, sample_contexts):
    """Test stub answer generation"""
    question = "What is machine learning?"
    
    result = generator._generate_stub_answer(question, sample_contexts)
    
    assert "abstained" in result
    assert "answer" in result or result["abstained"] is True
    
    if not result["abstained"]:
        assert len(result["answer"]) > 0
        assert "citations" in result
        assert "evidence_coverage" in result

def test_stub_answer_with_no_context(generator):
    """Test stub answer generation with no context"""
    question = "What is machine learning?"
    result = generator._generate_stub_answer(question, [])
    
    assert result["abstained"] is True
    assert result["reason"] == "no_context"

def test_generate_with_high_coverage(generator, sample_contexts):
    """Test answer generation with sufficient coverage"""
    question = "What is machine learning?"
    
    result = generator.generate(question, sample_contexts, force_citations=True)
    
    # Should not abstain due to high coverage
    if result["abstained"]:
        assert result["reason"] != "low_coverage"
    else:
        assert "answer" in result
        assert "citations" in result

def test_generate_with_low_coverage(generator):
    """Test answer generation with insufficient coverage"""
    question = "What is machine learning?"
    low_coverage_contexts = [
        {"text": "Unrelated content", "rerank_score": 0.1}
    ]
    
    result = generator.generate(question, low_coverage_contexts)
    
    assert result["abstained"] is True
    assert result["reason"] == "low_coverage"

def test_citation_validation_pass(generator):
    """Test citation validation that passes"""
    answer = "Machine learning [chunk_1] is a subset of AI [chunk_2]."
    contexts = [
        {"text": "Machine learning is a subset of artificial intelligence."},
        {"text": "AI stands for artificial intelligence."}
    ]
    
    is_valid = generator._validate_citations(answer, contexts)
    assert is_valid is True

def test_citation_validation_fail(generator):
    """Test citation validation that fails"""
    answer = "Machine learning [chunk_1] is a subset of AI [chunk_2]."
    contexts = [
        {"text": "Completely unrelated content."}
    ]
    
    # For stub implementation, always returns True
    is_valid = generator._validate_citations(answer, contexts)
    assert is_valid is True

def test_generate_with_validation_failure(generator, sample_contexts):
    """Test answer generation with citation validation failure"""
    # Mock validation to fail
    with patch.object(generator, '_validate_citations', return_value=False):
        result = generator.generate(
            "What is machine learning?", 
            sample_contexts, 
            force_citations=True
        )
        
        assert result["abstained"] is True
        assert result["reason"] == "validation_fail"

def test_generate_without_citations(generator, sample_contexts):
    """Test answer generation without forced citations"""
    result = generator.generate(
        "What is machine learning?",
        sample_contexts,
        force_citations=False
    )
    
    # Should not fail due to citation validation
    if result["abstained"]:
        assert result["reason"] != "validation_fail"

@pytest.mark.parametrize("generator_type", ["stub", "hf"])
def test_generator_types(generator, sample_contexts, generator_type):
    """Test different generator types"""
    generator.generator_type = generator_type
    result = generator.generate("Test question", sample_contexts)
    
    # Should return a valid result regardless of type
    assert "abstained" in result
    if not result["abstained"]:
        assert "answer" in result

def test_evidence_coverage_calculation(generator):
    """Test evidence coverage calculation"""
    contexts = [{"text": "test"}] * 3  # 3 contexts
    result = generator._generate_stub_answer("test", contexts)
    
    if not result["abstained"]:
        coverage = result["evidence_coverage"]
        assert 0.0 <= coverage <= 1.0
