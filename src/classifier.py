import os
import re
import tempfile
import joblib
import pandas as pd
import requests
from dotenv import load_dotenv
from werkzeug.datastructures import FileStorage
from src.extractor import extract_text

# Load environment variables
load_dotenv()
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
TOGETHER_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"
MODEL_PATH = "model/document_classifier.pkl"
TEMPLATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))

# Load trained model
try:
    pretrained_model = joblib.load(MODEL_PATH)
except Exception as e:
    print(f"Warning: Could not load model at {MODEL_PATH}. Model-based classification may not work.\n{e}")
    pretrained_model = None

# Retrieve all available labels from template directory
def get_all_labels():
    if not os.path.exists(TEMPLATE_DIR):
        return []
    return [
        fname.replace(".json", "")
        for fname in os.listdir(TEMPLATE_DIR)
        if fname.endswith(".json")
    ]

# Classify based on filename and content patterns
def classify_by_filename(filename: str, content: str = "") -> str:
    name = filename.lower()
    text = content.lower() if content else ""

    keywords = {
        "drivers_license": [["driver", "license"], ["driver", "licence"], ["dl", "id"]],
        "bank_statement": [["bank", "statement"], ["account", "summary"], ["account", "balance"]],
        "invoice": [["invoice"], ["amount", "due"], ["invoice", "number"], ["total", "payable"]],
        "pay_stub": [["employee", "id"], ["net", "pay"], ["gross", "pay"]],
    }

    for label, patterns in keywords.items():
        for pattern in patterns:
            if all(word in name for word in pattern) or all(word in text for word in pattern):
                return label

    return "unknown"

# Classify using trained model
def classify_by_model(text: str, filename: str = "", model=None) -> dict:
    if model is None:
        raise ValueError("No model provided for model-based classification.")

    df = pd.DataFrame([{
        "filename": filename.lower().replace("_", " "),
        "text": text
    }])

    probs = model.predict_proba(df)[0]
    classes = model.classes_
    max_idx = probs.argmax()
    predicted_label = classes[max_idx]
    confidence = float(probs[max_idx])

    return {
        "label": predicted_label,
        "confidence": round(confidence, 4)
    }

# Classify using LLM via Together API
def classify_by_llm(text: str, filename: str = "") -> dict:
    if not TOGETHER_API_KEY:
        raise RuntimeError("TOGETHER_API_KEY is not set in environment.")

    labels = get_all_labels()
    if not labels:
        raise RuntimeError("No templates found to determine categories.")

    categories_str = ", ".join(labels)
    system_message = (
        f"You are an AI assistant that classifies documents into one of the following categories: "
        f"{categories_str}. Respond with only one word — the exact label. Do not explain your answer."
    )

    user_prompt = f"""Document content:
{text[:4000]}

What is the category?"""

    payload = {
        "model": TOGETHER_MODEL,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0,
        "max_tokens": 20,
    }

    response = requests.post(
        "https://api.together.xyz/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        },
        json=payload
    )

    print("Together API raw response:", response.text)

    try:
        content = response.json()["choices"][0]["message"]["content"]
        print("LLM content:", content)

        raw_label = content.strip().lower().replace(" ", "_")

        if raw_label in labels:
            label = raw_label
        else:
            match = re.search(r'"([^"]+)"', content)
            if match:
                label = match.group(1).strip().lower().replace(" ", "_")
            else:
                label = next((lbl for lbl in labels if lbl in content.lower()), "unknown")

        if label not in labels:
            print(f"Label '{label}' not in known templates: {labels}")
            label = "unknown"

    except Exception as e:
        print("Failed to extract label from response:", e)
        label = "unknown"

    return {"label": label, "confidence": None}

# Unified classification entrypoint
def classify_file(file: FileStorage, method: str = "filename", model=None):
    filename = file.filename

    if method == "filename":
        return {"label": classify_by_filename(filename)}

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
        return classify_by_model(text, filename, model=pretrained_model)

    if method == "llm":
        return classify_by_llm(text, filename)

    raise ValueError(f"Unknown classification method: {method}")
