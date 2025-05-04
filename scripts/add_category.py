import argparse
import os
import random
import pandas as pd
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from pdf2image import convert_from_path
import subprocess

OUTPUT_DIR = "files/synthetic"
LABELS_PATH = "files/labels.csv"
DEFAULT_NUM = 10

def fake_value(field):
    field = field.lower()
    if "name" in field:
        return random.choice(["John Smith", "Jane Doe", "Chris Johnson", "Maria Garcia"])
    elif "id" in field:
        return str(random.randint(100000, 999999))
    elif "date" in field:
        return f"{random.randint(1,12):02d}/{random.randint(1,28):02d}/2024"
    elif "amount" in field or "salary" in field or "total" in field:
        return f"${round(random.uniform(1000, 5000), 2)}"
    else:
        return str(random.randint(1000, 9999))

def generate_pdf(content: str, pdf_path: str):
    c = canvas.Canvas(pdf_path, pagesize=LETTER)
    for i, line in enumerate(content.strip().split("\n")):
        c.drawString(100, 750 - 15 * i, line)
    c.save()

def generate_jpg(pdf_path, jpg_path):
    pages = convert_from_path(pdf_path, first_page=1, last_page=1)
    pages[0].save(jpg_path, "JPEG")

def build_template(label: str, fields: list[str]) -> str:
    lines = [f"Document Type: {label.upper()}"]
    for field in fields:
        value = fake_value(field)
        lines.append(f"{field}: {value}")
    return "\n".join(lines)

def add_category(label: str, fields: list[str], num: int):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    label = label.lower()
    new_rows = []

    for i in range(num):
        content = build_template(label, fields)
        base = f"{label}_synth_{i}"
        pdf_path = os.path.join(OUTPUT_DIR, f"{base}.pdf")
        jpg_path = os.path.join(OUTPUT_DIR, f"{base}.jpg")

        generate_pdf(content, pdf_path)
        generate_jpg(pdf_path, jpg_path)

        new_rows.append({"filename": f"{base}.pdf", "label": label})
        new_rows.append({"filename": f"{base}.jpg", "label": label})

    df_new = pd.DataFrame(new_rows)

    if os.path.exists(LABELS_PATH):
        df_existing = pd.read_csv(LABELS_PATH)
        df = pd.concat([df_existing, df_new], ignore_index=True).drop_duplicates()
    else:
        df = df_new

    df.to_csv(LABELS_PATH, index=False)
    print(f"✅ Added {2*num} files for label '{label}'")

    # Optional: retrain model
    print("🔄 Retraining model...")
    subprocess.run(["python", "scripts/train_model.py"], check=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True, help="New category label (e.g. payslip)")
    parser.add_argument("--fields", required=True, help="Comma-separated list of fields (e.g. Name,Employee ID,Amount,Date)")
    parser.add_argument("--num", type=int, default=DEFAULT_NUM, help="Number of samples to generate")

    args = parser.parse_args()
    field_list = [f.strip() for f in args.fields.split(",") if f.strip()]
    if not field_list:
        raise ValueError("You must provide at least one field.")

    add_category(args.label, field_list, args.num)
