import os
import sys
from pathlib import Path

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

from simplify import simplify_text
from tts import text_to_speech
from document_processor import extract_text_from_pdf

# Optional import of Amazon Transcribe module
try:
    from transcribe import transcribe_audio, SUPPORTED_MEDIA_FORMATS
    HAS_TRANSCRIBE = True
except ImportError:
    HAS_TRANSCRIBE = False
    SUPPORTED_MEDIA_FORMATS = {}


def process(
    text: str,
    target_language: str = "Hindi",
    audio_output_path: str = "output.mp3",
    provider: str = None,
) -> dict:
    """
    Simplifies government text into the target language and generates audio.

    :param text: Original government or administrative text.
    :param target_language: Language to simplify and translate to (e.g. "Hindi", "English").
    :param audio_output_path: Target filename/path for the output MP3.
    :param provider: TTS provider ("auto", "polly", or "gtts").
    :return: Dictionary containing original_text, simplified_text, language, and audio_path.
    """
    print(f"Simplifying text into {target_language}...")
    simplified = simplify_text(text, target_language)

    print(f"Generating audio ({audio_output_path})...")
    audio_path = text_to_speech(
        text=simplified,
        language=target_language,
        output_path=audio_output_path,
        provider=provider,
    )

    return {
        "original_text": text,
        "simplified_text": simplified,
        "language": target_language,
        "audio_path": audio_path,
    }


def process_file(
    file_path: str,
    target_language: str = "Hindi",
    audio_output_path: str = "output.mp3",
    provider: str = None,
) -> dict:
    """
    Extracts text from a document (PDF or text file), simplifies it, and generates audio.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    print(f"Reading document: {file_path}")
    if path.suffix.lower() == ".pdf":
        text = extract_text_from_pdf(str(path))
    else:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read().strip()

    if not text:
        raise ValueError(f"No text could be extracted from {file_path}")

    return process(
        text=text,
        target_language=target_language,
        audio_output_path=audio_output_path,
        provider=provider,
    )


def process_audio(
    audio_path: str,
    target_language: str = "Hindi",
    audio_output_path: str = "output.mp3",
    provider: str = None,
    s3_bucket: str = None,
) -> dict:
    """
    Transcribes spoken audio using Amazon Transcribe, simplifies the transcribed text,
    and generates spoken audio in the target language.
    """
    if not HAS_TRANSCRIBE:
        raise ImportError("Transcribe module is not available. Please verify transcribe.py.")

    print(f"Transcribing audio input: {audio_path}...")
    transcribed_text = transcribe_audio(
        audio_path=audio_path,
        language=target_language,
        bucket_name=s3_bucket,
    )
    print(f"Transcribed Text: {transcribed_text}")

    return process(
        text=transcribed_text,
        target_language=target_language,
        audio_output_path=audio_output_path,
        provider=provider,
    )


if __name__ == "__main__":
    # Support optional CLI arguments:
    # python pipeline.py [input_text_or_file] [language] [output_path] [provider]
    sample_text = (
        "Applicants must submit Form LLD-1 along with valid proof of address "
        "and proof of age within 30 days of the date of application. A fee of "
        "Rs. 200 is applicable. Failure to submit within the stipulated time "
        "will result in cancellation of the application."
    )

    input_arg = sys.argv[1] if len(sys.argv) > 1 else None
    language_arg = sys.argv[2] if len(sys.argv) > 2 else "Hindi"
    output_arg = sys.argv[3] if len(sys.argv) > 3 else "output.mp3"
    provider_arg = sys.argv[4] if len(sys.argv) > 4 else None

    if input_arg and os.path.isfile(input_arg):
        ext = Path(input_arg).suffix.lower()
        if ext in SUPPORTED_MEDIA_FORMATS:
            result = process_audio(
                audio_path=input_arg,
                target_language=language_arg,
                audio_output_path=output_arg,
                provider=provider_arg,
            )
        else:
            result = process_file(
                file_path=input_arg,
                target_language=language_arg,
                audio_output_path=output_arg,
                provider=provider_arg,
            )
    else:
        text_to_process = input_arg if input_arg else sample_text
        result = process(
            text=text_to_process,
            target_language=language_arg,
            audio_output_path=output_arg,
            provider=provider_arg,
        )

    print("\n=== ORIGINAL / INPUT ===")
    print(result["original_text"])
    print("\n=== SIMPLIFIED ===")
    print(result["simplified_text"])
    print(f"\n=== AUDIO SAVED TO: {result['audio_path']} ===")