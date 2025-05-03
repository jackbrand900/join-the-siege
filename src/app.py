from flask import Flask, request, jsonify

from src.classifier import classify_file
app = Flask(__name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/classify_file', methods=['POST'])
def classify_file_route():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '': # handle empty file
        return jsonify({"error": "No selected file"}), 400
    method = request.form.get('method', 'filename')

    allowed_methods = {"filename", "model", "llm"}
    if method not in allowed_methods:
        return jsonify({"error": f"Unsupported method: {method}"}), 400

    try:
        result = classify_file(file, method=method)
        return jsonify({"file_class": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
