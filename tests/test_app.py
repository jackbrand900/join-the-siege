from io import BytesIO
import os
import sys
import random
import string
import pytest
import pandas as pd
from werkzeug.datastructures import FileStorage

# Fix module path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app import app, allowed_file
from src.classifier import classify_file

TEST_LABELS_PATH = os.path.join("files", "test_labels.csv")
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
# New API tests
# ------------------------
def test_retrain_endpoint(client):
    response = client.post('/retrain')
    assert response.status_code in (200, 500)
    assert "status" in response.get_json() or "error" in response.get_json()

def test_generate_category_valid(client):
    response = client.post("/generate_category", json={
        "label": "test_category",
        "num": 2,
        "fields": ["Field One", "Field Two", "Amount"]
    })
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["label"] == "test_category"
    assert json_data["samples_generated"] == 2

def test_generate_category_missing_fields(client):
    response = client.post("/generate_category", json={
        "label": "missing_fields_case"
    })
    assert response.status_code == 400
    assert "error" in response.get_json()

def test_generate_examples_invalid_label(client):
    response = client.post("/generate_examples", json={
        "label": "nonexistent_label_123",
        "num": 1
    })
    assert response.status_code == 500
    assert "error" in response.get_json()

def test_list_categories(client):
    response = client.get("/list_categories")
    assert response.status_code == 200
    json_data = response.get_json()
    assert "categories" in json_data
    assert isinstance(json_data["categories"], list)

def test_delete_category_missing_label(client):
    response = client.delete("/delete_category", json={})
    assert response.status_code == 400
    assert "error" in response.get_json()

def test_delete_category_valid(client):
    label = "test_category"
    client.post("/generate_category", json={
        "label": label,
        "num": 1,
        "fields": ["Test Field"]
    })
    response = client.delete("/delete_category", json={"label": label})
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"

# ------------------------
# Accuracy test on test set (original filenames)
# ------------------------
@pytest.mark.parametrize("method", ["model"])
def test_testset_accuracy(method, monkeypatch, strict):
    if method == "llm":
        monkeypatch.setattr("src.classifier.classify_with_llm", lambda text: "invoice" if "invoice" in text.lower() else (
            "bank_statement" if "bank" in text.lower() else (
                "drivers_license" if "license" in text.lower() or "licence" in text.lower() else "unknown"
            )
        ))

    df = pd.read_csv(TEST_LABELS_PATH)
    label_map = dict(zip(df["filename"], df["label"]))

    total, correct, errors = 0, 0, []

    for filename, true_label in label_map.items():
        path = os.path.join(FILES_DIR, filename)
        if not os.path.exists(path):
            errors.append(f"{filename}: file not found")
            continue

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
    print(f"\n🧪 [{method.upper()}] Test set accuracy: {correct}/{total} = {accuracy:.2%}")

    if errors:
        print(f"\n⚠️  {len(errors)} error(s):")
        for e in errors:
            print(f" - {e}")

    if strict and (accuracy < 1.0 or errors):
        pytest.fail(f"{method} failed under strict mode with accuracy {accuracy:.2%} and {len(errors)} errors.")

# ------------------------
# Accuracy test on test set (randomized filenames)
# ------------------------
@pytest.mark.parametrize("method", ["model"])
def test_testset_randomized_filenames(method, monkeypatch, strict):
    if method == "llm":
        monkeypatch.setattr("src.classifier.classify_with_llm", lambda text: "invoice" if "invoice" in text.lower() else (
            "bank_statement" if "bank" in text.lower() else (
                "drivers_license" if "license" in text.lower() or "licence" in text.lower() else "unknown"
            )
        ))

    df = pd.read_csv(TEST_LABELS_PATH)
    label_map = dict(zip(df["filename"], df["label"]))

    total, correct, errors = 0, 0, []

    for filename, true_label in label_map.items():
        path = os.path.join(FILES_DIR, filename)
        if not os.path.exists(path):
            errors.append(f"{filename}: file not found")
            continue

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
