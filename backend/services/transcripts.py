from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from engine.prompts import TRANSCRIPT_ANALYSIS_PROMPT

from ..llm import ask_llm
from ..settings import settings


def _read_upload(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension == ".txt":
        return content.decode("utf-8", errors="ignore")
    if extension == ".pdf":
        import PyPDF2

        reader = PyPDF2.PdfReader(io.BytesIO(content))
        if len(reader.pages) > settings.max_pdf_pages:
            raise ValueError(f"PDF exceeds the {settings.max_pdf_pages}-page limit.")
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if extension == ".docx":
        from docx import Document

        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if "word/document.xml" not in archive.namelist():
                raise ValueError("DOCX document content is missing.")
        document = Document(io.BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ValueError("Only .txt, .pdf, and .docx files are supported.")


def analyze_transcript(filename: str, content: bytes) -> dict:
    if not content:
        raise ValueError("Transcript upload is empty.")
    if len(content) > settings.max_upload_bytes:
        raise ValueError(
            f"Transcript exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit."
        )

    transcript = _read_upload(filename, content)
    if not transcript.strip():
        raise ValueError("Transcript contains no readable text.")

    raw = ask_llm(
        TRANSCRIPT_ANALYSIS_PROMPT.format(transcript=transcript[:5000])
    )
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    result = json.loads(cleaned)
    if not isinstance(result, dict):
        raise ValueError("LLM returned an invalid transcript analysis.")
    return result
