from __future__ import annotations

from datetime import datetime
from pathlib import Path
import uuid

from reportlab.pdfgen import canvas

from .converter import RenderSettings, parse_graphic_assets, render_label_on_canvas, update_graphic_assets
from .schemas import ZplConversionReport, ZplConversionResponse, ZplLabelError
from .splitter import LABEL_RE, PRINTABLE_RE, split_zpl_labels


def _safe_filename(value: str) -> str:
    import re

    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "sem_nome")
    return value.strip("_") or "sem_nome"


def convert_zpl_batch(
    content: str,
    output_root: str | Path,
    original_filename: str,
    marketplace: str = "",
    width_mm: float = 100,
    height_mm: float = 150,
    dpi: int = 203,
    batch_name: str = "",
    job_id: str | None = None,
) -> ZplConversionReport:
    job_id = job_id or datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    output_dir = Path(output_root) / "zpl_converter" / _safe_filename(job_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    split = split_zpl_labels(content)
    settings = RenderSettings(width_mm=width_mm, height_mm=height_mm, dpi=dpi)
    pdf_path = output_dir / "etiquetas_convertidas.pdf"
    errors: list[ZplLabelError] = []
    warnings = list(split.warnings)
    converted = 0

    if split.labels:
        c = canvas.Canvas(str(pdf_path), pagesize=(settings.page_width, settings.page_height))
        graphics = {}
        cursor = 0
        index = 0
        for match in LABEL_RE.finditer(content or ""):
            prefix = content[cursor : match.start()]
            graphics, graphic_warnings = update_graphic_assets(graphics, prefix)
            warnings.extend(graphic_warnings)

            label = match.group(0).strip()
            if not PRINTABLE_RE.search(label):
                graphics, graphic_warnings = update_graphic_assets(graphics, label)
                warnings.extend(graphic_warnings)
                cursor = match.end()
                continue

            index += 1
            inline_graphics, graphic_warnings = parse_graphic_assets(label)
            warnings.extend(graphic_warnings)
            graphics_for_label = {**graphics, **inline_graphics}
            result = render_label_on_canvas(c, label, settings, index, graphics=graphics_for_label)
            warnings.extend(result.warnings)
            if result.converted:
                converted += 1
                c.showPage()
            else:
                errors.append(ZplLabelError(index=index, message=result.error or "Falha ao renderizar etiqueta."))

            graphics, graphic_warnings = update_graphic_assets(graphics, label)
            warnings.extend(graphic_warnings)
            cursor = match.end()
        if converted:
            c.save()
        else:
            pdf_path = None
    else:
        pdf_path = None

    total = len(split.labels)
    failed = total - converted
    if converted and failed:
        status = "partial_success"
    elif converted:
        status = "success"
    else:
        status = "failed"

    report = ZplConversionReport(
        job_id=job_id,
        status=status,
        total_labels=total,
        converted_labels=converted,
        failed_labels=failed,
        pdf_url=f"/api/zpl/{job_id}/pdf" if pdf_path else None,
        warnings=warnings,
        original_file=original_filename,
        marketplace=marketplace,
        batch_name=batch_name,
        width_mm=width_mm,
        height_mm=height_mm,
        dpi=dpi,
        errors=errors,
        output_pdf=str(pdf_path.resolve()) if pdf_path else None,
    )
    (output_dir / "relatorio.json").write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return report


def public_response(report: ZplConversionReport) -> ZplConversionResponse:
    return ZplConversionResponse(**report.model_dump(include=ZplConversionResponse.model_fields.keys()))
