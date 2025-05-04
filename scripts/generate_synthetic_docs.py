import os
import json
import random
from docx import Document
from openpyxl import Workbook
import pandas as pd
import subprocess
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from pdf2image import convert_from_path
from PIL import Image, ImageFilter
from sklearn.model_selection import train_test_split
import subprocess

TEMPLATE_DIR = "templates"
OUTPUT_DIR = "files/synthetic"
LABELS_PATH = "files/labels.csv"
TRAIN_LABELS_PATH = "files/train_labels.csv"
TEST_LABELS_PATH = "files/test_labels.csv"
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx', 'xlsx'}

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------
# 🧠 Field Value Generator
# -----------------------
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

# -----------------------
# 📄 PDF + JPG Generation
# -----------------------
def generate_pdf(content, path):
    c = canvas.Canvas(path, pagesize=LETTER)
    for i, line in enumerate(content.splitlines()):
        c.drawString(100, 750 - 15 * i, line)
    c.save()

def convert_pdf_to_image(pdf_path, image_path, fmt="JPEG"):
    images = convert_from_path(pdf_path)
    if images:
        img = images[0]
        if random.random() < 0.4:
            img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))
        if random.random() < 0.3:
            img = img.rotate(random.uniform(-2, 2), expand=True, fillcolor="white")
        img.save(image_path, fmt, quality=random.randint(70, 95))

def generate_docx(content, path):
    doc = Document()
    for line in content.strip().splitlines():
        doc.add_paragraph(line)
    doc.save(path)


def generate_xlsx(content, path):
    wb = Workbook()
    ws = wb.active
    for i, line in enumerate(content.strip().splitlines(), 1):
        ws.cell(row=i, column=1, value=line)
    wb.save(path)


def generate_docs(label, num_samples, test_size=0.2):
    label = label.lower()
    template_path = os.path.join(TEMPLATE_DIR, f"{label}.json")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"No template found for category '{label}'")

    with open(template_path, "r") as f:
        template = json.load(f)

    fields = template["fields"]

    rows = []

    for i in range(num_samples):
        # Randomly sample a subset of fields and shuffle their order
        sampled_fields = random.sample(fields, k=random.randint(2, len(fields)))
        random.shuffle(sampled_fields)

        # Generate fake values for the sampled fields
        field_map = {f["key"]: fake_value(f["label"]) for f in sampled_fields}

        # Build content dynamically based on sampled fields
        content_lines = [f"{f['label']}: {field_map[f['key']]}" for f in sampled_fields]
        content = "\n".join(content_lines)

        base = f"{label}_synth_{i}"

        if "pdf" in ALLOWED_EXTENSIONS:
            pdf_path = os.path.join(OUTPUT_DIR, f"{base}.pdf")
            generate_pdf(content, pdf_path)
            rows.append({"filename": f"{base}.pdf", "label": label})

            if "jpg" in ALLOWED_EXTENSIONS or "jpeg" in ALLOWED_EXTENSIONS:
                jpg_path = os.path.join(OUTPUT_DIR, f"{base}.jpg")
                convert_pdf_to_image(pdf_path, jpg_path, fmt="JPEG")
                rows.append({"filename": f"{base}.jpg", "label": label})

            if "png" in ALLOWED_EXTENSIONS:
                png_path = os.path.join(OUTPUT_DIR, f"{base}.png")
                convert_pdf_to_image(pdf_path, png_path, fmt="PNG")
                rows.append({"filename": f"{base}.png", "label": label})

        if "docx" in ALLOWED_EXTENSIONS:
            docx_path = os.path.join(OUTPUT_DIR, f"{base}.docx")
            generate_docx(content, docx_path)
            rows.append({"filename": f"{base}.docx", "label": label})

        if "xlsx" in ALLOWED_EXTENSIONS:
            xlsx_path = os.path.join(OUTPUT_DIR, f"{base}.xlsx")
            generate_xlsx(content, xlsx_path)
            rows.append({"filename": f"{base}.xlsx", "label": label})

    df = pd.DataFrame(rows)
    train_df, test_df = train_test_split(df, test_size=test_size, stratify=df["label"], random_state=42)

    for path, split_df in [(TRAIN_LABELS_PATH, train_df), (TEST_LABELS_PATH, test_df)]:
        if os.path.exists(path):
            existing = pd.read_csv(path)
            df_combined = pd.concat([existing, split_df], ignore_index=True).drop_duplicates()
        else:
            df_combined = split_df
        df_combined.to_csv(path, index=False)

    pd.concat([train_df, test_df]).to_csv(LABELS_PATH, index=False)

    print(f"✅ Generated {len(rows)} files for label '{label}' across all file types.")
    print(f"📁 Train: {len(train_df)}, Test: {len(test_df)}")
# -----------------------
# 🎯 Save template + call generate_docs + retrain
# -----------------------
def generate_category(label, fields, num_samples):
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    template_path = os.path.join(TEMPLATE_DIR, f"{label}.json")

    # Normalize fields into field objects if they’re just strings
    normalized_fields = [
        f if isinstance(f, dict) else {"label": f.replace("_", " ").title(), "key": f.lower().replace(" ", "_")}
        for f in fields
    ]

    # Extract keys already in field list
    existing_keys = {field["key"] for field in normalized_fields}

    # Build default layout if none exists
    layout = "\n".join([f"{field['label']}: {{{field['key']}}}" for field in normalized_fields])

    # Ensure all keys in layout are in fields
    keys_in_layout = set()
    start = 0
    while True:
        start = layout.find("{", start)
        if start == -1:
            break
        end = layout.find("}", start)
        if end == -1:
            break
        key = layout[start+1:end]
        keys_in_layout.add(key)
        start = end + 1

    for key in keys_in_layout - existing_keys:
        normalized_fields.append({
            "label": key.replace("_", " ").title(),
            "key": key
        })

    # Save as structured JSON template
    template = {
        "fields": normalized_fields,
        "layout": layout
    }

    with open(template_path, "w") as f:
        json.dump(template, f, indent=2)

    print(f"📝 Template saved to {template_path}")

    if num_samples > 0:
        generate_docs(label, num_samples)


# -----------------------
# 🛠️ CLI Entry Point
# -----------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True, help="Label to generate")
    parser.add_argument("--fields", required=True, help="Comma-separated fields (e.g. Name,Amount,Date)")
    parser.add_argument("--num", type=int, default=5, help="Number of synthetic samples")
    args = parser.parse_args()

    field_list = [f.strip() for f in args.fields.split(",") if f.strip()]
    generate_category(args.label, field_list, args.num)
