"""
Unit tests for text chunking algorithms.
"""
from services.ingestion.chunker import chunk_text, chunk_by_paragraphs


def test_chunk_text_simple():
    text = "This is a short test document for basic character chunking."
    chunks = chunk_text(text, chunk_size=20, chunk_overlap=5, split_by_headings=False)
    assert len(chunks) >= 2
    assert chunks[0]["text"]
    assert chunks[0]["start_index"] == 0


def test_chunk_text_with_headings():
    markdown_text = (
        "# Introduction\n"
        "This section introduces the local architecture.\n\n"
        "# Architecture\n"
        "This section details the services and vector stores."
    )
    chunks = chunk_text(markdown_text, chunk_size=100, chunk_overlap=10, split_by_headings=True)
    assert len(chunks) >= 2
    assert any("Introduction" in c["text"] for c in chunks)
    assert any("Architecture" in c["text"] for c in chunks)


def test_chunk_by_paragraphs():
    text = (
        "First paragraph describes the goal.\n\n"
        "Second paragraph outlines the implementation.\n\n"
        "Third paragraph summarizes the conclusion."
    )
    chunks = chunk_by_paragraphs(text, max_chunk_size=100)
    assert len(chunks) >= 2
    assert "First paragraph" in chunks[0]["text"]
