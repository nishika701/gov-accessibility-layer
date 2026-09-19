import boto3
import time


AWS_PROFILE = "gov-accessibility"
AWS_REGION = "us-east-1"


def get_textract_client():
    session = boto3.Session(
        profile_name=AWS_PROFILE,
        region_name=AWS_REGION
    )

    return session.client("textract")


def extract_text_from_s3(bucket_name: str, object_key: str) -> dict:
    """
    Extract text from a PDF stored in S3 using Amazon Textract.

    Returns:
        {
            "document_id": object_key,
            "text": "extracted text..."
        }
    """

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
        result = textract.get_document_text_detection(
            JobId=job_id
        )

        status = result["JobStatus"]

        print(f"[Textract] Job status: {status}")

        if status == "SUCCEEDED":
            break

        if status == "FAILED":
            raise RuntimeError(
                f"Textract job failed: {result.get('StatusMessage', 'Unknown error')}"
            )

        time.sleep(3)

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
        "text": extracted_text
    }


if __name__ == "__main__":

    BUCKET_NAME = (
        "gov-accessibility-layer-devforge-237303364767-us-east-1-an"
    )

    OBJECT_KEY = "CZ-Form-I.pdf"

    result = extract_text_from_s3(
        bucket_name=BUCKET_NAME,
        object_key=OBJECT_KEY
    )

    print("\n=== EXTRACTED TEXT ===")
    print(result["text"])