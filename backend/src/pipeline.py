from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import json
import re
import shutil
import uuid
import zipfile

from .label_reader import read_labels
from .matcher import match_nfes_to_labels
from .nfe_pdf_reader import parse_nfe_pdfs
from .pdf_generator import (
    generate_case_pdf,
    generate_individual_picking_pdfs,
    generate_individual_pdfs,
    generate_print_batch_picking_pdf,
    generate_print_batch_pdf,
)
from .report_generator import save_reports
from .utils import ensure_output_dirs
from .xml_reader import parse_nfe_xmls


@dataclass
class ProcessingOptions:
    print_layout: str = "picking"
    paper_size: str = "4x6"
    picking_format: str = "lines"
    thermal_mode: bool = True
    thermal_intensity: str = "strong"
    remove_white_margins: bool = True
    print_order: str = "label_first"
    sort_by: str = "label_order"
    nfe_layout: str = "full_page"


def safe_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "sem_nome")
    return value.strip("_") or "sem_nome"


def city_uf(city: str | None, uf: str | None) -> str:
    parts = [part for part in [city, uf] if part]
    return "/".join(parts)


def has_nfe(result: dict) -> bool:
    return bool((result.get("nfe") or {}).get("numero_nf"))


def has_label(result: dict) -> bool:
    label = result.get("label") or {}
    return bool(label.get("source_file") or label.get("raw_text"))


def case_pdf_name(result: dict, index: int) -> str:
    nfe = result.get("nfe") or {}
    label = result.get("label") or {}
    status = result.get("status", "pendente")
    if nfe.get("numero_nf"):
        base = f"NF_{nfe.get('numero_nf')}_{status}"
    else:
        base = f"ETIQUETA_{label.get('source_file', 'sem_nf')}_{status}_{index}"
    return f"{safe_filename(base)}.pdf"


def zip_files(files: list[Path], output_path: Path) -> Path | None:
    existing = [Path(file) for file in files if file and Path(file).exists()]
    if not existing:
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for file in existing:
            zip_file.write(file, arcname=file.name)
    return output_path


def as_absolute_path(value: str | Path | None) -> str:
    if not value:
        return ""
    return str(Path(value).resolve())


def num_sort(value: str) -> tuple[int, str]:
    value = str(value or "")
    digits = re.sub(r"\D", "", value)
    return (int(digits), value) if digits else (999999999, value)


def sort_conciliated_results(results: list[dict], sort_by: str) -> list[dict]:
    conciliated = [
        result
        for result in results
        if result.get("status") == "conciliado"
        and (result.get("nfe") or {}).get("numero_nf")
        and (result.get("label") or {}).get("source_file")
    ]

    if sort_by == "nf_number":
        return sorted(conciliated, key=lambda item: num_sort((item.get("nfe") or {}).get("numero_nf", "")))
    if sort_by == "customer":
        return sorted(conciliated, key=lambda item: str((item.get("nfe") or {}).get("destinatario_nome", "")).upper())
    if sort_by == "cep":
        return sorted(conciliated, key=lambda item: str((item.get("nfe") or {}).get("destinatario_cep", "")))
    if sort_by == "shopee_order":
        return sorted(conciliated, key=lambda item: str((item.get("label") or {}).get("pedido_shopee", "")).upper())

    return sorted(
        conciliated,
        key=lambda item: (
            str((item.get("label") or {}).get("source_path", "")),
            num_sort((item.get("label") or {}).get("source_page", "")),
            str((item.get("label") or {}).get("source_file", "")),
        ),
    )


def all_report_rows(results: list[dict]) -> list[dict]:
    rows = []
    for item in results:
        nfe = item.get("nfe") or {}
        label = item.get("label") or {}
        rows.append(
            {
                "nf": nfe.get("numero_nf", ""),
                "nf_etiqueta": label.get("numero_nf", ""),
                "chave_nfe": nfe.get("chave_nfe", ""),
                "chave_nfe_etiqueta": label.get("chave_nfe", ""),
                "cliente": nfe.get("destinatario_nome", ""),
                "cep": nfe.get("destinatario_cep", ""),
                "cidade_uf": city_uf(nfe.get("destinatario_cidade"), nfe.get("destinatario_uf")),
                "arquivo_nf": nfe.get("source_file", ""),
                "pagina_nf": nfe.get("source_page", ""),
                "arquivo_etiqueta": label.get("source_file", ""),
                "pagina_etiqueta": label.get("source_page", ""),
                "destinatario_etiqueta": label.get("destinatario", ""),
                "cep_etiqueta": label.get("cep", ""),
                "cidade_uf_etiqueta": city_uf(label.get("cidade"), label.get("uf")),
                "pedido_shopee": label.get("pedido_shopee", ""),
                "rastreio": label.get("rastreio", ""),
                "texto_ocr_resumido": label.get("ocr_summary", ""),
                "valor_total": nfe.get("valor_total_nf", ""),
                "confianca": item.get("score", 0),
                "status": item.get("status", ""),
                "motivos": "; ".join(item.get("reasons", [])),
                "pdf_final": item.get("pdf_final", ""),
            }
        )
    return rows


def conciliated_rows(results: list[dict]) -> list[dict]:
    return [row for row in all_report_rows(results) if row.get("status") == "conciliado" and row.get("nf")]


def labels_without_nfe_rows(results: list[dict]) -> list[dict]:
    rows = []
    for item in results:
        if has_nfe(item) or not has_label(item):
            continue
        label = item.get("label") or {}
        rows.append(
            {
                "arquivo_etiqueta": label.get("source_file", ""),
                "pagina_etiqueta": label.get("source_page", ""),
                "nf_encontrada": label.get("numero_nf", ""),
                "chave_nfe_encontrada": label.get("chave_nfe", ""),
                "destinatario": label.get("destinatario", ""),
                "cep": label.get("cep", ""),
                "cidade_uf": city_uf(label.get("cidade"), label.get("uf")),
                "pedido_shopee": label.get("pedido_shopee", ""),
                "rastreio": label.get("rastreio", ""),
                "texto_ocr_resumido": label.get("ocr_summary", ""),
                "motivo": "; ".join(item.get("reasons", [])),
            }
        )
    return rows


def nfes_without_label_rows(results: list[dict]) -> list[dict]:
    rows = []
    for item in results:
        if not has_nfe(item) or has_label(item) or item.get("status") != "pendente":
            continue
        nfe = item.get("nfe") or {}
        rows.append(
            {
                "nf": nfe.get("numero_nf", ""),
                "chave_nfe": nfe.get("chave_nfe", ""),
                "cliente": nfe.get("destinatario_nome", ""),
                "cep": nfe.get("destinatario_cep", ""),
                "cidade_uf": city_uf(nfe.get("destinatario_cidade"), nfe.get("destinatario_uf")),
                "arquivo_nf": nfe.get("source_file", ""),
                "pagina_nf": nfe.get("source_page", ""),
                "valor_total": nfe.get("valor_total_nf", ""),
                "motivo": "; ".join(item.get("reasons", [])),
            }
        )
    return rows


def review_rows(results: list[dict]) -> list[dict]:
    rows = []
    for item in results:
        if item.get("status") != "revisar":
            continue
        nfe = item.get("nfe") or {}
        label = item.get("label") or {}
        rows.append(
            {
                "nf": nfe.get("numero_nf", ""),
                "cliente": nfe.get("destinatario_nome", ""),
                "etiqueta_candidata": label.get("source_file", ""),
                "confianca": item.get("score", 0),
                "motivos": "; ".join(item.get("reasons", [])),
                "texto_ocr_resumido": label.get("ocr_summary", ""),
            }
        )
    return rows


def copy_input_files(files: list[Path], target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for index, source in enumerate(files, start=1):
        source_path = Path(source)
        target = target_dir / f"{index:03d}_{safe_filename(source_path.name)}"
        shutil.copy2(source_path, target)
        copied.append(target)
    return copied


def read_nfes(paths: list[Path]) -> tuple[list[dict], list[str]]:
    nfes = []
    errors = []
    for path in paths:
        try:
            if path.suffix.lower() == ".pdf":
                nfes.extend(parse_nfe_pdfs(path))
            elif path.suffix.lower() == ".xml":
                nfes.extend(parse_nfe_xmls(path))
            else:
                raise ValueError(f"Formato de NF nao suportado: {path.suffix}")
        except Exception as exc:  # noqa: BLE001 - batch processing should continue.
            errors.append(f"{path.name}: {exc}")
    return nfes, errors


def read_label_files(paths: list[Path]) -> tuple[list[dict], list[str]]:
    labels = []
    errors = []
    for path in paths:
        try:
            labels.extend(read_labels(path))
        except Exception as exc:  # noqa: BLE001 - batch processing should continue.
            errors.append(f"{path.name}: {exc}")
    return labels, errors


def process_batch(
    nfe_paths: list[Path],
    label_paths: list[Path],
    output_root: Path,
    options: ProcessingOptions | None = None,
    job_id: str | None = None,
    marketplace: str = "geral",
    batch_name: str = "",
) -> dict:
    options = options or ProcessingOptions()
    job_id = job_id or datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    marketplace = marketplace.strip() or "geral"
    marketplace_slug = safe_filename(marketplace).lower()
    batch_name = batch_name.strip() or f"Lote {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    job_dir = output_root / "api_jobs" / job_id
    input_nfe_dir = job_dir / "input" / "nfes"
    input_label_dir = job_dir / "input" / "labels"
    output_dirs = ensure_output_dirs(job_dir)

    copied_nfe_paths = copy_input_files(nfe_paths, input_nfe_dir)
    copied_label_paths = copy_input_files(label_paths, input_label_dir)

    nfes, nfe_errors = read_nfes(copied_nfe_paths)
    labels, label_errors = read_label_files(copied_label_paths)
    results = match_nfes_to_labels(nfes, labels)
    sorted_conciliated = sort_conciliated_results(results, options.sort_by)

    for index, result in enumerate(results, start=1):
        if result["status"] == "conciliado":
            target_dir = output_dirs["conciliados"]
        elif result["status"] == "revisar":
            target_dir = output_dirs["revisar"]
        else:
            target_dir = output_dirs["pendentes"]

        pdf_path = target_dir / case_pdf_name(result, index)
        result["pdf_final"] = str(generate_case_pdf(result, pdf_path))

    report_rows = all_report_rows(results)
    csv_path, xlsx_path = save_reports(report_rows, output_dirs["relatorios"])

    conciliated_pdf_paths = [Path(item["pdf_final"]) for item in results if item.get("status") == "conciliado"]
    pending_review_pdf_paths = [
        Path(item["pdf_final"]) for item in results if item.get("status") in {"pendente", "revisar"}
    ]
    conciliated_zip = zip_files(conciliated_pdf_paths, output_dirs["relatorios"] / "pdfs_conciliados.zip")
    pending_review_zip = zip_files(pending_review_pdf_paths, output_dirs["relatorios"] / "pdfs_pendentes_revisar.zip")

    if options.print_layout == "two_pages":
        print_batch_pdf, print_batch_warnings = generate_print_batch_pdf(
            sorted_conciliated,
            output_dirs["conciliados"] / "lote_impressao_organizado.pdf",
            order=options.print_order,
            nfe_layout=options.nfe_layout,
        )
        individual_pdf_paths, individual_warnings = generate_individual_pdfs(
            sorted_conciliated,
            output_dirs["conciliados"] / "individual",
            order=options.print_order,
            nfe_layout=options.nfe_layout,
        )
    else:
        print_batch_pdf, print_batch_warnings = generate_print_batch_picking_pdf(
            sorted_conciliated,
            output_dirs["conciliados"] / "lote_impressao_picking.pdf",
            paper_size=options.paper_size,
            picking_format=options.picking_format,
            thermal_mode=options.thermal_mode,
            thermal_intensity=options.thermal_intensity,
            remove_white_margins=options.remove_white_margins,
        )
        individual_pdf_paths, individual_warnings = generate_individual_picking_pdfs(
            sorted_conciliated,
            output_dirs["conciliados"] / "individual",
            paper_size=options.paper_size,
            picking_format=options.picking_format,
            thermal_mode=options.thermal_mode,
            thermal_intensity=options.thermal_intensity,
            remove_white_margins=options.remove_white_margins,
        )

    individual_zip = zip_files(individual_pdf_paths, output_dirs["relatorios"] / "pdfs_individuais_conciliados.zip")
    print_generation_warnings = print_batch_warnings + individual_warnings

    totals = {
        "notas_lidas": len(nfes),
        "etiquetas_lidas": len(labels),
        "conciliadas": len(conciliated_rows(results)),
        "etiquetas_sem_nf": len(labels_without_nfe_rows(results)),
        "notas_sem_etiqueta": len(nfes_without_label_rows(results)),
        "para_revisar": len(review_rows(results)),
    }
    totals["taxa_conciliacao"] = round((totals["conciliadas"] / totals["notas_lidas"] * 100), 2) if totals["notas_lidas"] else 0

    manifest = {
        "job_id": job_id,
        "marketplace": marketplace,
        "marketplace_slug": marketplace_slug,
        "batch_name": batch_name,
        "status": "concluido",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "totals": totals,
        "errors": {
            "nfes": nfe_errors,
            "etiquetas": label_errors,
            "pdfs": print_generation_warnings,
        },
        "downloads": {
            "pdf_final": as_absolute_path(print_batch_pdf),
            "relatorio_csv": as_absolute_path(csv_path),
            "relatorio_excel": as_absolute_path(xlsx_path),
            "zip_individuais": as_absolute_path(individual_zip),
            "zip_conciliados": as_absolute_path(conciliated_zip),
            "zip_pendentes_revisar": as_absolute_path(pending_review_zip),
        },
        "views": {
            "resultados": report_rows,
            "conciliados": conciliated_rows(results),
            "etiquetas_sem_nf": labels_without_nfe_rows(results),
            "notas_sem_etiqueta": nfes_without_label_rows(results),
            "revisar": review_rows(results),
        },
    }
    manifest_path = job_dir / "manifest.json"
    manifest_path.write_text(json.dumps(to_jsonable(manifest), ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def to_jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    return value


def read_manifest(output_root: Path, job_id: str) -> dict:
    manifest_path = output_root / "api_jobs" / safe_filename(job_id) / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Lote nao encontrado: {job_id}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def list_manifests(output_root: Path, marketplace: str | None = None) -> list[dict]:
    jobs_root = output_root / "api_jobs"
    if not jobs_root.exists():
        return []

    wanted_slug = safe_filename(marketplace).lower() if marketplace else ""
    summaries = []
    for manifest_path in jobs_root.glob("*/manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if wanted_slug and manifest.get("marketplace_slug") != wanted_slug:
            continue

        summaries.append(
            {
                "job_id": manifest.get("job_id", ""),
                "marketplace": manifest.get("marketplace", "geral"),
                "marketplace_slug": manifest.get("marketplace_slug", "geral"),
                "batch_name": manifest.get("batch_name", ""),
                "created_at": manifest.get("created_at", ""),
                "status": manifest.get("status", ""),
                "totals": manifest.get("totals", {}),
                "downloads": {
                    "pdf_final": bool((manifest.get("downloads") or {}).get("pdf_final")),
                    "relatorio_excel": bool((manifest.get("downloads") or {}).get("relatorio_excel")),
                    "zip_individuais": bool((manifest.get("downloads") or {}).get("zip_individuais")),
                },
            }
        )

    return sorted(summaries, key=lambda item: item.get("created_at", ""), reverse=True)
