from __future__ import annotations

from pydantic import BaseModel, Field


class ZplLabelError(BaseModel):
    index: int
    message: str


class ZplConversionResponse(BaseModel):
    job_id: str
    status: str = Field(description="success, partial_success ou failed")
    total_labels: int
    converted_labels: int
    failed_labels: int
    pdf_url: str | None = None
    warnings: list[str] = []


class ZplConversionReport(ZplConversionResponse):
    original_file: str
    marketplace: str = ""
    batch_name: str = ""
    width_mm: float
    height_mm: float
    dpi: int
    errors: list[ZplLabelError] = []
    output_pdf: str | None = None
