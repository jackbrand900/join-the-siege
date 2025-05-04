import os
import sys
import pandas as pd
import joblib
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Add src/ to path so we can import extract_text
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.extractor import extract_text

TRAIN_CSV_PATH = os.path.join("files", "train_labels.csv")
SYNTHETIC_DIR = os.path.join("files", "synthetic")
MODEL_PATH = os.path.join("model", "document_classifier.pkl")

# Load training labels
df = pd.read_csv(TRAIN_CSV_PATH)

texts = []
labels = []

for row in df.itertuples(index=False):
    file_path = os.path.join(SYNTHETIC_DIR, row.filename)
    if not os.path.exists(file_path):
        print(f"Skipping {row.filename}: file not found.")
        continue

    try:
        text = extract_text(file_path)
        if not text.strip():
            print(f"Skipping {row.filename}: empty extracted text.")
            continue

        # 👇 Combine filename and content for training
        combined = f"{row.filename} {text}"
        texts.append(combined)
        labels.append(row.label)
    except Exception as e:
        print(f"Skipping {row.filename}: {e}")

# Stop if no usable data
if not texts:
    raise RuntimeError("❌ No documents were successfully loaded. "
                       "Check that Tesseract is installed for image OCR, and paths in train_labels.csv are correct.")

# Optional: internal train/val split (for local validation)
X_train, X_val, y_train, y_val = train_test_split(
    texts, labels, test_size=0.2, stratify=labels, random_state=42
)

# Build and train pipeline
model = Pipeline([
    ("tfidf", TfidfVectorizer(max_features=3000)),
    ("clf", LogisticRegression(max_iter=1000))
])

model.fit(X_train, y_train)
y_pred = model.predict(X_val)

print("\n✅ Classification Report (validation on 20% of train set):\n")
print(classification_report(y_val, y_pred))

# Save trained model
os.makedirs("model", exist_ok=True)
joblib.dump(model, MODEL_PATH)
print(f"\n✅ Model saved to {MODEL_PATH}")
