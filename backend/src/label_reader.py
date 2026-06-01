from __future__ import annotations

from pathlib import Path
import re

from .ocr_reader import extract_text_from_label, extract_texts_from_label_file
from .utils import normalize_cep, normalize_text, only_digits, parse_datetime


def _search(patterns: list[str], text: str, flags: int = re.IGNORECASE) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match.group(1).strip()
    return ""


def _compact_ocr_labels(text: str) -> str:
    text = re.sub(r"\bN\s+F\s+E\b", "NFE", text)
    text = re.sub(r"\bNF\s+E\b", "NFE", text)
    text = re.sub(r"\bN\s+F\b", "NF", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_nfe_access_key(chave: str) -> dict:
    digits = only_digits(chave)
    if len(digits) != 44:
        return {}

    numero_nf = digits[25:34].lstrip("0") or "0"
    serie = digits[22:25].lstrip("0") or "0"
    return {
        "chave_nfe": digits,
        "cuf": digits[0:2],
        "ano_mes": digits[2:6],
        "cnpj": digits[6:20],
        "modelo": digits[20:22],
        "serie": serie,
        "numero_nf": numero_nf,
        "tipo_emissao": digits[34:35],
        "codigo_numerico": digits[35:43],
        "digito_verificador": digits[43:44],
    }


def extract_nfe_key_from_label(text: str) -> str:
    for line in text.splitlines():
        digits = only_digits(line)
        if len(digits) == 44:
            key_info = parse_nfe_access_key(digits)
            if key_info and (key_info.get("modelo") == "55" or key_info.get("cuf") == "35"):
                return key_info["chave_nfe"]

    for match in re.finditer(r"\b\d{44}\b", text):
        key_info = parse_nfe_access_key(match.group(0))
        if key_info and (key_info.get("modelo") == "55" or key_info.get("cuf") == "35"):
            return key_info["chave_nfe"]

    for match in re.finditer(r"(?:\d[\s.\-]*){44}", text):
        key_info = parse_nfe_access_key(match.group(0))
        if key_info and (key_info.get("modelo") == "55" or key_info.get("cuf") == "35"):
            return key_info["chave_nfe"]

    return ""


def _fix_sao_paulo_cep_ocr(cep: str, text: str, candidates: list[str]) -> str:
    """Fix common thermal OCR confusion where leading 0 is read as 9.

    Sao Paulo CEPs are expected in the 01000-19999 range. Some labels also
    show the same CEP twice; when the line CEP is read as 9xxxxxxx and a
    matching 0xxxxxxx candidate appears elsewhere, prefer the valid one.
    """
    if not cep:
        return ""

    normalized = normalize_text(text)
    if "SAO PAULO" not in normalized and "SAO BERNARDO" not in normalized and "MOGI DAS CRUZES" not in normalized:
        return cep

    if cep.startswith("9"):
        corrected = "0" + cep[1:]
        if corrected in candidates:
            return corrected
        for candidate in candidates:
            if candidate.startswith("0"):
                return candidate

    return cep


def extract_nf_number_from_label(text: str) -> str:
    """Extract NF number from noisy OCR text.

    The input is normalized before matching so OCR variants such as N F,
    N.F., N°, No. and accented text can still be recognized.
    """
    normalized = _compact_ocr_labels(normalize_text(text))
    patterns = [
        r"\bNF(?:E)?\b\s*(?:NUMERO\s*)?(\d{3,12})\b",
        r"\bNOTA\s+FISCAL\b\s*(?:NUMERO\s*)?(\d{3,12})\b",
        r"\bDANFE\b\s*(?:NUMERO\s*)?(\d{3,12})\b",
        r"\bN(?:UMERO|RO)?\b\s*(\d{3,12})\b",
        r"\bNO\b\s*(\d{3,12})\b",
    ]
    nf = _search(patterns, normalized, flags=0)
    if nf:
        return nf

    chave = extract_nfe_key_from_label(text)
    key_info = parse_nfe_access_key(chave)
    return key_info.get("numero_nf", "")


def extract_cep_from_label(text: str) -> str:
    normalized = normalize_text(text)
    candidates = []
    for match in re.finditer(r"\b(\d{5}[-.\s]?\d{3}|\d{8})\b", text):
        raw = match.group(1)
        cep = normalize_cep(raw)
        if not cep:
            continue
        context = normalize_text(text[max(0, match.start() - 12) : min(len(text), match.end() + 12)])
        has_separator = bool(re.search(r"[-.]", raw))
        near_cep_label = "CEP" in context
        candidates.append({"cep": cep, "raw": raw, "has_separator": has_separator, "near_cep_label": near_cep_label})

    all_ceps = [candidate["cep"] for candidate in candidates]
    recipient_ceps = [cep for cep in all_ceps if cep != "03619100"]
    if "PICKUP ID" in normalized or "ORDER ID" in normalized:
        cep = recipient_ceps[-1] if recipient_ceps else (all_ceps[-1] if all_ceps else "")
        return _fix_sao_paulo_cep_ocr(cep, text, recipient_ceps)

    strong_recipient_ceps = [
        candidate["cep"]
        for candidate in candidates
        if candidate["cep"] != "03619100" and (candidate["has_separator"] or candidate["near_cep_label"])
    ]
    if strong_recipient_ceps:
        return _fix_sao_paulo_cep_ocr(strong_recipient_ceps[0], text, strong_recipient_ceps)

    cep = _search(
        [
            r"\bCEP\b\s*([0-9]{5}\s*[0-9]{3})\b",
            r"\bCEP\b\s*([0-9]{8})\b",
        ],
        normalized,
        flags=0,
    )
    if cep:
        normalized_cep = normalize_cep(cep)
        return _fix_sao_paulo_cep_ocr(normalized_cep, text, recipient_ceps)

    raw_match = re.search(r"\b(\d{5}[-.\s]?\d{3})\b", text)
    cep = normalize_cep(raw_match.group(1)) if raw_match else ""
    return _fix_sao_paulo_cep_ocr(cep, text, recipient_ceps)


def extract_recipient_from_label(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    labels = ("DESTINATARIO", "CLIENTE", "NOME")

    def is_noise(value: str) -> bool:
        normalized_value = normalize_text(value)
        if not normalized_value:
            return True
        noise_terms = (
            "SHOPEE",
            "SHEPEE",
            "DESTINATARIO",
            "REMETENTE",
            "DANFE",
            "ETIQUETA",
            "SERIE",
            "EMISSAO",
            "CEP",
            "ENVIO",
            "SAIDA",
        )
        if any(term in normalized_value for term in noise_terms):
            return True
        if re.search(r"\b(?:ORDER|PICKUP|TBR|BRAZIL)\b", normalized_value):
            return True
        letters = re.findall(r"[A-Z]", normalized_value)
        words = normalized_value.split()
        return len(letters) < 5 or len(words) < 2

    def is_address_like(value: str) -> bool:
        normalized_value = normalize_text(value)
        address_terms = (
            "RUA",
            "AV",
            "AVENIDA",
            "ALAMEDA",
            "TRAVESSA",
            "ESTRADA",
            "RODOVIA",
            "APARTAMENTO",
            "CASA",
            "BLOCO",
            "SALA",
            "SAO PAULO",
        )
        has_number = bool(re.search(r"\d", normalized_value))
        return has_number and any(term in normalized_value.split() or term in normalized_value for term in address_terms)

    for index, line in enumerate(lines):
        normalized_line = normalize_text(line)
        if "PICKUP ID" not in normalized_line:
            continue
        for next_line in lines[index + 1 : index + 8]:
            next_value = normalize_text(next_line).strip(" :#-")
            if next_value and not is_noise(next_value):
                return next_value

    for index, line in enumerate(lines):
        normalized_line = normalize_text(line)
        for label in labels:
            match = re.match(rf"^{label}\b\s*(.*)$", normalized_line)
            if not match:
                continue

            value = match.group(1).strip(" :#-")
            if value and not is_noise(value) and not is_address_like(value):
                return value

            for next_line in lines[index + 1 : index + 6]:
                next_value = normalize_text(next_line).strip(" :#-")
                if next_value and not is_noise(next_value) and not is_address_like(next_value):
                    return next_value

    return ""


def summarize_ocr_text(fields: dict, limit: int = 260) -> str:
    parts = [
        f"NF encontrada: {fields.get('numero_nf', '') or '-'}",
        f"Chave encontrada: {fields.get('chave_nfe', '') or '-'}",
        f"CEP encontrado: {fields.get('cep', '') or '-'}",
        f"Rastreio encontrado: {fields.get('rastreio', '') or '-'}",
    ]
    summary = " | ".join(parts)
    return summary[: limit - 3] + "..." if len(summary) > limit else summary


def extract_label_fields(text: str) -> dict:
    normalized = normalize_text(text)

    chave_nfe = extract_nfe_key_from_label(text)
    chave_info = parse_nfe_access_key(chave_nfe)
    nf = extract_nf_number_from_label(text)
    serie = _search([r"\bSERIE\s*[:#]?\s*(\d{1,3})\b"], normalized, flags=0) or chave_info.get("serie", "")
    cep = extract_cep_from_label(text)
    destinatario = extract_recipient_from_label(text)
    pedido = _search(
        [
            r"\bORDER\s+ID\s*[:#]?\s*([0-9]{3}-[0-9]{7}-[0-9]{7})",
            r"\bPEDIDO\s+SHOPEE\s*[:#]?\s*([A-Z0-9]{8,30})",
            r"\bPEDIDO\s*[:#]?\s*([A-Z0-9]{8,30})",
        ],
        normalized,
        flags=0,
    )
    rastreio = _search(
        [
            r"\bRASTREIO\s*[:#]?\s*([A-Z]{1,3}\d{8,20}[A-Z]{0,3})",
            r"\bCODIGO\s*[:#]?\s*([A-Z]{1,3}\d{8,20}[A-Z]{0,3})",
            r"\b(TBR\d{8,20})\b",
            r"\b([A-Z]{2,4}\d{8,20}[A-Z]{0,3})\b",
        ],
        normalized,
        flags=0,
    )

    uf = ""
    cidade = ""
    city_match = re.search(r"\bCIDADE\s*[:#]?\s*([^\n\r]+?)\s*[-/]\s*([A-Z]{2})", text, re.IGNORECASE)
    if city_match:
        cidade = normalize_text(city_match.group(1))
        uf = normalize_text(city_match.group(2))

    emissao_raw = _search([r"\bEMISSAO\s*[:#]?\s*([0-9/\-:\s]{10,20})"], normalized, flags=0)

    fields = {
        "numero_nf": nf,
        "serie": serie,
        "chave_nfe": chave_nfe,
        "chave_nfe_info": chave_info,
        "chave_nfe_cuf": chave_info.get("cuf", ""),
        "chave_nfe_cnpj": chave_info.get("cnpj", ""),
        "chave_nfe_modelo": chave_info.get("modelo", ""),
        "chave_nfe_codigo_numerico": chave_info.get("codigo_numerico", ""),
        "cep": cep,
        "destinatario": destinatario,
        "pedido_shopee": pedido,
        "rastreio": rastreio,
        "cidade": cidade,
        "uf": uf,
        "data_emissao": emissao_raw,
        "data_emissao_dt": parse_datetime(emissao_raw),
        "raw_text": text,
    }
    fields["ocr_summary"] = summarize_ocr_text(fields)
    return fields


def read_label(file: str | Path) -> dict:
    path = Path(file)
    text = extract_text_from_label(path)
    fields = extract_label_fields(text)
    fields["source_file"] = path.name
    fields["source_path"] = str(path)
    fields["source_page"] = ""

    print(f"[LABEL] arquivo={path.name}")
    print(f"[LABEL] texto_ocr={text}")
    print(f"[LABEL] nf={fields.get('numero_nf', '')}")
    print(f"[LABEL] chave_nfe={fields.get('chave_nfe', '')}")
    print(f"[LABEL] cep={fields.get('cep', '')}")
    print(f"[LABEL] rastreio={fields.get('rastreio', '')}")
    return fields


def read_labels(file: str | Path) -> list[dict]:
    path = Path(file)
    texts = extract_texts_from_label_file(path, force_pdf_ocr=True)
    labels = []

    for index, text in enumerate(texts, start=1):
        fields = extract_label_fields(text)
        fields["source_file"] = f"{path.name} - pagina {index}" if len(texts) > 1 else path.name
        fields["source_path"] = str(path)
        fields["source_page"] = index if len(texts) > 1 else ""
        labels.append(fields)

        print(f"[LABEL] arquivo={fields['source_file']}")
        print(f"[LABEL] texto_ocr={text}")
        print(f"[LABEL] nf={fields.get('numero_nf', '')}")
        print(f"[LABEL] chave_nfe={fields.get('chave_nfe', '')}")
        print(f"[LABEL] cep={fields.get('cep', '')}")
        print(f"[LABEL] rastreio={fields.get('rastreio', '')}")

    return labels
