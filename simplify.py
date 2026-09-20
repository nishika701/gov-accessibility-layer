import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please add GEMINI_API_KEY to your .env file."
        )
    return genai.Client(api_key=api_key)


def call_llm(prompt: str, json_mode: bool = False) -> str:
    """
    Call Gemini API with optional JSON structure enforcement.
    """
    client = get_gemini_client()
    config = types.GenerateContentConfig()

    if json_mode:
        config.response_mime_type = "application/json"

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=config
    )

    return response.text


def simplify_text(text: str, target_language: str = "Hindi") -> str:
    prompt = f"""
You are an assistant helping ordinary citizens understand confusing government documents.

Simplify the following document into very simple everyday {target_language}.

Rules:
- Use ONLY information present in the document.
- Do not invent information.
- Explain difficult government/legal terms simply.
- Keep important dates, amounts, requirements and conditions.
- Make it understandable for a person with low literacy.
- Do not remove important information.
- CRITICAL SCRIPT RULE: You MUST write ONLY in the native/proper script of {target_language} (e.g. Devanagari script for Hindi/Marathi, Telugu script for Telugu, Tamil script for Tamil, Bengali script for Bengali, Kannada script for Kannada, Gujarati script for Gujarati, Malayalam script for Malayalam).
- NEVER use Romanized or English alphabet transliterations. Output the actual native alphabet characters directly.

DOCUMENT:
{text}

Return only the simplified explanation written in the native script of {target_language}.
"""
    return call_llm(prompt)


def analyze_document_with_llm(text: str) -> dict:
    prompt = f"""
Analyze the following government document.

Return ONLY valid JSON in this exact structure:

{{
    "summary": "",
    "important_facts": [],
    "requirements": [],
    "questions": [
        {{
            "question": "",
            "expected_answer": "",
            "explanation": ""
        }}
    ]
}}

Rules:
- Use ONLY information from the document.
- Do not invent facts.
- summary should be simple.
- important_facts should contain important dates, conditions, amounts,
  eligibility rules or other critical information.
- requirements should contain documents, actions or conditions required.
- Generate 2 to 5 questions that test whether the user understood
  important information.
- Questions must be answerable from the document.
- expected_answer must contain the correct answer.
- explanation should explain the relevant information simply.

DOCUMENT:
{text}
"""
    raw_response = call_llm(prompt, json_mode=True)

    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        print("LLM did not return valid JSON.")
        print(raw_response)
        return {
            "summary": raw_response,
            "important_facts": [],
            "requirements": [],
            "questions": []
        }


def generate_questions(text: str):
    """
    Generate document-specific comprehension questions.
    """
    analysis = analyze_document_with_llm(text)
    return analysis.get("questions", [])


if __name__ == "__main__":
    sample_text = """
    Applicants must submit the application before 30 September.
    The applicant must provide proof of identity and proof of address.
    Applications submitted after the deadline may not be accepted.
    """

    print("\n=== SIMPLIFIED DOCUMENT ===")
    try:
        simplified = simplify_text(sample_text)
        print(simplified)

        print("\n=== QUESTIONS ===")
        questions = generate_questions(sample_text)
        for i, question in enumerate(questions, 1):
            print(f"\nQuestion {i}: {question['question']}")
            print(f"Expected answer: {question['expected_answer']}")
    except ValueError as e:
        print(f"Configuration Error: {e}")