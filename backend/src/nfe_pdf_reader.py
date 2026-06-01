from __future__ import annotations

from pathlib import Path
import re

from .label_reader import extract_nfe_key_from_label, parse_nfe_access_key
from .ocr_reader import extract_texts_from_label_file
from .utils import normalize_cep, only_digits


def _money_candidates(lines: list[str]) -> list[str]:
    return [line for line in lines if re.fullmatch(r"\d{1,6},\d{2}", line.strip())]


def _extract_nf_number(text: str, key_info: dict) -> str:
    if key_info.get("numero_nf"):
        return key_info["numero_nf"]

    match = re.search(r"\bN[º°O]?\s*(\d{3,12})\b", text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _extract_recipient_block(lines: list[str]) -> dict:
    """Extract recipient data from common DANFE text order.

    In many generated DANFE PDFs, field labels are listed first and the actual
    values appear after "VALOR DO IPI". This parser handles that layout and
    falls back gracefully when the marker is not present.
    """
    start = -1
    for index, line in enumerate(lines):
        if line.upper() == "VALOR DO IPI":
            start = index + 1
            break

    values = lines[start : start + 14] if start >= 0 else []
    if len(values) >= 11:
        uf = values[9] if re.fullmatch(r"[A-Z]{2}", values[9].strip(), re.IGNORECASE) else values[10]
        return {
            "nome": values[0],
            "documento": only_digits(values[1]),
            "data_emissao": values[2],
            "cep": normalize_cep(values[4]),
            "bairro": values[5],
            "endereco": values[6],
            "cidade": values[7],
            "uf": uf,
        }

    return {
        "nome": "",
        "documento": "",
        "data_emissao": "",
        "cep": "",
        "bairro": "",
        "endereco": "",
        "cidade": "",
        "uf": "",
    }


def _extract_emitente(text: str, key_info: dict) -> tuple[str, str]:
    cnpj = key_info.get("cnpj", "")
    name_match = re.search(r"\n(DROGARIA[^\n]+)\n", text, re.IGNORECASE)
    return (name_match.group(1).strip() if name_match else "", cnpj)


def _extract_total_nf(lines: list[str]) -> str:
    for index, line in enumerate(lines):
        if line.upper() == "VALOR TOTAL DA NOTA":
            window = []
            for value in lines[index + 1 : index + 20]:
                if value.upper().startswith(
                    ("SEM FRETE", "COM FRETE", "DESTINATÁRIO", "DESTINATARIO", "CÓDIGO", "CODIGO", "VALOR DO CBS")
                ):
                    break
                window.append(value)
            candidates = _money_candidates(window)
            if candidates:
                return candidates[-1]
    candidates = _money_candidates(lines)
    return candidates[-1] if candidates else ""


def _extract_products(lines: list[str]) -> list[dict]:
    products = []
    start = 0
    for index, line in enumerate(lines):
        if "DADOS DO PRODUTO" in line.upper():
            start = index
            break

    stop_terms = (
        "INSCRIÇÃO MUNICIPAL",
        "INSCRICAO MUNICIPAL",
        "DADOS ADICIONAIS",
        "INFORMAÇÕES COMPLEMENTARES",
        "INFORMACOES COMPLEMENTARES",
    )

    for index in range(start, len(lines)):
        ean = lines[index].strip()
        if not re.fullmatch(r"\d{8,14}", ean):
            continue

        following = lines[index + 1 : index + 5]
        if not following or any(term in following[0].upper() for term in stop_terms):
            continue

        description_parts = []
        for value in following:
            upper = value.upper()
            if any(term in upper for term in stop_terms):
                break
            if upper.startswith(("DESCONTO", "LÍQ", "LIQ", "TOTAL L")):
                break
            if re.fullmatch(r"\d{1,6},\d{2}", value) or re.fullmatch(r"\d{1,2},\d{2}", value):
                break
            if re.fullmatch(r"\d{8}", value):
                break
            description_parts.append(value)

        if not description_parts:
            continue

        quantity = ""
        previous = lines[max(0, index - 12) : index]
        for prev_index, value in enumerate(previous):
            if value.upper() == "UN" and prev_index + 1 < len(previous):
                candidate = previous[prev_index + 1]
                if re.fullmatch(r"\d{1,4},\d{2,4}", candidate):
                    quantity = candidate
        if not quantity:
            for value in reversed(previous):
                if re.fullmatch(r"\d{1,4},\d{2,4}", value):
                    quantity = value
                    break

        products.append(
            {
                "codigo": ean,
                "ean": ean,
                "descricao": " ".join(description_parts),
                "quantidade": quantity,
                "valor_unitario": "",
                "valor_total": "",
            }
        )

    return products


def _parse_nfe_pdf_page(text: str, path: Path, page_index: int, total_pages: int) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    chave = extract_nfe_key_from_label(text)
    key_info = parse_nfe_access_key(chave)
    recipient = _extract_recipient_block(lines)
    emitente_nome, emitente_documento = _extract_emitente(text, key_info)
    numero_nf = _extract_nf_number(text, key_info)

    source_file = path.name if total_pages == 1 else f"{path.name} - pagina {page_index}"
    endereco = " ".join(
        part
        for part in [
            recipient.get("endereco"),
            recipient.get("bairro"),
            recipient.get("cidade"),
            recipient.get("uf"),
            recipient.get("cep"),
        ]
        if part
    )

    return {
        "numero_nf": numero_nf,
        "serie": key_info.get("serie", ""),
        "chave_nfe": chave,
        "data_emissao": recipient.get("data_emissao", ""),
        "emitente_nome": emitente_nome,
        "emitente_documento": emitente_documento,
        "destinatario_nome": recipient.get("nome", ""),
        "destinatario_documento": recipient.get("documento", ""),
        "destinatario_email": "",
        "destinatario_logradouro": recipient.get("endereco", ""),
        "destinatario_numero": "",
        "destinatario_bairro": recipient.get("bairro", ""),
        "destinatario_cidade": recipient.get("cidade", ""),
        "destinatario_uf": recipient.get("uf", ""),
        "destinatario_cep": recipient.get("cep", ""),
        "destinatario_endereco": endereco,
        "produtos": _extract_products(lines),
        "valor_total_nf": _extract_total_nf(lines),
        "status_autorizacao": "",
        "motivo_autorizacao": "",
        "autorizada": True,
        "source_file": source_file,
        "source_path": str(path),
        "source_page": page_index,
        "source_type": "pdf",
        "raw_text": text,
    }


def parse_nfe_pdfs(file: str | Path) -> list[dict]:
    path = Path(file)
    texts = extract_texts_from_label_file(path)
    total_pages = len(texts)
    nfes = [_parse_nfe_pdf_page(text, path, index, total_pages) for index, text in enumerate(texts, start=1)]
    print(f"[NF-PDF] arquivo={path.name} nfes_encontradas={len(nfes)} numeros={[nfe.get('numero_nf') for nfe in nfes]}")
    return nfes
