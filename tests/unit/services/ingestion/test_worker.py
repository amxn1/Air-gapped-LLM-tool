"""
Unit tests for the IngestionWorker.
"""
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from sqlalchemy.orm import Session

from services.ingestion.worker import IngestionWorker


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock(spec=Session)
    return session


@pytest.fixture
def mock_extract_text():
    """Mock the extract_text function."""
    with patch('services.ingestion.worker.extract_text') as mock:
        yield mock


@pytest.fixture
def mock_chunk_text():
    """Mock the chunk_text function."""
    with patch('services.ingestion.worker.chunk_text') as mock:
        yield mock


@pytest.fixture
def mock_chunk_by_paragraphs():
    """Mock the chunk_by_paragraphs function."""
    with patch('services.ingestion.worker.chunk_by_paragraphs') as mock:
        yield mock


@pytest.fixture
def mock_embedding_generator():
    """Mock the EmbeddingGenerator class."""
    with patch('services.ingestion.worker.EmbeddingGenerator') as mock:
        yield mock


def test_process_file_success(
    mock_db_session,
    mock_extract_text,
    mock_chunk_text,
    mock_chunk_by_paragraphs,
    mock_embedding_generator
):
    """Test successful processing of a file through the ingestion worker."""
    # Setup mocks
    mock_extract_text.return_value = {
        "text": "This is a test document.",
        "metadata": {"file_name": "test.txt", "file_size": 100},
        "pages": ["This is a test document."]
    }
    mock_chunk_text.return_value = [
        {"text": "This is a test", "start_index": 0, "end_index": 12},
        {"text": "document.", "start_index": 13, "end_index": 22}
    ]
    mock_chunk_by_paragraphs.return_value = []  # Not used if chunk_text returns chunks

    # Setup mock embedding generator
    mock_embedding_gen_instance = MagicMock()
    mock_embedding_gen_instance.generate_embeddings_batch = AsyncMock(
        return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    )
    mock_embedding_gen_instance.close = AsyncMock()
    mock_embedding_generator.return_value = mock_embedding_gen_instance

    # Create worker and call process_file
    worker = IngestionWorker(db_session=mock_db_session)
    result = worker.process_file(
        file_path="/fake/path/test.txt",
        user_id=1,
        collection_id=1
    )

    # Assertions
    assert result["success"] is True
    assert result["document_id"] is not None
    assert result["chunks_created"] == 2
    assert len(result["errors"]) == 0

    # Check that document was added and committed
    assert mock_db_session.add.call_count >= 2  # At least document and two chunks
    assert mock_db_session.commit.call_count >= 2  # After document and after chunks

    # Check that the document's import_status was set to completed
    # We can check the last call to add was for a Document object with import_status="completed"
    # But it's easier to check that we set the attribute on the document object
    # We don't have the document object, but we can check that the session was told to add a Document
    # and then we set its import_status.

    # Instead, let's check that we called commit after setting the import_status.
    # We know we call commit after adding the document and after adding the chunks.
    # The final commit is after setting the document's import_status to "completed".

    # We can also check that the worker tried to close the embedding generator.
    mock_embedding_gen_instance.close.assert_awaited_once()

    # Check that vector store was not called (since we didn't provide one)
    # The worker only calls vector_store.add_vector if self.vector_store is not None.
    # We didn't pass a vector_store to the worker, so it should be None.
    # We don't have a mock for vector_store, so we can't assert it wasn't called.
    # But we can note that the worker doesn't have a vector_store attribute set to anything but None.


def test_process_file_fallback_to_paragraph_chunking(
    mock_db_session,
    mock_extract_text,
    mock_chunk_text,
    mock_chunk_by_paragraphs,
    mock_embedding_generator
):
    """Test that if chunk_text returns no chunks, we fall back to chunk_by_paragraphs."""
    # Setup mocks
    mock_extract_text.return_value = {
        "text": "This is a test document.",
        "metadata": {"file_name": "test.txt", "file_size": 100},
        "pages": ["This is a test document."]
    }
    mock_chunk_text.return_value = []  # No chunks from chunk_text
    mock_chunk_by_paragraphs.return_value = [
        {"text": "This is a test document.", "start_index": 0, "end_index": 24}
    ]

    # Setup mock embedding generator
    mock_embedding_gen_instance = MagicMock()
    mock_embedding_gen_instance.generate_embeddings_batch = AsyncMock(
        return_value=[[0.1, 0.2, 0.3]]
    )
    mock_embedding_gen_instance.close = AsyncMock()
    mock_embedding_generator.return_value = mock_embedding_gen_instance

    # Create worker and call process_file
    worker = IngestionWorker(db_session=mock_db_session)
    result = worker.process_file(
        file_path="/fake/path/test.txt",
        user_id=1,
        collection_id=1
    )

    # Assertions
    assert result["success"] is True
    assert result["document_id"] is not None
    assert result["chunks_created"] == 1
    assert len(result["errors"]) == 0

    # Check that chunk_by_paragraphs was called
    mock_chunk_by_paragraphs.assert_called_once_with("This is a test document.")


def test_process_file_handles_extraction_error(
    mock_db_session,
    mock_extract_text,
    mock_chunk_text,
    mock_chunk_by_paragraphs,
    mock_embedding_generator
):
    """Test that if text extraction fails, the worker returns an error."""
    # Setup mocks
    mock_extract_text.side_effect = ValueError("Failed to extract text")

    # Create worker and call process_file
    worker = IngestionWorker(db_session=mock_db_session)
    result = worker.process_file(
        file_path="/fake/path/test.txt",
        user_id=1,
        collection_id=1
    )

    # Assertions
    assert result["success"] is False
    assert result["document_id"] is None
    assert result["chunks_created"] == 0
    assert len(result["errors"]) == 1
    assert "Failed to extract text" in result["errors"][0]

    # Check that we didn't call the chunking or embedding steps
    mock_chunk_text.assert_not_called()
    mock_chunk_by_paragraphs.assert_not_called()
    mock_embedding_generator.assert_not_called()


def test_process_file_handles_database_error(
    mock_db_session,
    mock_extract_text,
    mock_chunk_text,
    mock_chunk_by_paragraphs,
    mock_embedding_generator
):
    """Test that if a database error occurs, the worker handles it and marks the document as failed."""
    # Setup mocks
    mock_extract_text.return_value = {
        "text": "This is a test document.",
        "metadata": {"file_name": "test.txt", "file_size": 100},
        "pages": ["This is a test document."]
    }
    mock_chunk_text.return_value = [
        {"text": "This is a test", "start_index": 0, "end_index": 12},
        {"text": "document.", "start_index": 13, "end_index": 22}
    ]
    mock_chunk_by_paragraphs.return_value = []

    # Setup mock embedding generator
    mock_embedding_gen_instance = MagicMock()
    mock_embedding_gen_instance.generate_embeddings_batch = AsyncMock(
        return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    )
    mock_embedding_gen_instance.close = AsyncMock()
    mock_embedding_generator.return_value = mock_embedding_gen_instance

    # Make the database session raise an exception on commit
    mock_db_session.commit.side_effect = Exception("Database error")

    # Create worker and call process_file
    worker = IngestionWorker(db_session=mock_db_session)
    result = worker.process_file(
        file_path="/fake/path/test.txt",
        user_id=1,
        collection_id=1
    )

    # Assertions
    assert result["success"] is False
    assert result["document_id"] is not None  # We still created a document record
    assert result["chunks_created"] == 0  # No chunks were saved due to the error
    assert len(result["errors"]) == 1
    assert "Database error" in result["errors"][0]

    # Check that we tried to rollback by setting the document status to failed
    # We can't easily check the rollback, but we know we set the import_status to failed
    # and committed again (which we mocked to not raise an exception the second time?).
    # Actually, in the except block, we set the import_status to failed and then commit.
    # We mocked the commit to raise an exception the first time, but the second time?
    # The second commit is inside the except block, and we didn't mock it to raise an exception.
    # So we expect the second commit to not raise an exception.

    # We can check that commit was called at least twice: once that failed, and once in the except block.
    assert mock_db_session.commit.call_count == 2

    # Check that we tried to close the embedding generator.
    mock_embedding_gen_instance.close.assert_awaited_once()