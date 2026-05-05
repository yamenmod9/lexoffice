from __future__ import annotations

from io import BytesIO


def _pdf_reader():
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise RuntimeError("PyPDF2 is required for PDF text extraction") from exc
    return PdfReader


def extract_pdf_text(file_path: str) -> str:
    PdfReader = _pdf_reader()
    with open(file_path, "rb") as stream:
        reader = PdfReader(stream)
        chunks = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunks)


def extract_text_from_bytes(binary_data: bytes) -> str:
    PdfReader = _pdf_reader()
    reader = PdfReader(BytesIO(binary_data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
