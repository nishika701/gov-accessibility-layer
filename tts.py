"""
Text-to-Speech (TTS) dispatcher module.
Supports Amazon Polly (AWS) and gTTS (Google Text-to-Speech) with automatic fallback.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from gtts import gTTS

# Load environment variables (.env)
load_dotenv()

# Configure console encoding for Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Import Amazon Polly TTS module
try:
    from polly_tts import polly_text_to_speech
    HAS_POLLY_MODULE = True
except ImportError:
    HAS_POLLY_MODULE = False

# Map friendly language names to gTTS language codes
GTTS_LANGUAGE_CODES = {
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Bengali": "bn",
    "Marathi": "mr",
    "English": "en",
}


def gtts_text_to_speech(text: str, language: str = "Hindi", output_path: str = "output.mp3") -> str:
    """
    Synthesizes speech using gTTS.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for TTS.")

    output_file = Path(output_path).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    lang_code = GTTS_LANGUAGE_CODES.get(language, "en")
    tts = gTTS(text=text, lang=lang_code)
    tts.save(str(output_file))
    return str(output_file)


def text_to_speech(
    text: str,
    language: str = "Hindi",
    output_path: str = "output.mp3",
    provider: str = None,
) -> str:
    """
    Converts text to an audio file using either Amazon Polly or gTTS.

    :param text: Text to convert to speech.
    :param language: Language name (e.g. "Hindi", "English").
    :param output_path: Destination path for the saved audio file.
    :param provider: "polly", "gtts", or "auto" (default: reads TTS_PROVIDER or "auto").
    :return: Path to the saved audio file.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for text-to-speech conversion.")

    selected_provider = (
        provider
        or os.getenv("TTS_PROVIDER")
        or "auto"
    ).lower()

    if selected_provider == "polly":
        if not HAS_POLLY_MODULE:
            raise ImportError("polly_tts module not available. Install boto3 and check polly_tts.py.")
        return polly_text_to_speech(text=text, language=language, output_path=output_path)

    elif selected_provider == "auto":
        # Try Amazon Polly first if AWS credentials are configured
        has_aws_creds = bool(os.getenv("AWS_ACCESS_KEY_ID") or os.path.exists(os.path.expanduser("~/.aws/credentials")))
        if HAS_POLLY_MODULE and has_aws_creds:
            try:
                print(f"[TTS] Using Amazon Polly for {language}...")
                return polly_text_to_speech(text=text, language=language, output_path=output_path)
            except Exception as e:
                print(f"[TTS Warning] Amazon Polly failed ({e}). Falling back to gTTS...")
                return gtts_text_to_speech(text=text, language=language, output_path=output_path)
        else:
            print("[TTS] Using gTTS (set AWS credentials in .env to use Amazon Polly)...")
            return gtts_text_to_speech(text=text, language=language, output_path=output_path)

    else:
        # Fallback to gTTS
        return gtts_text_to_speech(text=text, language=language, output_path=output_path)


if __name__ == "__main__":
    sample_simplified_text = "आपको फॉर्म एलएलडी-1 जमा करना होगा। इसके साथ पता और उम्र का प्रमाण देना होगा।"
    path = text_to_speech(sample_simplified_text, "Hindi", "test_output.mp3")
    print(f"Audio saved to: {path}")