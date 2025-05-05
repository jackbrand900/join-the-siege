import os
import sys
import pandas as pd
import joblib
from collections import Counter
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.compose import ColumnTransformer

# Add src/ to path so we can import extract_text
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.extractor import extract_text

# Define paths
FILES_ROOT = "files"
SYNTHETIC_DIR = os.path.join(FILES_ROOT, "synthetic")
TRAIN_CSV_PATH = os.path.join(FILES_ROOT, "train_labels.csv")
MODEL_PATH = os.path.join("model", "document_classifier.pkl")

# Load and preprocess the dataset
df = pd.read_csv(TRAIN_CSV_PATH)

examples = []
labels = []

# Extract features from files
for row in df.itertuples(index=False):
    base_path = os.path.join(FILES_ROOT, row.filename)
    synth_path = os.path.join(SYNTHETIC_DIR, row.filename)
    file_path = synth_path if os.path.exists(synth_path) else base_path

    if not os.path.exists(file_path):
        print(f"Skipping {row.filename}: file not found.")
        continue

    try:
        text = extract_text(file_path)
        if not text.strip():
            print(f"Skipping {row.filename}: empty extracted text.")
            continue

        cleaned_name = row.filename.lower().replace("_", " ").replace("-", " ")
        examples.append({
            "filename": cleaned_name,
            "text": text
        })
        labels.append(row.label)
    except Exception as e:
        print(f"Skipping {row.filename}: {e}")

# Abort if no usable documents found
if not examples:
    raise RuntimeError("No documents were successfully loaded.")

X_df = pd.DataFrame(examples)
y = labels

# Determine whether we can stratify based on class distribution
label_counts = Counter(y)
num_classes = len(label_counts)
test_size = 0.2
total_samples = len(y)
test_count = int(total_samples * test_size)

can_stratify = (
    num_classes >= 2 and
    all(count >= 2 for count in label_counts.values()) and
    test_count >= num_classes
)

# Perform stratified split if possible
if can_stratify:
    X_train, X_val, y_train, y_val = train_test_split(
        X_df, y, test_size=test_size, stratify=y, random_state=42
    )
    print(f"Stratified train/val split: {len(X_train)} train / {len(X_val)} val")
else:
    print("Not enough data to stratify — using full dataset.")
    X_train, y_train = X_df, y
    X_val, y_val = pd.DataFrame(), []

# Create preprocessing pipeline for both filename and text
preprocessor = ColumnTransformer(transformers=[
    ("filename_tfidf", TfidfVectorizer(max_features=500), "filename"),
    ("text_tfidf", TfidfVectorizer(max_features=3000), "text")
])

# Build the complete model pipeline
model = Pipeline([
    ("features", preprocessor),
    ("clf", LogisticRegression(max_iter=1000))
])

# Train the model
model.fit(X_train, y_train)

# Evaluate on validation set if available
if not X_val.empty:
    y_pred = model.predict(X_val)
    print("\nClassification Report (validation set):\n")
    print(classification_report(y_val, y_pred))
else:
    print("Trained on full dataset (no validation report)")

# Save the trained model
os.makedirs("model", exist_ok=True)
joblib.dump(model, MODEL_PATH)
print(f"\nModel saved to {MODEL_PATH}")
