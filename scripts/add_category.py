import argparse
import os
import json
from scripts import generate_synthetic_docs

TEMPLATE_DIR = os.path.join("templates")

# Save a new template for the label
def save_template(label: str, fields: list[str]):
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    template_path = os.path.join(TEMPLATE_DIR, f"{label}.json")
    normalized_fields = [
        {"label": f.replace("_", " ").title(), "key": f.lower().replace(" ", "_")}
        for f in fields
    ]
    template = {
        "fields": normalized_fields,
        "layout": "\n".join([f"{f['label']}: {{{f['key']}}}" for f in normalized_fields])
    }
    with open(template_path, "w") as f:
        json.dump(template, f, indent=2)
    print(f"✅ Template saved to {template_path}")

# Add a new synthetic document category
def add_category(label: str, fields: list[str], num: int):
    label = label.lower()
    save_template(label, fields)

    print(f"📄 Generating {num} synthetic documents for label '{label}'...")
    generate_synthetic_docs.generate_docs(label, num)

# CLI entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True, help="New category label (e.g. payslip)")
    parser.add_argument("--fields", required=True, help="Comma-separated list of fields (e.g. Name,Employee ID,Amount,Date)")
    parser.add_argument("--num", type=int, default=10, help="Number of samples to generate")

    args = parser.parse_args()
    field_list = [f.strip() for f in args.fields.split(",") if f.strip()]
    if not field_list:
        raise ValueError("You must provide at least one field.")

    add_category(args.label, field_list, args.num)
