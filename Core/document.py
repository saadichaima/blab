# core/document.py

import fitz  # PyMuPDF
from docx import Document as DocxDocument

def extract_text(file):
    """Extrait le texte brut d'un fichier PDF ou DOCX"""
    if file.name.lower().endswith(".pdf"):
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "".join(page.get_text() for page in doc)
    elif file.name.lower().endswith(".docx"):
        document = DocxDocument(file)
        return "\n".join(p.text for p in document.paragraphs)
    return ""

def chunk_text(text, size=1000, overlap=200):
    """Divise le texte en blocs avec chevauchement"""
    words = text.split()
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size - overlap)]
