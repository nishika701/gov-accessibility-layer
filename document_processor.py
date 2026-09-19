import os
import sys
import pymupdf

# Configure console encoding for Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a text-based PDF file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found at: {file_path}")

    document = pymupdf.open(file_path)
    extracted_text = ""

    for page in document:
        extracted_text += page.get_text()

    document.close()
    return extracted_text.strip()


if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "sample_document.pdf"

    if not os.path.exists(pdf_path):
        print(f"Usage: python document_processor.py <path_to_pdf>")
        print(f"Notice: '{pdf_path}' does not exist.")
    else:
        text = extract_text_from_pdf(pdf_path)
        print("=== EXTRACTED TEXT ===")
        print(text)