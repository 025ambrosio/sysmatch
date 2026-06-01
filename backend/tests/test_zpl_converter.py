from __future__ import annotations

import fitz

from services.zpl_converter.pdf_builder import convert_zpl_batch
from services.zpl_converter.splitter import split_zpl_labels


def test_split_single_label():
    result = split_zpl_labels("^XA^FO20,20^FDTeste^FS^XZ")

    assert len(result.labels) == 1
    assert result.labels[0].startswith("^XA")
    assert result.labels[0].endswith("^XZ")


def test_split_multiple_labels():
    result = split_zpl_labels("^XA^FO10,10^FDUm^FS^XZ\n^XA^FO10,10^FDDois^FS^XZ")

    assert len(result.labels) == 2


def test_detect_invalid_zpl_without_blocks():
    result = split_zpl_labels("conteudo sem comandos de etiqueta")

    assert result.labels == []
    assert any("^XA" in warning for warning in result.warnings)


def test_generate_pdf_with_multiple_pages(tmp_path):
    zpl = "^XA^FO20,20^FDUm^FS^XZ\n^XA^FO20,20^FDDois^FS^XZ"

    report = convert_zpl_batch(zpl, tmp_path, "teste.zpl", job_id="job_pdf")

    assert report.converted_labels == 2
    assert report.failed_labels == 0
    assert report.output_pdf
    with fitz.open(report.output_pdf) as doc:
        assert doc.page_count == 2


def test_invalid_label_does_not_break_batch(tmp_path):
    zpl = "^XA^GFTHIS_IS_NOT_RENDERED^XZ\n^XA^FO20,20^FDValida^FS^XZ"

    report = convert_zpl_batch(zpl, tmp_path, "parcial.zpl", job_id="job_partial")

    assert report.status == "partial_success"
    assert report.converted_labels == 1
    assert report.failed_labels == 1
    assert report.errors[0].index == 1


def test_control_only_blocks_are_ignored():
    zpl = "^XA^FO20,20^FDValida^FS^XZ\n^XA^IDR:DEMO.GRF^FS^XZ"

    result = split_zpl_labels(zpl)

    assert len(result.labels) == 1
    assert "Valida" in result.labels[0]


def _page_black_pixels(pdf_path: str, page_index: int) -> int:
    with fitz.open(pdf_path) as doc:
        page = doc[page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(4, 4), alpha=False)
        data = pix.samples
        return sum(
            1
            for index in range(0, len(data), pix.n)
            if data[index] < 80 and data[index + 1] < 80 and data[index + 2] < 80
        )


def test_reused_graphic_name_uses_current_label_asset(tmp_path):
    black_graphic = "FF" * 100
    sparse_graphic = ("00" * 99) + "FF"
    zpl = (
        f"~DGR:DEMO.GRF,100,10,{black_graphic}"
        "^XA^FO0,0^XGR:DEMO.GRF,1,1^FS^XZ"
        "^XA^IDR:DEMO.GRF^FS^XZ"
        f"~DGR:DEMO.GRF,100,10,{sparse_graphic}"
        "^XA^FO0,0^XGR:DEMO.GRF,1,1^FS^XZ"
        "^XA^IDR:DEMO.GRF^FS^XZ"
    )

    report = convert_zpl_batch(zpl, tmp_path, "graficos_repetidos.zpl", job_id="job_reused_graphics")

    assert report.status == "success"
    assert report.total_labels == 2
    assert report.converted_labels == 2
    assert report.output_pdf
    first_black_pixels = _page_black_pixels(report.output_pdf, 0)
    second_black_pixels = _page_black_pixels(report.output_pdf, 1)
    assert first_black_pixels > second_black_pixels * 20
