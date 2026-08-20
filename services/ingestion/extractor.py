"""
Document extractor for various file formats (TXT, MD, PDF, DOCX, HTML).
"""
import logging
from pathlib import Path
from typing import Any, Dict, Union

logger = logging.getLogger(__name__)


def extract_text(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Extract text from a document file safely.

    Args:
        file_path: Path to the document file

    Returns:
        Dictionary with extracted text, page sections, and metadata.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extension = file_path.suffix.lower()

    result = {
        "text": "",
        "metadata": {
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "extension": extension,
        },
        "pages": [],
    }

    try:
        if extension in [".txt", ".md", ".markdown"]:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            result["text"] = text
            result["pages"] = [{"section": "Full Document", "text": text}]

        elif extension == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(file_path))
                text_pages = []
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    text_pages.append({"section": f"Page {page_num + 1}", "text": page_text})
                result["text"] = "\n\n".join([p["text"] for p in text_pages])
                result["pages"] = text_pages
                result["metadata"]["page_count"] = len(text_pages)
            except Exception as pdf_err:
                logger.warning(f"pypdf failed ({pdf_err}), attempting binary fallback read.")
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                result["text"] = text
                result["pages"] = [{"section": "Fallback Text", "text": text}]

        elif extension == ".docx":
            try:
                import docx
                doc = docx.Document(str(file_path))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                text = "\n\n".join(paragraphs)
                result["text"] = text
                result["pages"] = [{"section": "Document Body", "text": text}]
            except Exception as docx_err:
                logger.warning(f"docx extraction error: {docx_err}")
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                result["text"] = text
                result["pages"] = [{"section": "Fallback", "text": text}]

        elif extension in [".html", ".htm"]:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                raw_html = f.read()
            # Simple tag stripping without external dependencies
            import re
            clean_text = re.sub(r"<[^>]+>", " ", raw_html)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()
            result["text"] = clean_text
            result["pages"] = [{"section": "HTML Body", "text": clean_text}]

        else:
            logger.warning(f"Reading {extension} with generic text extractor.")
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            result["text"] = text
            result["pages"] = [{"section": "Raw Text", "text": text}]

    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        result["text"] = ""
        result["metadata"]["error"] = str(e)

    return result