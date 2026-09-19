import re


def normalize(text):
    """
    Normalize text for simple answer comparison.
    """

    text = text.lower().strip()

    text = re.sub(r"[^\w\s]", "", text)

    text = re.sub(r"\s+", " ", text)

    return text


def answer_matches(user_answer, expected_answer):
    """
    Check whether the user's answer matches the expected answer.
    """

    user = normalize(user_answer)
    expected = normalize(expected_answer)

    if user == expected:
        return True

    # Allow the expected answer to be contained in
    # a slightly longer user response.
    if expected in user:
        return True

    return False


def check_answer(user_answer, expected_answer):
    """
    Public function used by pipeline.py.
    """

    return answer_matches(
        user_answer,
        expected_answer
    )


def run_check(question):
    """
    Check a complete question object.

    Expected format:

    {
        "question": "...",
        "expected_answer": "...",
        "explanation": "..."
    }
    """

    print("\nQuestion:")
    print(question["question"])

    user_answer = input("Your answer: ")

    correct = check_answer(
        user_answer,
        question["expected_answer"]
    )

    if correct:
        print("\n✓ Correct!")
        return True

    print("\n✗ Not quite.")

    print("\nExplanation:")
    print(question["explanation"])

    return False


if __name__ == "__main__":

    test_question = {
        "question": "What document must the applicant attach?",
        "expected_answer": "identity proof",
        "explanation": "The applicant must attach identity proof."
    }

    print("=== UNDERSTANDING CHECK TEST ===")

    run_check(test_question)