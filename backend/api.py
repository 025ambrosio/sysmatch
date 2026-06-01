from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from services.zpl_converter import convert_zpl_batch
from services.zpl_converter.pdf_builder import public_response
from src.pipeline import ProcessingOptions, list_manifests, process_batch, read_manifest, safe_filename, to_jsonable


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
ZPL_OUTPUT_DIR = OUTPUT_DIR / "zpl_converter"
MARKETPLACES = [
    {"id": "shopee", "name": "Shopee"},
    {"id": "amazon", "name": "Amazon"},
    {"id": "tiktok_shop", "name": "TikTok Shop"},
    {"id": "beleza_na_web", "name": "Beleza na Web"},
]


def _allowed_origins() -> list[str]:
    raw = os.environ.get("ALLOWED_ORIGINS", "*")
    return [item.strip() for item in raw.split(",") if item.strip()]


app = FastAPI(
    title="Conciliador NF x Etiquetas API",
    version="1.0.0",
    description="API para processar PDFs/XMLs de NF/DANFE e etiquetas usando a logica do sistema atual.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/marketplaces")
def listar_marketplaces() -> dict:
    return {"marketplaces": MARKETPLACES}


def _zpl_job_dir(job_id: str) -> Path:
    return ZPL_OUTPUT_DIR / safe_filename(job_id)


def _zpl_report_path(job_id: str) -> Path:
    return _zpl_job_dir(job_id) / "relatorio.json"


async def _save_uploads(files: list[UploadFile], target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, upload in enumerate(files, start=1):
        filename = safe_filename(upload.filename or f"arquivo_{index}")
        target = target_dir / f"{index:03d}_{filename}"
        target.write_bytes(await upload.read())
        paths.append(target)
    return paths


@app.post("/api/processar-lote")
async def processar_lote(
    nfe_files: list[UploadFile] = File(..., description="PDFs ou XMLs de NF/DANFE"),
    label_files: list[UploadFile] = File(..., description="PDFs, imagens, ZPL ou TXT de etiquetas"),
    marketplace: str = Form("Shopee"),
    batch_name: str = Form(""),
    print_layout: str = Form("picking"),
    paper_size: str = Form("4x6"),
    picking_format: str = Form("lines"),
    thermal_mode: bool = Form(True),
    thermal_intensity: str = Form("strong"),
    remove_white_margins: bool = Form(True),
    print_order: str = Form("label_first"),
    sort_by: str = Form("label_order"),
    nfe_layout: str = Form("full_page"),
) -> dict:
    if not nfe_files:
        raise HTTPException(status_code=400, detail="Envie ao menos um arquivo de NF/DANFE.")
    if not label_files:
        raise HTTPException(status_code=400, detail="Envie ao menos um arquivo de etiquetas.")

    options = ProcessingOptions(
        print_layout=print_layout,
        paper_size=paper_size,
        picking_format=picking_format,
        thermal_mode=thermal_mode,
        thermal_intensity=thermal_intensity,
        remove_white_margins=remove_white_margins,
        print_order=print_order,
        sort_by=sort_by,
        nfe_layout=nfe_layout,
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        nfe_paths = await _save_uploads(nfe_files, tmp_dir / "nfes")
        label_paths = await _save_uploads(label_files, tmp_dir / "labels")
        try:
            result = process_batch(
                nfe_paths,
                label_paths,
                OUTPUT_DIR,
                options,
                marketplace=marketplace,
                batch_name=batch_name,
            )
        except Exception as exc:  # noqa: BLE001 - return a clean API error.
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return to_jsonable(result)


@app.post("/api/zpl/convert")
async def converter_zpl_pdf(
    file: UploadFile = File(..., description="Arquivo .zpl ou .txt com uma ou mais etiquetas ZPL"),
    marketplace: str = Form(""),
    width_mm: float = Form(100),
    height_mm: float = Form(150),
    dpi: int = Form(203),
    batch_name: str = Form(""),
) -> dict:
    filename = file.filename or "etiquetas.zpl"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".zpl", ".txt"}:
        raise HTTPException(status_code=400, detail="Envie um arquivo .zpl ou .txt.")
    if width_mm <= 0 or height_mm <= 0:
        raise HTTPException(status_code=400, detail="Largura e altura da etiqueta devem ser maiores que zero.")
    if dpi <= 0:
        raise HTTPException(status_code=400, detail="DPI deve ser maior que zero.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("latin-1", errors="replace")

    report = convert_zpl_batch(
        content=content,
        output_root=OUTPUT_DIR,
        original_filename=filename,
        marketplace=marketplace,
        width_mm=width_mm,
        height_mm=height_mm,
        dpi=dpi,
        batch_name=batch_name,
    )
    if report.total_labels == 0:
        raise HTTPException(status_code=400, detail="Arquivo sem blocos ZPL validos no formato ^XA ... ^XZ.")
    if report.converted_labels == 0:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Nenhuma etiqueta pode ser convertida com os comandos suportados.",
                "warnings": report.warnings,
                "errors": [error.model_dump() for error in report.errors],
            },
        )
    return public_response(report).model_dump()


@app.get("/api/zpl/{job_id}/pdf")
def baixar_pdf_zpl(job_id: str):
    report_path = _zpl_report_path(job_id)
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"Conversao ZPL nao encontrada: {job_id}")
    report = to_jsonable(json.loads(report_path.read_text(encoding="utf-8")))
    pdf_value = report.get("output_pdf")
    if not pdf_value:
        raise HTTPException(status_code=404, detail="PDF nao disponivel para esta conversao.")
    path = Path(pdf_value)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo PDF nao encontrado.")
    return FileResponse(path, filename=path.name, media_type="application/pdf")


@app.get("/api/zpl/{job_id}/relatorio")
def relatorio_zpl(job_id: str) -> dict:
    report_path = _zpl_report_path(job_id)
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"Conversao ZPL nao encontrada: {job_id}")
    return to_jsonable(json.loads(report_path.read_text(encoding="utf-8")))


@app.get("/api/lotes")
def listar_lotes(marketplace: str | None = None) -> list[dict]:
    return list_manifests(OUTPUT_DIR, marketplace=marketplace)


@app.get("/api/lotes/{job_id}")
def obter_lote(job_id: str) -> dict:
    try:
        return read_manifest(OUTPUT_DIR, job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/lotes/{job_id}/arquivos/{file_key}")
def baixar_arquivo(job_id: str, file_key: str):
    try:
        manifest = read_manifest(OUTPUT_DIR, job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    downloads = manifest.get("downloads", {})
    file_path = downloads.get(file_key)
    if not file_path:
        raise HTTPException(status_code=404, detail=f"Arquivo nao disponivel: {file_key}")

    path = Path(file_path)
    if not path.is_absolute():
        path = BASE_DIR / path
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo nao encontrado: {file_key}")

    return FileResponse(path, filename=path.name)
