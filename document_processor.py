import pymupdf


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a normal text-based PDF.
    """

    document = pymupdf.open(file_path)

    extracted_text = ""

    for page in document:
        extracted_text += page.get_text()

    document.close()

    return extracted_text.strip()


if __name__ == "__main__":

    pdf_path = "SOP_K_K_selectable.pdf"

    text = extract_text_from_pdf(pdf_path)

    print("=== EXTRACTED TEXT ===")
    print(text)