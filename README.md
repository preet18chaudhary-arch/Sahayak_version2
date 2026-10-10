# Sahayak Verification Engine

> **AI-Assisted Pre-Submission Document Verification for Scholarship Applications**

The **Sahayak Verification Engine** is a policy-driven verification platform designed to help students identify document errors, missing records, inconsistent information, and scholarship eligibility issues *before* submitting their scholarship applications.

It combines multi-format PDF and image processing (direct text extraction and Tesseract OCR fallback), document classification, slot-based expected document type validation, structured field extraction, configurable scholarship eligibility rules, cross-document fuzzy consistency checks, unified SQLite session persistence, and human-in-the-loop resolution.

---

## The Problem

Scholarship applications are frequently rejected or delayed due to avoidable document mistakes discovered only after formal submission:
* **Wrong document types uploaded in slot** (e.g., uploading an ITR Computation instead of an official Income Certificate, or uploading a PAN card instead of an Aadhaar card).
* **Identity variations across documents** (e.g., spelling differences in name or minor DOB mismatches between Aadhaar and 12th Marksheet).
* **Financial eligibility violations** (e.g., family annual income exceeding the scheme's ceiling).
* **Academic qualification failures** (e.g., aggregate percentage falling below the mandatory cutoff).
* **Missing mandatory certificates** or unreadable document scans.
* **Lack of transparency** as applicants have no pre-submission feedback on why their application might fail.

---

## The Solution

Sahayak acts as an intelligent pre-submission verification partner:

```text
Student Selects Slot → Uploads Document (PDF / Image) → Validates Format & Size
                    │
                    ▼
Direct Text Extraction (PDF) / Page-to-Image OCR (Scanned / Images)
                    │
                    ▼
Document Classification & Slot Validation (Expected vs. Detected)
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
    [MISMATCH]               [MATCH]
Flag DOCUMENT_TYPE_MISMATCH  Extract Structured Fields
Slot Unsatisfied             Evaluate Scholarship Rules
Show Guidance & Replace      Run Cross-Document Consistency
                             Recalculate Session Readiness
```

### Core Verification Philosophy
**AI Detects → Explains → Human Confirms → System Re-evaluates**
Sahayak functions strictly as an assistive pre-submission verification tool. It never makes silent assumptions, never invents classifications, and leaves final award decisions to official scholarship authorities.

---

## Key Features & Capabilities

### 1. Robust Multi-Format Document Processing
* **Text-Based PDFs (`.pdf`)**: Direct, high-speed text extraction using PyMuPDF (`pymupdf`).
* **Scanned / Image-Only PDFs**: Automatic page rendering to high-resolution images with seamless fallback to Tesseract OCR.
* **Image Uploads**: Supports PNG, JPG, JPEG, and WEBP formats with preprocessing and OCR.
* **Multi-Page Handling**: Supports multi-page documents (up to 10 pages) with configurable limits.
* **Validation & Security**: Rejects empty files (0 bytes), corrupted PDFs, encrypted files, and unsupported extensions with clear HTTP 400 responses. Enforces a 15MB file size limit.

### 2. Slot-Based Expected Document Type Validation
* **Slot Association**: Every document upload can be targeted to a specific slot (e.g., `expected_type: "income_certificate"`).
* **Precise Detection**:
  * Distinguishes **Income Certificate** from **ITR Computation** and **ITR Acknowledgement (ITR-V)**.
  * Distinguishes **Aadhaar Card** from **PAN Card** and marksheet documents.
  * Identifies Class 10th and 12th marksheets accurately.
  * Returns `UNKNOWN` with actionable guidance if a document cannot be reliably identified.
* **Mismatch Protection**:
  * If the wrong document is uploaded (e.g. ITR Computation into an Income Certificate slot), the engine returns `DOCUMENT_TYPE_MISMATCH` with `classification_status: MISMATCH`.
  * **Critical Invariant**: Mismatched or unreadable documents **never** satisfy a required document slot, never pollute extracted fields, and prevent the application from becoming `READY_FOR_SUBMISSION`.
* **Slot Replacement & Deletion**:
  * Uploading a new file into an existing slot replaces the old document record, purges its stale extracted fields and discrepancies, and re-evaluates session readiness automatically.
  * Dedicated `DELETE /api/sessions/{session_id}/documents/{doc_id}` endpoint allows instant removal of any uploaded document.

### 3. Unified SQLite Database & Safe Schema Migration
* Uses a single database-backed session store (`DatabaseSessionStore`) persisted in `sahayak.db`.
* Automatic, non-destructive schema migration initializes new columns (`expected_type`, `classification_status`, `verification_status`, `message`) on existing databases without data loss.

### 4. Scholarship Rule Engine & Eligibility Evaluation
* Configurable rule presets (e.g. *National Merit-cum-Means Scholarship*):
  * Mandatory document checklist (Aadhaar, 12th Marksheet, Income Certificate).
  * Income ceiling enforcement (e.g. family income $\le$ ₹2,50,000/year).
  * Academic percentage cutoff enforcement (e.g. $\ge$ 60%).
* Live evaluation updates after every upload, replacement, or deletion.

### 5. Cross-Document Consistency & Human-in-the-Loop Review
* Cross-document name and Date of Birth comparison using fuzzy similarity algorithms.
* Configurable matching thresholds:
  * **Auto-approve** ($\ge 98\%$ similarity): Automatically approved.
  * **Human Review** ($80\% - 97\%$ similarity): Flagged as a spelling variation; prompts the student for a confirmation note.
  * **Hard Mismatch** ($< 80\%$ similarity): Blocks submission until resolved or replaced.

### 6. Application Readiness States
* `READY_FOR_SUBMISSION`: All mandatory documents verified, identity fields consistent, eligibility criteria satisfied.
* `ACTION_REQUIRED`: Document type mismatch, critical discrepancy, or eligibility violation requires correction.
* `INCOMPLETE`: One or more mandatory documents have not been uploaded.
* `IN_REVIEW`: Minor variation flagged requiring human confirmation note.

---

## System Architecture

```text
┌────────────────────────────────────────────────────────┐
│                   React + Vite Frontend                │
│  - Slot-based checklist & direct file replacement      │
│  - Mismatch warning banners with clear instructions   │
│  - Real-time verification badges & readiness scorecard │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP / REST API (Port 8001)
                           ▼
┌────────────────────────────────────────────────────────┐
│                   FastAPI Backend Core                 │
│  ├── Document Upload API (multipart/form-data)         │
│  ├── Document Detector (Slot matching & taxonomy)      │
│  ├── OCR Service (PyMuPDF + Dynamic Tesseract OCR)     │
│  ├── Field Extractor (Regex for Income, Marks, DOB)    │
│  ├── Verification Service (Cross-document matching)    │
│  ├── Rule Registry (Scholarship policy definitions)    │
│  └── Database Session Store (SQLite via SQLAlchemy)    │
└────────────────────────────────────────────────────────┘
```

---

## Installation & Setup

### Prerequisites
* **Python**: 3.10 to 3.14 (Python 3.14 tested and verified)
* **Node.js**: v18+ and npm (Node.js v24 tested and verified)
* **Tesseract OCR**: Required for scanned PDF and image OCR processing

---

### Step 1: Install Tesseract OCR

#### Windows
You can install Tesseract using Windows Package Manager or the official installer:
```powershell
winget install UB-Mannheim.TesseractOCR
```
* Or download the installer from: [UB-Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
* **Default search paths detected automatically by Sahayak**:
  * System `PATH` (`tesseract.exe`)
  * `%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe`
  * `C:\Program Files\Tesseract-OCR\tesseract.exe`
  * Or specify explicitly via the `TESSERACT_CMD` environment variable.

#### Linux (Ubuntu / Debian)
```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-eng libtesseract-dev
```

#### macOS (Homebrew)
```bash
brew install tesseract
```

---

### Step 2: Clone and Setup Backend

```powershell
# Navigate to backend directory
cd backend

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Copy environment template
Copy-Item .env.example .env
```

---

### Step 3: Setup Frontend

```powershell
# Navigate to frontend directory
cd ..\frontend

# Install node dependencies
# Note: On Windows PowerShell, use npm.cmd if PowerShell script execution is restricted:
npm.cmd install

# (Optional) Copy environment template
Copy-Item .env.example .env
```

---

## Running the Application

### 1. Start the FastAPI Backend
Open a terminal in the `backend` directory:
```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```
* **API Server**: `http://127.0.0.1:8001`
* **Swagger API Documentation**: `http://127.0.0.1:8001/docs`
* **Health Check**: `http://127.0.0.1:8001/health`

### 2. Start the React Frontend
Open a second terminal in the `frontend` directory:
```powershell
cd frontend
npm.cmd run dev
```
* **Web Application**: `http://localhost:5173`

---

## Running Automated Tests

The test suite covers PDF text extraction, scanned PDF OCR fallback, image OCR, file validation, document slot mismatch validation, document replacement, document deletion, and database persistence.

To execute the test suite from either repository root or `backend`:
```powershell
# From repository root:
backend\.venv\Scripts\python.exe -m pytest -v

# Or from backend directory:
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

All 24 test suites execute and pass against the real engine:
```text
tests/test_eligibility_integration.py .......... PASSED
tests/test_emergency_repairs_and_slots.py ...... PASSED (10 tests)
tests/test_mismatch_integration.py ............. PASSED
tests/test_resolution_integration.py ........... PASSED
tests/test_step1.py ............................ PASSED
tests/test_upload_integration.py ............... PASSED
tests/test_verification.py ..................... PASSED (8 tests)
======================== 24 passed in 5.03s ========================
```

---

## API Specification

### 1. Document Upload / Replacement
`POST /api/sessions/{session_id}/documents/upload`
* **Content-Type**: `multipart/form-data`
* **Form Fields**:
  * `file`: Binary file (PDF, PNG, JPG, JPEG, WEBP; max 15MB)
  * `expected_type` *(optional)*: Target slot (`aadhaar`, `marksheet_12th`, `income_certificate`, etc.)
  * `doc_id` *(optional)*: Existing document ID if replacing an existing file record

#### Example Response: Success (Document Matched)
```json
{
  "doc_id": "doc_sess_123_1",
  "file_name": "income_certificate.pdf",
  "detected_type": "income_certificate",
  "expected_type": "income_certificate",
  "expected_document_type": "income_certificate",
  "detected_document_type": "income_certificate",
  "classification_status": "MATCH",
  "verification_status": "VERIFIED",
  "message": "Document recognized and verified as Income Certificate.",
  "fields": {
    "name": "Hana Sharma",
    "income": "180000"
  },
  "readiness": {
    "overall_status": "READY_FOR_SUBMISSION",
    "status_message": "All required documents verified. Application ready for submission.",
    "documents_checked": 3,
    "fields_extracted": 6,
    "fields_consistent": 6,
    "potential_mismatches": 0,
    "required_documents_missing": []
  }
}
```

#### Example Response: Document Type Mismatch
```json
{
  "doc_id": "doc_sess_123_2",
  "file_name": "itr_computation.pdf",
  "detected_type": "itr_computation",
  "expected_type": "income_certificate",
  "expected_document_type": "income_certificate",
  "detected_document_type": "itr_computation",
  "classification_status": "MISMATCH",
  "verification_status": "DOCUMENT_TYPE_MISMATCH",
  "message": "This appears to be an ITR Computation, but an Income Certificate is required. Please upload the correct Income Certificate.",
  "fields": {},
  "readiness": {
    "overall_status": "ACTION_REQUIRED",
    "status_message": "Document type mismatch detected. Upload correct document for required slot.",
    "required_documents_missing": ["income_certificate"]
  }
}
```

### 2. Document Deletion
`DELETE /api/sessions/{session_id}/documents/{doc_id}`
* Removes document and all its extracted fields from the session.
* Recalculates scholarship readiness immediately.
* Returns updated `VerificationSession` model.

### 3. Session Management
* `POST /api/sessions/create`: Create a new verification session.
* `GET /api/sessions/{session_id}`: Fetch complete live session state.
* `GET /api/scholarships`: Fetch supported scholarship rule presets.
* `POST /api/sessions/{session_id}/discrepancies/{discrepancy_id}/resolve`: Submit a human confirmation note to resolve a flagged discrepancy.

---

## Supported Document Types

| Document Type | Key Identifiers | Typical Use |
| :--- | :--- | :--- |
| `aadhaar` | Unique Identification Authority, Government of India, Aadhaar | Primary identity & DOB verification |
| `marksheet_12th` | Senior Secondary, Class XII, Board Examination, Marks / CGPA | Academic qualification & marks cutoff |
| `marksheet_10th` | Secondary School Examination, Class X, Matriculation | Secondary academic & DOB record |
| `income_certificate` | Revenue Department, Tehsildar, Annual Family Income | Financial eligibility ceiling |
| `pan_card` | Income Tax Department, Permanent Account Number | Financial ID (Distinguished from Aadhaar) |
| `itr_computation` | Computation of Total Income, Gross Total Income | Tax computation (Distinguished from Income Cert) |
| `itr_acknowledgement` | Indian Income Tax Return Acknowledgement, ITR-V | Tax filing ack (Distinguished from Income Cert) |
| `caste_certificate` | Caste / Community Certificate, SC / ST / OBC | Category reservation verification |
| `domicile_certificate` | Resident / Domicile Certificate | State domicile eligibility |
| `bank_passbook` | Account Number, IFSC Code, Bank Branch | Direct Benefit Transfer (DBT) disbursement |
| `unknown` | Document headers not recognized with confidence | Flags for clear scan or replacement |

---

## License & Disclaimer

This project was built as a hackathon submission. It is an assistive verification layer to help applicants detect avoidable document mistakes early; it does not replace official institutional verification or guarantee scholarship disbursement.
