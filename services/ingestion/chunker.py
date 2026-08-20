"""
Text chunking utilities for document processing.
"""
import re
from typing import List, Dict, Any


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    split_by_headings: bool = True,
) -> List[Dict[str, Any]]:
    """
    Split text into chunks for processing.

    Args:
        text: The input text to chunk
        chunk_size: Target size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        split_by_headings: Whether to try to split by headings first

    Returns:
        List of dictionaries, each containing:
            - text: The chunk text
            - start_index: Starting character index in the original text
            - end_index: Ending character index in the original text
    """
    if not text:
        return []

    # If we want to split by headings first (for markdown-like text)
    if split_by_headings:
        # Simple header detection: lines that start with # or are all caps and short
        lines = text.split("\n")
        chunks = []
        current_chunk = ""
        current_start = 0

        for i, line in enumerate(lines):
            # Check if this line looks like a header
            is_header = (
                line.startswith("#")
                or (line.isupper() and len(line) < 100 and not line.endswith("."))
            )
            if is_header and current_chunk:
                # Save the current chunk
                chunks.append(
                    {
                        "text": current_chunk.strip(),
                        "start_index": current_start,
                        "end_index": current_start + len(current_chunk),
                    }
                )
                # Start new chunk with overlap
                overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
                current_chunk = overlap_text + "\n" + line
                current_start = current_start + len(current_chunk) - len(overlap_text) - len(line) - 1
            else:
                current_chunk += line + "\n"

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(
                {
                    "text": current_chunk.strip(),
                    "start_index": current_start,
                    "end_index": current_start + len(current_chunk),
                }
            )

        # If we didn't split into multiple chunks, fall back to regular chunking
        if len(chunks) <= 1:
            return _simple_chunk_text(text, chunk_size, chunk_overlap)
        return chunks
    else:
        return _simple_chunk_text(text, chunk_size, chunk_overlap)


def _simple_chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
    """
    Simple text chunking by character count with overlap.
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk_text = text[start:end]

        chunks.append(
            {
                "text": chunk_text,
                "start_index": start,
                "end_index": end,
            }
        )

        # Move start forward, but leave overlap
        start = end - chunk_overlap
        if start < 0:
            start = 0

        # Break if we've covered the entire text
        if end >= text_length:
            break

    return chunks


def chunk_by_paragraphs(
    text: str,
    max_chunk_size: int = 1000,
    overlap_sentences: int = 1,
) -> List[Dict[str, Any]]:
    """
    Chunk text by paragraphs, trying to keep paragraphs together.

    Args:
        text: The input text
        max_chunk_size: Maximum size of a chunk in characters
        overlap_sentences: Number of sentences to overlap between chunks

    Returns:
        List of chunk dictionaries
    """
    # Split into paragraphs (double newline)
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    current_chunk = ""
    current_start = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If adding this paragraph would exceed max size, finalize current chunk
        if len(current_chunk) + len(para) + 2 > max_chunk_size and current_chunk:
            chunks.append(
                {
                    "text": current_chunk.strip(),
                    "start_index": current_start,
                    "end_index": current_start + len(current_chunk),
                }
                )
            # Start new chunk with overlap from the end of current chunk
            # For simplicity, we'll just start fresh but could implement sentence overlap
            current_chunk = para
            current_start = current_start + len(current_chunk) - len(para)
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    # Add the last chunk
    if current_chunk:
        chunks.append(
            {
                "text": current_chunk.strip(),
                "start_index": current_start,
                "end_index": current_start + len(current_chunk),
            }
        )

    return chunks