import os
import time
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import BotoCoreError, ClientError

load_dotenv()

AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
AWS_PROFILE = os.getenv("AWS_PROFILE", "gov-accessibility")


def has_valid_aws_credentials() -> bool:
    """Check if AWS credentials are real and not placeholder."""
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    if "your_access_key" in access_key.lower() or not access_key:
        aws_creds = Path.home() / ".aws" / "credentials"
        return aws_creds.exists()
    return bool(access_key and secret_key)


def get_textract_client():
    """Initializes a Boto3 Textract client with profile or environment credentials."""
    try:
        session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
        return session.client("textract")
    except Exception:
        return boto3.client("textract", region_name=AWS_REGION)


def extract_text_from_s3(
    bucket_name: str,
    object_key: str,
    local_file_path: str = None
) -> dict:
    """
    Extract text from a PDF stored in S3 using Amazon Textract.
    Falls back gracefully to local PyMuPDF extraction or mock text
    if AWS credentials or S3 bucket is unavailable.

    Returns:
        {
            "document_id": object_key,
            "text": "extracted text...",
            "source": "textract" | "pymupdf_local" | "mock_engine",
            "lines_count": int
        }
    """
    # 1. Attempt AWS Textract if credentials are valid
    if has_valid_aws_credentials():
        try:
            textract = get_textract_client()
            print(f"[Textract] Starting OCR for s3://{bucket_name}/{object_key}")

            response = textract.start_document_text_detection(
                DocumentLocation={
                    "S3Object": {
                        "Bucket": bucket_name,
                        "Name": object_key
                    }
                }
            )

            job_id = response["JobId"]
            print(f"[Textract] Job started: {job_id}")

            # Wait for the asynchronous Textract job to finish
            while True:
                result = textract.get_document_text_detection(JobId=job_id)
                status = result["JobStatus"]
                print(f"[Textract] Job status: {status}")

                if status == "SUCCEEDED":
                    break
                if status == "FAILED":
                    raise RuntimeError(
                        f"Textract job failed: {result.get('StatusMessage', 'Unknown error')}"
                    )
                time.sleep(2)

            # Collect text from all pages/results
            lines = []
            while True:
                for block in result.get("Blocks", []):
                    if block.get("BlockType") == "LINE":
                        lines.append(block.get("Text", ""))

                next_token = result.get("NextToken")
                if not next_token:
                    break

                result = textract.get_document_text_detection(
                    JobId=job_id,
                    NextToken=next_token
                )

            extracted_text = "\n".join(lines).strip()
            print(f"[Textract] Extracted {len(lines)} lines.")

            return {
                "document_id": object_key,
                "text": extracted_text,
                "source": "textract",
                "lines_count": len(lines)
            }
        except Exception as e:
            print(f"[Textract Warning] Textract execution failed ({e}). Falling back to local OCR...")

    # 2. Local fallback using PyMuPDF if the file exists locally
    candidate_paths = [
        Path(local_file_path) if local_file_path else None,
        Path("uploads") / Path(object_key).name,
        Path("uploads") / object_key,
        Path(object_key),
        Path("sample_document.pdf")
    ]

    for p in candidate_paths:
        if p and p.exists() and p.is_file():
            try:
                import pymupdf
                doc = pymupdf.open(str(p))
                extracted_lines = []
                for page in doc:
                    extracted_lines.append(page.get_text())
                full_text = "\n".join(extracted_lines).strip()
                if full_text:
                    print(f"[PyMuPDF] Extracted text from local file: {p}")
                    return {
                        "document_id": object_key,
                        "text": full_text,
                        "source": "pymupdf_local",
                        "lines_count": len(full_text.splitlines())
                    }
            except Exception as pe:
                print(f"[PyMuPDF Warning] Failed to parse {p}: {pe}")

    # 3. Intelligent mock government document text fallback
    fallback_text = (
        "GOVERNMENT OF INDIA / STATE ADMINISTRATION\n"
        "DEPARTMENT OF TRANSPORT AND PUBLIC SERVICES\n\n"
        "NOTIFICATION: CITIZEN REGISTRATION AND LICENSING\n"
        "Form Reference: Form LLD-1 (Application for Verification and Renewal)\n\n"
        "Instructions to Applicants:\n"
        "1. All registered citizens must submit Form LLD-1 for renewal and identity confirmation.\n"
        "2. The completed application must be accompanied by a valid Proof of Address (e.g. Utility Bill, Voter ID)\n"
        "   and valid Proof of Age (e.g. Birth Certificate, School Leaving Certificate).\n"
        "3. Submission Deadline: All supporting documents must be submitted within 30 days from the date of application.\n"
        "4. Application Fee: A non-refundable processing fee of Rs. 200 must be paid at the designated counter or online portal.\n"
        "5. Cancellation Clause: Failure to submit required proofs within the stipulated 30-day window will result in the immediate\n"
        "   cancellation and invalidation of the application."
    )

    print("[Mock OCR] Returning structured government document text.")
    return {
        "document_id": object_key,
        "text": fallback_text,
        "source": "mock_engine",
        "lines_count": len(fallback_text.splitlines())
    }


if __name__ == "__main__":
    BUCKET_NAME = "gov-accessibility-layer-mock"
    OBJECT_KEY = "CZ-Form-I.pdf"
    result = extract_text_from_s3(bucket_name=BUCKET_NAME, object_key=OBJECT_KEY)
    print("\n=== EXTRACTED TEXT ===")
    print(result["text"])