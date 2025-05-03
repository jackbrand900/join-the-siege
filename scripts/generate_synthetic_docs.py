import os
import random
import pandas as pd
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from pdf2image import convert_from_path
from src.categories import CategoryManager
from src.templates import TemplateManager, DEFAULT_TEMPLATES

OUTPUT_DIR = "files/synthetic"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_pdf(text, pdf_path):
    c = canvas.Canvas(pdf_path, pagesize=LETTER)
    for i, line in enumerate(text.splitlines()):
        c.drawString(100, 750 - 15 * i, line)
    c.save()

def convert_pdf_to_jpg(pdf_path, jpg_path):
    images = convert_from_path(pdf_path)
    if images:
        images[0].save(jpg_path, 'JPEG')

def generate_docs(num_per_class=10):
    rows = []
    category_manager = CategoryManager()
    template_manager = TemplateManager(DEFAULT_TEMPLATES)

    for category_name in category_manager.get_category_names():
        template = template_manager.get_random_template(category_name)
        if not template:
            print(f"Warning: No template found for category {category_name}")
            continue

        for i in range(num_per_class):
            # Generate random values for template variables
            values = {
                "id": str(random.randint(100000, 999999)),
                "amount": str(round(random.uniform(20, 5000), 2)),
                "date": f"{random.randint(1,12):02d}/{random.randint(1,28):02d}/2023"
            }
            
            # Only use variables that are actually in the template
            template_values = {k: values[k] for k in template.variables if k in values}
            content = template.content.format(**template_values)
            
            base_name = f"{category_name}_synth_{i}"
            pdf_path = os.path.join(OUTPUT_DIR, f"{base_name}.pdf")
            jpg_path = os.path.join(OUTPUT_DIR, f"{base_name}.jpg")

            generate_pdf(content, pdf_path)
            convert_pdf_to_jpg(pdf_path, jpg_path)

            rows.append({"filename": f"{base_name}.pdf", "label": category_name})
            rows.append({"filename": f"{base_name}.jpg", "label": category_name})

    df = pd.DataFrame(rows)
    label_csv = os.path.join("files", "labels.csv")

    if os.path.exists(label_csv):
        existing = pd.read_csv(label_csv)
        df = pd.concat([existing, df], ignore_index=True).drop_duplicates()

    df.to_csv(label_csv, index=False)
    print(f"✅ Generated {len(rows)} synthetic files and updated labels.csv")

if __name__ == "__main__":
    generate_docs()
