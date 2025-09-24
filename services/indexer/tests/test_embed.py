"""
Tests for embedding generation
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from pipelines.embed import EmbeddingGenerator

@pytest.fixture
def sample_texts():
    """Sample texts for embedding tests"""
    return [
        "This is a test sentence about machine learning.",
        "Deep learning is a subset of machine learning.",
        "Natural language processing uses various techniques.",
        "Computer vision enables machines to see and understand images.",
        "Data science combines statistics and programming."
    ]

@pytest.fixture
def mock_model():
    """Mock SentenceTransformer model"""
    model = Mock()
    model.max_seq_length = 512
    model.encode.return_value = np.random.rand(5, 768)  # Mock embeddings
    return model

@pytest.fixture
def embedding_generator():
    """Create embedding generator with mocked model"""
    with patch('pipelines.embed.SentenceTransformer') as mock_st:
        mock_st.return_value = Mock()
        generator = EmbeddingGenerator()
        generator.model = Mock()
        generator.model.encode.return_value = np.random.rand(5, 768)
        return generator

def test_embedding_generator_initialization(embedding_generator):
    """Test embedding generator initialization"""
    assert embedding_generator.config["model_name"] == "intfloat/e5-base"
    assert embedding_generator.config["batch_size"] == 32
    assert embedding_generator.config["normalize_embeddings"] is True

def test_generate_embeddings_success(embedding_generator, sample_texts):
    """Test successful embedding generation"""
    # Mock the model.encode method
    mock_embeddings = np.random.rand(len(sample_texts), 768)
    embedding_generator.model.encode.return_value = mock_embeddings
    
    embeddings = embedding_generator.generate_embeddings(sample_texts)
    
    assert embeddings.shape == (len(sample_texts), 768)
    assert isinstance(embeddings, np.ndarray)

def test_generate_embeddings_empty_list(embedding_generator):
    """Test embedding generation with empty input"""
    embeddings = embedding_generator.generate_embeddings([])
    
    assert embeddings.shape == (0,)
    assert len(embeddings) == 0

def test_generate_single_embedding(embedding_generator):
    """Test single embedding generation"""
    text = "This is a test sentence."
    mock_embedding = np.random.rand(1, 768)
    embedding_generator.model.encode.return_value = mock_embedding
    
    embedding = embedding_generator.generate_single_embedding(text)
    
    assert embedding.shape == (768,)
    assert isinstance(embedding, np.ndarray)

def test_process_documents_with_chunks(embedding_generator):
    """Test processing documents with chunks"""
    documents = [
        {
            "doc_id": "doc1",
            "title": "Test Document",
            "chunks": [
                {"chunk_id": "chunk1", "text": "First chunk text."},
                {"chunk_id": "chunk2", "text": "Second chunk text."}
            ]
        }
    ]
    
    # Mock embeddings for 2 chunks
    mock_embeddings = np.random.rand(2, 768)
    embedding_generator.model.encode.return_value = mock_embeddings
    
    processed_docs = embedding_generator.process_documents(documents)
    
    assert len(processed_docs) == 1
    assert "embedding" in processed_docs[0]["chunks"][0]
    assert "embedding" in processed_docs[0]["chunks"][1]
    assert len(processed_docs[0]["chunks"][0]["embedding"]) == 768

def test_process_documents_without_chunks(embedding_generator):
    """Test processing documents without chunks"""
    documents = [
        {
            "doc_id": "doc1",
            "title": "Test Document",
            "text": "This is the document text."
        }
    ]
    
    # Mock embedding for 1 document
    mock_embedding = np.random.rand(1, 768)
    embedding_generator.model.encode.return_value = mock_embedding
    
    processed_docs = embedding_generator.process_documents(documents)
    
    assert len(processed_docs) == 1
    assert "embedding" in processed_docs[0]
    assert len(processed_docs[0]["embedding"]) == 768

def test_process_documents_empty_text(embedding_generator):
    """Test processing documents with empty text"""
    documents = [
        {
            "doc_id": "doc1",
            "title": "Test Document",
            "chunks": [
                {"chunk_id": "chunk1", "text": ""},  # Empty text
                {"chunk_id": "chunk2", "text": "Valid text."}
            ]
        }
    ]
    
    # Mock embedding for 1 valid chunk
    mock_embedding = np.random.rand(1, 768)
    embedding_generator.model.encode.return_value = mock_embedding
    
    processed_docs = embedding_generator.process_documents(documents)
    
    # Should only process the valid chunk
    assert "embedding" not in processed_docs[0]["chunks"][0]  # Empty text chunk
    assert "embedding" in processed_docs[0]["chunks"][1]  # Valid text chunk

def test_batch_processing(embedding_generator):
    """Test batch processing of embeddings"""
    # Create more texts than batch size
    texts = [f"This is test text number {i}." for i in range(100)]
    
    # Mock embeddings
    mock_embeddings = np.random.rand(100, 768)
    embedding_generator.model.encode.return_value = mock_embeddings
    
    embeddings = embedding_generator.generate_embeddings(texts)
    
    assert embeddings.shape == (100, 768)
    # Verify that model.encode was called (batch processing handled internally)
    embedding_generator.model.encode.assert_called()

def test_similarity_computation(embedding_generator):
    """Test similarity computation between embeddings"""
    embedding1 = np.array([1.0, 0.0, 0.0])
    embedding2 = np.array([0.0, 1.0, 0.0])
    embedding3 = np.array([1.0, 0.0, 0.0])
    
    # Test orthogonal vectors (similarity = 0)
    similarity1 = embedding_generator.compute_similarity(embedding1, embedding2)
    assert abs(similarity1) < 1e-10
    
    # Test identical vectors (similarity = 1)
    similarity2 = embedding_generator.compute_similarity(embedding1, embedding3)
    assert abs(similarity2 - 1.0) < 1e-10

def test_find_similar_texts(embedding_generator):
    """Test finding similar texts"""
    query_embedding = np.array([1.0, 0.0, 0.0])
    text_embeddings = np.array([
        [1.0, 0.0, 0.0],  # Should be most similar
        [0.5, 0.5, 0.0],  # Medium similarity
        [0.0, 1.0, 0.0],  # Low similarity
        [0.8, 0.2, 0.0]   # High similarity
    ])
    
    similar_indices = embedding_generator.find_similar_texts(
        query_embedding, text_embeddings, top_k=2
    )
    
    assert len(similar_indices) == 2
    # First result should be index 0 (most similar)
    assert similar_indices[0][0] == 0
    # Second result should be index 3 (second most similar)
    assert similar_indices[1][0] == 3

def test_save_and_load_embeddings(embedding_generator, tmp_path):
    """Test saving and loading embeddings"""
    embeddings = np.random.rand(5, 768)
    
    # Test saving as numpy file
    npy_path = tmp_path / "embeddings.npy"
    embedding_generator.save_embeddings(embeddings, str(npy_path))
    
    loaded_embeddings = embedding_generator.load_embeddings(str(npy_path))
    np.testing.assert_array_equal(embeddings, loaded_embeddings)

def test_model_loading_failure():
    """Test handling of model loading failure"""
    with patch('pipelines.embed.SentenceTransformer') as mock_st:
        mock_st.side_effect = Exception("Model loading failed")
        
        with pytest.raises(Exception, match="Model loading failed"):
            EmbeddingGenerator()

def test_embedding_generation_failure(embedding_generator, sample_texts):
    """Test handling of embedding generation failure"""
    embedding_generator.model.encode.side_effect = Exception("Encoding failed")
    
    with pytest.raises(Exception, match="Encoding failed"):
        embedding_generator.generate_embeddings(sample_texts)

def test_device_selection():
    """Test automatic device selection"""
    with patch('pipelines.embed.SentenceTransformer'):
        with patch('pipelines.embed.torch.cuda.is_available', return_value=True):
            generator = EmbeddingGenerator()
            assert generator.device == "cuda"
        
        with patch('pipelines.embed.torch.cuda.is_available', return_value=False):
            generator = EmbeddingGenerator()
            assert generator.device == "cpu"
