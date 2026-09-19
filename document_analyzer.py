import json
import re


def clean_text(text: str) -> str:
    """Clean OCR output."""

    text = text.replace("\r", "\n")

    # Remove excessive whitespace
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_into_sections(text: str):
    """
    Split a document into manageable sections.

    This is intentionally simple for the MVP.
    Later this can be replaced with embedding-based RAG.
    """

    paragraphs = [
        p.strip()
        for p in text.split("\n")
        if p.strip()
    ]

    sections = []

    current = []

    for paragraph in paragraphs:

        current.append(paragraph)

        # Keep sections reasonably small
        if len(" ".join(current)) >= 800:
            sections.append(" ".join(current))
            current = []

    if current:
        sections.append(" ".join(current))

    return sections


def detect_fields(text: str):
    """
    Generic field detection.

    This does NOT assume a specific government form.
    """

    field_patterns = [
        r"name",
        r"date of birth",
        r"dob",
        r"address",
        r"mobile",
        r"phone",
        r"email",
        r"gender",
        r"sex",
        r"age",
        r"occupation",
        r"income",
        r"district",
        r"state",
        r"village",
        r"pincode",
        r"pin code",
        r"aadhaar",
        r"father",
        r"mother",
        r"guardian",
        r"applicant",
    ]

    fields = []

    lines = text.split("\n")

    for line in lines:

        clean_line = line.strip()

        if not clean_line:
            continue

        lower_line = clean_line.lower()

        for pattern in field_patterns:

            if re.search(pattern, lower_line):

                fields.append({
                    "label": clean_line,
                    "type": "text"
                })

                break

    return fields


def analyze_document(text: str):
    """
    Convert raw OCR text into a generic document structure.
    """

    cleaned = clean_text(text)

    sections = split_into_sections(cleaned)

    fields = detect_fields(cleaned)

    return {
        "document_text": cleaned,
        "sections": sections,
        "fields": fields,
        "important_facts": [],
        "requirements": [],
        "questions": []
    }


if __name__ == "__main__":

    sample = """
    Application Form

    Name of Applicant:
    Date of Birth:
    Address:
    Mobile Number:

    Applicant must attach identity proof.
    """

    result = analyze_document(sample)

    print(json.dumps(result, indent=2))