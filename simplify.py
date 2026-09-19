import json
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1"


def call_llm(prompt):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )

    response.raise_for_status()

    return response.json()["response"]


def simplify_text(text):
    prompt = f"""
You are an assistant helping people understand government documents.

Simplify the following document into very simple everyday language.

Rules:
- Use ONLY information present in the document.
- Do not invent information.
- Explain difficult government/legal terms simply.
- Keep important dates, amounts, requirements and conditions.
- Make it understandable for a person with low literacy.
- Do not remove important information.

DOCUMENT:
{text}

Return only the simplified explanation.
"""

    return call_llm(prompt)


def analyze_document_with_llm(text):
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

    raw_response = call_llm(prompt)

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


def generate_questions(text):
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

    simplified = simplify_text(sample_text)
    print(simplified)

    print("\n=== QUESTIONS ===")

    questions = generate_questions(sample_text)

    for i, question in enumerate(questions, 1):
        print(f"\nQuestion {i}: {question['question']}")
        print(f"Expected answer: {question['expected_answer']}")