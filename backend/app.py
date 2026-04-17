from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from pdf_utils import extract_text

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return jsonify({"message": "Backend running 🚀"})

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # 🔥 Extract text
    text = extract_text(filepath)

    return jsonify({
        "message": "File uploaded and processed",
        "preview": text  # send all extracted text
    })

if __name__ == "__main__":
    app.run(debug=True)