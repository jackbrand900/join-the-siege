import os
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import docx
import openpyxl
from PyPDF2 import PdfReader

def extract_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    elif ext in [".jpg", ".jpeg", ".png"]:
        return pytesseract.image_to_string(Image.open(path))

    elif ext == ".docx":
        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    elif ext == ".xlsx":
        try:
            df = pd.read_excel(path, sheet_name=None)
            return "\n".join(df[sheet].to_string(index=False) for sheet in df)
        except Exception as e:
            return f"Error reading Excel file: {e}"

    else:
        return ""

def extract_from_pdf(path: str) -> str:
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)

def extract_from_image(path: str) -> str:
    img = Image.open(path)
    return pytesseract.image_to_string(img)

def extract_from_docx(path: str) -> str:
    doc = docx.Document(path)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_from_xlsx(path: str) -> str:
    wb = openpyxl.load_workbook(path, data_only=True)
    text = []
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(values_only=True):
            line = " ".join([str(cell) for cell in row if cell])
            if line.strip():
                text.append(line)
    return "\n".join(text)
