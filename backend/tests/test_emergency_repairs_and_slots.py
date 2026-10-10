import io
import pymupdf
import pytest
from PIL import Image, ImageDraw, ImageFont
from starlette.testclient import TestClient

from app.main import app
from app.models.schemas import ClassificationStatus, DocumentType, DocumentVerificationStatus, ReadinessStatus
from app.services.database_session_store import session_store
from app.services.ocr_service import is_tesseract_available

client = TestClient(app, base_url="http://127.0.0.1:8000")


def create_sample_pdf(text: str) -> bytes:
    """Helper to generate an in-memory selectable text PDF."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def create_scanned_pdf(text: str) -> bytes:
    """Helper to generate an in-memory scanned/image-only PDF."""
    img = Image.new("RGB", (600, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 30), text, fill=(0, 0, 0))

    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_bytes = img_buffer.getvalue()

    doc = pymupdf.open()
    page = doc.new_page(width=600, height=300)
    page.insert_image(page.rect, stream=img_bytes)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def test_valid_text_pdf_upload():
    """Requirement: valid text-based PDF upload extracts text directly."""
    sess = client.post("/api/sessions/create", json={"student_name": "Hana Sharma", "scholarship_id": "merit-cum-means"}).json()
    sid = sess["session_id"]

    pdf_bytes = create_sample_pdf("AADHAAR\nName: Hana Sharma\nDate of Birth: 15/08/2002")

    res = client.post(
        f"/api/sessions/{sid}/documents/upload",
        data={"expected_type": "aadhaar"},
        files={"file": ("aadhaar_doc.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["classification_status"] == ClassificationStatus.MATCH.value
    assert data["verification_status"] == DocumentVerificationStatus.VERIFIED.value
    assert data["expected_document_type"] == "aadhaar"
    assert data["detected_document_type"] == "aadhaar"
    assert data["fields"]["name"] == "Hana Sharma"
    assert data["fields"]["date_of_birth"] == "15/08/2002"


def test_scanned_pdf_upload():
    """Requirement: scanned PDF upload converts page to image and runs OCR."""
    if not is_tesseract_available():
        pytest.skip("Tesseract is not available on this system")

    sess = client.post("/api/sessions/create", json={"student_name": "Hana Sharma", "scholarship_id": "merit-cum-means"}).json()
    sid = sess["session_id"]

    pdf_bytes = create_scanned_pdf("AADHAAR\nName: Hana Sharma\nDate of Birth: 15/08/2002")

    res = client.post(
        f"/api/sessions/{sid}/documents/upload",
        data={"expected_type": "aadhaar"},
        files={"file": ("scanned_aadhaar.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["verification_status"] == DocumentVerificationStatus.VERIFIED.value
    assert data["detected_document_type"] == "aadhaar"
    assert "Hana Sharma" in data["fields"].get("name", "")


def test_image_upload():
    """Requirement: image upload extracts fields using OCR."""
    if not is_tesseract_available():
        pytest.skip("Tesseract is not available on this system")

    sess = client.post("/api/sessions/create", json={"student_name": "Hana Sharma", "scholarship_id": "merit-cum-means"}).json()
    sid = sess["session_id"]

    with open("../fake_aadhaar.png", "rb") as f:
        img_bytes = f.read()

    res = client.post(
        f"/api/sessions/{sid}/documents/upload",
        data={"expected_type": "aadhaar"},
        files={"file": ("aadhaar.png", img_bytes, "image/png")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["verification_status"] == DocumentVerificationStatus.VERIFIED.value
    assert data["detected_type"] == "aadhaar"
    assert data["fields"]["name"] == "Hana Sharma"


def test_empty_corrupted_and_unsupported_files():
    """Requirement: reject empty, corrupted, and unsupported file types with 400 error."""
    sess = client.post("/api/sessions/create", json={"student_name": "Hana Sharma", "scholarship_id": "merit-cum-means"}).json()
    sid = sess["session_id"]

    # Empty file
    r_empty = client.post(
        f"/api/sessions/{sid}/documents/upload",
        files={"file": ("test.pdf", b"", "application/pdf")},
    )
    assert r_empty.status_code == 400
    assert "empty" in r_empty.json()["detail"].lower()

    # Corrupted PDF
    r_corrupt = client.post(
        f"/api/sessions/{sid}/documents/upload",
        files={"file": ("bad.pdf", b"corrupted random data not a pdf", "application/pdf")},
    )
    assert r_corrupt.status_code == 400
    assert "corrupted" in r_corrupt.json()["detail"].lower()

    # Unsupported extension
    r_unsupported = client.post(
        f"/api/sessions/{sid}/documents/upload",
        files={"file": ("test.exe", b"executable binary", "application/octet-stream")},
    )
    assert r_unsupported.status_code == 400
    assert "unsupported" in r_unsupported.json()["detail"].lower()


def test_expected_document_type_mismatch_itr_vs_income():
    """
    Critical Requirement:
    Expected: Income Certificate
    Uploaded: ITR Computation
    Must return DOCUMENT_TYPE_MISMATCH with clear message and NOT satisfy slot.
    """
    sess = client.post("/api/sessions/create", json={"student_name": "Hana Sharma", "scholarship_id": "merit-cum-means"}).json()
    sid = sess["session_id"]

    itr_text = (
        "INCOME TAX DEPARTMENT\n"
        "Computation of Total Income\n"
        "Assessment Year: 2024-25\n"
        "Name: Hana Sharma\n"
        "Gross Total Income: 180000"
    )
    pdf_bytes = create_sample_pdf(itr_text)

    res = client.post(
        f"/api/sessions/{sid}/documents/upload",
        data={"expected_type": "income_certificate"},
        files={"file": ("itr_computation.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["expected_document_type"] == "income_certificate"
    assert data["detected_document_type"] == "itr_computation"
    assert data["classification_status"] == ClassificationStatus.MISMATCH.value
    assert data["verification_status"] == DocumentVerificationStatus.DOCUMENT_TYPE_MISMATCH.value
    assert "ITR Computation" in data["message"]
    assert "Income Certificate is required" in data["message"]
    assert data["fields"] == {}

    # Check session state: income_certificate must NOT be satisfied!
    session_data = client.get(f"/api/sessions/{sid}").json()
    assert "income_certificate" in session_data["readiness"]["required_documents_missing"]
    assert session_data["readiness"]["overall_status"] == ReadinessStatus.ACTION_REQUIRED.value


def test_expected_document_type_mismatch_pan_vs_aadhaar():
    """
    Critical Requirement:
    Expected: Aadhaar
    Uploaded: PAN card
    """
    sess = client.post("/api/sessions/create", json={"student_name": "Hana Sharma", "scholarship_id": "merit-cum-means"}).json()
    sid = sess["session_id"]

    pan_text = (
        "INCOME TAX DEPARTMENT\n"
        "Permanent Account Number Card\n"
        "Name: Hana Sharma\n"
        "Father's Name: R. K. Sharma\n"
        "PAN: ABCDE1234F"
    )
    pdf_bytes = create_sample_pdf(pan_text)

    res = client.post(
        f"/api/sessions/{sid}/documents/upload",
        data={"expected_type": "aadhaar"},
        files={"file": ("pan_card.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["expected_document_type"] == "aadhaar"
    assert data["detected_document_type"] == "pan_card"
    assert data["classification_status"] == ClassificationStatus.MISMATCH.value
    assert data["verification_status"] == DocumentVerificationStatus.DOCUMENT_TYPE_MISMATCH.value
    assert "PAN Card" in data["message"]
    assert "Aadhaar Card is required" in data["message"]


def test_uncertain_document_classification():
    """Requirement: Unidentifiable documents return UNKNOWN status instead of inventing a type."""
    sess = client.post("/api/sessions/create", json={"student_name": "Hana Sharma", "scholarship_id": "merit-cum-means"}).json()
    sid = sess["session_id"]

    random_doc_text = "Shopping Grocery List:\n1. 2kg Rice\n2. 1L Milk\n3. Bread and Butter\nTotal: Rs 250"
    pdf_bytes = create_sample_pdf(random_doc_text)

    res = client.post(
        f"/api/sessions/{sid}/documents/upload",
        data={"expected_type": "aadhaar"},
        files={"file": ("grocery.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_document_type"] == "unknown"
    assert data["classification_status"] == ClassificationStatus.UNKNOWN.value
    assert data["verification_status"] == DocumentVerificationStatus.UNKNOWN_DOCUMENT.value


def test_replace_mismatched_document_with_correct_type():
    """
    Requirement: Replacing an incorrect document updates the record, removes stale results,
    and updates scholarship readiness.
    """
    sess = client.post("/api/sessions/create", json={"student_name": "Hana Sharma", "scholarship_id": "merit-cum-means"}).json()
    sid = sess["session_id"]

    # Step 1: Upload Aadhaar
    aadhaar_bytes = create_sample_pdf("AADHAAR\nName: Hana Sharma\nDate of Birth: 15/08/2002")
    client.post(
        f"/api/sessions/{sid}/documents/upload",
        data={"expected_type": "aadhaar"},
        files={"file": ("aadhaar.pdf", aadhaar_bytes, "application/pdf")},
    )

    # Step 2: Upload 12th Marksheet
    marksheet_bytes = create_sample_pdf("SENIOR SCHOOL CERTIFICATE EXAMINATION\nMARKSHEET\nClass XII\nName: Hana Sharma\nDate of Birth: 15/08/2002\nPercentage: 78%")
    client.post(
        f"/api/sessions/{sid}/documents/upload",
        data={"expected_type": "marksheet_12th"},
        files={"file": ("marksheet.pdf", marksheet_bytes, "application/pdf")},
    )

    # Step 3: Upload WRONG document in Income Certificate slot (ITR instead of Income Certificate)
    itr_bytes = create_sample_pdf("INCOME TAX DEPARTMENT\nComputation of Total Income\nAssessment Year 2024-25\nName: Hana Sharma\nTotal Income: 180000")
    r_wrong = client.post(
        f"/api/sessions/{sid}/documents/upload",
        data={"expected_type": "income_certificate"},
        files={"file": ("itr.pdf", itr_bytes, "application/pdf")},
    )
    assert r_wrong.json()["verification_status"] == DocumentVerificationStatus.DOCUMENT_TYPE_MISMATCH.value

    # Application must NOT be ready
    s_before = client.get(f"/api/sessions/{sid}").json()
    assert s_before["readiness"]["overall_status"] != ReadinessStatus.READY_FOR_SUBMISSION.value
    assert "income_certificate" in s_before["readiness"]["required_documents_missing"]

    # Step 4: Replace with the correct Income Certificate
    income_cert_bytes = create_sample_pdf("GOVERNMENT REVENUE DEPARTMENT\nINCOME CERTIFICATE\nName: Hana Sharma\nAnnual Income: 180000")
    r_correct = client.post(
        f"/api/sessions/{sid}/documents/upload",
        data={"expected_type": "income_certificate"},
        files={"file": ("income_certificate.pdf", income_cert_bytes, "application/pdf")},
    )
    assert r_correct.json()["verification_status"] == DocumentVerificationStatus.VERIFIED.value

    # Step 5: Check updated session
    s_after = client.get(f"/api/sessions/{sid}").json()
    # No duplicate documents created for the income slot
    income_docs = [d for d in s_after["documents"] if getattr(d, "expected_type", None) == "income_certificate" or d.get("expected_type") == "income_certificate"]
    assert len(income_docs) == 1
    # Slot is now satisfied
    assert s_after["readiness"]["required_documents_missing"] == []
    assert s_after["readiness"]["overall_status"] == ReadinessStatus.READY_FOR_SUBMISSION.value


def test_session_database_persistence():
    """Requirement: Ensure session and verification results persist in SQLite database."""
    sess = client.post("/api/sessions/create", json={"student_name": "Persist Student", "scholarship_id": "merit-cum-means"}).json()
    sid = sess["session_id"]

    pdf_bytes = create_sample_pdf("AADHAAR\nName: Persist Student\nDate of Birth: 15/08/2002")
    client.post(
        f"/api/sessions/{sid}/documents/upload",
        data={"expected_type": "aadhaar"},
        files={"file": ("aadhaar.pdf", pdf_bytes, "application/pdf")},
    )

    # Clear memory cache on session_store to force database retrieval
    if hasattr(session_store, "_cache"):
        session_store._cache.clear()

    # Retrieve fresh from SQLite
    res = client.get(f"/api/sessions/{sid}")
    assert res.status_code == 200
    persisted = res.json()
    assert persisted["session_id"] == sid
    assert persisted["student_name"] == "Persist Student"
    assert len(persisted["documents"]) == 1
    assert persisted["documents"][0]["file_name"] == "aadhaar.pdf"
    assert persisted["documents"][0]["detected_type"] == "aadhaar"
    assert persisted["documents"][0]["verification_status"] == "VERIFIED"


def test_delete_document_endpoint():
    """Requirement: deleting a document removes it from session and recalculates readiness."""
    sess = client.post("/api/sessions/create", json={"student_name": "Delete Student", "scholarship_id": "merit-cum-means"}).json()
    sid = sess["session_id"]

    pdf_bytes = create_sample_pdf("AADHAAR\nName: Delete Student\nDate of Birth: 15/08/2002")
    r_up = client.post(
        f"/api/sessions/{sid}/documents/upload",
        data={"expected_type": "aadhaar"},
        files={"file": ("aadhaar.pdf", pdf_bytes, "application/pdf")},
    )
    doc_id = r_up.json()["doc_id"]

    # Verify document exists in session
    s_before = client.get(f"/api/sessions/{sid}").json()
    assert len(s_before["documents"]) == 1

    # Delete document
    r_del = client.delete(f"/api/sessions/{sid}/documents/{doc_id}")
    assert r_del.status_code == 200
    del_data = r_del.json()
    assert del_data["session_id"] == sid
    assert len(del_data["documents"]) == 0

    # Verify document is removed and readiness updated
    s_after = client.get(f"/api/sessions/{sid}").json()
    assert len(s_after["documents"]) == 0
    assert "aadhaar" in s_after["readiness"]["required_documents_missing"]
