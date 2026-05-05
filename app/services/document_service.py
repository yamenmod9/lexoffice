from __future__ import annotations

from io import BytesIO

from PyPDF2 import PdfReader


def extract_pdf_text(file_path: str) -> str:
    with open(file_path, "rb") as stream:
        reader = PdfReader(stream)
        chunks = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunks)


def extract_text_from_bytes(binary_data: bytes) -> str:
    reader = PdfReader(BytesIO(binary_data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
