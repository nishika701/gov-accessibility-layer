"""
Amazon Polly Text-to-Speech (TTS) module.
Converts text into natural-sounding speech using AWS Amazon Polly.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

# Load environment variables from .env file if present
load_dotenv()

# Configure console encoding for Windows if needed
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Voice configuration mapping for Amazon Polly
POLLY_VOICE_CONFIG = {
    "Hindi": {
        "voice_id": "Kajal",
        "engine": "neural",
        "language_code": "hi-IN",
        "fallback_voice": "Aditi",
        "fallback_engine": "standard",
    },
    "English": {
        "voice_id": "Kajal",
        "engine": "neural",
        "language_code": "en-IN",
        "fallback_voice": "Joanna",
        "fallback_engine": "neural",
    },
}


def get_polly_client(region_name: str = None):
    """
    Initializes and returns a boto3 Polly client using
    the AWS IAM Identity Center SSO profile.
    """
    region = region_name or "us-east-1"

    session = boto3.Session(
        profile_name="gov-accessibility",
        region_name=region
    )

    return session.client("polly")


def polly_text_to_speech(
    text: str,
    language: str = "Hindi",
    output_path: str = "output.mp3",
    voice_id: str = None,
    engine: str = None,
    region_name: str = None,
) -> str:
    """
    Synthesizes speech using Amazon Polly and saves to output_path.

    :param text: Text to convert to speech.
    :param language: Language name (e.g. "Hindi", "English").
    :param output_path: Destination path for the generated MP3 file.
    :param voice_id: Optional specific Amazon Polly VoiceId (e.g. "Kajal", "Aditi").
    :param engine: Optional engine type ("neural" or "standard").
    :param region_name: Optional AWS region (e.g. "ap-south-1").
    :return: Path to the generated audio file.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for text-to-speech conversion.")

    # Determine voice and engine
    voice_config = POLLY_VOICE_CONFIG.get(language, POLLY_VOICE_CONFIG["Hindi"])
    selected_voice = voice_id or voice_config["voice_id"]
    selected_engine = engine or voice_config.get("engine", "neural")

    client = get_polly_client(region_name)

    # Ensure output directory exists
    output_file = Path(output_path).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    def _call_polly(v_id: str, eng: str):
        kwargs = {
            "Text": text,
            "OutputFormat": "mp3",
            "VoiceId": v_id,
        }
        if eng:
            kwargs["Engine"] = eng
        return client.synthesize_speech(**kwargs)

    try:
        response = _call_polly(selected_voice, selected_engine)
    except (ClientError, BotoCoreError) as err:
        # If neural engine is unavailable for the region or voice, try fallback standard voice
        fallback_voice = voice_config.get("fallback_voice")
        fallback_engine = voice_config.get("fallback_engine")
        if fallback_voice and (fallback_voice != selected_voice or fallback_engine != selected_engine):
            print(f"[Amazon Polly] Attempt with {selected_voice} ({selected_engine}) failed: {err}")
            print(f"[Amazon Polly] Retrying with fallback voice {fallback_voice} ({fallback_engine})...")
            response = _call_polly(fallback_voice, fallback_engine)
        else:
            raise

    # Write the audio stream to file
    if "AudioStream" in response:
        with open(output_file, "wb") as f:
            f.write(response["AudioStream"].read())
        return str(output_file)
    else:
        raise RuntimeError("Amazon Polly did not return an AudioStream.")


if __name__ == "__main__":
    sample_hindi_text = "आपको फॉर्म एलएलडी-1 जमा करना होगा। इसके साथ पता और उम्र का प्रमाण देना होगा।"
    output = "polly_output.mp3"
    print(f"Synthesizing Hindi speech via Amazon Polly into {output}...")
    try:
        path = polly_text_to_speech(sample_hindi_text, "Hindi", output)
        print(f"Success! Audio saved to: {path}")
    except NoCredentialsError:
        print("[Error] AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env or environment variables.")
    except Exception as e:
        print(f"[Error] Amazon Polly TTS failed: {e}")
