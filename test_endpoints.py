"""
Test script for verifying all 5 API endpoints in api.py using FastAPI TestClient.
"""

import sys

# Configure UTF-8 for Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient
from api import app
from pathlib import Path

client = TestClient(app)


def run_all_tests():
    print("\n==========================================")
    print("Testing Gov Accessibility Layer Endpoints")
    print("==========================================\n")

    # 1. Test GET /
    print("[1/6] Testing GET / (Root Info)...")
    res = client.get("/")
    assert res.status_code == 200, f"GET / failed: {res.text}"
    print("[PASS] GET / returned 200 OK")
    print(f"  Service: {res.json().get('service')}")
    print(f"  Endpoints: {list(res.json().get('endpoints', {}).keys())}")

    # 2. Test POST /upload
    print("\n[2/6] Testing POST /upload...")
    pdf_path = Path("sample_document.pdf")
    if not pdf_path.exists():
        pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")

    with open(pdf_path, "rb") as f:
        res = client.post("/upload", files={"file": ("sample_document.pdf", f, "application/pdf")})
    assert res.status_code == 201, f"POST /upload failed: {res.text}"
    upload_data = res.json()
    print("[PASS] POST /upload returned 201 Created")
    print(f"  Key: {upload_data.get('key')}")
    print(f"  S3 URI: {upload_data.get('s3_uri')}")
    print(f"  Storage: {upload_data.get('storage')}")

    # 3. Test POST /process
    print("\n[3/6] Testing POST /process...")
    res = client.post("/process", json={
        "bucket": upload_data.get("bucket"),
        "key": upload_data.get("key"),
        "s3_uri": upload_data.get("s3_uri")
    })
    assert res.status_code == 200, f"POST /process failed: {res.text}"
    process_data = res.json()
    print("[PASS] POST /process returned 200 OK")
    print(f"  Source: {process_data.get('source')}")
    print(f"  Lines extracted: {process_data.get('lines_count')}")
    extracted_text = process_data.get("text", "")

    # 4. Test POST /explain
    print("\n[4/6] Testing POST /explain (Hindi)...")
    res = client.post("/explain", json={
        "text": extracted_text,
        "language": "Hindi"
    })
    assert res.status_code == 200, f"POST /explain failed: {res.text}"
    explain_data = res.json()
    print("[PASS] POST /explain returned 200 OK")
    print(f"  Source: {explain_data.get('source')}")
    print(f"  Language: {explain_data.get('language')}")
    print(f"  Simplified text snippet: {explain_data.get('simplified_text')[:120]}...")
    print(f"  Key points: {explain_data.get('key_points')}")

    # 5. Test POST /question
    print("\n[5/6] Testing POST /question...")
    res = client.post("/question", json={
        "document_context": extracted_text,
        "language": "Hindi"
    })
    assert res.status_code == 200, f"POST /question failed: {res.text}"
    question_data = res.json()
    print("[PASS] POST /question returned 200 OK")
    print(f"  Question ID: {question_data.get('question_id')}")
    print(f"  Question: {question_data.get('question')}")
    print(f"  Options: {question_data.get('options')}")

    # 6. Test POST /check-answer
    print("\n[6/6] Testing POST /check-answer...")
    options = question_data.get("options", ["30 दिनों के भीतर"])
    selected_option = options[1] if len(options) > 1 else options[0]

    res = client.post("/check-answer", json={
        "question": question_data.get("question"),
        "user_answer": selected_option,
        "document_context": extracted_text,
        "question_id": question_data.get("question_id")
    })
    assert res.status_code == 200, f"POST /check-answer failed: {res.text}"
    check_data = res.json()
    print("[PASS] POST /check-answer returned 200 OK")
    print(f"  Understood: {check_data.get('understood')}")
    print(f"  Feedback: {check_data.get('feedback')}")
    print(f"  Explanation: {check_data.get('explanation')}")

    print("\n==========================================")
    print("ALL 5 ENDPOINTS VERIFIED SUCCESSFULLY!")
    print("==========================================\n")


if __name__ == "__main__":
    run_all_tests()
