from flask import Flask, request, jsonify
from scripts import generate_synthetic_docs
from src.classifier import classify_file
import logging
import os
import pandas as pd
from werkzeug.datastructures import FileStorage

# Setup
app = Flask(__name__)
FILES_ROOT = "files"
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx', 'xlsx'}

# Logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# -----------------------
# 🛠️ Utility
# -----------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -----------------------
# 🔍 Classify a file
# -----------------------
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
        logger.info(f"📦 Generating category: {label} x{num} — fields: {fields}")
        
        # Save the template
        generate_synthetic_docs.generate_category(label, fields, 0)

        # Generate synthetic docs using the saved template
        generate_synthetic_docs.generate_docs(label, num)

        return jsonify({"status": "success", "label": label, "samples_generated": num}), 200
    except Exception as e:
        logger.error(f"❌ Generation error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# -----------------------
# 🔁 Generate examples from existing template
# -----------------------
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
        logger.error(f"❌ Example generation error: {e}")
        return jsonify({"error": str(e)}), 500


# -----------------------
# 🧠 Classify all files in files/
# -----------------------
@app.route("/classify_all_files", methods=["POST"])
def classify_all_files():
    method = request.form.get("method", "filename")
    if method not in {"filename", "model", "llm"}:
        return jsonify({"error": f"Unsupported method: {method}"}), 400

    results = []

    for root, _, files in os.walk(FILES_ROOT):
        for fname in sorted(files):
            if not allowed_file(fname):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, "rb") as f:
                    file = FileStorage(stream=f, filename=fname)
                    label = classify_file(file, method=method)
                    results.append({
                        "filename": os.path.relpath(path, FILES_ROOT),
                        "label": label
                    })
            except Exception as e:
                results.append({
                    "filename": os.path.relpath(path, FILES_ROOT),
                    "error": str(e)
                })

    return jsonify(results), 200


# -----------------------
# 📂 List all available templates
# -----------------------
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
        logger.error(f"❌ Failed to list categories: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/delete_category", methods=["DELETE"])
def delete_category():
    data = request.get_json(force=True)
    label = data.get("label")
    if not label:
        return jsonify({"error": "Missing label"}), 400

    label = label.lower()
    deleted_files = []
    synthetic_dir = os.path.join("files", "synthetic")
    extensions = {".pdf", ".jpg", ".jpeg", ".png", ".docx", ".xlsx"}

    try:
        # Delete template
        template_path = os.path.join("templates", f"{label}.json")
        if os.path.exists(template_path):
            os.remove(template_path)

        # Delete synthetic files
        for fname in os.listdir(synthetic_dir):
            base, ext = os.path.splitext(fname)
            if ext.lower() in extensions and base.lower().startswith(f"{label}_synth_"):
                full_path = os.path.join(synthetic_dir, fname)
                os.remove(full_path)
                deleted_files.append(fname)

        # Update train/test CSVs
        for csv_path in ["files/train_labels.csv", "files/test_labels.csv"]:
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                df = df[df["label"].str.lower() != label]
                df.to_csv(csv_path, index=False)

        return jsonify({
            "status": "success",
            "template_deleted": not os.path.exists(template_path),
            "deleted_files": deleted_files
        }), 200
    except Exception as e:
        logger.error(f"❌ Failed to delete category '{label}': {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/retrain", methods=["POST"])
def retrain_model():
    try:
        logger.info("🔄 Retraining model...")
        result = os.system("python scripts/train_model.py")

        if result != 0:
            raise RuntimeError("Training script failed.")

        return jsonify({"status": "success", "message": "Model retrained successfully."}), 200
    except Exception as e:
        logger.error(f"❌ Retraining failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# -----------------------
# 🚀 Run the server
# -----------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
