from __future__ import annotations

import re

try:
    from rapidfuzz import fuzz
except ImportError:
    from difflib import SequenceMatcher

    class _FallbackFuzz:
        @staticmethod
        def token_set_ratio(left: str, right: str) -> float:
            left_tokens = " ".join(sorted(set(left.split())))
            right_tokens = " ".join(sorted(set(right.split())))
            return SequenceMatcher(None, left_tokens, right_tokens).ratio() * 100

        @staticmethod
        def partial_ratio(left: str, right: str) -> float:
            if not left or not right:
                return 0
            short, long = (left, right) if len(left) <= len(right) else (right, left)
            best = 0.0
            window = max(len(short), 1)
            for start in range(0, max(len(long) - window + 1, 1)):
                chunk = long[start : start + window]
                best = max(best, SequenceMatcher(None, short, chunk).ratio() * 100)
            return best

    fuzz = _FallbackFuzz()

from .utils import normalize_cep, normalize_text, only_digits


AUTO_THRESHOLD = 80
REVIEW_THRESHOLD = 50


def _page_number(value) -> int | None:
    try:
        if value in ("", None):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _nf_variants(nfe_number: str) -> list[str]:
    nf = only_digits(nfe_number).lstrip("0")
    if not nf:
        return []

    variants = {nf}
    for size in (6, 9, 12):
        if len(nf) <= size:
            variants.add(nf.zfill(size))
    return sorted(variants, key=len, reverse=True)


def _set_label_nf_from_raw_ocr(label: dict, nfe_number: str) -> None:
    if label.get("numero_nf"):
        return

    label["numero_nf"] = only_digits(nfe_number).lstrip("0") or str(nfe_number).strip()
    summary = str(label.get("ocr_summary", ""))
    if summary:
        label["ocr_summary"] = re.sub(
            r"NF encontrada:\s*[^|]*",
            f"NF encontrada: {label['numero_nf']} ",
            summary,
            count=1,
        )


def _set_label_key_from_raw_ocr(label: dict, nfe: dict) -> None:
    chave = only_digits(nfe.get("chave_nfe", ""))
    if chave and not label.get("chave_nfe"):
        label["chave_nfe"] = chave

    nfe_number = only_digits(nfe.get("numero_nf", "")).lstrip("0")
    if nfe_number:
        _set_label_nf_from_raw_ocr(label, nfe_number)
        label.setdefault("chave_nfe_info", {})
        label["chave_nfe_info"]["numero_nf"] = nfe_number

    emitente = only_digits(nfe.get("emitente_documento", ""))
    if emitente and not label.get("chave_nfe_cnpj"):
        label["chave_nfe_cnpj"] = emitente

    summary = str(label.get("ocr_summary", ""))
    if summary and chave:
        label["ocr_summary"] = re.sub(
            r"Chave encontrada:\s*[^|]*",
            f"Chave encontrada: {chave} ",
            label["ocr_summary"],
            count=1,
        )


def _key_found_in_raw_ocr(nfe: dict, label: dict) -> tuple[bool, str]:
    nfe_key = only_digits(nfe.get("chave_nfe", ""))
    raw_text = str(label.get("raw_text", "") or "")
    if len(nfe_key) != 44 or not raw_text:
        return False, ""

    raw_digits = only_digits(raw_text)
    if nfe_key in raw_digits:
        _set_label_key_from_raw_ocr(label, nfe)
        return True, "Chave NF-e encontrada no texto bruto do OCR"

    key_prefix = nfe_key[:20]
    key_cnpj = nfe_key[6:20]
    long_sequences = []
    for match in re.finditer(r"(?:\d[\s:;.,\-]*){30,55}", raw_text):
        digits = only_digits(match.group(0))
        if len(digits) >= 30:
            long_sequences.append(digits)

    for digits in long_sequences:
        if key_prefix not in digits and key_cnpj not in digits:
            continue

        ratio = fuzz.ratio(nfe_key, digits)
        partial_ratio = fuzz.partial_ratio(nfe_key, digits)
        if ratio >= 94 or partial_ratio >= 92:
            _set_label_key_from_raw_ocr(label, nfe)
            return True, f"Chave NF-e provavelmente igual no OCR mesmo com falhas ({max(ratio, partial_ratio):.0f}%)"

    return False, ""


def _nf_found_in_raw_ocr(nfe: dict, label: dict) -> tuple[bool, str]:
    """Find the NF in OCR text even when regex extraction missed it.

    This is intentionally stricter than name/address matching: exact NF digits,
    zero-padded NF digits, or the same digits separated by OCR punctuation/spaces.
    It avoids guessing when OCR removed digits from the number.
    """
    nfe_number = str(nfe.get("numero_nf", "")).strip()
    raw_text = str(label.get("raw_text", "") or "")
    if not nfe_number or not raw_text:
        return False, ""

    nf = only_digits(nfe_number).lstrip("0")
    if len(nf) < 3:
        return False, ""

    digits_stream = only_digits(raw_text)
    for variant in _nf_variants(nf):
        if variant in digits_stream:
            _set_label_nf_from_raw_ocr(label, nf)
            if variant == nf:
                return True, "NF encontrada no texto bruto do OCR"
            return True, f"NF encontrada no OCR com zeros a esquerda ({variant})"

    spaced_pattern = r"\D*".join(re.escape(char) for char in nf)
    if re.search(spaced_pattern, raw_text):
        _set_label_nf_from_raw_ocr(label, nf)
        return True, "NF encontrada no OCR com espacos/pontuacao entre digitos"

    return False, ""


def score_match(nfe: dict, label: dict) -> tuple[int, list[str]]:
    nfe_number = str(nfe.get("numero_nf", "")).strip()
    label_number = str(label.get("numero_nf", "")).strip()
    nfe_emitente = str(nfe.get("emitente_documento", "")).strip()
    label_key_nf = str((label.get("chave_nfe_info") or {}).get("numero_nf", "")).strip()
    label_key_cnpj = str(label.get("chave_nfe_cnpj", "")).strip()

    if nfe_number and label_key_nf and nfe_number == label_key_nf and nfe_emitente and label_key_cnpj == nfe_emitente:
        return 100, ["Chave NF-e contem mesma NF e mesmo CNPJ emitente"]

    if nfe_number and label_number and nfe_number == label_number:
        return 100, ["NF igual: match automatico"]

    found_key_raw, raw_key_reason = _key_found_in_raw_ocr(nfe, label)
    if found_key_raw:
        return 100, [raw_key_reason]

    found_in_raw, raw_reason = _nf_found_in_raw_ocr(nfe, label)
    if found_in_raw:
        return 100, [raw_reason]

    score = 0
    reasons = []

    nfe_cep = normalize_cep(nfe.get("destinatario_cep"))
    label_cep = normalize_cep(label.get("cep"))
    if nfe_cep and label_cep and nfe_cep == label_cep:
        score += 40
        reasons.append("CEP igual")

    nfe_name = normalize_text(nfe.get("destinatario_nome"))
    label_name = normalize_text(label.get("destinatario"))
    if nfe_name and label_name:
        ratio = fuzz.token_set_ratio(nfe_name, label_name)
        if ratio >= 95:
            score += 50
            reasons.append(f"Nome praticamente igual ({ratio:.0f}%)")
        elif ratio >= 80:
            score += 30
            reasons.append(f"Nome parecido ({ratio:.0f}%)")

    nfe_address = normalize_text(nfe.get("destinatario_endereco"))
    label_text = normalize_text(label.get("raw_text"))
    if nfe_address and label_text:
        address_ratio = max(
            fuzz.partial_ratio(nfe_address, label_text),
            fuzz.token_set_ratio(nfe_address, label_text),
        )
        if address_ratio >= 70:
            score += 30
            reasons.append(f"Endereco parecido ({address_ratio:.0f}%)")
        elif address_ratio >= 60:
            score += 20
            reasons.append(f"Endereco parcialmente parecido ({address_ratio:.0f}%)")

    nfe_city = normalize_text(nfe.get("destinatario_cidade"))
    label_city = normalize_text(label.get("cidade"))
    if nfe_city and label_city:
        city_ratio = fuzz.token_set_ratio(nfe_city, label_city)
        if city_ratio >= 85:
            score += 30
            reasons.append(f"Cidade parecida ({city_ratio:.0f}%)")
    elif nfe_city and label_text:
        city_ratio = fuzz.partial_ratio(nfe_city, label_text)
        if city_ratio >= 85:
            score += 30
            reasons.append(f"Cidade encontrada no OCR ({city_ratio:.0f}%)")

    return score, reasons


def classify_score(score: int) -> str:
    if score >= AUTO_THRESHOLD:
        return "conciliado"
    if score >= REVIEW_THRESHOLD:
        return "revisar"
    return "pendente"


def _log_match_result(nfe: dict, label: dict, score: int, status: str, reasons: list[str]) -> None:
    print(
        "[MATCH] "
        f"nfe_nf={nfe.get('numero_nf', '')} "
        f"etiqueta={label.get('source_file', '')} "
        f"nf_etiqueta={label.get('numero_nf', '')} "
        f"chave_nfe_etiqueta={label.get('chave_nfe', '')} "
        f"score={score} "
        f"status={status} "
        f"motivo={'; '.join(reasons) if reasons else 'sem criterios suficientes'}"
    )


def _can_use_page_order_fallback(nfes: list[dict], labels: list[dict]) -> bool:
    if len(nfes) != len(labels) or not nfes:
        return False
    nfe_pages = [_page_number(nfe.get("source_page")) for nfe in nfes]
    label_pages = [_page_number(label.get("source_page")) for label in labels]
    if any(page is None for page in nfe_pages + label_pages):
        return False
    return sorted(nfe_pages) == sorted(label_pages)


def _is_conflicting_nf(nfe: dict, label: dict) -> bool:
    nfe_number = str(nfe.get("numero_nf", "")).strip()
    label_number = str(label.get("numero_nf", "")).strip()
    label_key_nf = str((label.get("chave_nfe_info") or {}).get("numero_nf", "")).strip()
    if nfe_number and label_number and nfe_number != label_number:
        return True
    if nfe_number and label_key_nf and nfe_number != label_key_nf:
        return True
    return False


def _find_available_label_by_page(nfe: dict, available_labels: list[dict]) -> dict | None:
    nfe_page = _page_number(nfe.get("source_page"))
    if nfe_page is None:
        return None

    candidates = [label for label in available_labels if _page_number(label.get("source_page")) == nfe_page]
    if len(candidates) != 1:
        return None

    label = candidates[0]
    if _is_conflicting_nf(nfe, label):
        return None
    return label


def _apply_page_order_fallback(results: list[dict], available_labels: list[dict], nfes: list[dict], labels: list[dict]) -> None:
    if not _can_use_page_order_fallback(nfes, labels):
        return

    label_by_page = {_page_number(label.get("source_page")): label for label in labels}
    used_by_conciliated = {
        id(result.get("label"))
        for result in results
        if result.get("status") == "conciliado" and (result.get("label") or {}).get("source_file")
    }

    for result in results:
        if result.get("status") == "conciliado":
            continue

        nfe = result.get("nfe") or {}
        if not nfe.get("source_file"):
            continue

        nfe_page = _page_number(nfe.get("source_page"))
        label = label_by_page.get(nfe_page) or _find_available_label_by_page(nfe, available_labels)
        if not label:
            continue
        if id(label) in used_by_conciliated:
            continue
        if nfe_page != _page_number(label.get("source_page")):
            continue
        if _is_conflicting_nf(nfe, label):
            continue

        result["label"] = label
        result["score"] = max(int(result.get("score") or 0), 85)
        result["status"] = "conciliado"
        result["reasons"] = ["Fallback por mesma pagina/ordem do lote apos OCR incompleto"]
        _log_match_result(nfe, label, result["score"], result["status"], result["reasons"])

    assigned_label_ids = {
        id(result.get("label"))
        for result in results
        if (result.get("label") or {}).get("source_file")
    }
    available_labels[:] = [label for label in labels if id(label) not in assigned_label_ids]


def match_nfes_to_labels(nfes: list[dict], labels: list[dict]) -> list[dict]:
    available_labels = labels.copy()
    results = []

    for nfe in nfes:
        best_label = None
        best_score = -1
        best_reasons: list[str] = []

        for label in available_labels:
            score, reasons = score_match(nfe, label)
            if score > best_score:
                best_label = label
                best_score = score
                best_reasons = reasons

        status = classify_score(best_score)
        matched_label = best_label or {}

        if status == "pendente":
            _log_match_result(nfe, matched_label, max(best_score, 0), status, best_reasons)
            matched_label = {}
            best_reasons = best_reasons if best_score > 0 else ["NF sem etiqueta correspondente"]
        elif best_label in available_labels:
            available_labels.remove(best_label)
            _log_match_result(nfe, matched_label, best_score, status, best_reasons)

        results.append(
            {
                "nfe": nfe,
                "label": matched_label,
                "score": max(best_score, 0),
                "reasons": best_reasons,
                "status": status,
            }
        )

    for label in available_labels:
        reason = "Etiqueta lida, mas nenhuma NF/DANFE correspondente foi enviada"
        print(
            "[MATCH] "
            f"etiqueta={label.get('source_file', '')} "
            f"nf_etiqueta={label.get('numero_nf', '')} "
            f"chave_nfe_etiqueta={label.get('chave_nfe', '')} "
            f"status=pendente motivo={reason}"
        )
        results.append(
            {
                "nfe": {},
                "label": label,
                "score": 0,
                "reasons": [reason],
                "status": "pendente",
            }
        )

    return results
