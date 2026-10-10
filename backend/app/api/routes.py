import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.config import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    UPLOAD_DIR,
)
from app.models.schemas import (
    ClassificationStatus,
    CreateSessionRequest,
    DocumentType,
    DocumentUploadResponse,
    DocumentVerificationStatus,
    ExtractedField,
    ReadinessStatus,
    ScholarshipRuleConfig,
    UploadedDocumentMetadata,
    VerificationSession,
)
from app.services.database_session_store import session_store
from app.services.document_detector import detect_document_type
from app.services.field_extractor import extract_fields
from app.services.ocr_service import process_uploaded_document
from app.services.rule_registry import (
    get_available_scholarships,
    get_scholarship_rule_by_id,
)
from app.services.verification_service import run_name_verification

router = APIRouter(prefix="/api", tags=["Sahayak Verification"])

DOCUMENT_TYPE_LABELS = {
    "aadhaar": "Aadhaar Card",
    "marksheet_10th": "Class 10 Marksheet",
    "marksheet_12th": "Class 12 Marksheet",
    "income_certificate": "Income Certificate",
    "caste_certificate": "Caste Certificate",
    "domicile_certificate": "Domicile Certificate",
    "bank_passbook": "Bank Passbook",
    "pan_card": "PAN Card",
    "itr_computation": "ITR Computation",
    "itr_acknowledgement": "ITR Acknowledgement",
    "unknown": "Unknown Document",
    "other": "Other Document",
}


def format_doc_name(type_val: Optional[str]) -> str:
    if not type_val:
        return "Unknown Document"
    return DOCUMENT_TYPE_LABELS.get(type_val.lower(), type_val.replace("_", " ").title())


@router.get(
    "/scholarships",
    response_model=List[ScholarshipRuleConfig],
    summary="List configurable scholarship schemes",
    description="Returns pre-registered scholarship rules with their required documents, income ceilings, and matching thresholds.",
)
async def list_scholarships():
    """Retrieve all available scholarship rule profiles."""
    return get_available_scholarships()


@router.post(
    "/sessions/create",
    response_model=VerificationSession,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new verification session",
    description="Initializes a new verification session with either a preset scholarship scheme or a fully customized rule profile.",
)
async def create_session(request: CreateSessionRequest):
    """
    Create a verification session.
    If `custom_rules` are provided, they take priority.
    Otherwise, the rule profile corresponding to `scholarship_id` is applied.
    """
    rule_config: ScholarshipRuleConfig

    if request.custom_rules:
        rule_config = request.custom_rules
    else:
        preset_id = request.scholarship_id or "merit-cum-means"
        preset = get_scholarship_rule_by_id(preset_id)

        if not preset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scholarship scheme '{preset_id}' was not found. Use GET /api/scholarships to inspect available presets.",
            )

        rule_config = preset

    session = session_store.create_session(
        student_name=request.student_name,
        rule_config=rule_config,
    )

    return session


@router.get(
    "/sessions/{session_id}",
    response_model=VerificationSession,
    summary="Get verification session details",
    description="Fetches the full session state including active rule profile, uploaded documents, extracted fields, and readiness scorecard.",
)
async def get_session(session_id: str):
    """Fetch session details by session_id."""
    session = session_store.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    return session


@router.post(
    "/sessions/{session_id}/documents/upload",
    response_model=DocumentUploadResponse,
    summary="Upload document, extract text/OCR, detect type, validate expected slot",
)
async def upload_document(
    session_id: str,
    file: UploadFile = File(...),
    expected_type: Optional[str] = Form(None),
    doc_id: Optional[str] = Form(None),
):
    """
    Upload a document (PDF or image), extract text or run OCR,
    validate document type against expected slot, extract fields if matched,
    and recalculate cross-document consistency and scholarship readiness.
    """
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    # 1. Validate file extension
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file format '{file_ext}'. Supported formats are: "
                "PDF (.pdf), PNG (.png), JPG/JPEG (.jpg, .jpeg), and WEBP (.webp)."
            ),
        )

    # 2. Read bytes and validate size
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file exceeds the maximum allowed size of {max_mb:.0f}MB.",
        )

    # 3. Safe temporary file processing
    safe_temp_name = f"upload_{uuid.uuid4().hex[:12]}{file_ext}"
    temp_path = UPLOAD_DIR / safe_temp_name

    try:
        with open(temp_path, "wb") as f_out:
            f_out.write(file_bytes)

        # 4. Extract text using PDF or OCR pipeline
        try:
            extracted_text, method = process_uploaded_document(file_bytes, file.filename or "")
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(ve),
            )
        except RuntimeError as re:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(re),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process document: {str(e)}",
            )
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass

    # 5. Check if document could be read
    if not extracted_text or len(extracted_text.strip()) < 10:
        classification_status = ClassificationStatus.UNREADABLE.value
        verification_status = DocumentVerificationStatus.UNREADABLE.value
        detected_type = DocumentType.UNKNOWN
        message = "We could not read this document. Please upload a clearer scan or a supported PDF."
        extracted_fields = {}
    else:
        # Detect document type
        detected_type = detect_document_type(extracted_text)
        detected_str = detected_type.value if hasattr(detected_type, "value") else str(detected_type)

        # Parse expected_type if given
        norm_expected_str: Optional[str] = None
        if expected_type:
            clean_exp = expected_type.strip().lower()
            try:
                norm_expected = DocumentType(clean_exp)
                norm_expected_str = norm_expected.value
            except ValueError:
                norm_expected_str = clean_exp

        # Evaluate match / mismatch
        if norm_expected_str:
            if detected_str == norm_expected_str:
                classification_status = ClassificationStatus.MATCH.value
                verification_status = DocumentVerificationStatus.VERIFIED.value
                message = f"Document recognized and verified as {format_doc_name(detected_str)}."
                extracted_fields = extract_fields(extracted_text)
            elif detected_type == DocumentType.UNKNOWN:
                classification_status = ClassificationStatus.UNKNOWN.value
                verification_status = DocumentVerificationStatus.UNKNOWN_DOCUMENT.value
                message = (
                    f"Unable to identify this document as an {format_doc_name(norm_expected_str)}. "
                    "Please ensure the document is clear and matches the required format."
                )
                extracted_fields = {}
            else:
                classification_status = ClassificationStatus.MISMATCH.value
                verification_status = DocumentVerificationStatus.DOCUMENT_TYPE_MISMATCH.value
                message = (
                    f"This appears to be an {format_doc_name(detected_str)}, but an "
                    f"{format_doc_name(norm_expected_str)} is required. Please upload the correct {format_doc_name(norm_expected_str)}."
                )
                extracted_fields = {}
        else:
            # No explicit expected slot provided (auto-detect against scholarship requirements)
            req_types_str = [
                (t.value if hasattr(t, "value") else str(t))
                for t in session.rule_config.required_documents
            ]
            if detected_str in req_types_str:
                classification_status = ClassificationStatus.MATCH.value
                verification_status = DocumentVerificationStatus.VERIFIED.value
                norm_expected_str = detected_str
                message = f"Document recognized as {format_doc_name(detected_str)}."
                extracted_fields = extract_fields(extracted_text)
            elif detected_type == DocumentType.UNKNOWN:
                classification_status = ClassificationStatus.UNKNOWN.value
                verification_status = DocumentVerificationStatus.UNKNOWN_DOCUMENT.value
                message = "Unable to identify document. Please upload a clear official document."
                extracted_fields = {}
            else:
                classification_status = ClassificationStatus.UNKNOWN.value
                verification_status = DocumentVerificationStatus.UNKNOWN_DOCUMENT.value
                message = f"Detected {format_doc_name(detected_str)}, which is not in the required documents list."
                extracted_fields = {}

    # 6. Document replacement & Session State update
    target_doc_id: Optional[str] = doc_id

    # If no explicit doc_id provided, look for an existing slot to replace ONLY when expected_type is explicitly provided
    if not target_doc_id and expected_type is not None and norm_expected_str:
        existing = next(
            (
                d
                for d in session.documents
                if getattr(d, "expected_type", None) == norm_expected_str
                or (getattr(d, "expected_type", None) and getattr(d.expected_type, "value", None) == norm_expected_str)
                or (getattr(d, "verification_status", None) == "VERIFIED" and getattr(d.detected_type, "value", str(d.detected_type)) == norm_expected_str)
            ),
            None,
        )
        if existing:
            target_doc_id = existing.doc_id

    now_iso = datetime.now(timezone.utc).isoformat()

    expected_doc_enum: Optional[DocumentType] = None
    if norm_expected_str:
        try:
            expected_doc_enum = DocumentType(norm_expected_str)
        except ValueError:
            expected_doc_enum = None

    if target_doc_id:
        # Replace existing document record
        doc_record = next((d for d in session.documents if d.doc_id == target_doc_id), None)
        if doc_record:
            doc_record.file_name = file.filename or "uploaded_file"
            doc_record.detected_type = detected_type
            doc_record.expected_type = expected_doc_enum
            doc_record.classification_status = classification_status
            doc_record.verification_status = verification_status
            doc_record.message = message
            doc_record.uploaded_at = now_iso
        else:
            doc_record = UploadedDocumentMetadata(
                doc_id=target_doc_id,
                file_name=file.filename or "uploaded_file",
                detected_type=detected_type,
                expected_type=expected_doc_enum,
                classification_status=classification_status,
                verification_status=verification_status,
                message=message,
                uploaded_at=now_iso,
            )
            session.documents.append(doc_record)

        # Remove old extracted fields for this replaced document
        session.extracted_fields = [
            f for f in session.extracted_fields if f.source_doc_id != target_doc_id
        ]
        assigned_doc_id = target_doc_id
    else:
        # Create new document record
        assigned_doc_id = f"doc_{session_id}_{len(session.documents) + 1}"
        doc_record = UploadedDocumentMetadata(
            doc_id=assigned_doc_id,
            file_name=file.filename or "uploaded_file",
            detected_type=detected_type,
            expected_type=expected_doc_enum,
            classification_status=classification_status,
            verification_status=verification_status,
            message=message,
            uploaded_at=now_iso,
        )
        session.documents.append(doc_record)

    # 7. Add extracted fields ONLY if verified
    if verification_status == DocumentVerificationStatus.VERIFIED.value:
        for field_name, field_value in extracted_fields.items():
            session.extracted_fields.append(
                ExtractedField(
                    field_name=field_name,
                    value=str(field_value),
                    confidence=1.0,
                    source_doc_id=assigned_doc_id,
                )
            )

    # 8. Recalculate scorecard & readiness
    session.readiness.documents_checked = len(session.documents)
    session.readiness.fields_extracted = len(session.extracted_fields)

    run_name_verification(session)
    session_store.update_session(session)

    return DocumentUploadResponse(
        session_id=session_id,
        file_name=file.filename or "uploaded_file",
        doc_id=assigned_doc_id,
        expected_document_type=norm_expected_str,
        detected_document_type=detected_type.value if hasattr(detected_type, "value") else str(detected_type),
        detected_type=detected_type.value if hasattr(detected_type, "value") else str(detected_type),
        classification_status=classification_status,
        verification_status=verification_status,
        message=message,
        fields=extracted_fields,
        extracted_text=extracted_text,
    )


@router.delete(
    "/sessions/{session_id}/documents/{doc_id}",
    response_model=VerificationSession,
    summary="Remove an uploaded document and recalculate readiness",
)
async def delete_document(session_id: str, doc_id: str):
    """Delete a document from a session, purge its fields, and re-evaluate readiness."""
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    doc = next((d for d in session.documents if d.doc_id == doc_id), None)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found in session.",
        )

    # Remove document
    session.documents = [d for d in session.documents if d.doc_id != doc_id]

    # Remove fields
    session.extracted_fields = [
        f for f in session.extracted_fields if f.source_doc_id != doc_id
    ]

    session.readiness.documents_checked = len(session.documents)
    session.readiness.fields_extracted = len(session.extracted_fields)

    run_name_verification(session)
    session_store.update_session(session)

    return session


class ResolveDiscrepancyRequest(BaseModel):
    resolution_note: str


@router.post("/sessions/{session_id}/discrepancies/{discrepancy_id}/resolve")
async def resolve_discrepancy(
    session_id: str,
    discrepancy_id: str,
    request: ResolveDiscrepancyRequest,
):
    """Resolve a flagged discrepancy after human review."""
    session = session_store.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    discrepancy = next(
        (
            item
            for item in session.discrepancies
            if item.id == discrepancy_id
        ),
        None,
    )

    if not discrepancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discrepancy '{discrepancy_id}' not found.",
        )

    discrepancy.resolved = True
    discrepancy.resolution_note = request.resolution_note

    run_name_verification(session)
    session_store.update_session(session)

    return {
        "session_id": session_id,
        "discrepancy_id": discrepancy_id,
        "resolved": discrepancy.resolved,
        "resolution_note": discrepancy.resolution_note,
        "overall_status": session.readiness.overall_status,
        "message": "Discrepancy resolved successfully.",
    }
