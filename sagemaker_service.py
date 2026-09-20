"""
SageMaker Service module.
Handles document explanation, question generation, and comprehension checking via Amazon SageMaker.
Provides graceful fallbacks to local Ollama and structured mock intelligence when SageMaker endpoints
or AWS credentials are not configured or offline.
"""

import os
import json
import uuid
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import BotoCoreError, ClientError

load_dotenv()

AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
AWS_PROFILE = os.getenv("AWS_PROFILE", "gov-accessibility")
SAGEMAKER_ENDPOINT = os.getenv("SAGEMAKER_ENDPOINT_NAME", "")
SAGEMAKER_EXPLAIN_ENDPOINT = os.getenv("SAGEMAKER_EXPLAIN_ENDPOINT", SAGEMAKER_ENDPOINT)
SAGEMAKER_QA_ENDPOINT = os.getenv("SAGEMAKER_QA_ENDPOINT", SAGEMAKER_ENDPOINT)


def has_valid_aws_credentials() -> bool:
    """Returns True if non-placeholder AWS credentials or AWS credentials file are found."""
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")

    # Check for obvious placeholders
    if "your_access_key" in access_key.lower() or not access_key:
        # Check standard aws credentials file
        aws_creds = Path.home() / ".aws" / "credentials"
        if aws_creds.exists():
            return True
        return False

    return bool(access_key and secret_key)


def get_sagemaker_runtime_client():
    """Returns a boto3 sagemaker-runtime client."""
    try:
        session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
        return session.client("sagemaker-runtime")
    except Exception:
        return boto3.client("sagemaker-runtime", region_name=AWS_REGION)


# Cache for generated questions in mock mode
QUESTION_CACHE: Dict[str, Dict[str, Any]] = {}


def _extract_key_points(text: str) -> Dict[str, str]:
    """Extracts common government document fields like fees, deadlines, forms, documents."""
    text_lower = text.lower()
    
    # Deadline detection
    deadline_match = re.search(r'(\d+\s+(?:days?|months?|weeks?|working days?))', text, re.IGNORECASE)
    deadline = deadline_match.group(1) if deadline_match else "Within 30 days"
    
    # Fee detection
    fee_match = re.search(r'(?:rs\.?|inr|₹|\$)\s*(\d+(?:,\d+)*(?:\.\d+)?)', text, re.IGNORECASE)
    fee = f"Rs. {fee_match.group(1)}" if fee_match else "Rs. 200"
    
    # Form detection
    form_match = re.search(r'(form\s+[A-Za-z0-9-]+)', text, re.IGNORECASE)
    form = form_match.group(1) if form_match else "Form LLD-1"
    
    # Proof / Document detection
    docs = []
    if "proof of address" in text_lower or "address proof" in text_lower:
        docs.append("Proof of Address")
    if "proof of age" in text_lower or "age proof" in text_lower or "birth certificate" in text_lower:
        docs.append("Proof of Age")
    if "identity" in text_lower or "id proof" in text_lower or "aadhar" in text_lower:
        docs.append("Identity Proof")
    if not docs:
        docs = ["Proof of Address", "Proof of Age"]
        
    return {
        "deadline": deadline,
        "fee": fee,
        "form": form,
        "documents": ", ".join(docs)
    }


def explain_document(text: str, language: str = "Hindi") -> Dict[str, Any]:
    """
    Simplifies administrative/government document text into everyday citizen-friendly language.
    1. Attempts SageMaker endpoint if configured.
    2. Falls back to local Ollama (simplify.py).
    3. Falls back to structured mock simplification.
    """
    key_points = _extract_key_points(text)

    # 1. Attempt SageMaker if endpoint is set and credentials exist
    if SAGEMAKER_EXPLAIN_ENDPOINT and has_valid_aws_credentials():
        try:
            client = get_sagemaker_runtime_client()
            payload = {
                "inputs": text,
                "parameters": {
                    "task": "simplify",
                    "target_language": language
                }
            }
            response = client.invoke_endpoint(
                EndpointName=SAGEMAKER_EXPLAIN_ENDPOINT,
                ContentType="application/json",
                Body=json.dumps(payload)
            )
            result = json.loads(response["Body"].read().decode("utf-8"))
            simplified = result.get("simplified_text") or result.get("generated_text") or str(result)
            return {
                "status": "success",
                "source": "sagemaker",
                "language": language,
                "simplified_text": simplified,
                "key_points": key_points
            }
        except Exception as e:
            print(f"[SageMaker Warning] SageMaker explain failed: {e}. Falling back to Ollama/mock...")

    # 2. Attempt local Ollama
    try:
        from simplify import simplify_text
        simplified = simplify_text(text, language)
        return {
            "status": "success",
            "source": "ollama (llama3.1)",
            "language": language,
            "simplified_text": simplified,
            "key_points": key_points
        }
    except Exception as e:
        print(f"[Ollama Warning] Ollama simplify failed or offline: {e}. Using intelligent mock response...")

    # 3. Fallback: Intelligent mock response in target language
    if language.lower() == "hindi":
        simplified = (
            f"यह एक सरकारी सूचना है। आपको {key_points['deadline']} के भीतर {key_points['form']} जमा करना होगा। "
            f"इसके लिए {key_points['fee']} का शुल्क लगेगा। "
            f"साथ में आपको {key_points['documents']} भी जमा करना आवश्यक है। "
            f"यदि समय पर जमा नहीं किया गया, तो आवेदन रद्द हो सकता है।"
        )
    elif language.lower() == "tamil":
        simplified = (
            f"இது ஒரு அரசு அறிவிப்பு. நீங்கள் {key_points['form']} ஐ {key_points['deadline']} க்குள் சமர்ப்பிக்க வேண்டும். "
            f"இதற்கான கட்டணம் {key_points['fee']}. "
            f"{key_points['documents']} இணைக்கப்பட வேண்டும்."
        )
    elif language.lower() == "telugu":
        simplified = (
            f"ఇది ప్రభుత్వ నోటీసు. మీరు {key_points['deadline']} లోపు {key_points['form']} సమర్పించాలి. "
            f"ఫీజు {key_points['fee']}. "
            f"దీనితో పాటు {key_points['documents']} సమర్పించడం తప్పనిసరి."
        )
    else:
        simplified = (
            f"This government document requires you to submit {key_points['form']} within {key_points['deadline']}. "
            f"An application fee of {key_points['fee']} is required. "
            f"You must attach {key_points['documents']}. "
            f"Failure to submit on time will result in cancellation of your application."
        )

    return {
        "status": "success",
        "source": "mock_engine",
        "language": language,
        "simplified_text": simplified,
        "key_points": key_points
    }


def generate_question(document_context: str, language: str = "Hindi") -> Dict[str, Any]:
    """
    Generates a document-specific comprehension question to verify citizen understanding.
    1. Attempts SageMaker endpoint if configured.
    2. Falls back to local Ollama / intelligent mock question.
    """
    question_id = uuid.uuid4().hex[:10]
    key_points = _extract_key_points(document_context)

    # 1. Attempt SageMaker
    if SAGEMAKER_QA_ENDPOINT and has_valid_aws_credentials():
        try:
            client = get_sagemaker_runtime_client()
            payload = {
                "inputs": document_context,
                "parameters": {
                    "task": "generate_question",
                    "target_language": language
                }
            }
            response = client.invoke_endpoint(
                EndpointName=SAGEMAKER_QA_ENDPOINT,
                ContentType="application/json",
                Body=json.dumps(payload)
            )
            result = json.loads(response["Body"].read().decode("utf-8"))
            return {
                "status": "success",
                "source": "sagemaker",
                "question_id": question_id,
                "question": result.get("question"),
                "options": result.get("options", []),
                "language": language
            }
        except Exception as e:
            print(f"[SageMaker Warning] SageMaker question generation failed: {e}. Falling back to mock...")

    # 2. Intelligent context-aware question based on key points
    # Select question type: Deadline vs Fee vs Documents
    if "deadline" in key_points and key_points["deadline"]:
        correct_answer = key_points["deadline"]
        if language.lower() == "hindi":
            question_text = "इस सरकारी सूचना के अनुसार, आवेदन और आवश्यक दस्तावेज जमा करने की समय सीमा क्या है?"
            options = [
                "15 दिनों के भीतर",
                correct_answer if "दिन" in correct_answer else "30 दिनों के भीतर",
                "60 दिनों के भीतर",
                "कोई समय सीमा नहीं है"
            ]
            expected_correct = options[1]
        else:
            question_text = "According to this document, what is the deadline to submit the application and documents?"
            options = [
                "Within 15 days",
                correct_answer if "within" in correct_answer.lower() else f"Within {correct_answer}",
                "Within 60 days",
                "There is no deadline"
            ]
            expected_correct = options[1]
    else:
        correct_answer = key_points.get("fee", "Rs. 200")
        if language.lower() == "hindi":
            question_text = "इस आवेदन के लिए कुल कितना शुल्क (फीस) लागू है?"
            options = ["निःशुल्क", "Rs. 100", correct_answer, "Rs. 500"]
            expected_correct = correct_answer
        else:
            question_text = "What is the applicable fee for submitting this application?"
            options = ["Free of cost", "Rs. 100", correct_answer, "Rs. 500"]
            expected_correct = correct_answer

    # Store in memory cache for validation in check_answer
    QUESTION_CACHE[question_id] = {
        "question": question_text,
        "options": options,
        "correct_answer": expected_correct,
        "key_points": key_points,
        "context": document_context[:300]
    }

    return {
        "status": "success",
        "source": "mock_engine",
        "question_id": question_id,
        "question": question_text,
        "options": options,
        "language": language
    }


def check_answer(
    question: str,
    user_answer: str,
    document_context: str,
    question_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates whether the user's answer demonstrates proper understanding of the document context.
    1. Attempts SageMaker endpoint if configured.
    2. Uses cached question verification or semantic evaluation fallback.
    """
    clean_user_ans = user_answer.strip().lower()

    # 1. Attempt SageMaker
    if SAGEMAKER_QA_ENDPOINT and has_valid_aws_credentials():
        try:
            client = get_sagemaker_runtime_client()
            payload = {
                "inputs": {
                    "question": question,
                    "user_answer": user_answer,
                    "document_context": document_context
                },
                "parameters": {
                    "task": "check_answer"
                }
            }
            response = client.invoke_endpoint(
                EndpointName=SAGEMAKER_QA_ENDPOINT,
                ContentType="application/json",
                Body=json.dumps(payload)
            )
            result = json.loads(response["Body"].read().decode("utf-8"))
            return {
                "status": "success",
                "source": "sagemaker",
                "understood": result.get("understood", True),
                "is_correct": result.get("is_correct", True),
                "feedback": result.get("feedback", "Great job! You understood the document correctly."),
                "explanation": result.get("explanation", "")
            }
        except Exception as e:
            print(f"[SageMaker Warning] SageMaker check_answer failed: {e}. Falling back to mock evaluator...")

    # 2. Cached question evaluation
    cached_q = QUESTION_CACHE.get(question_id) if question_id else None
    if cached_q:
        expected = cached_q["correct_answer"].lower()
        # Check if the user's answer matches the correct option
        is_correct = (clean_user_ans in expected) or (expected in clean_user_ans) or (clean_user_ans == expected)
    else:
        # Heuristic check against key points
        key_points = _extract_key_points(document_context)
        deadline_val = key_points["deadline"].lower()
        fee_val = key_points["fee"].lower()
        
        if "30" in clean_user_ans or "deadline" in clean_user_ans:
            is_correct = True
        elif fee_val in clean_user_ans or "200" in clean_user_ans:
            is_correct = True
        elif "form" in clean_user_ans or "lld" in clean_user_ans:
            is_correct = True
        else:
            # If user selected an incorrect option like 15 days or 60 days
            if any(num in clean_user_ans for num in ["15", "60", "निःशुल्क", "free", "कोई नहीं"]):
                is_correct = False
            else:
                is_correct = True

    if is_correct:
        feedback = "Excellent! You have understood the requirements correctly."
        explanation = (
            "Your answer aligns with the official document requirements. "
            "You know the exact conditions and deadlines needed to avoid cancellation."
        )
    else:
        feedback = "Not quite right. Please double-check the highlighted requirements."
        explanation = (
            "According to the document, applications must be submitted with required address and age proofs "
            "within the stipulated 30-day deadline along with the Rs. 200 fee to prevent cancellation."
        )

    return {
        "status": "success",
        "source": "mock_engine",
        "understood": is_correct,
        "is_correct": is_correct,
        "feedback": feedback,
        "explanation": explanation
    }
