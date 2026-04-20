from flask import Flask, request, jsonify
from flask_cors import CORS

import os

from pdf_utils import extract_text
from chunking import smart_chunk_text
from vector_store import create_vector_store, search
from reranker import rerank
from llm import generate_answer, generate_summary, generate_quiz

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def home():
    return jsonify({"message": "Backend running 🚀"})


def expand_query(query):
    return f"""
{query}

Similar meanings:
objective goal purpose aim intent summary overview
"""


# ---------------------------
# 📂 UPLOAD + PROCESS PDF
# ---------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    try:
        text = extract_text(filepath)

        if not text or len(text.strip()) == 0:
            return jsonify({"error": "Failed to extract text"}), 400

        print("✅ TEXT LENGTH:", len(text))

        chunks = smart_chunk_text(text, chunk_size=800, overlap=150)

        print("✅ CHUNKS:", len(chunks))

        index, embeddings = create_vector_store(chunks)

        app.config["index"] = index
        app.config["chunks"] = chunks

        return jsonify({
            "message": "PDF processed successfully",
            "text_length": len(text),
            "chunks": len(chunks)
        })

    except Exception as e:
        print("❌ ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ---------------------------
# 🔍 QUERY API (Q&A)
# ---------------------------
@app.route("/ask", methods=["POST"])
def ask_question():
    data = request.json
    query = data.get("query")

    if not query:
        return jsonify({"error": "No query provided"}), 400

    index = app.config.get("index")
    chunks = app.config.get("chunks")

    if index is None or chunks is None:
        return jsonify({"error": "No document uploaded yet"}), 400

    try:
        expanded_query = expand_query(query)
        results = search(expanded_query, index, chunks, top_k=20)
        results = rerank(query, results)
        answer = generate_answer(query, results)

        return jsonify({
            "query": query,
            "answer": answer,
            "sources": results
        })

    except Exception as e:
        print("❌ SEARCH ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ---------------------------
# 📝 SUMMARIZE API
# ---------------------------
@app.route("/summarize", methods=["POST"])
def summarize_document():
    chunks = app.config.get("chunks")

    if chunks is None:
        return jsonify({"error": "No document uploaded yet"}), 400

    try:
        summary = generate_summary(chunks)
        return jsonify({"summary": summary})

    except Exception as e:
        print("❌ SUMMARIZE ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ---------------------------
# 🧠 QUIZ API
# ---------------------------
@app.route("/quiz", methods=["POST"])
def generate_quiz_api():
    data = request.json or {}
    num_questions = data.get("num_questions", 5)
    difficulty = data.get("difficulty", "medium")  # "easy" | "medium" | "hard"

    # Validate difficulty
    if difficulty not in ("easy", "medium", "hard"):
        difficulty = "medium"

    chunks = app.config.get("chunks")

    if chunks is None:
        return jsonify({"error": "No document uploaded yet"}), 400

    try:
        print(f"🧠 Generating {num_questions} {difficulty.upper()} questions...")
        quiz = generate_quiz(chunks, num_questions=num_questions, difficulty=difficulty)

        if not quiz:
            return jsonify({"error": "Failed to generate quiz. Try again."}), 500

        return jsonify({
            "quiz": quiz,
            "total": len(quiz),
            "difficulty": difficulty
        })

    except Exception as e:
        print("❌ QUIZ ERROR:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
