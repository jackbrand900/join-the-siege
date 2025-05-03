from werkzeug.datastructures import FileStorage
from src.extractor import extract_text
import tempfile
import os

# -----------------------
# 1. Filename-based classification
# -----------------------
def classify_by_filename(filename: str) -> str:
    name = filename.lower()
    if "driver" in name and ("license" in name or "licence" in name):
        return "drivers_license"
    if "bank_statement" in name:
        return "bank_statement"
    if "invoice" in name:
        return "invoice"
    return "unknown"


# -----------------------
# 2. Model-based classification
# -----------------------
def classify_by_model(text: str, model=None) -> str:
    if model is None:
        raise ValueError("No model provided for model-based classification.")
    return model.predict([text])[0]


# -----------------------
# 3. LLM-based classification (OpenAI example)
# -----------------------
def classify_with_llm(text: str) -> str:
    import openai

    prompt = f"""
You are a document classifier. Categorize the document as one of the following:
- invoice
- bank_statement
- drivers_license
- unknown

Document:
{text[:3000]}

Respond with only the label.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a document classification assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response['choices'][0]['message']['content'].strip().lower()


# -----------------------
# Main entry point
# -----------------------
def classify_file(file: FileStorage, method: str = "filename", model=None) -> str:
    filename = file.filename

    if method == "filename":
        return classify_by_filename(filename)

    # Extract content from the file
    suffix = os.path.splitext(filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        text = extract_text(tmp_path).lower()
    finally:
        os.remove(tmp_path)

    if method == "model":
        return classify_by_model(text, model=model)

    if method == "llm":
        return classify_with_llm(text)

    raise ValueError(f"Unknown classification method: {method}")
