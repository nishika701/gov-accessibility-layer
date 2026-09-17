"""
Converts simplified text into spoken audio, so users who find listening
easier than reading can access the explanation.

Note: gTTS requires a small internet call (it uses Google's TTS service) —
this is the one piece of the pipeline that isn't fully offline. The core
reasoning/simplification (simplify.py) runs entirely local via Ollama.
"""

from gtts import gTTS

# Map friendly language names to gTTS language codes
LANGUAGE_CODES = {
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Bengali": "bn",
    "Marathi": "mr",
    "English": "en",
}


def text_to_speech(text: str, language: str = "Hindi", output_path: str = "output.mp3") -> str:
    """
    Converts text to an audio file in the given language.
    Returns the path to the saved audio file.
    """
    lang_code = LANGUAGE_CODES.get(language, "en")
    tts = gTTS(text=text, lang=lang_code)
    tts.save(output_path)
    return output_path


if __name__ == "__main__":
    # Quick manual test
    sample_simplified_text = "आपको फॉर्म एलएलडी-1 जमा करना होगा। इसके साथ पता और उम्र का प्रमाण देना होगा।"
    path = text_to_speech(sample_simplified_text, "Hindi", "test_output.mp3")
    print(f"Audio saved to: {path}")
    print("Play this file to check pronunciation quality.")