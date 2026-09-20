# Gov Accessibility Layer

An AI-powered citizen accessibility platform designed to simplify complex government and administrative documents into plain, citizen-friendly language in native Indian languages, test citizen comprehension with interactive questions, and support voice accessibility.

---

## 1. Prerequisites & Environment Setup

### Environment Variables (.env)
Create or update your `.env` file in the project root:

```env
# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash

# AWS Configuration (Optional for cloud features, local fallbacks are supported)
AWS_PROFILE=gov-accessibility
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=gov-accessibility-layer-devforge-237303364767-us-east-1-an
TRANSCRIBE_S3_BUCKET=gov-accessibility-layer-devforge-237303364767-us-east-1-an

# Audio Settings
TTS_PROVIDER=auto
```

### Install Dependencies
Run in PowerShell / Terminal:
```powershell
pip install -r requirements.txt
```
*(If you are using the virtual environment, use `.venv\Scripts\pip.exe install -r requirements.txt`)*

---

## 2. How to Run the Program

### Method 1: FastAPI Web Server (Interactive Swagger UI)

1. Start the server:
```powershell
uvicorn api:app --reload --port 8000
```
*(Or with virtualenv: `.venv\Scripts\uvicorn.exe api:app --reload --port 8000`)*

2. Open the interactive Swagger documentation in your browser:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

### Method 2: Command Line Testing

You can run individual Python modules directly:

1. **Test Gemini AI functions directly:**
```powershell
python -c "import gemini_service; print(gemini_service.explain_document('Renewal notice: submit Form LLD-1 within 30 days.', 'Hindi'))"
```

2. **Test Document Simplification & Question Analysis:**
```powershell
python simplify.py
```

3. **Test Full Pipeline on a Document:**
```powershell
python pipeline.py
```

---

## 3. Test Data & Request Payloads for AI Endpoints

Here are the complete test payloads and requests to test each endpoint via Swagger UI, Postman, or `curl`:

---

### Test Data A: Base Government Document Text (Input Context)

```text
GOVERNMENT OF DELHI - TRANSPORT DEPARTMENT
NOTICE: Renewal of Driving License
Applicants must submit Form LLD-1 within 30 days of expiry.
A fee of Rs. 200 must be deposited.
Attach Proof of Address and Proof of Age.
Failure to do so will result in penalty and cancellation.
```

---

### Endpoint 1: Upload Document (`POST /upload`)

* **URL:** `http://127.0.0.1:8000/upload`
* **Method:** `POST`
* **Type:** `multipart/form-data`
* **Field Name:** `file`
* **File to use:** Select [`sample_document.pdf`](sample_document.pdf) from the project root.
* **Sample Response (201 Created):**
```json
{
  "status": "success",
  "message": "PDF successfully stored (s3 or local_mock)",
  "filename": "sample_document.pdf",
  "bucket": "gov-accessibility-layer-devforge-237303364767-us-east-1-an",
  "key": "uploads/caae1350_sample_document.pdf",
  "s3_uri": "s3://gov-accessibility-layer-devforge-237303364767-us-east-1-an/uploads/caae1350_sample_document.pdf",
  "storage": "local_mock",
  "local_path": "uploads\\caae1350_sample_document.pdf"
}
```

---

### Endpoint 2: Process & Extract OCR Text (`POST /process`)

* **URL:** `http://127.0.0.1:8000/process`
* **Method:** `POST`
* **Content-Type:** `application/json`
* **Request Body:**
```json
{
  "bucket": "gov-accessibility-layer-devforge-237303364767-us-east-1-an",
  "key": "uploads/ac8cb84e_sample_document.pdf",
  "s3_uri": "s3://gov-accessibility-layer-devforge-237303364767-us-east-1-an/uploads/ac8cb84e_sample_document.pdf",
  "document_id": "string"
}
```
* **Sample Response (200 OK):**
```json
{
  "status": "success",
  "document_id": "uploads/ac8cb84e_sample_document.pdf",
  "source": "local_ocr",
  "lines_count": 1,
  "text": "Applicants must submit Form LLD-1 along with valid proof of address and proof of age within 30 days of the date"
}
```

---

### Endpoint 3: Simplify Document with Gemini AI (`POST /explain`)

* **URL:** `http://127.0.0.1:8000/explain`
* **Method:** `POST`
* **Content-Type:** `application/json`
* **Request Body:**
```json
{
  "text": "GOVERNMENT OF DELHI - TRANSPORT DEPARTMENT\nNOTICE: Renewal of Driving License\nApplicants must submit Form LLD-1 within 30 days of expiry.\nA fee of Rs. 200 must be deposited.\nAttach Proof of Address and Proof of Age.\nFailure to do so will result in penalty and cancellation.",
  "language": "Hindi"
}
```
* **Sample Response (200 OK):**
```json
{
  "status": "success",
  "source": "gemini",
  "language": "Hindi",
  "simplified_text": "**दिल्ली सरकार - आवश्यक सूचना**\n\n**विषय: ड्राइविंग लाइसेंस का नवीनीकरण (रिन्यू करवाना)**\n\n* **क्या करना है?:** अगर आपका ड्राइविंग लाइसेंस खत्म (एक्सपायर) हो गया है, तो आपको **फॉर्म LLD-1** भरना होगा।\n* **समय सीमा:** लाइसेंस खत्म होने के **30 दिनों के भीतर** यह फॉर्म जमा करना जरूरी है।\n* **फीस:** इसके लिए आपको **200 रुपये** की सरकारी फीस देनी होगी।\n* **जरूरी दस्तावेज:** पते का प्रमाण पत्र और उम्र का प्रमाण पत्र।",
  "key_points": {
    "deadline": "30 days",
    "fee": "Rs. 200",
    "form": "Form LLD-1",
    "documents": "Proof of Address, Proof of Age"
  }
}
```

---

### Endpoint 4: Generate Understanding Question with Gemini AI (`POST /question`)

* **URL:** `http://127.0.0.1:8000/question`
* **Method:** `POST`
* **Content-Type:** `application/json`
* **Request Body:**
```json
{
  "document_context": "Applicants must submit Form LLD-1 within 30 days of expiry. A fee of Rs. 200 must be deposited. Attach Proof of Address and Proof of Age.",
  "language": "Hindi"
}
```
* **Sample Response (200 OK):**
```json
{
  "status": "success",
  "source": "gemini",
  "question_id": "bbe7d50a26",
  "question": "ड्राइविंग लाइसेंस की समय सीमा समाप्त होने के कितने दिनों के भीतर फॉर्म LLD-1 जमा करना अनिवार्य है?",
  "options": [
    "15 दिन",
    "30 दिन",
    "45 दिन",
    "60 दिन"
  ],
  "language": "Hindi"
}
```

---

### Endpoint 5: Check Citizen Answer with Gemini AI (`POST /check-answer`)

* **URL:** `http://127.0.0.1:8000/check-answer`
* **Method:** `POST`
* **Content-Type:** `application/json`
* **Request Body:**
```json
{
  "question": "ड्राइविंग लाइसेंस की समय सीमा समाप्त होने के कितने दिनों के भीतर फॉर्म LLD-1 जमा करना अनिवार्य है?",
  "user_answer": "30 दिनों के भीतर",
  "document_context": "Applicants must submit Form LLD-1 within 30 days of expiry. A fee of Rs. 200 must be deposited. Attach Proof of Address and Proof of Age.",
  "question_id": "bbe7d50a26"
}
```
* **Sample Response (200 OK):**
```json
{
  "status": "success",
  "source": "gemini",
  "understood": true,
  "is_correct": true,
  "feedback": "शानदार! आपका उत्तर पूरी तरह से सही है। ड्राइविंग लाइसेंस समाप्त होने के 30 दिनों के भीतर ही फॉर्म LLD-1 जमा करना होता है।",
  "explanation": "दस्तावेज़ के अनुसार, आवेदन और शुल्क 30 दिनों की समय सीमा के अंदर जमा किया जाना चाहिए।"
}
```

---

## 4. Testing with Other Indian Languages

In both `POST /explain` and `POST /question`, you can change `"language"` to any of the following to receive explanations in native scripts:

| Language | Sample Value | Example Output Script |
| :--- | :--- | :--- |
| **Hindi** | `"language": "Hindi"` | देवनागरी लिपि (हिन्दी) |
| **Tamil** | `"language": "Tamil"` | தமிழ் எழுத்துக்கள் |
| **Telugu** | `"language": "Telugu"` | తెలుగు లిపి |
| **Marathi** | `"language": "Marathi"` | देवनागरी (मराठी) |
| **Bengali** | `"language": "Bengali"` | বাংলা লিপি |
| **Kannada** | `"language": "Kannada"` | ಕನ್ನಡ ಲಿಪಿ |
| **Gujarati** | `"language": "Gujarati"` | ગુજરાતી લિપિ |
| **English** | `"language": "English"` | Plain English |
