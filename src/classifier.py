import os
import tempfile
import requests
import joblib
from werkzeug.datastructures import FileStorage
from src.extractor import extract_text
from src.categories import CategoryManager

# -----------------------
# Load trained model
# -----------------------
MODEL_PATH = "model/document_classifier.pkl"

try:
    pretrained_model = joblib.load(MODEL_PATH)
except Exception as e:
    print(f"⚠️ Warning: Could not load model at {MODEL_PATH}. Model-based classification may not work.\n{e}")
    pretrained_model = None

# -----------------------
# Category Manager (keyword-based)
# -----------------------
category_manager = CategoryManager()


# -----------------------
# 1. Filename-based classification
# -----------------------
def classify_by_filename(filename: str, content: str = "") -> str:
    name = filename.lower()
    text = content.lower()

    # Try filename-based match
    result = category_manager.match_text(name)
    if result != "unknown":
        return result

    # Try text-based match
    return category_manager.match_text(text)


# -----------------------
# 2. Model-based classification
# -----------------------
def classify_by_model(text: str, model=None) -> str:
    if model is None:
        raise ValueError("No model provided for model-based classification.")
    return model.predict([text])[0]


# -----------------------
# 3. LLM-based classification (e.g. Hugging Face API)
# -----------------------
def classify_with_llm(text: str) -> str:
    try:
        API_URL = "https://api-inference.huggingface.co/models/TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        headers = {}  # optionally: {"Authorization": f"Bearer {os.environ.get('HF_API_KEY')}"}

        prompt = f"""
Classify the following document:
{text[:1000]}

Choose one: invoice, bank_statement, drivers_license, unknown.
"""

        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
        response.raise_for_status()
        output = response.json()

        # Handle Hugging Face API response format
        if isinstance(output, list) and "generated_text" in output[0]:
            return output[0]["generated_text"].strip().lower()

        if isinstance(output, dict) and "generated_text" in output:
            return output["generated_text"].strip().lower()

        raise RuntimeError(f"Unexpected LLM response: {output}")

    except Exception as e:
        raise RuntimeError(f"LLM classification failed: {e}")


# -----------------------
# Main entry point
# -----------------------
def classify_file(file: FileStorage, method: str = "filename", model=None) -> str:
    filename = file.filename
    suffix = os.path.splitext(filename)[1]

    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        text = extract_text(tmp_path).lower()
    finally:
        os.remove(tmp_path)

    # Dispatch based on method
    if method == "filename":
        return classify_by_filename(filename, content=text)

    if method == "model":
        if pretrained_model is None:
            raise RuntimeError("Model not loaded. Ensure 'model/document_classifier.pkl' exists.")
        return classify_by_model(text, model=pretrained_model)

    if method == "llm":
        return classify_with_llm(text)

    raise ValueError(f"Unknown classification method: {method}")
