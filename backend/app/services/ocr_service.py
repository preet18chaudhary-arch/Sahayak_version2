import io
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple, Union

import pymupdf
import pytesseract
from PIL import Image

from app.config import MAX_PDF_PAGES, TESSERACT_CMD


def resolve_tesseract_path() -> Optional[str]:
    """
    Dynamically locate the Tesseract OCR executable.
    Checks:
    1. TESSERACT_CMD env var or config
    2. System PATH (shutil.which)
    3. Common Windows paths (local appdata, program files)
    4. Common Linux/Unix paths
    """
    if TESSERACT_CMD and Path(TESSERACT_CMD).is_file():
        return str(Path(TESSERACT_CMD).resolve())

    env_cmd = os.getenv("TESSERACT_CMD")
    if env_cmd and Path(env_cmd).is_file():
        return str(Path(env_cmd).resolve())

    which_cmd = shutil.which("tesseract")
    if which_cmd:
        return which_cmd

    candidates = [
        Path(os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe")),
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        Path("/usr/bin/tesseract"),
        Path("/usr/local/bin/tesseract"),
    ]

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())

    return None


def configure_tesseract() -> Optional[str]:
    """Configure pytesseract with the resolved binary path and tessdata location."""
    path = resolve_tesseract_path()
    if path:
        pytesseract.pytesseract.tesseract_cmd = path
        tessdata_dir = Path(path).parent / "tessdata"
        if tessdata_dir.is_dir() and "TESSDATA_PREFIX" not in os.environ:
            os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)
        return path
    return None


# Initialize on import
configure_tesseract()


def is_tesseract_available() -> bool:
    """Return True if Tesseract OCR executable is available and verified."""
    cmd = resolve_tesseract_path()
    return cmd is not None


def extract_text_from_image(file_source: Union[str, Path, bytes, Image.Image]) -> str:
    """
    Extract text from an image using Tesseract OCR.
    Accepts a filepath, bytes, or PIL Image.
    """
    cmd = configure_tesseract()
    if not cmd:
        raise RuntimeError(
            "Tesseract OCR is not installed or configured on this system. "
            "Please install Tesseract OCR (e.g., UB-Mannheim Tesseract on Windows or "
            "'sudo apt install tesseract-ocr' on Linux) or configure TESSERACT_CMD."
        )

    if isinstance(file_source, Image.Image):
        image = file_source
    elif isinstance(file_source, (bytes, bytearray)):
        image = Image.open(io.BytesIO(file_source))
    else:
        image_path = Path(file_source)
        if not image_path.exists():
            raise FileNotFoundError(f"File not found: {file_source}")
        image = Image.open(image_path)

    # Convert to RGB if needed (e.g. RGBA or palette)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    try:
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"OCR processing failed: {str(e)}") from e


def extract_text_from_pdf(
    pdf_source: Union[bytes, str, Path],
    max_pages: int = MAX_PDF_PAGES,
) -> Tuple[str, bool]:
    """
    Extract text from a PDF file.
    - If the PDF has embedded selectable text, extracts it directly.
    - If the PDF is scanned or has sparse text (< 20 characters), renders pages to images and runs OCR.
    Returns:
        (extracted_text, is_scanned)
    """
    try:
        if isinstance(pdf_source, (bytes, bytearray)):
            doc = pymupdf.open(stream=pdf_source, filetype="pdf")
        else:
            doc = pymupdf.open(str(pdf_source))
    except Exception as e:
        raise ValueError(f"Could not open PDF file. The file may be corrupted: {str(e)}") from e

    try:
        if doc.is_encrypted:
            raise ValueError(
                "Password-protected or encrypted PDFs are not supported. "
                "Please upload an unencrypted document."
            )

        num_pages = len(doc)
        if num_pages == 0:
            return "", False

        pages_to_process = min(num_pages, max_pages)

        # 1. Attempt direct text extraction
        direct_text_chunks = []
        for i in range(pages_to_process):
            page = doc[i]
            page_text = page.get_text()
            if page_text:
                direct_text_chunks.append(page_text.strip())

        combined_direct_text = "\n\n".join(direct_text_chunks).strip()

        # Check if direct text is substantial (at least 20 chars and 4 words)
        words = combined_direct_text.split()
        if len(combined_direct_text) >= 20 and len(words) >= 4:
            return combined_direct_text, False

        # 2. If text is sparse or absent, fall back to OCR on rendered page images
        if not is_tesseract_available():
            # If we extracted at least some text, return it, otherwise warn
            if combined_direct_text:
                return combined_direct_text, False
            raise RuntimeError(
                "This document appears to be a scanned PDF requiring OCR, but "
                "Tesseract OCR is not installed or configured on this server."
            )

        ocr_chunks = []
        for i in range(pages_to_process):
            page = doc[i]
            # Render page to image at 200 DPI for reliable OCR
            pix = page.get_pixmap(dpi=200)
            page_img = Image.open(io.BytesIO(pix.tobytes("png")))
            page_text = pytesseract.image_to_string(page_img)
            if page_text.strip():
                ocr_chunks.append(page_text.strip())

        combined_ocr_text = "\n\n".join(ocr_chunks).strip()
        # Return OCR text if found, else fallback to whatever direct text existed
        return combined_ocr_text or combined_direct_text, True

    finally:
        doc.close()


def process_uploaded_document(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """
    Process an uploaded file (PDF or image) and extract text.
    Returns:
        (extracted_text, method)
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        text, is_scanned = extract_text_from_pdf(file_bytes)
        method = "pdf_ocr" if is_scanned else "pdf_text"
        return text, method

    elif ext in (".png", ".jpg", ".jpeg", ".webp"):
        text = extract_text_from_image(file_bytes)
        return text, "image_ocr"

    else:
        raise ValueError(
            f"Unsupported file format '{ext}'. Supported formats are: PDF, PNG, JPG, JPEG, WEBP."
        )
