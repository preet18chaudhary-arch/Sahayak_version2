import re


def extract_fields(ocr_text: str) -> dict:
    """Extract structured fields from OCR/PDF text using regex patterns."""
    if not ocr_text:
        return {}

    fields = {}

    # Extract Name
    name_match = re.search(
        r"(?:Candidate Name|Student Name|Name of Student|Name)\s*[:\-]?\s*([A-Za-z\s\.]+)",
        ocr_text,
        re.IGNORECASE,
    )
    if name_match:
        extracted_name = name_match.group(1).strip()
        # Clean up if matched multiple lines
        extracted_name = extracted_name.split("\n")[0].strip()
        if len(extracted_name) >= 2:
            fields["name"] = extracted_name

    # Extract Date of Birth
    dob_match = re.search(
        r"(?:Date of Birth|DOB|Birth Date)\s*[:\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})",
        ocr_text,
        re.IGNORECASE,
    )
    if dob_match:
        fields["date_of_birth"] = dob_match.group(1).strip()

    # Extract Income (handling common OCR variations like Incame)
    income_match = re.search(
        r"(?:Annual Family Inc[ao]me|Annual Inc[ao]me|Total Inc[ao]me|Family Inc[ao]me|Inc[ao]me)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]{2})?)",
        ocr_text,
        re.IGNORECASE,
    )
    if income_match:
        raw_income = income_match.group(1).replace(",", "").split(".")[0].strip()
        if raw_income.isdigit():
            fields["income"] = raw_income

    # Extract Percentage / Marks
    marks_match = re.search(
        r"(?:Percentage|Aggregate Marks|Marks|Score)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*%?",
        ocr_text,
        re.IGNORECASE,
    )
    if marks_match:
        fields["percentage"] = marks_match.group(1).strip()

    return fields
