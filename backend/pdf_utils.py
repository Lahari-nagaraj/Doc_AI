import pdfplumber
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
import re


def extract_text(file_path):
    text = ""

    # ---------------------------
    # 🔹 METHOD 1: pdfplumber
    # ---------------------------
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        print("pdfplumber failed:", e)

    # ---------------------------
    # 🔹 METHOD 2: PyMuPDF (IMPORTANT FIX)
    # ---------------------------
    if len(text.strip()) < 500:
        try:
            print("⚡ Using PyMuPDF fallback...")
            doc = fitz.open(file_path)

            for page in doc:
                text += page.get_text("text") + "\n"

        except Exception as e:
            print("PyMuPDF failed:", e)

    # ---------------------------
    # 🔹 METHOD 3: OCR (LAST RESORT)
    # ---------------------------
    if len(text.strip()) < 500:
        try:
            print("⚡ Using OCR fallback...")
            images = convert_from_path(file_path)

            for img in images:
                text += pytesseract.image_to_string(img)

        except Exception as e:
            print("OCR failed:", e)

    # ---------------------------
    # 🔹 CLEAN TEXT
    # ---------------------------
    text = clean_text(text)

    # 🔥 DEBUG (VERY IMPORTANT)
    print("✅ FINAL TEXT LENGTH:", len(text))

    return text


def clean_text(text):
    text = text.replace("\r", "\n")
    text = re.sub(r"\n+", "\n", text)
    return text.strip()
