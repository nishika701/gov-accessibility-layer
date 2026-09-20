import os
import uuid
import re
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Local services
import aws_document_processor
import gemini_service
import polly_tts
import tts

# Load environment variables
load_dotenv()

# Ensure uploads directory exists for local/mock storage
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Gov Accessibility Layer API",
    description=(
        "Production-ready accessibility API for government documents. "
        "Supports S3 storage, Textract OCR extraction, Gemini AI simplification, "
        "comprehension question generation, and citizen answer verification."
    ),
    version="1.2.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS Configuration from environment
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
AWS_PROFILE = os.getenv("AWS_PROFILE", "gov-accessibility")
AWS_S3_BUCKET = os.getenv(
    "AWS_S3_BUCKET",
    "gov-accessibility-layer-devforge-237303364767-us-east-1-an"
)


# ---------------------------------------------------------
# Pydantic Request Models
# ---------------------------------------------------------

class ProcessRequest(BaseModel):
    bucket: Optional[str] = Field(None, description="S3 bucket name where the document is stored")
    key: Optional[str] = Field(None, description="S3 object key or filename of the document")
    s3_uri: Optional[str] = Field(None, description="Full S3 URI (s3://bucket/key) as alternative to bucket/key")
    document_id: Optional[str] = Field(None, description="Unique document ID or filename")



class ExplainRequest(BaseModel):
    text: str = Field(..., description="Document text extracted via OCR or submitted by citizen")
    language: Optional[str] = Field("Hindi", description="Target language (e.g. Hindi, English, Tamil, Telugu)")


class QuestionRequest(BaseModel):
    document_context: str = Field(..., description="Context text of the document used to formulate understanding question")
    language: Optional[str] = Field("Hindi", description="Language of the generated question")


class CheckAnswerRequest(BaseModel):
    question: str = Field(..., description="The comprehension question that was asked")
    user_answer: str = Field(..., description="The citizen's selected or typed answer")
    document_context: str = Field(..., description="Original document context used for factual verification")
    question_id: Optional[str] = Field(None, description="Optional ID of the generated question for exact matching")


# ---------------------------------------------------------
# AWS Helper Functions
# ---------------------------------------------------------

def has_valid_aws_credentials() -> bool:
    """Checks if valid non-placeholder AWS credentials exist."""
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    if "your_access_key" in access_key.lower() or not access_key:
        aws_creds = Path.home() / ".aws" / "credentials"
        return aws_creds.exists()
    return bool(access_key and secret_key)


def get_s3_client():
    """Initializes a Boto3 S3 client with profile or default credentials."""
    try:
        session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
        return session.client("s3")
    except Exception:
        return boto3.client("s3", region_name=AWS_REGION)


# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------

@app.get("/")
def root_info():
    """Root info endpoint providing service health and available routes."""
    return {
        "service": "Gov Accessibility Layer API",
        "status": "online",
        "version": "1.1.0",
        "aws_s3_bucket": AWS_S3_BUCKET,
        "region": AWS_REGION,
        "aws_credentials_detected": has_valid_aws_credentials(),
        "endpoints": {
            "POST /upload": "Upload PDF document to Amazon S3 (or mock storage)",
            "POST /process": "Extract text from document via Amazon Textract",
            "POST /explain": "Generate citizen-friendly explanation via Gemini AI",
            "POST /question": "Generate document understanding question via Gemini AI",
            "POST /check-answer": "Verify citizen answer against document context via Gemini AI",
        }
    }


@app.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_pdf(file: UploadFile = File(...)):
    """
    POST /upload — Receives a PDF file and stores it in Amazon S3.
    Gracefully saves locally to 'uploads/' with mock S3 metadata if AWS credentials
    or S3 bucket are not configured.
    """
    filename = file.filename or "document.pdf"

    # Validate file extension
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type for '{filename}'. Only PDF documents (.pdf) are supported.",
        )

    clean_filename = Path(filename).name.replace(" ", "_")
    unique_id = uuid.uuid4().hex[:8]
    s3_key = f"uploads/{unique_id}_{clean_filename}"
    local_path = UPLOADS_DIR / f"{unique_id}_{clean_filename}"

    # Read uploaded file contents into memory
    file_bytes = await file.read()

    # Always save a local copy in uploads/ for offline/mock fallback
    with open(local_path, "wb") as f:
        f.write(file_bytes)

    # 1. Attempt upload to Amazon S3 if credentials exist
    bucket_name = AWS_S3_BUCKET or "gov-accessibility-layer-mock"
    uploaded_to_s3 = False

    if has_valid_aws_credentials():
        try:
            s3 = get_s3_client()
            s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=file_bytes,
                ContentType="application/pdf"
            )
            uploaded_to_s3 = True
            print(f"[S3 Upload] Successfully uploaded {s3_key} to s3://{bucket_name}")
        except Exception as e:
            print(f"[S3 Warning] S3 upload failed ({e}). Proceeding in local fallback mode.")

    storage_mode = "s3" if uploaded_to_s3 else "local_mock"
    s3_uri = f"s3://{bucket_name}/{s3_key}"

    return {
        "status": "success",
        "testKey": f"PDF successfully stored ({storage_mode})",
        "message": f"PDF successfully stored!",
        "filename": filename,
        "bucket": bucket_name,
        "key": s3_key,
        "s3_uri": s3_uri,
        "storage": storage_mode,
        "local_path": str(local_path),
    }


@app.post("/process")
def process_document(request: ProcessRequest):
    """
    POST /process — Takes the uploaded document and triggers Textract to extract text.
    Accepts { bucket, key }, { s3_uri }, or { document_id }.
    Falls back gracefully to PyMuPDF local OCR if Textract is unavailable.
    """
    bucket = request.bucket or AWS_S3_BUCKET or "gov-accessibility-layer-mock"
    key = request.key or request.document_id

    # If s3_uri is passed, parse bucket and key
    if request.s3_uri and request.s3_uri.startswith("s3://"):
        parts = request.s3_uri[5:].split("/", 1)
        if len(parts) == 2:
            bucket, key = parts[0], parts[1]

    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'key', 'document_id', or 's3_uri' in request body.",
        )

    # Trigger Textract / fallback OCR
    try:
        result = aws_document_processor.extract_text_from_s3(
            bucket_name=bucket,
            object_key=key
        )
        return {
            "status": "success",
            "document_id": result.get("document_id", key),
            "source": result.get("source", "mock_engine"),
            "lines_count": result.get("lines_count", 0),
            "text": result.get("text", ""),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document text: {str(e)}"
        )


@app.post("/explain")
def explain_text(request: ExplainRequest):
    """
    POST /explain — Sends extracted text to Gemini API and returns simplified explanation.
    Falls back gracefully to structured mock intelligence.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text field cannot be empty."
        )

    target_lang = request.language or "Hindi"

    try:
        result = gemini_service.explain_document(
            text=request.text,
            language=target_lang
        )
        simplified_text = result.get("simplified_text", "")

        # Generate audio of the explanation using Amazon Polly (with automated fallback via tts module)
        audio_base64 = None
        audio_format = "audio/mp3"
        audio_file_path = None

        if simplified_text and simplified_text.strip():
            try:
                unique_audio_id = uuid.uuid4().hex[:8]
                audio_output_path = UPLOADS_DIR / f"explain_audio_{unique_audio_id}.mp3"
                
                generated_path = tts.text_to_speech(
                    text=simplified_text,
                    language=target_lang,
                    output_path=str(audio_output_path)
                )
                
                if generated_path and os.path.exists(generated_path):
                    audio_file_path = str(generated_path)
                    with open(generated_path, "rb") as af:
                        audio_base64 = base64.b64encode(af.read()).decode("utf-8")
            except Exception as tts_err:
                print(f"[Explain TTS Warning] Failed to generate audio: {tts_err}")

        return {
            "status": "success",
            "source": result.get("source", "mock_engine"),
            "language": target_lang,
            "simplified_text": simplified_text,
            "key_points": result.get("key_points", {}),
            "audio_base64": audio_base64,
            "audio_format": audio_format,
            "audio_url": f"/uploads/{Path(audio_file_path).name}" if audio_file_path else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate explanation: {str(e)}"
        )


@app.post("/question")
def generate_question(request: QuestionRequest):
    """
    POST /question — Generates a document-specific understanding question using Gemini API.
    Returns the question, multiple choice options, and a question_id.
    """
    if not request.document_context or not request.document_context.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_context field cannot be empty."
        )

    target_lang = request.language or "Hindi"

    try:
        result = gemini_service.generate_question(
            document_context=request.document_context,
            language=target_lang
        )
        return {
            "status": "success",
            "source": result.get("source", "mock_engine"),
            "question_id": result.get("question_id", ""),
            "question": result.get("question", ""),
            "options": result.get("options", []),
            "language": target_lang,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate understanding question: {str(e)}"
        )


@app.post("/check-answer")
def check_citizen_answer(request: CheckAnswerRequest):
    """
    POST /check-answer — Sends the user's answer + document context to Gemini API
    and returns whether they understood it.
    """
    if not request.user_answer or not request.user_answer.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_answer field cannot be empty."
        )

    try:
        result = gemini_service.check_answer(
            question=request.question,
            user_answer=request.user_answer,
            document_context=request.document_context,
            question_id=request.question_id
        )
        return {
            "status": "success",
            "source": result.get("source", "mock_engine"),
            "understood": result.get("understood", True),
            "is_correct": result.get("is_correct", True),
            "feedback": result.get("feedback", ""),
            "explanation": result.get("explanation", ""),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check answer: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
