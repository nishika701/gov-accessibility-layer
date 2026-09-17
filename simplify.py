import ollama

MODEL_NAME = "llama3.1"


def simplify_text(text: str, target_language: str = "Hindi") -> str:
    prompt = f"""You are helping an ordinary citizen understand a confusing government document or form.

ORIGINAL TEXT:
\"\"\"{text}\"\"\"

Your task:
1. Explain what this means in simple, everyday {target_language} — avoid bureaucratic or legal jargon.
2. Clearly call out any of the following, if present: deadlines, fees/amounts, required documents, eligibility conditions.
3. Keep it short — a few sentences, not an essay.
4. If anything in the original text is genuinely ambiguous or unclear, say so honestly instead of guessing.

Respond ONLY in {target_language}, written in its native/proper script (e.g. Devanagari for Hindi, Tamil script for Tamil, Telugu script for Telugu) — never Romanized/transliterated text. Do not include English unless a proper noun requires it.

Example of correct Hindi output style (Devanagari script, NOT Romanized):
"आपको फॉर्म जमा करना होगा। इसके साथ पते और उम्र का प्रमाण देना होगा। समय सीमा 30 दिनों की है और शुल्क 200 रुपये है।"

Now respond in the same script style as the example above, but in {target_language}.
"""

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]


if __name__ == "__main__":
    sample_text = (
        "Applicants must submit Form LLD-1 along with valid proof of address "
        "and proof of age within 30 days of the date of application. A fee of "
        "Rs. 200 is applicable. Failure to submit within the stipulated time "
        "will result in cancellation of the application."
    )

    print("=== ORIGINAL ===")
    print(sample_text)
    print("\n=== SIMPLIFIED (Hindi) ===")
    print(simplify_text(sample_text, "Hindi"))