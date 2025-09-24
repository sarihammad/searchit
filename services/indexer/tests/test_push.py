"""
Tests for pushing documents to stores
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pipelines.push_to_stores import StorePusher

@pytest.fixture
def sample_documents():
    """Sample documents for testing"""
    return [
        {
            "doc_id": "doc1",
            "title": "Test Document 1",
            "text": "This is the content of document 1.",
            "url": "https://example.com/doc1",
            "lang": "en",
            "tags": ["test", "document"],
            "source": "web",
            "chunks": [
                {
                    "chunk_id": "chunk1",
                    "text": "This is chunk 1 content.",
                    "section": "Introduction",
                    "tokens": 10,
                    "embedding": [0.1] * 768
                },
                {
                    "chunk_id": "chunk2", 
                    "text": "This is chunk 2 content.",
                    "section": "Methods",
                    "tokens": 8,
                    "embedding": [0.2] * 768
                }
            ]
        },
        {
            "doc_id": "doc2",
            "title": "Test Document 2",
            "text": "This is the content of document 2.",
            "url": "https://example.com/doc2",
            "lang": "en",
            "tags": ["test"],
            "source": "web",
            "embedding": [0.3] * 768
        }
    ]

@pytest.fixture
def mock_store_pusher():
    """Create mock store pusher with mocked adapters"""
    with patch('pipelines.push_to_stores.OpenSearchAdapter') as mock_os, \
         patch('pipelines.push_to_stores.QdrantAdapter') as mock_qd, \
         patch('pipelines.push_to_stores.PostgresAdapter') as mock_pg, \
         patch('pipelines.push_to_stores.S3Adapter') as mock_s3:
        
        pusher = StorePusher()
        pusher.opensearch = AsyncMock()
        pusher.qdrant = AsyncMock()
        pusher.postgres = AsyncMock()
        pusher.s3 = Mock()
        
        return pusher

@pytest.mark.asyncio
async def test_push_documents_success(mock_store_pusher, sample_documents):
    """Test successful document pushing"""
    # Setup mocks
    mock_store_pusher.opensearch.create_index_if_missing.return_value = None
    mock_store_pusher.opensearch.bulk_index.return_value = True
    
    mock_store_pusher.qdrant.create_collection_if_missing.return_value = None
    mock_store_pusher.qdrant.upsert_points.return_value = True
    
    mock_store_pusher.postgres.store_document.return_value = True
    mock_store_pusher.postgres.store_chunk.return_value = True
    
    mock_store_pusher.s3.upload_data.return_value = True
    
    # Enable all stores
    mock_store_pusher.config["stores"] = {
        "opensearch": True,
        "qdrant": True,
        "postgres": True,
        "s3": True
    }
    
    results = await mock_store_pusher.push_documents(sample_documents)
    
    # Verify results
    assert results["total_documents"] == len(sample_documents)
    assert results["opensearch"]["success"] > 0
    assert results["qdrant"]["success"] > 0
    assert results["postgres"]["success"] > 0
    assert results["s3"]["success"] > 0

@pytest.mark.asyncio
async def test_push_to_opensearch_success(mock_store_pusher, sample_documents):
    """Test successful pushing to OpenSearch"""
    mock_store_pusher.opensearch.create_index_if_missing.return_value = None
    mock_store_pusher.opensearch.bulk_index.return_value = True
    
    result = await mock_store_pusher._push_to_opensearch(sample_documents)
    
    assert result["success"] > 0
    assert result["failed"] == 0
    mock_store_pusher.opensearch.create_index_if_missing.assert_called_once()
    mock_store_pusher.opensearch.bulk_index.assert_called_once()

@pytest.mark.asyncio
async def test_push_to_opensearch_failure(mock_store_pusher, sample_documents):
    """Test OpenSearch push failure"""
    mock_store_pusher.opensearch.create_index_if_missing.return_value = None
    mock_store_pusher.opensearch.bulk_index.return_value = False
    
    result = await mock_store_pusher._push_to_opensearch(sample_documents)
    
    assert result["success"] == 0
    assert result["failed"] > 0

@pytest.mark.asyncio
async def test_push_to_qdrant_success(mock_store_pusher, sample_documents):
    """Test successful pushing to Qdrant"""
    mock_store_pusher.qdrant.create_collection_if_missing.return_value = None
    mock_store_pusher.qdrant.upsert_points.return_value = True
    
    result = await mock_store_pusher._push_to_qdrant(sample_documents)
    
    assert result["success"] > 0
    assert result["failed"] == 0
    mock_store_pusher.qdrant.create_collection_if_missing.assert_called_once()
    mock_store_pusher.qdrant.upsert_points.assert_called_once()

@pytest.mark.asyncio
async def test_push_to_postgres_success(mock_store_pusher, sample_documents):
    """Test successful pushing to PostgreSQL"""
    mock_store_pusher.postgres.store_document.return_value = True
    mock_store_pusher.postgres.store_chunk.return_value = True
    
    result = await mock_store_pusher._push_to_postgres(sample_documents)
    
    assert result["success"] > 0
    assert result["failed"] == 0
    # Should call store_document for each document
    assert mock_store_pusher.postgres.store_document.call_count == len(sample_documents)

@pytest.mark.asyncio
async def test_push_to_postgres_document_failure(mock_store_pusher, sample_documents):
    """Test PostgreSQL document storage failure"""
    mock_store_pusher.postgres.store_document.return_value = False
    
    result = await mock_store_pusher._push_to_postgres(sample_documents)
    
    assert result["success"] == 0
    assert result["failed"] > 0

@pytest.mark.asyncio
async def test_push_to_s3_success(mock_store_pusher, sample_documents):
    """Test successful pushing to S3"""
    mock_store_pusher.s3.upload_data.return_value = True
    
    result = await mock_store_pusher._push_to_s3(sample_documents)
    
    assert result["success"] == len(sample_documents)
    assert result["failed"] == 0
    # Should call upload_data for each document
    assert mock_store_pusher.s3.upload_data.call_count == len(sample_documents)

@pytest.mark.asyncio
async def test_push_to_s3_failure(mock_store_pusher, sample_documents):
    """Test S3 push failure"""
    mock_store_pusher.s3.upload_data.return_value = False
    
    result = await mock_store_pusher._push_to_s3(sample_documents)
    
    assert result["success"] == 0
    assert result["failed"] == len(sample_documents)

@pytest.mark.asyncio
async def test_batch_processing(mock_store_pusher, sample_documents):
    """Test batch processing of documents"""
    # Create more documents than batch size
    many_documents = sample_documents * 10  # 20 documents
    mock_store_pusher.config["batch_size"] = 5
    
    # Setup mocks
    mock_store_pusher.opensearch.create_index_if_missing.return_value = None
    mock_store_pusher.opensearch.bulk_index.return_value = True
    
    mock_store_pusher.qdrant.create_collection_if_missing.return_value = None
    mock_store_pusher.qdrant.upsert_points.return_value = True
    
    mock_store_pusher.postgres.store_document.return_value = True
    mock_store_pusher.postgres.store_chunk.return_value = True
    
    # Enable stores
    mock_store_pusher.config["stores"] = {
        "opensearch": True,
        "qdrant": True,
        "postgres": True,
        "s3": False
    }
    
    results = await mock_store_pusher.push_documents(many_documents)
    
    # Verify batch processing
    assert results["total_documents"] == len(many_documents)
    # Should process in batches (4 batches of 5 documents each)
    expected_batches = (len(many_documents) + mock_store_pusher.config["batch_size"] - 1) // mock_store_pusher.config["batch_size"]
    assert mock_store_pusher.opensearch.bulk_index.call_count == expected_batches

@pytest.mark.asyncio
async def test_documents_without_chunks(mock_store_pusher):
    """Test processing documents without chunks"""
    documents_without_chunks = [
        {
            "doc_id": "doc1",
            "title": "Document without chunks",
            "text": "This is the full document text.",
            "embedding": [0.1] * 768
        }
    ]
    
    mock_store_pusher.opensearch.create_index_if_missing.return_value = None
    mock_store_pusher.opensearch.bulk_index.return_value = True
    
    result = await mock_store_pusher._push_to_opensearch(documents_without_chunks)
    
    assert result["success"] > 0
    # Verify that bulk_index was called with document data
    mock_store_pusher.opensearch.bulk_index.assert_called_once()

@pytest.mark.asyncio
async def test_empty_documents_list(mock_store_pusher):
    """Test processing empty documents list"""
    results = await mock_store_pusher.push_documents([])
    
    assert results["total_documents"] == 0
    assert results["opensearch"]["success"] == 0
    assert results["qdrant"]["success"] == 0
    assert results["postgres"]["success"] == 0
    assert results["s3"]["success"] == 0

@pytest.mark.asyncio
async def test_store_selection(mock_store_pusher, sample_documents):
    """Test selective store pushing"""
    # Enable only OpenSearch
    mock_store_pusher.config["stores"] = {
        "opensearch": True,
        "qdrant": False,
        "postgres": False,
        "s3": False
    }
    
    mock_store_pusher.opensearch.create_index_if_missing.return_value = None
    mock_store_pusher.opensearch.bulk_index.return_value = True
    
    results = await mock_store_pusher.push_documents(sample_documents)
    
    # Only OpenSearch should have results
    assert results["opensearch"]["success"] > 0
    assert results["qdrant"]["success"] == 0
    assert results["postgres"]["success"] == 0
    assert results["s3"]["success"] == 0

@pytest.mark.asyncio
async def test_exception_handling(mock_store_pusher, sample_documents):
    """Test exception handling during push"""
    mock_store_pusher.opensearch.create_index_if_missing.side_effect = Exception("OpenSearch error")
    
    result = await mock_store_pusher._push_to_opensearch(sample_documents)
    
    assert result["success"] == 0
    assert result["failed"] > 0
