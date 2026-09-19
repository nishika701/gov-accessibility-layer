from aws_document_processor import extract_text_from_s3
from document_analyzer import analyze_document
from retrieval import retrieve
from simplify import simplify_text, analyze_document_with_llm
from understanding_check import check_answer


BUCKET_NAME = "gov-accessibility-layer-devforge-237303364767-us-east-1-an"


def process_document(object_key):

    print("\n================================")
    print("STEP 1: EXTRACTING DOCUMENT")
    print("================================")

    result = extract_text_from_s3(
        bucket_name=BUCKET_NAME,
        object_key=object_key
    )

    text = result["text"]

    print(f"Extracted {len(text)} characters.")


    print("\n================================")
    print("STEP 2: ANALYZING DOCUMENT")
    print("================================")

    document = analyze_document(text)

    print(f"Detected {len(document['sections'])} sections.")
    print(f"Detected {len(document['fields'])} possible fields.")


    print("\n================================")
    print("STEP 3: AI ANALYSIS")
    print("================================")

    ai_analysis = analyze_document_with_llm(text)

    print("\nSUMMARY:")
    print(ai_analysis.get("summary", ""))


    print("\nIMPORTANT FACTS:")

    for fact in ai_analysis.get("important_facts", []):
        print(f"- {fact}")


    print("\nREQUIREMENTS:")

    for requirement in ai_analysis.get("requirements", []):
        print(f"- {requirement}")


    print("\nQUESTIONS:")

    for i, question in enumerate(
        ai_analysis.get("questions", []), 1
    ):
        print(f"{i}. {question['question']}")


    return {
        "document": document,
        "ai_analysis": ai_analysis,
        "text": text
    }


def answer_document_question(
    question,
    sections,
    user_answer,
    expected_answer
):

    relevant_sections = retrieve(
        question,
        sections,
        top_k=3
    )

    result = check_answer(
        user_answer,
        expected_answer
    )

    if result:
        return {
            "correct": True,
            "message": "Correct. You understood the information.",
            "relevant_sections": relevant_sections
        }

    return {
        "correct": False,
        "message": (
            "That is not quite correct. "
            "Let me explain that part again."
        ),
        "relevant_sections": relevant_sections
    }


def run_understanding_check(result):

    questions = result["ai_analysis"].get("questions", [])
    sections = result["document"].get("sections", [])

    if not questions:
        print("\nNo questions were generated.")
        return

    print("\n================================")
    print("UNDERSTANDING CHECK")
    print("================================")

    for i, question_data in enumerate(questions, 1):

        question = question_data["question"]
        expected_answer = question_data["expected_answer"]
        explanation = question_data["explanation"]

        print(f"\nQuestion {i}: {question}")

        user_answer = input("Your answer: ")

        check = answer_document_question(
            question,
            sections,
            user_answer,
            expected_answer
        )

        if check["correct"]:

            print("\n✓ Correct!")

        else:

            print("\nLet's go through that again.")
            print(explanation)

            retry = input("\nTry answering again: ")

            retry_check = check_answer(
                retry,
                expected_answer
            )

            if retry_check:
                print("\n✓ Correct!")
            else:
                print("\nWe'll move to the next question.")


def run_voice_loop(result):

    """
    Placeholder for the AWS Polly + Transcribe voice loop.

    The actual AWS calls can be connected here without
    changing the document-processing pipeline.
    """

    print("\n================================")
    print("VOICE MODE")
    print("================================")

    print("Document is ready for voice interaction.")

    while True:

        user_input = input(
            "\nType your question "
            "(or type 'exit'): "
        )

        if user_input.lower() == "exit":
            break

        sections = result["document"]["sections"]

        relevant = retrieve(
            user_input,
            sections,
            top_k=3
        )

        context = "\n".join(relevant)

        print("\nRelevant document information:")
        print(context)

        print("\nVoice response would be generated here using Polly.")


if __name__ == "__main__":

    OBJECT_KEY = "CZ-Form-I.pdf"

    result = process_document(OBJECT_KEY)

    run_understanding_check(result)

    # Enable later when the complete voice system is connected.
    # run_voice_loop(result)