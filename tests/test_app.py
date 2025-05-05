from io import BytesIO
import os
import sys
import random
import string
import pytest
from werkzeug.datastructures import FileStorage

# Setup path to import from src/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app import app, allowed_file
from src.classifier import classify_file

FILES_DIR = os.path.join("files", "synthetic")
LABELS_PATH = "tests/files/synthetic/labels.csv"

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# ✅ File extension checking
@pytest.mark.parametrize("filename, expected", [
    ("file.pdf", True),
    ("file.png", True),
    ("file.jpg", True),
    ("file.txt", False),
    ("file", False),
])
def test_allowed_file(filename, expected):
    assert allowed_file(filename) == expected

# ✅ Reject missing file
def test_no_file_in_request(client):
    response = client.post('/classify_file')
    assert response.status_code == 400

# ✅ Reject empty file name
def test_no_selected_file(client):
    data = {'file': (BytesIO(b""), '')}
    response = client.post('/classify_file', data=data, content_type='multipart/form-data')
    assert response.status_code == 400

# ✅ Return mocked label
def test_success(client, mocker):
    mocker.patch('src.app.classify_file', return_value='test_class')
    data = {'file': (BytesIO(b"dummy content"), 'file.pdf')}
    response = client.post('/classify_file', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert response.get_json() == {"file_class": "test_class"}

# ✅ Generate new category
def test_generate_category_valid(client):
    response = client.post("/generate_category", json={
        "label": "test_category",
        "num": 2,
        "fields": ["Field One", "Amount"]
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["label"] == "test_category"
    assert data["samples_generated"] == 2

# ✅ Reject missing fields
def test_generate_category_missing_fields(client):
    response = client.post("/generate_category", json={"label": "no_fields"})
    assert response.status_code == 400
    assert "error" in response.get_json()

# ✅ Reject examples for missing category
def test_generate_examples_invalid_label(client):
    response = client.post("/generate_examples", json={"label": "fake_label", "num": 1})
    assert response.status_code == 500

# ✅ List categories
def test_list_categories(client):
    response = client.get("/list_categories")
    assert response.status_code == 200
    assert isinstance(response.get_json().get("categories"), list)

# ✅ LLM classify newly generated file
def test_llm_generate_and_classify(client):
    label = "demo_invoice"
    fields = ["Invoice Number", "Date", "Amount", "Client Name"]

    # Generate new category
    res = client.post("/generate_category", json={
        "label": label,
        "fields": fields,
        "num": 1
    })
    assert res.status_code == 200

    # Grab generated file
    filenames = os.listdir(FILES_DIR)
    match = [f for f in filenames if f.startswith(label)]
    assert match, f"No files found for label {label}"

    # Classify using LLM
    path = os.path.join(FILES_DIR, match[0])
    with open(path, "rb") as f:
        file = FileStorage(stream=f, filename=match[0])
        prediction = classify_file(file, method="llm")
        assert isinstance(prediction, dict)
        print(f"LLM classified {match[0]} as: {prediction['label']}")

# ✅ Test classify with randomized filename
def test_classify_with_random_filename(client):
    label = "demo_random"
    fields = ["Name", "Account Number", "Amount"]
    client.post("/generate_category", json={
        "label": label,
        "fields": fields,
        "num": 1
    })

    files = [f for f in os.listdir(FILES_DIR) if f.startswith(label)]
    assert files

    path = os.path.join(FILES_DIR, files[0])
    ext = os.path.splitext(files[0])[1]
    random_name = ''.join(random.choices(string.ascii_lowercase, k=8)) + ext

    with open(path, "rb") as f:
        file = FileStorage(stream=f, filename=random_name)
        prediction = classify_file(file, method="llm")
        assert isinstance(prediction, dict)
        print(f"Classified with randomized name: {random_name} → {prediction['label']}")
