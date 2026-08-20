"""
Unit tests for document text extractors.
"""
import tempfile
from pathlib import Path
from services.ingestion.extractor import extract_text


def test_extract_plain_text():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Sample plain text content for extraction.")
        temp_path = f.name

    try:
        res = extract_text(temp_path)
        assert res["text"] == "Sample plain text content for extraction."
        assert res["metadata"]["file_name"] == Path(temp_path).name
        assert len(res["pages"]) == 1
    finally:
        Path(temp_path).unlink()


def test_extract_markdown():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Security Header\n\nAir-gap verification guidelines.")
        temp_path = f.name

    try:
        res = extract_text(temp_path)
        assert "Security Header" in res["text"]
        assert "Air-gap verification" in res["text"]
    finally:
        Path(temp_path).unlink()


def test_extract_html():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write("<html><body><h1>Title</h1><p>Paragraph content.</p></body></html>")
        temp_path = f.name

    try:
        res = extract_text(temp_path)
        assert "Title" in res["text"]
        assert "Paragraph content" in res["text"]
    finally:
        Path(temp_path).unlink()
