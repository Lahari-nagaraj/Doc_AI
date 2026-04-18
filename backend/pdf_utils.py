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
    # 🔹 METHOD 3: OCR (ALTERNATIVE FOR SCANNED PDFs)
    # ---------------------------
    if len(text.strip()) < 500:
        try:
            print("⚡ Detected scanned PDF or text extraction failed. Using OCR...")
            images = convert_from_path(file_path, dpi=300)

            for page_num, img in enumerate(images, 1):
                page_text = pytesseract.image_to_string(img)
                if page_text.strip():
                    text += page_text + "\n"
                    print(f"  ✓ Page {page_num} OCR extracted")

            if text.strip():
                print(f"✅ OCR completed successfully! Total: {len(text)} chars")

        except Exception as e:
            print(f"⚠️ OCR failed: {e}")
            print("  Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")

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
