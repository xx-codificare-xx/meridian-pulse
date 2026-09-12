from __future__ import annotations

import io
import json
import re
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

    prompt = f"""Return ONLY valid JSON, with concise values and no markdown.
Use exactly this shape, with no more than one item in each array:
{{"pulse_check":"short summary","green_signals":["one signal"],"red_signals":["one risk"],"future_horizon":["one outlook"],"data_spotlight":["one metric"],"speakers":[],"company":"unknown","period":"unknown"}}
Analyze this transcript excerpt:
{transcript[:1000]}"""
    raw = ask_llm(prompt, max_tokens=3000)
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        compact_prompt = f"""Return ONLY valid JSON, with concise values and no markdown.
{{"pulse_check":"short summary","green_signals":["one signal"],"red_signals":["one risk"],"future_horizon":["one outlook"],"data_spotlight":["one metric"],"speakers":[],"company":"unknown","period":"unknown"}}
Transcript excerpt:
{transcript[:700]}"""
        compact = ""
        try:
            compact = ask_llm(compact_prompt, max_tokens=3000)
            compact = compact.replace("```json", "").replace("```", "").strip()
            result = json.loads(compact)
        except (RuntimeError, ValueError, json.JSONDecodeError):
            def field(name: str, default: str) -> str:
                match = re.search(rf'"{name}"\s*:\s*"((?:\\.|[^"\\])*)', compact)
                return match.group(1).replace('\\"', '"') if match else default

            result = {
                "pulse_check": field("pulse_check", "The transcript was received, but the model returned incomplete structured output."),
                "green_signals": ["Review the source transcript for positive operating signals."],
                "red_signals": ["Review the source transcript for risks and uncertainties."],
                "future_horizon": ["Review the source transcript for forward-looking plans."],
                "data_spotlight": ["Review the source transcript for reported metrics."],
                "speakers": [],
                "company": field("company", "Unknown"),
                "period": field("period", "Unknown"),
            }
    if not isinstance(result, dict):
        raise ValueError("LLM returned an invalid transcript analysis.")
    return result
