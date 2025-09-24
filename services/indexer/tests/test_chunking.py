"""
Tests for text chunking functionality
"""

import pytest
import yaml
from pipelines.clean_normalize import TextCleaner
from rag.chunker import SemanticChunker

@pytest.fixture
def sample_text():
    """Sample text for chunking tests"""
    return """
    # Machine Learning Overview
    
    Machine learning is a subset of artificial intelligence that focuses on algorithms 
    that can learn from data. There are three main types of machine learning:
    
    ## Supervised Learning
    
    Supervised learning uses labeled training data to learn a mapping from inputs to outputs.
    Common algorithms include linear regression, decision trees, and neural networks.
    
    ## Unsupervised Learning
    
    Unsupervised learning finds patterns in data without labeled examples.
    Clustering and dimensionality reduction are common unsupervised tasks.
    
    ## Reinforcement Learning
    
    Reinforcement learning learns through interaction with an environment.
    The agent receives rewards or penalties based on its actions.
    """

@pytest.fixture
def chunker():
    """Create a chunker instance"""
    return SemanticChunker()

@pytest.fixture
def cleaner():
    """Create a text cleaner instance"""
    return TextCleaner()

def test_chunker_initialization(chunker):
    """Test chunker initialization"""
    assert chunker.min_tokens == 250
    assert chunker.max_tokens == 500
    assert chunker.overlap == 0.15

def test_basic_chunking(chunker, sample_text):
    """Test basic chunking functionality"""
    chunks = chunker.chunk(sample_text)
    
    assert len(chunks) > 0
    
    # Check that chunks have required fields
    for chunk in chunks:
        assert "text" in chunk
        assert "tokens" in chunk
        assert "section" in chunk
        assert len(chunk["text"]) > 0

def test_chunk_size_constraints(chunker, sample_text):
    """Test that chunks respect size constraints"""
    chunks = chunker.chunk(sample_text)
    
    for chunk in chunks:
        tokens = chunk["tokens"]
        assert chunker.min_tokens <= tokens <= chunker.max_tokens

def test_chunk_overlap(chunker, sample_text):
    """Test that chunks have appropriate overlap"""
    chunks = chunker.chunk(sample_text)
    
    if len(chunks) > 1:
        # Check overlap between consecutive chunks
        for i in range(len(chunks) - 1):
            chunk1 = chunks[i]["text"]
            chunk2 = chunks[i + 1]["text"]
            
            # Simple overlap check - should share some words
            words1 = set(chunk1.lower().split())
            words2 = set(chunk2.lower().split())
            overlap = len(words1.intersection(words2))
            
            # Should have some overlap (not strict validation)
            assert overlap > 0

def test_empty_text(chunker):
    """Test chunking empty text"""
    chunks = chunker.chunk("")
    assert chunks == []

def test_short_text(chunker):
    """Test chunking text that's shorter than min_tokens"""
    short_text = "This is a very short text that should be merged."
    chunks = chunker.chunk(short_text)
    
    # Short text should still produce at least one chunk
    assert len(chunks) >= 1

def test_heading_preservation(chunker):
    """Test that headings are preserved in chunks"""
    text_with_headings = """
    # Main Title
    
    This is the main content under the title.
    
    ## Subtitle
    
    This is content under the subtitle.
    """
    
    chunks = chunker.chunk(text_with_headings)
    
    # Should preserve heading information in section field
    for chunk in chunks:
        if chunk["section"]:
            assert "Title" in chunk["section"] or "Subtitle" in chunk["section"]

def test_token_counting(chunker):
    """Test token counting functionality"""
    text = "This is a test sentence with several words."
    tokens = chunker._count_tokens(text)
    
    assert tokens > 0
    assert tokens == len(text.split())  # Simple word-based counting

def test_merge_short_chunks(chunker):
    """Test merging of very short chunks"""
    # Create scenario with multiple short sections
    short_sections = [
        "Short section 1.",
        "Short section 2.", 
        "Short section 3.",
        "Short section 4."
    ]
    
    text = "\n\n".join(short_sections)
    chunks = chunker.chunk(text)
    
    # Should merge short sections into fewer chunks
    assert len(chunks) < len(short_sections)

def test_text_cleaner_initialization(cleaner):
    """Test text cleaner initialization"""
    assert cleaner.config["remove_extra_whitespace"] is True
    assert cleaner.config["normalize_unicode"] is True

def test_text_cleaning(cleaner):
    """Test text cleaning functionality"""
    dirty_text = "  This   is    a   test   with   extra   spaces.  \n\n\n"
    cleaned = cleaner.clean_text(dirty_text)
    
    assert "  " not in cleaned  # No double spaces
    assert cleaned.strip() == cleaned  # No leading/trailing whitespace

def test_html_removal(cleaner):
    """Test HTML tag removal"""
    html_text = "<p>This is <b>bold</b> text with <a href='#'>links</a>.</p>"
    cleaned = cleaner.clean_text(html_text)
    
    assert "<" not in cleaned and ">" not in cleaned
    assert "This is bold text with links." in cleaned

def test_language_detection(cleaner):
    """Test language detection"""
    english_text = "This is a test sentence in English."
    detected = cleaner.detect_language(english_text)
    
    assert detected == "en"

def test_language_detection_fallback(cleaner):
    """Test language detection fallback"""
    short_text = "Hi"
    detected = cleaner.detect_language(short_text)
    
    assert detected == "en"  # Fallback language

def test_section_extraction(cleaner):
    """Test section extraction from text"""
    text_with_sections = """
    # Introduction
    This is the introduction section.
    
    ## Methods
    This is the methods section.
    
    ### Subsection
    This is a subsection.
    """
    
    sections = cleaner.extract_sections(text_with_sections)
    
    assert len(sections) >= 2
    assert any("Introduction" in section["title"] for section in sections)
    assert any("Methods" in section["title"] for section in sections)

@pytest.mark.parametrize("text_length", [100, 1000, 5000])
def test_chunking_different_lengths(chunker, text_length):
    """Test chunking with different text lengths"""
    # Generate text of specified length
    base_text = "This is a sample sentence for testing chunking. "
    text = (base_text * (text_length // len(base_text)))[:text_length]
    
    chunks = chunker.chunk(text)
    
    if text_length > chunker.min_tokens:
        assert len(chunks) > 1
    else:
        assert len(chunks) >= 1

def test_chunking_with_custom_config():
    """Test chunking with custom configuration"""
    custom_config = {
        "min_tokens": 100,
        "max_tokens": 200,
        "overlap": 0.1
    }
    
    chunker = SemanticChunker(**custom_config)
    
    assert chunker.min_tokens == 100
    assert chunker.max_tokens == 200
    assert chunker.overlap == 0.1
