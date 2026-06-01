from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import textwrap

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code128
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from PIL import Image, ImageEnhance, ImageFilter


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

THERMAL_PRESETS = {
    "normal": {"contrast_factor": 1.55, "sharpness_factor": 1.35, "threshold_value": 188, "black_dilation": 0, "render_zoom": 3.0},
    "strong": {"contrast_factor": 2.05, "sharpness_factor": 1.75, "threshold_value": 200, "black_dilation": 0, "render_zoom": 3.5},
    "very_strong": {"contrast_factor": 2.45, "sharpness_factor": 2.05, "threshold_value": 212, "black_dilation": 1, "render_zoom": 4.0},
}


def enhance_for_thermal_print(
    image: Image.Image,
    intensity: str = "forte",
    threshold_value: int = 195,
    contrast_factor: float = 2.0,
    sharpness_factor: float = 1.8,
    black_dilation: int = 0,
) -> Image.Image:
    intensity_key = {
        "forte": "strong",
        "muito forte": "very_strong",
    }.get(intensity, intensity)
    if intensity_key in {"normal", "strong", "very_strong"}:
        preset = _thermal_settings(intensity_key)
        threshold_value = preset["threshold_value"]
        contrast_factor = preset["contrast_factor"]
        sharpness_factor = preset["sharpness_factor"]
        black_dilation = preset["black_dilation"]

    grayscale = image.convert("L")
    contrasted = ImageEnhance.Contrast(grayscale).enhance(contrast_factor)
    sharpened = ImageEnhance.Sharpness(contrasted).enhance(sharpness_factor)
    threshold_value = max(0, min(255, int(threshold_value)))
    binary = sharpened.point(lambda pixel: 255 if pixel > threshold_value else 0, mode="1").convert("L")
    for _ in range(max(0, int(black_dilation))):
        binary = binary.filter(ImageFilter.MinFilter(3))
    return binary


def crop_white_margins(image: Image.Image, white_threshold: int = 245, safety_margin: int = 8) -> Image.Image:
    grayscale = image.convert("L")
    mask = grayscale.point(lambda pixel: 0 if pixel > white_threshold else 255, mode="L")
    bbox = mask.getbbox()
    if not bbox:
        return image

    left, top, right, bottom = bbox
    left = max(0, left - safety_margin)
    top = max(0, top - safety_margin)
    right = min(image.width, right + safety_margin)
    bottom = min(image.height, bottom + safety_margin)

    if right <= left or bottom <= top:
        return image
    return image.crop((left, top, right, bottom))


def _thermal_settings(intensity: str) -> dict:
    return THERMAL_PRESETS.get(intensity, THERMAL_PRESETS["strong"])


def _draw_wrapped(c: canvas.Canvas, text: str, x: float, y: float, width_chars: int = 95, leading: float = 12) -> float:
    for line in textwrap.wrap(str(text or ""), width=width_chars) or [""]:
        c.drawString(x, y, line)
        y -= leading
    return y


def _fit_text(c: canvas.Canvas, text: str, x: float, y: float, max_width: float, font: str = "Helvetica", max_size: int = 9, min_size: int = 5) -> None:
    text = str(text or "")
    size = max_size
    while size > min_size and c.stringWidth(text, font, size) > max_width:
        size -= 0.5
    c.setFont(font, size)
    c.drawString(x, y, text)


def _draw_fit_wrapped_lines(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    max_lines: int = 2,
    font: str = "Helvetica",
    font_size: float = 6.3,
    leading: float = 3.7 * mm,
) -> float:
    words = str(text or "").split()
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        if c.stringWidth(candidate, font, font_size) <= max_width or not current:
            current = candidate
            continue
        lines.append(current)
        current = word
        if len(lines) == max_lines:
            break

    if current and len(lines) < max_lines:
        lines.append(current)

    c.setFont(font, font_size)
    for line in lines[:max_lines]:
        _fit_text(c, line, x, y, max_width, font, font_size, 4.4)
        y -= leading
    return y


def _draw_code128(c: canvas.Canvas, value: str, x: float, y: float, width: float, height: float, human_readable: bool = True) -> None:
    value = str(value or "").strip()
    if not value:
        return
    barcode = code128.Code128(value, barHeight=height, humanReadable=human_readable)
    scale = min(width / barcode.width, 1.25)
    c.saveState()
    c.translate(x, y)
    c.scale(scale, 1)
    barcode.drawOn(c, 0, 0)
    c.restoreState()


def _draw_original_label_area(
    c: canvas.Canvas,
    label: dict,
    x: float,
    y: float,
    width: float,
    height: float,
    warnings: list[str],
    thermal_mode: bool = False,
    render_zoom: float = 3.0,
    threshold_value: int = 195,
    contrast_factor: float = 2.0,
    sharpness_factor: float = 1.8,
    black_dilation: int = 0,
    remove_white_margins: bool = False,
) -> None:
    source_path = Path(label.get("source_path") or "")
    suffix = source_path.suffix.lower()

    if not source_path.exists():
        warnings.append(f"Etiqueta original nao encontrada: {source_path}")
        return

    try:
        if suffix == ".pdf":
            import fitz

            page_index = _pdf_page_index(label.get("source_page"))
            with fitz.open(source_path) as doc:
                if page_index >= doc.page_count:
                    warnings.append(f"Pagina da etiqueta nao existe: {source_path.name} pagina {page_index + 1}")
                    return
                page = doc[page_index]
                pix = page.get_pixmap(matrix=fitz.Matrix(render_zoom, render_zoom), alpha=False)
                image_bytes = pix.tobytes("png")
                pil_image = Image.open(BytesIO(image_bytes))
        elif suffix in IMAGE_EXTENSIONS:
            pil_image = Image.open(source_path)
        else:
            warnings.append(f"Etiqueta {source_path.name}: formato original nao renderizado na etiqueta unificada.")
            return

        if remove_white_margins:
            before_size = pil_image.size
            pil_image = crop_white_margins(pil_image)
            print(f"[PDF-LABEL] crop margens {before_size} -> {pil_image.size}")

        if thermal_mode:
            pil_image = enhance_for_thermal_print(
                pil_image,
                intensity="",
                threshold_value=threshold_value,
                contrast_factor=contrast_factor,
                sharpness_factor=sharpness_factor,
                black_dilation=black_dilation,
            )
        image = ImageReader(pil_image)
        c.drawImage(image, x, y, width=width, height=height, preserveAspectRatio=True, anchor="c")
        print(
            "[PDF-LABEL] etiqueta original renderizada "
            f"{label.get('source_file', '')} thermal={thermal_mode} crop={remove_white_margins} zoom={render_zoom}"
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Falha ao renderizar etiqueta original {source_path.name}: {exc}")


def _draw_label_page(c: canvas.Canvas, result: dict) -> None:
    label = result.get("label") or {}
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, 280 * mm, "Etiqueta de envio")
    c.setFont("Helvetica", 10)

    y = 265 * mm
    rows = [
        ("Arquivo", label.get("source_file")),
        ("NF lida na etiqueta", label.get("numero_nf")),
        ("Serie", label.get("serie")),
        ("Destinatario", label.get("destinatario")),
        ("CEP", label.get("cep")),
        ("Pedido Shopee", label.get("pedido_shopee")),
        ("Rastreio", label.get("rastreio")),
        ("Confianca", result.get("score")),
        ("Status", result.get("status")),
        ("Motivos", "; ".join(result.get("reasons", []))),
    ]
    for key, value in rows:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(20 * mm, y, f"{key}:")
        c.setFont("Helvetica", 10)
        y = _draw_wrapped(c, value, 55 * mm, y)
        y -= 2 * mm

    raw_text = label.get("raw_text", "")
    if raw_text:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, y, "Texto OCR bruto:")
        y -= 6 * mm
        c.setFont("Courier", 8)
        for line in raw_text.splitlines()[:35]:
            y = _draw_wrapped(c, line, 20 * mm, y, width_chars=115, leading=9)
            if y < 20 * mm:
                break


def _draw_nfe_page(c: canvas.Canvas, result: dict) -> None:
    nfe = result.get("nfe") or {}
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, 280 * mm, "Conferencia da NF-e")
    c.setFont("Helvetica", 10)

    y = 265 * mm
    rows = [
        ("Numero da NF", nfe.get("numero_nf")),
        ("Serie", nfe.get("serie")),
        ("Chave NF-e", nfe.get("chave_nfe")),
        ("Data de emissao", nfe.get("data_emissao")),
        ("Emitente", nfe.get("emitente_nome")),
        ("Destinatario", nfe.get("destinatario_nome")),
        ("Documento", nfe.get("destinatario_documento")),
        ("E-mail", nfe.get("destinatario_email")),
        ("Endereco", nfe.get("destinatario_endereco")),
        ("Valor total", nfe.get("valor_total_nf")),
        ("Autorizacao", f"{nfe.get('status_autorizacao', '')} - {nfe.get('motivo_autorizacao', '')}"),
        ("Arquivo NF/DANFE", nfe.get("source_file")),
    ]
    for key, value in rows:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(20 * mm, y, f"{key}:")
        c.setFont("Helvetica", 10)
        y = _draw_wrapped(c, value, 55 * mm, y)
        y -= 2 * mm

    products = nfe.get("produtos") or []
    if products:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, y, "Produtos:")
        y -= 6 * mm
        c.setFont("Helvetica", 8)
        for product in products[:12]:
            line = (
                f"{product.get('codigo', '')} | {product.get('descricao', '')} | "
                f"qtd {product.get('quantidade', '')} | total {product.get('valor_total', '')}"
            )
            y = _draw_wrapped(c, line, 20 * mm, y, width_chars=120, leading=9)
            if y < 20 * mm:
                break


def generate_case_pdf(result: dict, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(path), pagesize=A4)
    _draw_label_page(c, result)
    c.showPage()
    _draw_nfe_page(c, result)
    c.save()
    return path


def _safe_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "sem_nome")
    return value.strip("_") or "sem_nome"


def _pdf_page_index(page_value) -> int:
    try:
        page = int(page_value)
    except (TypeError, ValueError):
        page = 1
    return max(page - 1, 0)


def _content_bbox(page, fitz_module, margin: float = 8):
    bbox = None

    def add_rect(rect_value) -> None:
        nonlocal bbox
        rect = fitz_module.Rect(rect_value)
        if rect.is_empty or rect.width < 1 or rect.height < 1:
            return
        bbox = rect if bbox is None else bbox | rect

    for block in page.get_text("blocks"):
        add_rect(block[:4])

    try:
        for drawing in page.get_drawings():
            if drawing.get("rect"):
                add_rect(drawing["rect"])
    except Exception:  # noqa: BLE001 - drawing extraction is best effort.
        pass

    try:
        for image in page.get_image_info():
            if image.get("bbox"):
                add_rect(image["bbox"])
    except Exception:  # noqa: BLE001 - image extraction is best effort.
        pass

    if bbox is None:
        return page.rect

    bbox = fitz_module.Rect(
        max(page.rect.x0, bbox.x0 - margin),
        max(page.rect.y0, bbox.y0 - margin),
        min(page.rect.x1, bbox.x1 + margin),
        min(page.rect.y1, bbox.y1 + margin),
    )
    return bbox if not bbox.is_empty else page.rect


def _append_pdf_page_fit_content(output_doc, source_doc, page_index: int, warnings: list[str], description: str) -> bool:
    try:
        import fitz
    except ImportError:
        warnings.append("PyMuPDF nao esta instalado; nao foi possivel montar PDFs de impressao.")
        return False

    try:
        source_page = source_doc[page_index]
        clip = _content_bbox(source_page, fitz)
        page = output_doc.new_page(width=595, height=842)
        target = fitz.Rect(18, 18, 577, 824)
        page.show_pdf_page(target, source_doc, page_index, clip=clip, keep_proportion=True)
        print(
            "[PDF-PRINT] adicionada pagina "
            f"{page_index + 1} recortada/ampliada ({description}) "
            f"clip=({clip.x0:.1f},{clip.y0:.1f},{clip.x1:.1f},{clip.y1:.1f})"
        )
        return True
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"{description}: falha ao recortar/ampliar pagina: {exc}")
        return False


def _append_pdf_page_split_content(output_doc, source_path: Path, page_value, warnings: list[str], description: str) -> bool:
    try:
        import fitz
    except ImportError:
        warnings.append("PyMuPDF nao esta instalado; nao foi possivel montar PDFs de impressao.")
        return False

    if not source_path.exists():
        warnings.append(f"{description}: arquivo original nao encontrado: {source_path}")
        return False

    try:
        with fitz.open(source_path) as source_doc:
            page_index = _pdf_page_index(page_value)
            if page_index >= source_doc.page_count:
                warnings.append(f"{description}: pagina {page_index + 1} nao existe em {source_path.name}")
                return False

            source_page = source_doc[page_index]
            clip = _content_bbox(source_page, fitz)
            middle_y = clip.y0 + (clip.height / 2)
            clips = [
                ("parte superior", fitz.Rect(clip.x0, clip.y0, clip.x1, middle_y + 10)),
                ("parte inferior", fitz.Rect(clip.x0, middle_y - 10, clip.x1, clip.y1)),
            ]
            target = fitz.Rect(18, 18, 577, 824)
            for part_name, part_clip in clips:
                page = output_doc.new_page(width=595, height=842)
                page.show_pdf_page(target, source_doc, page_index, clip=part_clip, keep_proportion=True)
                print(
                    "[PDF-PRINT] adicionada "
                    f"{part_name} da pagina {page_index + 1} ({description}) "
                    f"clip=({part_clip.x0:.1f},{part_clip.y0:.1f},{part_clip.x1:.1f},{part_clip.y1:.1f})"
                )
            return True
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"{description}: falha ao dividir/ampliar pagina: {exc}")
        return False


def _append_pdf_page(
    output_doc,
    source_path: Path,
    page_value,
    warnings: list[str],
    description: str,
    fit_content: bool = False,
) -> bool:
    try:
        import fitz
    except ImportError:
        warnings.append("PyMuPDF nao esta instalado; nao foi possivel montar PDFs de impressao.")
        return False

    if not source_path.exists():
        warnings.append(f"{description}: arquivo original nao encontrado: {source_path}")
        return False

    try:
        with fitz.open(source_path) as source_doc:
            page_index = _pdf_page_index(page_value)
            if page_index >= source_doc.page_count:
                warnings.append(f"{description}: pagina {page_index + 1} nao existe em {source_path.name}")
                return False
            if fit_content and _append_pdf_page_fit_content(output_doc, source_doc, page_index, warnings, description):
                return True
            output_doc.insert_pdf(source_doc, from_page=page_index, to_page=page_index)
            print(f"[PDF-PRINT] adicionada pagina {page_index + 1} de {source_path.name} ({description})")
            return True
    except Exception as exc:  # noqa: BLE001 - keep batch generation resilient.
        warnings.append(f"{description}: falha ao copiar pagina de {source_path.name}: {exc}")
        return False


def _append_image_page(output_doc, source_path: Path, warnings: list[str], description: str) -> bool:
    try:
        import fitz
    except ImportError:
        warnings.append("PyMuPDF nao esta instalado; nao foi possivel montar PDFs de impressao.")
        return False

    if not source_path.exists():
        warnings.append(f"{description}: imagem original nao encontrada: {source_path}")
        return False

    try:
        image_doc = fitz.open(source_path)
        pdf_bytes = image_doc.convert_to_pdf()
        image_doc.close()
        with fitz.open("pdf", pdf_bytes) as image_pdf:
            output_doc.insert_pdf(image_pdf)
        print(f"[PDF-PRINT] adicionada imagem {source_path.name} ({description})")
        return True
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"{description}: falha ao inserir imagem {source_path.name}: {exc}")
        return False


def _append_text_page(output_doc, title: str, rows: list[tuple[str, str]], warnings: list[str]) -> None:
    try:
        import fitz
    except ImportError:
        warnings.append("PyMuPDF nao esta instalado; nao foi possivel montar pagina de conferencia.")
        return

    page = output_doc.new_page(width=595, height=842)
    page.insert_text((50, 50), title, fontsize=16, fontname="helv")
    y = 90
    for key, value in rows:
        text = f"{key}: {value or ''}"
        rect = fitz.Rect(50, y, 545, y + 48)
        page.insert_textbox(rect, text, fontsize=10, fontname="helv")
        y += 42
        if y > 780:
            page = output_doc.new_page(width=595, height=842)
            y = 50


def _append_label(output_doc, result: dict, warnings: list[str]) -> None:
    label = result.get("label") or {}
    source_path = Path(label.get("source_path") or "")
    suffix = source_path.suffix.lower()
    description = f"etiqueta {label.get('source_file', '')}"

    if suffix == ".pdf" and _append_pdf_page(output_doc, source_path, label.get("source_page"), warnings, description):
        return
    if suffix in IMAGE_EXTENSIONS and _append_image_page(output_doc, source_path, warnings, description):
        return

    warnings.append(f"{description}: sem pagina PDF/imagem original; foi gerada pagina de conferencia.")
    _append_text_page(
        output_doc,
        "Etiqueta de envio - conferencia",
        [
            ("Arquivo", label.get("source_file", "")),
            ("NF encontrada", label.get("numero_nf", "")),
            ("Destinatario", label.get("destinatario", "")),
            ("CEP", label.get("cep", "")),
            ("Pedido Shopee", label.get("pedido_shopee", "")),
            ("Rastreio", label.get("rastreio", "")),
            ("Texto OCR", label.get("ocr_summary", "")),
        ],
        warnings,
    )


def _append_nfe(output_doc, result: dict, warnings: list[str], nfe_layout: str = "full_page") -> None:
    nfe = result.get("nfe") or {}
    source_path = Path(nfe.get("source_path") or "")
    suffix = source_path.suffix.lower()
    description = f"NF {nfe.get('numero_nf', '')}"

    if suffix == ".pdf" and nfe_layout == "split_pages" and _append_pdf_page_split_content(
        output_doc,
        source_path,
        nfe.get("source_page"),
        warnings,
        description,
    ):
        return

    if suffix == ".pdf" and _append_pdf_page(
        output_doc,
        source_path,
        nfe.get("source_page"),
        warnings,
        description,
        fit_content=True,
    ):
        return

    warnings.append(f"{description}: sem pagina DANFE PDF original; foi gerada pagina de conferencia.")
    _append_text_page(
        output_doc,
        "NF-e/DANFE - conferencia",
        [
            ("Numero da NF", nfe.get("numero_nf", "")),
            ("Serie", nfe.get("serie", "")),
            ("Chave NF-e", nfe.get("chave_nfe", "")),
            ("Cliente", nfe.get("destinatario_nome", "")),
            ("Documento", nfe.get("destinatario_documento", "")),
            ("Endereco", nfe.get("destinatario_endereco", "")),
            ("CEP", nfe.get("destinatario_cep", "")),
            ("Valor total", nfe.get("valor_total_nf", "")),
            ("Arquivo", nfe.get("source_file", "")),
        ],
        warnings,
    )


def _append_match(output_doc, result: dict, order: str, warnings: list[str], nfe_layout: str = "full_page") -> None:
    if order == "nfe_first":
        _append_nfe(output_doc, result, warnings, nfe_layout=nfe_layout)
        _append_label(output_doc, result, warnings)
    else:
        _append_label(output_doc, result, warnings)
        _append_nfe(output_doc, result, warnings, nfe_layout=nfe_layout)


def _conciliated(matches: list[dict]) -> list[dict]:
    return [
        match
        for match in matches
        if match.get("status") == "conciliado" and (match.get("nfe") or {}).get("numero_nf") and (match.get("label") or {})
    ]


def generate_print_batch_pdf(
    matches: list[dict],
    output_path: str | Path,
    order: str = "label_first",
    nfe_layout: str = "full_page",
) -> tuple[Path | None, list[str]]:
    try:
        import fitz
    except ImportError:
        return None, ["PyMuPDF nao esta instalado; instale PyMuPDF para gerar PDF de impressao."]

    warnings: list[str] = []
    conciliated = _conciliated(matches)
    if not conciliated:
        return None, ["Nenhum item conciliado para gerar PDF de impressao."]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    output_doc = fitz.open()
    try:
        for result in conciliated:
            nfe = result.get("nfe") or {}
            label = result.get("label") or {}
            print(
                "[PDF-PRINT] match "
                f"NF={nfe.get('numero_nf', '')} "
                f"etiqueta={label.get('source_file', '')} "
                f"ordem={order}"
            )
            _append_match(output_doc, result, order, warnings, nfe_layout=nfe_layout)

        if output_doc.page_count == 0:
            warnings.append("Nenhuma pagina foi adicionada ao PDF de impressao.")
            return None, warnings

        output_doc.save(path)
        print(f"[PDF-PRINT] PDF unico salvo em {path}")
        return path, warnings
    finally:
        output_doc.close()


def generate_individual_pdfs(
    matches: list[dict],
    output_dir: str | Path,
    order: str = "label_first",
    nfe_layout: str = "full_page",
) -> tuple[list[Path], list[str]]:
    try:
        import fitz
    except ImportError:
        return [], ["PyMuPDF nao esta instalado; instale PyMuPDF para gerar PDFs individuais."]

    warnings: list[str] = []
    paths: list[Path] = []
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for result in _conciliated(matches):
        nfe = result.get("nfe") or {}
        client = _safe_filename(nfe.get("destinatario_nome", "cliente"))
        number = _safe_filename(nfe.get("numero_nf", "sem_nf"))
        path = output_path / f"NF_{number}_{client}.pdf"

        output_doc = fitz.open()
        try:
            _append_match(output_doc, result, order, warnings, nfe_layout=nfe_layout)
            if output_doc.page_count == 0:
                warnings.append(f"NF {number}: nenhuma pagina adicionada ao PDF individual.")
                continue
            output_doc.save(path)
            paths.append(path)
            print(f"[PDF-PRINT] PDF individual salvo em {path}")
        finally:
            output_doc.close()

    if not paths:
        warnings.append("Nenhum PDF individual foi gerado.")
    return paths, warnings


def _product_code(product: dict) -> str:
    for key in ("ean", "cEAN", "cEANTrib", "codigo", "cProd"):
        value = str(product.get(key) or "").strip()
        if value and value.upper() != "SEM GTIN":
            return value
    return ""


def _product_quantity(product: dict) -> str:
    return str(product.get("quantidade") or product.get("qCom") or product.get("qTrib") or "").strip()


def _product_description(product: dict) -> str:
    return str(product.get("descricao") or product.get("xProd") or "").strip()


def contar_produtos_pedido(result_or_nfe: dict) -> int:
    nfe = result_or_nfe.get("nfe") or result_or_nfe
    return len(nfe.get("produtos") or [])


def classificar_pedidos(matches: list[dict]) -> list[dict]:
    conciliated = _conciliated(matches)
    single_product = [item for item in conciliated if contar_produtos_pedido(item) <= 1]
    two_products = [item for item in conciliated if contar_produtos_pedido(item) == 2]
    multiple_products = [item for item in conciliated if contar_produtos_pedido(item) >= 3]
    return single_product + two_products + multiple_products


def _draw_picking_block(
    c: canvas.Canvas,
    nfe: dict,
    x: float,
    y: float,
    width: float,
    height: float,
    compact: bool = False,
    block_format: str = "lines",
) -> None:
    if contar_produtos_pedido(nfe) > 2:
        desenhar_conferencia_na_etiqueta(c, nfe, x, y, width, height, compact=compact)
        return

    if block_format == "lines":
        _draw_picking_lines_block(c, nfe, x, y, width, height, compact=compact)
        return

    products = nfe.get("produtos") or []
    c.setLineWidth(1.0 if compact else 0.8)
    c.rect(x, y, width, height)

    title_size = 7.5 if compact else 12
    header_size = 5.8 if compact else 8
    row_size = 6 if compact else 9
    title_y = y + height - (10 if compact else 8 * mm)
    c.setFont("Helvetica-Bold", title_size)
    c.drawString(x + 4 * mm, title_y, "CONFERENCIA DO PRODUTO")

    header_y = title_y - (10 if compact else 8 * mm)
    ean_x = x + (5 if compact else 4 * mm)
    product_x = x + (78 if compact else 50 * mm)
    qtd_x = x + width - (20 if compact else 18 * mm)
    c.setFont("Helvetica-Bold", header_size)
    c.drawString(ean_x, header_y, "EAN")
    c.drawString(product_x, header_y, "PRODUTO")
    c.drawString(qtd_x, header_y, "QTD")
    c.line(x + 4, header_y - 4, x + width - 4, header_y - 4)

    row_y = header_y - (12 if compact else 8 * mm)
    row_h = 10 if compact else 8 * mm
    if not products:
        c.setFont("Helvetica", row_size)
        c.drawString(ean_x, row_y, "Produtos nao extraidos da NF/DANFE.")
        return

    for product in products[:5]:
        if row_y < y + (5 if compact else 6 * mm):
            c.setFont("Helvetica-Oblique", 7)
            c.drawString(ean_x, row_y, "Demais produtos no relatorio.")
            break

        c.setFont("Helvetica", row_size)
        ean_w = 68 if compact else 42 * mm
        product_w = width - (105 if compact else 75 * mm)
        qtd_w = 16 if compact else 15 * mm
        _fit_text(c, _product_code(product), ean_x, row_y, ean_w, "Helvetica", row_size, 4.8 if compact else 6)
        _fit_text(c, _product_description(product), product_x, row_y, product_w, "Helvetica", row_size, 4.5 if compact else 6)
        _fit_text(c, _product_quantity(product), qtd_x, row_y, qtd_w, "Helvetica-Bold", row_size, 4.8 if compact else 6)
        row_y -= row_h


def desenhar_conferencia_na_etiqueta(
    c: canvas.Canvas,
    nfe: dict,
    x: float,
    y: float,
    width: float,
    height: float,
    compact: bool = False,
) -> None:
    product_count = contar_produtos_pedido(nfe)
    c.setLineWidth(1.1 if compact else 0.9)
    c.rect(x, y, width, height)

    pad_x = 6 if compact else 4 * mm
    top = y + height - (10 if compact else 8 * mm)
    c.setFont("Helvetica-Bold", 8.8 if compact else 12)
    c.drawString(x + pad_x, top, "CONFERENCIA DO PRODUTO")

    center_x = x + width / 2
    line_y = top - (16 if compact else 13 * mm)
    c.setFont("Helvetica-Bold", 9.0 if compact else 13)
    c.drawCentredString(center_x, line_y, f"PEDIDO COM {product_count} PRODUTOS")
    line_y -= 13 if compact else 12 * mm
    c.setFont("Helvetica-Bold", 7.2 if compact else 10)
    c.drawCentredString(center_x, line_y, "VER ETIQUETA DE CONFERENCIA ANEXA")


def _draw_label_value(
    c: canvas.Canvas,
    label: str,
    value: str,
    x: float,
    y: float,
    label_w: float,
    value_w: float,
    font_size: float,
    value_font: str = "Helvetica",
) -> None:
    c.setFont("Helvetica-Bold", font_size)
    c.drawString(x, y, label)
    _fit_text(c, value, x + label_w, y, value_w, value_font, font_size, max(4.8, font_size - 2))


def _draw_product_name_lines(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    font_size: float,
    leading: float,
    max_lines: int,
) -> float:
    words = str(text or "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if c.stringWidth(candidate, "Helvetica-Bold", font_size) <= width or not current:
            current = candidate
            continue
        lines.append(current)
        current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)

    for line in lines[:max_lines]:
        _fit_text(c, line, x, y, width, "Helvetica-Bold", font_size, max(4.8, font_size - 2))
        y -= leading
    return y


def _draw_picking_lines_block(
    c: canvas.Canvas,
    nfe: dict,
    x: float,
    y: float,
    width: float,
    height: float,
    compact: bool = False,
) -> None:
    products = nfe.get("produtos") or []
    c.setLineWidth(1.1 if compact else 0.9)
    c.rect(x, y, width, height)

    pad_x = 6 if compact else 4 * mm
    top = y + height - (10 if compact else 8 * mm)
    title_size = 8.8 if compact else 12
    field_size = 7.4 if compact else 10
    qty_size = 9.0 if compact else 11
    label_w = 56 if compact else 28 * mm
    value_w = width - label_w - (2 * pad_x)

    c.setFont("Helvetica-Bold", title_size)
    c.drawString(x + pad_x, top, "CONFERENCIA DO PRODUTO")

    if not products:
        c.setFont("Helvetica", field_size)
        c.drawString(x + pad_x, top - 13, "Produtos nao extraidos da NF/DANFE.")
        return

    if compact and len(products) > 1:
        _draw_picking_compact_columns(c, products, x, y, width, height, pad_x, top)
        return

    row_y = top - (13 if compact else 9 * mm)
    max_products = 2 if compact else 4
    for index, product in enumerate(products[:max_products], start=1):
        if row_y < y + 10:
            break
        if len(products) > 1:
            c.setFont("Helvetica-Bold", 6.5 if compact else 8)
            c.drawString(x + pad_x, row_y, f"PRODUTO {index}")
            row_y -= 8 if compact else 10

        _draw_label_value(
            c,
            "EAN:",
            _product_code(product),
            x + pad_x,
            row_y,
            label_w,
            value_w,
            field_size,
        )
        row_y -= 10 if compact else 14

        c.setFont("Helvetica-Bold", field_size)
        c.drawString(x + pad_x, row_y, "PRODUTO:")
        row_y = _draw_product_name_lines(
            c,
            _product_description(product),
            x + pad_x + label_w,
            row_y,
            value_w,
            field_size,
            9 if compact else 12,
            max_lines=2,
        )

        _draw_label_value(
            c,
            "QTD:",
            _product_quantity(product),
            x + pad_x,
            row_y,
            label_w,
            value_w,
            qty_size,
            value_font="Helvetica-Bold",
        )
        row_y -= 11 if compact else 15


def _draw_picking_compact_columns(
    c: canvas.Canvas,
    products: list[dict],
    x: float,
    y: float,
    width: float,
    height: float,
    pad_x: float,
    top: float,
) -> None:
    """Draw multiple products in the small 4x6 picking footer."""
    visible_products = products[:2]
    gap = 6
    col_w = (width - (2 * pad_x) - gap) / 2
    label_w = 29
    value_w = col_w - label_w
    field_size = 5.6
    product_size = 5.3
    qty_size = 6.6
    title_y = top - 10

    for index, product in enumerate(visible_products, start=1):
        col_x = x + pad_x + ((index - 1) * (col_w + gap))
        row_y = title_y

        c.setFont("Helvetica-Bold", 6.2)
        c.drawString(col_x, row_y, f"PRODUTO {index}")
        row_y -= 8

        _draw_label_value(
            c,
            "EAN:",
            _product_code(product),
            col_x,
            row_y,
            label_w,
            value_w,
            field_size,
        )
        row_y -= 8

        c.setFont("Helvetica-Bold", product_size)
        c.drawString(col_x, row_y, "PRODUTO:")
        row_y = _draw_product_name_lines(
            c,
            _product_description(product),
            col_x + label_w,
            row_y,
            value_w,
            product_size,
            6.7,
            max_lines=2,
        )

        _draw_label_value(
            c,
            "QTD:",
            _product_quantity(product),
            col_x,
            row_y,
            label_w,
            value_w,
            qty_size,
            value_font="Helvetica-Bold",
        )

    if len(products) > 2:
        c.setFont("Helvetica-Bold", 5.2)
        c.drawRightString(x + width - pad_x, y + 4, f"+ {len(products) - 2} produto(s) no relatorio")


def _picking_page_size(paper_size: str) -> tuple[tuple[float, float], float, float, float]:
    if paper_size == "a4":
        return A4, 8 * mm, 55 * mm, 5 * mm
    return (288, 432), 3, 55, 2


def _draw_label_with_picking_page(
    c: canvas.Canvas,
    result: dict,
    warnings: list[str],
    paper_size: str = "4x6",
    picking_format: str = "lines",
    thermal_mode: bool = True,
    thermal_intensity: str = "very_strong",
    remove_white_margins: bool = True,
) -> None:
    nfe = result.get("nfe") or {}
    label = result.get("label") or {}
    (page_w, page_h), margin, picking_h, gap = _picking_page_size(paper_size)
    label_x = margin
    label_y = margin + picking_h + gap
    label_w = page_w - (2 * margin)
    label_h = page_h - label_y - margin

    settings = dict(_thermal_settings(thermal_intensity))
    render_zoom = settings.pop("render_zoom", 4.0 if paper_size != "a4" else 2.5)
    _draw_original_label_area(
        c,
        label,
        label_x,
        label_y,
        label_w,
        label_h,
        warnings,
        thermal_mode=thermal_mode and paper_size != "a4",
        render_zoom=render_zoom if paper_size != "a4" else 2.5,
        remove_white_margins=remove_white_margins and paper_size != "a4",
        **settings,
    )
    _draw_picking_block(
        c,
        nfe,
        margin,
        margin,
        page_w - (2 * margin),
        picking_h,
        compact=paper_size != "a4",
        block_format=picking_format,
    )
    print(
        "[PDF-PICKING] pagina adicionada "
        f"NF={nfe.get('numero_nf', '')} etiqueta={label.get('source_file', '')} papel={paper_size}"
    )


def _draw_extra_conference_header(
    c: canvas.Canvas,
    result: dict,
    page_w: float,
    page_h: float,
    margin: float,
    page_number: int,
    total_pages: int,
) -> float:
    nfe = result.get("nfe") or {}
    label = result.get("label") or {}
    y = page_h - margin

    c.setLineWidth(1.1)
    c.rect(margin, margin, page_w - (2 * margin), page_h - (2 * margin))

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin + 5, y - 13, "CONFERENCIA DO PRODUTO")
    if total_pages > 1:
        c.setFont("Helvetica-Bold", 7)
        c.drawRightString(page_w - margin - 5, y - 12, f"PAGINA {page_number}/{total_pages}")

    y -= 29
    c.setFont("Helvetica-Bold", 6.8)
    c.drawString(margin + 5, y, "NF:")
    c.setFont("Helvetica", 6.8)
    c.drawString(margin + 23, y, str(nfe.get("numero_nf", "")))

    pedido = label.get("pedido_shopee") or label.get("rastreio") or label.get("source_file", "")
    c.setFont("Helvetica-Bold", 6.8)
    c.drawString(margin + 75, y, "IDENTIFICADOR:")
    _fit_text(c, pedido, margin + 130, y, page_w - margin - 135, "Helvetica", 6.8, 4.8)

    y -= 12
    c.setFont("Helvetica-Bold", 6.8)
    c.drawString(margin + 5, y, "DESTINATARIO:")
    _fit_text(c, nfe.get("destinatario_nome", ""), margin + 60, y, page_w - margin - 65, "Helvetica-Bold", 6.8, 4.8)

    return y - 13


def _draw_extra_product_block(
    c: canvas.Canvas,
    product: dict,
    index: int,
    x: float,
    y: float,
    width: float,
    row_h: float,
) -> None:
    c.setLineWidth(0.7)
    c.rect(x, y - row_h + 2, width, row_h)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawString(x + 5, y - 8, f"PRODUTO {index}")

    c.setFont("Helvetica-Bold", 6.2)
    c.drawString(x + 5, y - 20, "EAN:")
    _fit_text(c, _product_code(product), x + 32, y - 20, width - 37, "Helvetica-Bold", 7.2, 5.0)

    c.setFont("Helvetica-Bold", 6.2)
    c.drawString(x + 5, y - 32, "PRODUTO:")
    _fit_text(c, _product_description(product), x + 48, y - 32, width - 53, "Helvetica-Bold", 6.5, 4.6)

    c.setFont("Helvetica-Bold", 6.2)
    c.drawString(x + 5, y - 44, "QTD:")
    _fit_text(c, _product_quantity(product), x + 32, y - 44, width - 37, "Helvetica-Bold", 7.8, 5.0)


def gerar_etiqueta_extra_conferencia(
    c: canvas.Canvas,
    result: dict,
    paper_size: str = "4x6",
) -> int:
    nfe = result.get("nfe") or {}
    products = nfe.get("produtos") or []
    if len(products) <= 2:
        return 0

    (page_w, page_h), margin, _, _ = _picking_page_size(paper_size)
    if paper_size == "a4":
        margin = 8 * mm
        row_h = 23 * mm
    else:
        margin = 4
        row_h = 54

    header_h = 62 if paper_size != "a4" else 38 * mm
    available_h = page_h - (2 * margin) - header_h
    per_page = max(1, int(available_h // row_h))
    total_pages = (len(products) + per_page - 1) // per_page

    for page_index in range(total_pages):
        if page_index > 0:
            c.showPage()
        start = page_index * per_page
        chunk = products[start : start + per_page]
        y = _draw_extra_conference_header(c, result, page_w, page_h, margin, page_index + 1, total_pages)
        for offset, product in enumerate(chunk, start=1):
            _draw_extra_product_block(
                c,
                product,
                start + offset,
                margin + 5,
                y,
                page_w - (2 * margin) - 10,
                row_h,
            )
            y -= row_h + 4

    print(
        "[PDF-PICKING] etiqueta extra de conferencia adicionada "
        f"NF={nfe.get('numero_nf', '')} produtos={len(products)} paginas={total_pages}"
    )
    return total_pages


def montar_pdf_final_ordenado(matches: list[dict]) -> list[dict]:
    return classificar_pedidos(matches)


def _append_picking_pages(
    c: canvas.Canvas,
    result: dict,
    warnings: list[str],
    paper_size: str,
    picking_format: str,
    thermal_mode: bool,
    thermal_intensity: str,
    remove_white_margins: bool,
) -> None:
    _draw_label_with_picking_page(
        c,
        result,
        warnings,
        paper_size=paper_size,
        picking_format=picking_format,
        thermal_mode=thermal_mode,
        thermal_intensity=thermal_intensity,
        remove_white_margins=remove_white_margins,
    )
    c.showPage()

    if contar_produtos_pedido(result) > 2:
        gerar_etiqueta_extra_conferencia(c, result, paper_size=paper_size)
        c.showPage()


def generate_label_with_picking_pdf(
    match: dict,
    output_path: str | Path,
    paper_size: str = "4x6",
    picking_format: str = "lines",
    thermal_mode: bool = True,
    thermal_intensity: str = "very_strong",
    remove_white_margins: bool = True,
) -> tuple[Path | None, list[str]]:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    page_size, _, _, _ = _picking_page_size(paper_size)

    c = canvas.Canvas(str(path), pagesize=page_size)
    _append_picking_pages(
        c,
        match,
        warnings,
        paper_size,
        picking_format,
        thermal_mode,
        thermal_intensity,
        remove_white_margins,
    )
    c.save()
    print(f"[PDF-PICKING] PDF individual salvo em {path}")
    return path, warnings


def generate_print_batch_picking_pdf(
    matches: list[dict],
    output_path: str | Path,
    paper_size: str = "4x6",
    picking_format: str = "lines",
    thermal_mode: bool = True,
    thermal_intensity: str = "very_strong",
    remove_white_margins: bool = True,
) -> tuple[Path | None, list[str]]:
    conciliated = montar_pdf_final_ordenado(matches)
    if not conciliated:
        return None, ["Nenhum item conciliado para gerar PDF de impressao com picking."]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    page_size, _, _, _ = _picking_page_size(paper_size)
    c = canvas.Canvas(str(path), pagesize=page_size)

    for result in conciliated:
        _append_picking_pages(
            c,
            result,
            warnings,
            paper_size,
            picking_format,
            thermal_mode,
            thermal_intensity,
            remove_white_margins,
        )

    c.save()
    print(f"[PDF-PICKING] PDF em lote salvo em {path}")
    return path, warnings


def generate_individual_picking_pdfs(
    matches: list[dict],
    output_dir: str | Path,
    paper_size: str = "4x6",
    picking_format: str = "lines",
    thermal_mode: bool = True,
    thermal_intensity: str = "very_strong",
    remove_white_margins: bool = True,
) -> tuple[list[Path], list[str]]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    warnings: list[str] = []

    for result in _conciliated(matches):
        nfe = result.get("nfe") or {}
        client = _safe_filename(nfe.get("destinatario_nome", "cliente"))
        number = _safe_filename(nfe.get("numero_nf", "sem_nf"))
        path = output_path / f"NF_{number}_{client}.pdf"
        pdf_path, item_warnings = generate_label_with_picking_pdf(
            result,
            path,
            paper_size=paper_size,
            picking_format=picking_format,
            thermal_mode=thermal_mode,
            thermal_intensity=thermal_intensity,
            remove_white_margins=remove_white_margins,
        )
        warnings.extend(item_warnings)
        if pdf_path and pdf_path.exists():
            paths.append(pdf_path)

    if not paths:
        warnings.append("Nenhum PDF individual com picking foi gerado.")
    return paths, warnings


def _draw_unified_label(c: canvas.Canvas, result: dict, page_size: tuple[float, float], warnings: list[str]) -> None:
    nfe = result.get("nfe") or {}
    label = result.get("label") or {}
    width, height = page_size
    margin = 2.5 * mm
    left_w = 76 * mm
    right_x = margin + left_w + 2.5 * mm
    right_w = width - right_x - margin

    c.setLineWidth(0.7)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)
    c.line(right_x - 1.5 * mm, margin, right_x - 1.5 * mm, height - margin)

    _draw_original_label_area(
        c,
        label,
        margin + 1 * mm,
        margin + 1 * mm,
        left_w - 2 * mm,
        height - 2 * margin - 2 * mm,
        warnings,
    )

    y = height - 7 * mm
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(right_x, y, "DANFE SIMPLIFICADA")
    y -= 7 * mm
    c.setFont("Helvetica-Bold", 13.5)
    c.drawString(right_x, y, f"NF {nfe.get('numero_nf', '')}")
    c.setFont("Helvetica", 6.4)
    c.drawRightString(right_x + right_w, y + 1.5 * mm, f"Serie: {nfe.get('serie', '')}")
    c.drawRightString(right_x + right_w, y - 1.5 * mm, f"Emissao: {nfe.get('data_emissao', '')}")

    y -= 10 * mm
    _draw_code128(c, nfe.get("chave_nfe", ""), right_x, y, right_w, 8.5 * mm, human_readable=False)
    y -= 3 * mm
    _fit_text(c, nfe.get("chave_nfe", ""), right_x, y, right_w, "Helvetica", 5.3, 4.2)

    y -= 5.5 * mm
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(right_x, y, "DESTINATARIO:")
    _fit_text(c, nfe.get("destinatario_nome", ""), right_x + 23 * mm, y, right_w - 23 * mm, "Helvetica-Bold", 6.5)
    y -= 4.5 * mm
    c.setFont("Helvetica-Bold", 5.8)
    c.drawString(right_x, y, "ENDERECO:")
    y -= 3.8 * mm
    y = _draw_fit_wrapped_lines(c, nfe.get("destinatario_logradouro", ""), right_x, y, right_w, max_lines=2, font_size=6.1)
    _fit_text(c, f"{nfe.get('destinatario_bairro', '')} | CEP: {nfe.get('destinatario_cep', '')}", right_x, y, right_w, "Helvetica", 6.0)
    y -= 3.7 * mm
    _fit_text(c, f"{nfe.get('destinatario_cidade', '')}/{nfe.get('destinatario_uf', '')}", right_x, y, right_w, "Helvetica-Bold", 6.5)

    y -= 4.2 * mm
    c.setLineWidth(0.5)
    table_x = right_x
    table_w = right_w
    row_h = 10 * mm
    c.rect(table_x, y - row_h, table_w, row_h)
    c.setFont("Helvetica-Bold", 5.2)
    c.drawString(table_x + 1 * mm, y - 4 * mm, "COD. BARRAS")
    c.drawString(table_x + 29 * mm, y - 4 * mm, "DESCRICAO")
    c.drawString(table_x + table_w - 9 * mm, y - 4 * mm, "QTD")

    products = nfe.get("produtos") or []
    y -= row_h
    for product in products[:3]:
        c.rect(table_x, y - row_h, table_w, row_h)
        code = _product_code(product)
        _draw_code128(c, code, table_x + 1 * mm, y - row_h + 2 * mm, 26 * mm, 5 * mm, human_readable=False)
        _fit_text(c, code, table_x + 1 * mm, y - row_h + 0.8 * mm, 26 * mm, max_size=4.6, min_size=3.6)
        _fit_text(c, product.get("descricao", ""), table_x + 29 * mm, y - 5 * mm, table_w - 40 * mm, max_size=5.4, min_size=3.9)
        _fit_text(c, product.get("quantidade", ""), table_x + table_w - 9 * mm, y - 5 * mm, 8 * mm, "Helvetica-Bold", 5.6)
        y -= row_h

    if not products:
        c.rect(table_x, y - row_h, table_w, row_h)
        c.setFont("Helvetica", 5.5)
        c.drawString(table_x + 1 * mm, y - 5 * mm, "Produtos nao extraidos da NF/DANFE.")

    c.setFont("Helvetica-Bold", 5.2)
    c.drawRightString(width - margin - 1 * mm, margin + 2 * mm, f"Valor NF: {nfe.get('valor_total_nf', '')}")


def _draw_danfe_compact_area(
    c: canvas.Canvas,
    nfe: dict,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    c.setLineWidth(0.7)
    c.rect(x, y, width, height)

    top = y + height - 5 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x + 2 * mm, top, "DANFE SIMPLIFICADA")
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(x + width - 2 * mm, top - 0.7 * mm, f"NF {nfe.get('numero_nf', '')}")

    top -= 8 * mm
    c.setFont("Helvetica", 7)
    c.drawString(x + 2 * mm, top, f"Serie: {nfe.get('serie', '')}")
    c.drawRightString(x + width - 2 * mm, top, f"Emissao: {nfe.get('data_emissao', '')}")

    top -= 4.5 * mm
    _fit_text(c, nfe.get("chave_nfe", ""), x + 2 * mm, top, width - 4 * mm, "Helvetica", 5.2, 4)

    top -= 5.5 * mm
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x + 2 * mm, top, "DESTINATARIO:")
    _fit_text(c, nfe.get("destinatario_nome", ""), x + 29 * mm, top, width - 31 * mm, "Helvetica-Bold", 7)

    top -= 4.5 * mm
    address = nfe.get("destinatario_logradouro") or nfe.get("destinatario_endereco") or ""
    top = _draw_fit_wrapped_lines(c, address, x + 2 * mm, top, width - 4 * mm, max_lines=2, font_size=6.6)
    _fit_text(
        c,
        f"{nfe.get('destinatario_bairro', '')} | CEP: {nfe.get('destinatario_cep', '')}",
        x + 2 * mm,
        top,
        width - 4 * mm,
        "Helvetica",
        6.5,
    )
    top -= 4.1 * mm
    _fit_text(
        c,
        f"{nfe.get('destinatario_cidade', '')}/{nfe.get('destinatario_uf', '')}",
        x + 2 * mm,
        top,
        width - 4 * mm,
        "Helvetica-Bold",
        7.1,
    )

    products = nfe.get("produtos") or []
    if not products:
        return

    product = products[0]
    product_y = y + 4 * mm
    c.line(x, product_y + 20 * mm, x + width, product_y + 20 * mm)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(x + 2 * mm, product_y + 16.5 * mm, "COD. BARRAS")
    c.drawString(x + 34 * mm, product_y + 16.5 * mm, "PRODUTO")
    c.drawRightString(x + width - 2 * mm, product_y + 16.5 * mm, "QTD")

    code = _product_code(product)
    _draw_code128(c, code, x + 2 * mm, product_y + 5 * mm, 29 * mm, 9 * mm, human_readable=False)
    _fit_text(c, code, x + 2 * mm, product_y + 0.8 * mm, 28 * mm, max_size=5, min_size=4)
    _fit_text(c, product.get("descricao", ""), x + 34 * mm, product_y + 10 * mm, width - 48 * mm, max_size=6.3, min_size=4.5)
    _fit_text(c, product.get("quantidade", ""), x + width - 12 * mm, product_y + 10 * mm, 10 * mm, "Helvetica-Bold", 7)
    c.setFont("Helvetica-Bold", 5.4)
    c.drawRightString(x + width - 2 * mm, y + 1.6 * mm, f"Valor NF: {nfe.get('valor_total_nf', '')}")


def _draw_unified_label_vertical(c: canvas.Canvas, result: dict, page_size: tuple[float, float], warnings: list[str]) -> None:
    nfe = result.get("nfe") or {}
    label = result.get("label") or {}
    width, height = page_size
    margin = 2 * mm
    gap = 2 * mm
    label_h = 84 * mm
    danfe_h = height - (2 * margin) - gap - label_h

    c.setLineWidth(0.7)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    _draw_original_label_area(
        c,
        label,
        margin + 1 * mm,
        height - margin - label_h + 1 * mm,
        width - 2 * margin - 2 * mm,
        label_h - 2 * mm,
        warnings,
    )
    c.line(margin, margin + danfe_h + gap / 2, width - margin, margin + danfe_h + gap / 2)
    _draw_danfe_compact_area(c, nfe, margin, margin, width - 2 * margin, danfe_h)


def _draw_thermal_label_only(c: canvas.Canvas, result: dict, page_size: tuple[float, float], warnings: list[str]) -> None:
    label = result.get("label") or {}
    width, height = page_size
    margin = 2 * mm
    _draw_original_label_area(c, label, margin, margin, width - 2 * margin, height - 2 * margin, warnings)


def _draw_thermal_danfe_only(c: canvas.Canvas, result: dict, page_size: tuple[float, float]) -> None:
    nfe = result.get("nfe") or {}
    width, height = page_size
    margin = 2 * mm
    _draw_danfe_compact_area(c, nfe, margin, margin, width - 2 * margin, height - 2 * margin)


def generate_unified_thermal_labels_pdf(
    matches: list[dict],
    output_path: str | Path,
    layout: str = "vertical_100x150",
) -> tuple[Path | None, list[str]]:
    conciliated = _conciliated(matches)
    if not conciliated:
        return None, ["Nenhum item conciliado para gerar etiqueta termica unificada."]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    page_size = (100 * mm, 150 * mm) if layout in {"vertical_100x150", "two_pages_100x150"} else (150 * mm, 100 * mm)
    c = canvas.Canvas(str(path), pagesize=page_size)

    for result in conciliated:
        nfe = result.get("nfe") or {}
        print(f"[PDF-THERMAL] etiqueta unificada NF={nfe.get('numero_nf', '')} layout={layout}")
        if not (nfe.get("produtos") or []):
            warnings.append(f"NF {nfe.get('numero_nf', '')}: produtos/codigos de barras nao extraidos.")
        if layout == "two_pages_100x150":
            _draw_thermal_label_only(c, result, page_size, warnings)
            c.showPage()
            _draw_thermal_danfe_only(c, result, page_size)
        elif layout == "side_by_side_150x100":
            _draw_unified_label(c, result, page_size, warnings)
        else:
            _draw_unified_label_vertical(c, result, page_size, warnings)
        c.showPage()

    c.save()
    print(f"[PDF-THERMAL] PDF salvo em {path}")
    return path, warnings
