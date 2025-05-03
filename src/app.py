from flask import Flask, request, jsonify
from src.classifier import classify_file
from src.api import api
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.register_blueprint(api, url_prefix='/api')

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/classify_file', methods=['POST'])
def classify_file_route():
    logger.debug("Received classify_file request")
    logger.debug(f"Request files: {request.files}")
    logger.debug(f"Request form: {request.form}")
    
    if 'file' not in request.files:
        logger.error("No file part in request")
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '': # handle empty file
        logger.error("No selected file")
        return jsonify({"error": "No selected file"}), 400
        
    logger.debug(f"Processing file: {file.filename}")
    method = request.form.get('method', 'filename')
    logger.debug(f"Using classification method: {method}")

    allowed_methods = {"filename", "model", "llm"}
    if method not in allowed_methods:
        logger.error(f"Unsupported method: {method}")
        return jsonify({"error": f"Unsupported method: {method}"}), 400

    try:
        result = classify_file(file, method=method)
        logger.debug(f"Classification result: {result}")
        return jsonify({"file_class": result}), 200
    except Exception as e:
        logger.error(f"Error during classification: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
