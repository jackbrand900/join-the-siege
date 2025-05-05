import os
import pytesseract
import pandas as pd
from PIL import Image
import fitz  # PyMuPDF
import docx
import openpyxl
from PyPDF2 import PdfReader

# Main text extraction dispatcher based on file extension
def extract_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        return extract_from_pdf(path)
    elif ext in [".jpg", ".jpeg", ".png"]:
        return extract_from_image(path)
    elif ext == ".docx":
        return extract_from_docx(path)
    elif ext == ".xlsx":
        return extract_from_xlsx(path)
    else:
        return ""

# Extract text from PDF using PyMuPDF or PyPDF2 fallback
def extract_from_pdf(path: str) -> str:
    try:
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        doc = fitz.open(path)
        return "\n".join(page.get_text() for page in doc)

# Extract text from image using OCR
def extract_from_image(path: str) -> str:
    img = Image.open(path)
    return pytesseract.image_to_string(img)

# Extract text from DOCX file
def extract_from_docx(path: str) -> str:
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

# Extract text from XLSX file
def extract_from_xlsx(path: str) -> str:
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
        text = []
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                line = " ".join(str(cell) for cell in row if cell)
                if line.strip():
                    text.append(line)
        return "\n".join(text)
    except Exception as e:
        return f"Error reading Excel file: {e}"
