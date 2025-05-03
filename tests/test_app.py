from io import BytesIO
import os
import random
import string
import pytest
import pandas as pd
from werkzeug.datastructures import FileStorage
from src.app import app, allowed_file
from src.classifier import classify_file

LABELS_PATH = os.path.join("files", "labels.csv")
FILES_DIR = os.path.join("files", "synthetic")


# ------------------------
# Flask client fixture
# ------------------------
@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# ------------------------
# Unit tests
# ------------------------
@pytest.mark.parametrize("filename, expected", [
    ("file.pdf", True),
    ("file.png", True),
    ("file.jpg", True),
    ("file.txt", False),
    ("file", False),
])
def test_allowed_file(filename, expected):
    assert allowed_file(filename) == expected


def test_no_file_in_request(client):
    response = client.post('/classify_file')
    assert response.status_code == 400


def test_no_selected_file(client):
    data = {'file': (BytesIO(b""), '')}
    response = client.post('/classify_file', data=data, content_type='multipart/form-data')
    assert response.status_code == 400


def test_success(client, mocker):
    mocker.patch('src.app.classify_file', return_value='test_class')
    data = {'file': (BytesIO(b"dummy content"), 'file.pdf')}
    response = client.post('/classify_file', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert response.get_json() == {"file_class": "test_class"}


# ------------------------
# Accuracy test for all files and all methods
# ------------------------

@pytest.mark.parametrize("method", ["filename", "model", "llm"])
def test_all_files_all_methods_with_accuracy(method, monkeypatch):
    if method == "llm":
        monkeypatch.setattr("src.classifier.classify_with_llm", lambda text: "invoice" if "invoice" in text.lower() else (
            "bank_statement" if "bank" in text.lower() else (
                "drivers_license" if "license" in text.lower() or "licence" in text.lower() else "unknown"
            )
        ))

    df = pd.read_csv(LABELS_PATH)
    label_map = dict(zip(df["filename"], df["label"]))

    total = 0
    correct = 0
    errors = []

    for filename in sorted(os.listdir(FILES_DIR)):
        if not filename.lower().endswith((".pdf", ".jpg", ".png")):
            continue

        true_label = label_map.get(filename, "unknown")
        path = os.path.join(FILES_DIR, filename)

        with open(path, "rb") as f:
            file = FileStorage(stream=BytesIO(f.read()), filename=filename)
            try:
                prediction = classify_file(file, method=method)
                result = "✅" if prediction == true_label else "❌"
                print(f"{result} [{method}] {filename:30} → predicted: {prediction:18} | expected: {true_label}")
                total += 1
                if prediction == true_label:
                    correct += 1
            except Exception as e:
                errors.append(f"{filename}: {e}")

    if total == 0:
        raise RuntimeError("No files tested. Check your directory and labels.")

    accuracy = correct / total
    print(f"\n🔍 [{method.upper()}] Accuracy: {correct}/{total} = {accuracy:.2%}")
    assert not errors, f"Errors occurred:\n" + "\n".join(errors)


# ------------------------
# Randomized filename test
# ------------------------

@pytest.mark.parametrize("method", ["filename", "model", "llm"])
def test_all_classifiers_with_random_filenames(method, monkeypatch):
    if method == "llm":
        monkeypatch.setattr("src.classifier.classify_with_llm", lambda text: "invoice" if "invoice" in text.lower() else (
            "bank_statement" if "bank" in text.lower() else (
                "drivers_license" if "license" in text.lower() or "licence" in text.lower() else "unknown"
            )
        ))

    df = pd.read_csv(LABELS_PATH)
    label_map = dict(zip(df["filename"], df["label"]))

    total = 0
    correct = 0
    errors = []

    for filename in sorted(os.listdir(FILES_DIR)):
        if not filename.lower().endswith((".pdf", ".jpg", ".png")):
            continue

        true_label = label_map.get(filename, "unknown")
        path = os.path.join(FILES_DIR, filename)
        ext = os.path.splitext(filename)[1]
        fake_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12)) + ext

        with open(path, "rb") as f:
            file = FileStorage(stream=BytesIO(f.read()), filename=fake_name)

            try:
                prediction = classify_file(file, method=method)
                result = "✅" if prediction == true_label else "❌"
                print(f"{result} [{method}] {fake_name:30} → predicted: {prediction:18} | expected: {true_label}")
                total += 1
                if prediction == true_label:
                    correct += 1
            except Exception as e:
                errors.append(f"{filename} (as {fake_name}): {e}")

    if total == 0:
        raise RuntimeError("No files tested with randomized filenames.")

    accuracy = correct / total
    print(f"\n🔍 [{method.upper()} w/ random filenames] Accuracy: {correct}/{total} = {accuracy:.2%}")
    assert not errors, f"Errors occurred:\n" + "\n".join(errors)
