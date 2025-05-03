from werkzeug.datastructures import FileStorage
from src.extractor import extract_text
from src.categories import CategoryManager
import tempfile
import os
import joblib
import requests

# Load trained classifier (e.g., TF-IDF + LogisticRegression)
MODEL_PATH = "model/document_classifier.pkl"

try:
    pretrained_model = joblib.load(MODEL_PATH)
except Exception as e:
    print(f"Warning: Could not load model at {MODEL_PATH}. Model-based classification may not work.\n{e}")
    pretrained_model = None

# Initialize category manager
category_manager = CategoryManager()

# -----------------------
# 1. Filename-based classification
# -----------------------
def classify_by_filename(filename: str, content: str = "") -> str:
    """
    Classifies a file based on its filename and optionally its content.
    Returns one of the known categories or 'unknown'
    """
    name = filename.lower()
    text = content.lower() if content else ""
    
    # Try to match against filename first
    result = category_manager.match_text(name)
    if result != "unknown":
        return result
        
    # If no match in filename, try content
    return category_manager.match_text(text)


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
    try:
        API_URL = "https://api-inference.huggingface.co/models/TinyLlama/TinyLlama-1.1B-Chat-v1.0"

        prompt = f"""
            Classify the following document:
            {text[:1000]}

            Choose one: invoice, bank_statement, drivers_license, unknown.
        """

        response = requests.post(API_URL, headers={}, json={"inputs": prompt})
        return response.json()[0]["generated_text"].strip().lower()
    except Exception as e:
        raise RuntimeError(f"LLM classification failed: {e}")


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
        if pretrained_model is None:
            raise RuntimeError("Model not loaded. Ensure 'model/document_classifier.pkl' exists.")
        return classify_by_model(text, model=pretrained_model)

    if method == "llm":
        return classify_with_llm(text)

    raise ValueError(f"Unknown classification method: {method}")
