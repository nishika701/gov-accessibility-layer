"""
Amazon Transcribe (Speech-to-Text) module.
Converts spoken audio files into text using AWS Amazon Transcribe and S3.
"""

import os
import sys
import time
import uuid
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
import requests

# Load environment variables from .env
load_dotenv()

# Configure console encoding for Windows to prevent UnicodeEncodeError
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Supported media extensions mapped to Amazon Transcribe MediaFormat values
SUPPORTED_MEDIA_FORMATS = {
    ".mp3": "mp3",
    ".wav": "wav",
    ".flac": "flac",
    ".ogg": "ogg",
    ".amr": "amr",
    ".webm": "webm",
    ".mp4": "mp4",
    ".m4a": "mp4",
}

# Language codes supported by Amazon Transcribe for Indian and standard languages
TRANSCRIBE_LANGUAGE_CODES = {
    "Hindi": "hi-IN",
    "English": "en-IN",
    "English-US": "en-US",
    "Tamil": "ta-IN",
    "Telugu": "te-IN",
    "Marathi": "mr-IN",
    "Bengali": "bn-IN",
    "Kannada": "kn-IN",
    "Malayalam": "ml-IN",
    "Gujarati": "gu-IN",
}


def get_aws_client(service_name: str, region_name: str = None):
    """
    Initializes and returns a boto3 client (e.g. 'transcribe' or 's3').
    """
    region = (
        region_name
        or os.getenv("AWS_DEFAULT_REGION")
        or os.getenv("AWS_REGION")
        or "ap-south-1"
    )
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_session_token = os.getenv("AWS_SESSION_TOKEN")

    client_kwargs = {"region_name": region}
    if aws_access_key and aws_secret_key:
        client_kwargs["aws_access_key_id"] = aws_access_key
        client_kwargs["aws_secret_access_key"] = aws_secret_key
        if aws_session_token:
            client_kwargs["aws_session_token"] = aws_session_token

    return boto3.client(service_name, **client_kwargs)


def upload_audio_to_s3(file_path: str, bucket_name: str, object_key: str, region_name: str = None) -> str:
    """
    Uploads a local audio file to the specified S3 bucket.
    Returns the S3 URI (s3://bucket/key).
    """
    s3_client = get_aws_client("s3", region_name=region_name)
    s3_client.upload_file(file_path, bucket_name, object_key)
    return f"s3://{bucket_name}/{object_key}"


def delete_s3_object(bucket_name: str, object_key: str, region_name: str = None):
    """
    Deletes an object from S3 after processing.
    """
    try:
        s3_client = get_aws_client("s3", region_name=region_name)
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)
    except Exception as e:
        print(f"[Warning] Failed to clean up S3 object {object_key}: {e}")


def transcribe_audio(
    audio_path: str,
    language: str = "Hindi",
    bucket_name: str = None,
    delete_s3_after: bool = False,
    region_name: str = None,
    poll_interval_seconds: int = 3,
    max_wait_seconds: int = 300,
) -> str:
    """
    Transcribes an audio file into text using Amazon Transcribe.

    :param audio_path: Path to the local audio file (.mp3, .wav, etc.).
    :param language: Language name (e.g. "Hindi", "English") or "auto" for auto-detection.
    :param bucket_name: S3 bucket name for uploading audio. If omitted, reads AWS_S3_BUCKET from .env.
    :param delete_s3_after: Whether to delete the audio file from S3 once completed.
    :param region_name: AWS region (e.g. "ap-south-1").
    :param poll_interval_seconds: Polling interval while waiting for transcription job.
    :param max_wait_seconds: Maximum seconds to wait before timing out.
    :return: Transcribed text string.
    """
    audio_file = Path(audio_path).resolve()
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    ext = audio_file.suffix.lower()
    if ext not in SUPPORTED_MEDIA_FORMATS:
        supported = ", ".join(SUPPORTED_MEDIA_FORMATS.keys())
        raise ValueError(f"Unsupported audio format '{ext}'. Supported formats: {supported}")
    media_format = SUPPORTED_MEDIA_FORMATS[ext]

    s3_bucket = bucket_name or os.getenv("AWS_S3_BUCKET") or os.getenv("TRANSCRIBE_S3_BUCKET")
    if not s3_bucket:
        raise ValueError(
            "Amazon Transcribe requires an S3 bucket to process audio files. "
            "Please configure AWS_S3_BUCKET in your .env file or pass bucket_name to transcribe_audio()."
        )

    # Generate unique job name and S3 key
    job_id = uuid.uuid4().hex[:10]
    job_name = f"gov_transcribe_{job_id}"
    s3_key = f"transcribe-inputs/{job_id}_{audio_file.name}"

    print(f"[Transcribe] Uploading '{audio_file.name}' to S3 (s3://{s3_bucket}/{s3_key})...")
    s3_uri = upload_audio_to_s3(str(audio_file), s3_bucket, s3_key, region_name=region_name)

    transcribe_client = get_aws_client("transcribe", region_name=region_name)

    job_args = {
        "TranscriptionJobName": job_name,
        "Media": {"MediaFileUri": s3_uri},
        "MediaFormat": media_format,
    }

    if language.lower() == "auto":
        job_args["IdentifyLanguage"] = True
    else:
        lang_code = TRANSCRIBE_LANGUAGE_CODES.get(language, "hi-IN")
        job_args["LanguageCode"] = lang_code

    print(f"[Transcribe] Starting transcription job '{job_name}' (language: {language})...")
    transcribe_client.start_transcription_job(**job_args)

    # Poll for completion
    start_time = time.time()
    try:
        while True:
            response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            job = response.get("TranscriptionJob", {})
            status = job.get("TranscriptionJobStatus")

            if status == "COMPLETED":
                transcript_url = job.get("Transcript", {}).get("TranscriptFileUri")
                if not transcript_url:
                    raise RuntimeError("Transcription job completed but TranscriptFileUri was missing.")

                print("[Transcribe] Job completed. Downloading transcript...")
                res = requests.get(transcript_url, timeout=30)
                res.raise_for_status()
                data = res.json()

                transcripts = data.get("results", {}).get("transcripts", [])
                full_text = " ".join(t.get("transcript", "") for t in transcripts).strip()
                return full_text

            elif status == "FAILED":
                reason = job.get("FailureReason", "Unknown failure reason")
                raise RuntimeError(f"Amazon Transcribe job failed: {reason}")

            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                raise TimeoutError(f"Amazon Transcribe timed out after {max_wait_seconds} seconds.")

            time.sleep(poll_interval_seconds)

    finally:
        if delete_s3_after:
            print(f"[Transcribe] Cleaning up S3 object: {s3_key}")
            delete_s3_object(s3_bucket, s3_key, region_name=region_name)


if __name__ == "__main__":
    # Standalone CLI execution:
    # python transcribe.py [audio_file] [language] [bucket_name]
    sample_audio = sys.argv[1] if len(sys.argv) > 1 else "output.mp3"
    target_lang = sys.argv[2] if len(sys.argv) > 2 else "Hindi"
    bucket = sys.argv[3] if len(sys.argv) > 3 else None

    print(f"=== Amazon Transcribe CLI ===")
    print(f"Target file: {sample_audio}")
    print(f"Language:    {target_lang}")

    if not os.path.exists(sample_audio):
        print(f"[Error] Audio file '{sample_audio}' not found. Please provide a valid audio file.")
        print("Usage: python transcribe.py <path_to_audio.mp3> [language] [s3_bucket]")
        sys.exit(1)

    try:
        transcript = transcribe_audio(
            audio_path=sample_audio,
            language=target_lang,
            bucket_name=bucket,
        )
        print("\n=== TRANSCRIPTION RESULT ===")
        print(transcript)
    except NoCredentialsError:
        print("\n[Error] AWS credentials not found.")
        print("Please configure AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_S3_BUCKET in .env.")
    except ValueError as ve:
        print(f"\n[Configuration Required] {ve}")
    except Exception as ex:
        print(f"\n[Error] Transcription failed: {ex}")
