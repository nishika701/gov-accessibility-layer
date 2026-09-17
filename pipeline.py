from simplify import simplify_text
from tts import text_to_speech


def process(text: str, target_language: str = "Hindi", audio_output_path: str = "output.mp3") -> dict:
    print(f"Simplifying text into {target_language}...")
    simplified = simplify_text(text, target_language)

    print("Generating audio...")
    audio_path = text_to_speech(simplified, target_language, audio_output_path)

    return {
        "original_text": text,
        "simplified_text": simplified,
        "language": target_language,
        "audio_path": audio_path,
    }


if __name__ == "__main__":
    sample_text = (
        "Applicants must submit Form LLD-1 along with valid proof of address "
        "and proof of age within 30 days of the date of application. A fee of "
        "Rs. 200 is applicable. Failure to submit within the stipulated time "
        "will result in cancellation of the application."
    )

    result = process(sample_text, "Hindi")

    print("\n=== ORIGINAL ===")
    print(result["original_text"])
    print("\n=== SIMPLIFIED ===")
    print(result["simplified_text"])
    print(f"\n=== AUDIO SAVED TO: {result['audio_path']} ===")