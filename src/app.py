from flask import Flask, request, jsonify, send_from_directory
from scripts import generate_synthetic_docs
import scripts.add_category as ac
from src.classifier import classify_file
import logging
import os
import pandas as pd
from flask_cors import CORS
from werkzeug.datastructures import FileStorage
from time import sleep

# Flask app setup to serve React/Vite frontend
app = Flask(__name__, static_folder="../frontend/build", static_url_path="/")
CORS(app)

# Constants
FILES_ROOT = "files"
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx', 'xlsx'}
BASE_DIRS = ["files", "files/synthetic"]

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Serve frontend
@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def serve_static_file(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/classify_file', methods=['POST'])
def classify_file_route():
    logger.debug("Received classify_file request")
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    method = request.form.get('method', 'filename')
    if method not in {"filename", "model", "llm"}:
        return jsonify({"error": f"Unsupported method: {method}"}), 400

    try:
        result = classify_file(file, method=method)
        return jsonify({"file_class": result}), 200
    except Exception as e:
        logger.error(f"Classification error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/classify_by_path", methods=["POST"])
def classify_by_path():
    data = request.get_json(force=True)
    path = data.get("path")
    method = data.get("method", "model")

    if not path or not os.path.exists(path):
        return jsonify({"error": "Invalid or missing path"}), 400

    try:
        with open(path, "rb") as f:
            file = FileStorage(stream=f, filename=os.path.basename(path))
            result = classify_file(file, method=method)
            return jsonify({"file_class": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/generate_category", methods=["POST"])
def generate_category_route():
    data = request.get_json(force=True)
    label = data.get("label")
    num = data.get("num", 10)
    fields = data.get("fields")

    if not label:
        return jsonify({"error": "Missing label"}), 400
    if not fields:
        return jsonify({"error": "Missing fields"}), 400

    try:
        logger.info(f"Generating category: {label} x{num} fields: {fields}")
        ac.add_category(label, fields, 0)
        generate_synthetic_docs.generate_docs(label, num)

        return jsonify({"status": "success", "label": label, "samples_generated": num, "retrained": True}), 200
    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/generate_examples", methods=["POST"])
def generate_examples_route():
    data = request.get_json(force=True)
    label = data.get("label")
    num = data.get("num", 10)

    if not label:
        return jsonify({"error": "Missing label"}), 400

    try:
        generate_synthetic_docs.generate_docs(label, num)
        return jsonify({"status": "success", "label": label, "samples_generated": num}), 200
    except Exception as e:
        logger.error(f"Example generation error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/classify_all_files", methods=["POST"])
def classify_all_files():
    method = request.get_json(force=True).get("method", "filename")
    if method not in {"filename", "model", "llm"}:
        return jsonify({"error": f"Unsupported method: {method}"}), 400

    results = []
    correct = 0
    total = 0
    batch_size = 5

    label_df = pd.concat([
        pd.read_csv(os.path.join(FILES_ROOT, "train_labels.csv")),
        pd.read_csv(os.path.join(FILES_ROOT, "test_labels.csv"))
    ])
    label_map = dict(zip(label_df["filename"], label_df["label"]))

    all_files = []
    for root, _, files in os.walk(FILES_ROOT):
        for fname in sorted(files):
            if allowed_file(fname):
                all_files.append(os.path.join(root, fname))

    for i in range(0, len(all_files), batch_size):
        batch = all_files[i:i + batch_size]
        for path in batch:
            fname = os.path.relpath(path, FILES_ROOT)
            try:
                with open(path, "rb") as f:
                    file = FileStorage(stream=f, filename=os.path.basename(path))
                    label_result = classify_file(file, method=method)
                    predicted = label_result["label"]
                    ground_truth = label_map.get(os.path.basename(path))

                    item = {
                        "filename": fname,
                        "label": predicted,
                        "expected": ground_truth
                    }

                    if ground_truth:
                        if predicted == ground_truth:
                            correct += 1
                        total += 1

                    results.append(item)
            except Exception as e:
                results.append({
                    "filename": fname,
                    "error": str(e)
                })

        sleep(1.2)  # delay to respect API rate limits

    accuracy = round((correct / total) * 100, 2) if total else None
    return jsonify({
        "results": results,
        "total": total,
        "correct": correct,
        "accuracy_percent": accuracy
    }), 200

@app.route("/list_categories", methods=["GET"])
def list_categories():
    try:
        os.makedirs("templates", exist_ok=True)
        categories = [
            fname.replace(".json", "")
            for fname in os.listdir("templates")
            if fname.endswith(".json")
        ]
        return jsonify({"categories": categories}), 200
    except Exception as e:
        logger.error(f"Failed to list categories: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/retrain", methods=["POST"])
def retrain_model():
    try:
        logger.info("Retraining model...")
        result = os.system("python scripts/train_model.py")
        if result != 0:
            raise RuntimeError("Training script failed.")
        return jsonify({"status": "success", "message": "Model retrained successfully."}), 200
    except Exception as e:
        logger.error(f"Retraining failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/list_files", methods=["GET"])
def list_files():
    try:
        files = []
        for root, _, filenames in os.walk(FILES_ROOT):
            for fname in filenames:
                if allowed_file(fname):
                    relative_path = os.path.relpath(os.path.join(root, fname), FILES_ROOT)
                    files.append({
                        "filename": fname,
                        "relative_path": relative_path
                    })
        return jsonify({"files": files}), 200
    except Exception as e:
        logger.error(f"Failed to list files: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Run the Flask server locally
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
