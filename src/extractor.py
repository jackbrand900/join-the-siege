import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import os

def extract_text(path: str) -> str:
    """Extract text from a file based on its extension."""
    ext = os.path.splitext(path)[1].lower()

    if ext == '.pdf':
        return extract_text_from_pdf(path)
    elif ext in ['.jpg', '.jpeg', '.png']:
        return extract_text_from_image(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def extract_text_from_pdf(path: str) -> str:
    """Extract text from a PDF using PyMuPDF."""
    doc = fitz.open(path)
    return " ".join([page.get_text() for page in doc])

def extract_text_from_image(path: str) -> str:
    """Extract text from an image using Tesseract OCR."""
    image = Image.open(path)
    return pytesseract.image_to_string(image)
