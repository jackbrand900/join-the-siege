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
# Command-line flag
# ------------------------
def pytest_addoption(parser):
    parser.addoption("--strict", action="store_true", default=False, help="Fail tests on accuracy mismatches")


@pytest.fixture
def strict(request):
    return request.config.getoption("--strict")


# ------------------------
# Flask client
# ------------------------
@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# ------------------------
# Basic tests
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
# Accuracy test with original filenames
# ------------------------

@pytest.mark.parametrize("method", ["filename", "model", "llm"])
def test_all_files_accuracy(method, monkeypatch, strict):
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

    accuracy = correct / total if total else 0
    print(f"\n📊 [{method.upper()}] Accuracy: {correct}/{total} = {accuracy:.2%}")

    if errors:
        print(f"\n⚠️  {len(errors)} error(s):")
        for e in errors:
            print(f" - {e}")

    if strict and (accuracy < 1.0 or errors):
        pytest.fail(f"{method} failed under strict mode with accuracy {accuracy:.2%} and {len(errors)} errors.")


# ------------------------
# Accuracy test with randomized filenames
# ------------------------

@pytest.mark.parametrize("method", ["filename", "model", "llm"])
def test_accuracy_randomized_filenames(method, monkeypatch, strict):
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
        randomized = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + ext

        with open(path, "rb") as f:
            file = FileStorage(stream=BytesIO(f.read()), filename=randomized)
            try:
                prediction = classify_file(file, method=method)
                result = "✅" if prediction == true_label else "❌"
                print(f"{result} [{method}] {randomized:30} → predicted: {prediction:18} | expected: {true_label}")
                total += 1
                if prediction == true_label:
                    correct += 1
            except Exception as e:
                errors.append(f"{filename} (as {randomized}): {e}")

    accuracy = correct / total if total else 0
    print(f"\n📎 [{method.upper()}] Accuracy with randomized filenames: {correct}/{total} = {accuracy:.2%}")

    if errors:
        print(f"\n⚠️  {len(errors)} error(s):")
        for e in errors:
            print(f" - {e}")

    if strict and (accuracy < 1.0 or errors):
        pytest.fail(f"{method} (randomized) failed under strict mode with accuracy {accuracy:.2%} and {len(errors)} errors.")
