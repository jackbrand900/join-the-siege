import os
import sys
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

# Add src/ to path so we can import extract_text
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.extractor import extract_text

def train_model():
    # Load labeled data
    label_csv_path = os.path.join("files", "labels.csv")
    df = pd.read_csv(label_csv_path)

    texts = []
    labels = []

    for row in df.itertuples(index=False):
        file_path = os.path.join("files", "synthetic", row.filename)
        if not os.path.exists(file_path):
            print(f"Skipping {row.filename}: file not found.")
            continue

        try:
            text = extract_text(file_path)
            if not text.strip():
                print(f"Skipping {row.filename}: empty extracted text.")
                continue
            texts.append(text)
            labels.append(row.label)
        except Exception as e:
            print(f"Skipping {row.filename}: {e}")

    # Stop if no data was successfully loaded
    if not texts:
        raise RuntimeError("❌ No documents were successfully loaded. "
                           "Check that Tesseract is installed for image OCR, and that your paths in files/labels.csv are correct.")

    # Split and train
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, stratify=labels, random_state=42
    )

    model = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=3000)),
        ("clf", LogisticRegression(max_iter=1000))
    ])

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    print("\n✅ Classification Report:\n")
    print(classification_report(y_test, y_pred))

    # Save model
    os.makedirs("model", exist_ok=True)
    joblib.dump(model, "model/document_classifier.pkl")
    print("\n✅ Model saved to model/document_classifier.pkl")

# Optional: Run as a script
if __name__ == "__main__":
    train_model()
