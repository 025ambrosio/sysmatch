from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path

from .zpl_converter import convert_zpl_to_image


TEXT_EXTENSIONS = {".txt", ".zpl"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
DEFAULT_TESSERACT_PATH = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def _candidate_tesseract_paths() -> list[Path]:
    candidates = []
    env_cmd = os.environ.get("CONCILIADOR_TESSERACT_CMD")
    if env_cmd:
        candidates.append(Path(env_cmd))

    data_dir = os.environ.get("CONCILIADOR_DATA_DIR")
    if data_dir:
        candidates.append(Path(data_dir) / "tesseract" / "tesseract.exe")

    candidates.extend(
        [
            Path.cwd() / "tesseract" / "tesseract.exe",
            DEFAULT_TESSERACT_PATH,
        ]
    )
    return candidates


def _configure_tesseract(pytesseract_module) -> str:
    for path in _candidate_tesseract_paths():
        if path.exists():
            pytesseract_module.pytesseract.tesseract_cmd = str(path)
            return ""
    return (
        "[ERRO OCR] Tesseract OCR nao encontrado. Instale em "
        f"{DEFAULT_TESSERACT_PATH}, coloque em uma pasta tesseract ao lado do sistema "
        "ou configure CONCILIADOR_TESSERACT_CMD."
    )


def _read_text_file(path: Path) -> str:
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def _ocr_image(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "[ERRO OCR] Dependencias pytesseract/Pillow nao instaladas."

    config_error = _configure_tesseract(pytesseract)
    if config_error:
        return config_error

    try:
        with Image.open(path) as image:
            return pytesseract.image_to_string(image, lang="por+eng")
    except pytesseract.TesseractNotFoundError:
        return "[ERRO OCR] Tesseract OCR nao esta instalado ou nao esta no PATH."


def _ocr_pdf_pages(path: Path, force_ocr: bool = False, combine_with_embedded: bool = False) -> list[str]:
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError:
        return ["[ERRO OCR] Dependencias PyMuPDF/pytesseract/Pillow nao instaladas."]

    config_error = _configure_tesseract(pytesseract)
    if config_error:
        return [config_error]

    page_texts = []
    doc = fitz.open(path)
    try:
        print(f"[OCR-PDF] arquivo={path.name} paginas={doc.page_count} force_ocr={force_ocr}")
        for page_index, page in enumerate(doc, start=1):
            embedded_text = page.get_text("text").strip()
            if embedded_text and not force_ocr:
                page_texts.append(embedded_text)
                continue

            pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
            image_bytes = pix.tobytes("png")
            try:
                with Image.open(BytesIO(image_bytes)) as image:
                    ocr_text = pytesseract.image_to_string(image, lang="por+eng")
                    if embedded_text and combine_with_embedded:
                        page_texts.append(f"{embedded_text}\n\n{ocr_text}".strip())
                    else:
                        page_texts.append(ocr_text)
                    print(f"[OCR-PDF] arquivo={path.name} pagina={page_index}/{doc.page_count} ok")
            except pytesseract.TesseractNotFoundError:
                page_texts.append("[ERRO OCR] Tesseract OCR nao esta instalado ou nao esta no PATH.")
    finally:
        doc.close()

    return page_texts


def _ocr_pdf(path: Path) -> str:
    return "\n\n--- PAGINA ---\n\n".join(_ocr_pdf_pages(path))


def extract_texts_from_label_file(file: str | Path, force_pdf_ocr: bool = False) -> list[str]:
    path = Path(file)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        texts = _ocr_pdf_pages(path, force_ocr=force_pdf_ocr, combine_with_embedded=force_pdf_ocr)
        return texts or [""]

    return [extract_text_from_label(path)]


def extract_text_from_label(file: str | Path) -> str:
    path = Path(file)
    suffix = path.suffix.lower()

    if suffix == ".zpl":
        raw_text = _read_text_file(path)
        if raw_text and ":Z64:" not in raw_text:
            return raw_text

        converted = convert_zpl_to_image(path, path.parent)
        if converted:
            return _ocr_image(converted)
        return raw_text

    if suffix == ".txt":
        return _read_text_file(path)

    if suffix == ".pdf":
        return _ocr_pdf(path)

    if suffix in IMAGE_EXTENSIONS:
        return _ocr_image(path)

    return ""
