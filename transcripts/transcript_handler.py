# =============================================================================
# transcripts/transcript_handler.py — Read txt, pdf, docx files
# =============================================================================

import os


def read_txt(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def read_pdf(filepath: str) -> str:
    try:
        import PyPDF2
        text = ""
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"Could not read PDF: {e}"


def read_docx(filepath: str) -> str:
    try:
        from docx import Document
        doc  = Document(filepath)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        return f"Could not read DOCX: {e}"


def read_transcript(filepath: str) -> str:
    """Auto-detect file type and extract text."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".txt":
        return read_txt(filepath)
    elif ext == ".pdf":
        return read_pdf(filepath)
    elif ext == ".docx":
        return read_docx(filepath)
    else:
        return f"Unsupported file type: {ext}"


def get_transcript_files(folder: str) -> list:
    """Return all supported transcript files in folder."""
    supported = {".txt", ".pdf", ".docx"}
    if not os.path.exists(folder):
        return []
    return [
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in supported
    ]