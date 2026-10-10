import re
from app.models.schemas import DocumentType


def detect_document_type(ocr_text: str) -> DocumentType:
    """
    Detect the document type using keyword and structural pattern rules.
    Returns the specific DocumentType enum value or DocumentType.UNKNOWN
    if the document cannot be reliably identified.
    """
    if not ocr_text or len(ocr_text.strip()) < 10:
        return DocumentType.UNKNOWN

    text = ocr_text.lower()

    # 1. PAN Card checks (must be checked before generic income tax / ITR)
    pan_pattern = re.search(r"\b[a-z]{5}[0-9]{4}[a-z]\b", text, re.IGNORECASE)
    if "permanent account number" in text or "pan card" in text or (
        "income tax department" in text and (pan_pattern or "father's name" in text)
        and "computation" not in text and "itr" not in text and "acknowledgement" not in text
    ):
        return DocumentType.PAN_CARD

    # 2. ITR Acknowledgement / ITR-V checks (must be checked before generic Income Certificate)
    if (
        "income tax return acknowledgement" in text
        or "itr-v" in text
        or "itr-1" in text
        or "itr-4" in text
        or ("acknowledgement" in text and ("income tax" in text or "e-filing" in text))
    ):
        return DocumentType.ITR_ACKNOWLEDGEMENT

    # 3. ITR Computation checks
    if (
        "computation of income" in text
        or "computation of total income" in text
        or ("income tax return" in text and "computation" in text)
        or ("assessment year" in text and ("total income" in text or "gross income" in text or "taxable income" in text))
        or "form 16" in text
        or "form 26as" in text
    ):
        return DocumentType.ITR_COMPUTATION

    # 4. Aadhaar checks
    aadhaar_pattern = re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", text)
    if (
        "aadhaar" in text
        or "unique identification authority" in text
        or "uidai" in text
        or "mera aadhaar" in text
        or aadhaar_pattern
    ):
        return DocumentType.AADHAAR

    # 5. Marksheet checks
    if (
        "marksheet" in text
        or "mark sheet" in text
        or "senior secondary" in text
        or "class xii" in text
        or "class 12" in text
        or "12th" in text
        or "class x" in text
        or "10th" in text
        or "secondary school" in text
        or "cbse" in text
        or "icse" in text
    ):
        if (
            "class xii" in text
            or "12th" in text
            or "class 12" in text
            or "senior secondary" in text
            or "senior secondary school certificate" in text
            or "higher secondary" in text
            or "hsc" in text
            or "intermediate" in text
        ):
            return DocumentType.MARKSHEET_12TH

        if (
            "class x" in text
            or "10th" in text
            or "class 10" in text
            or "matriculation" in text
            or "ssc" in text
        ):
            return DocumentType.MARKSHEET_10TH

        if "percentage" in text or "marks" in text or "grade" in text:
            return DocumentType.MARKSHEET_12TH

    # 6. Income Certificate checks (State/Revenue issued)
    if (
        "income certificate" in text
        or "certificate of income" in text
        or "parivar pehchan" in text
        or (
            "annual income" in text
            and ("tahsildar" in text or "tehsildar" in text or "revenue" in text or "competent authority" in text or "certified that" in text)
        )
        or ("annual income" in text and "name" in text and "income tax" not in text and "itr" not in text)
    ):
        return DocumentType.INCOME_CERTIFICATE

    # 7. Caste Certificate checks
    if (
        "caste certificate" in text
        or "scheduled caste" in text
        or "scheduled tribe" in text
        or "other backward class" in text
        or "obc certificate" in text
        or "community certificate" in text
    ):
        return DocumentType.CASTE_CERTIFICATE

    # 8. Domicile Certificate checks
    if (
        "domicile certificate" in text
        or "resident certificate" in text
        or "residence certificate" in text
        or "bonafide resident" in text
        or "resident of" in text
    ):
        return DocumentType.DOMICILE_CERTIFICATE

    # 9. Bank Passbook checks
    if (
        "bank passbook" in text
        or "account number" in text
        or "ifsc" in text
        or "savings bank" in text
        or "bank account" in text
        or "bank statement" in text
    ):
        return DocumentType.BANK_PASSBOOK

    return DocumentType.UNKNOWN
