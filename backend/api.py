from __future__ import annotations

from pathlib import Path
import os
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.pipeline import ProcessingOptions, list_manifests, process_batch, read_manifest, safe_filename, to_jsonable


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
MARKETPLACES = [
    {"id": "shopee", "name": "Shopee"},
    {"id": "amazon", "name": "Amazon"},
    {"id": "tiktok_shop", "name": "TikTok Shop"},
    {"id": "beleza_na_web", "name": "Beleza na Web"},
    {"id": "magalu", "name": "Magalu"},
    {"id": "vtex", "name": "VTEX"},
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
