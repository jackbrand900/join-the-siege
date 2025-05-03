from werkzeug.datastructures import FileStorage
from src.extractor import extract_text
import tempfile
import os
import joblib

# Load trained classifier (e.g., TF-IDF + LogisticRegression)
MODEL_PATH = "model/document_classifier.pkl"

try:
    pretrained_model = joblib.load(MODEL_PATH)
except Exception as e:
    print(f"Warning: Could not load model at {MODEL_PATH}. Model-based classification may not work.\n{e}")
    pretrained_model = None


# -----------------------
# 1. Filename-based classification
# -----------------------
def classify_by_filename(filename: str, content: str = "") -> str:
    """
    Classifies a file based on its filename and optionally its content.
    Returns one of: 'drivers_license', 'bank_statement', 'invoice', or 'unknown'
    """

    name = filename.lower()
    text = content.lower() if content else ""

    # Keywords per class
    keywords = {
        "drivers_license": [
            ["driver", "license"],
            ["driver", "licence"],
            ["dl", "id"],
        ],
        "bank_statement": [
            ["bank", "statement"],
            ["account", "summary"],
            ["account", "balance"],
        ],
        "invoice": [
            ["invoice"],
            ["amount", "due"],
            ["invoice", "number"],
            ["total", "payable"]
        ]
    }

    # Check for matches in filename and content
    for label, patterns in keywords.items():
        for pattern in patterns:
            if all(word in name for word in pattern) or all(word in text for word in pattern):
                return label

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
        if pretrained_model is None:
            raise RuntimeError("Model not loaded. Ensure 'model/document_classifier.pkl' exists.")
        return classify_by_model(text, model=pretrained_model)

    if method == "llm":
        return classify_with_llm(text)

    raise ValueError(f"Unknown classification method: {method}")
