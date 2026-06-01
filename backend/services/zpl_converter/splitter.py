from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass
class SplitResult:
    labels: list[str]
    warnings: list[str]


LABEL_RE = re.compile(r"\^XA.*?\^XZ", re.IGNORECASE | re.DOTALL)
PRINTABLE_RE = re.compile(r"\^(FD|GB|BC|XG|GF|BQ|BX|B3|B7|BD)", re.IGNORECASE)


def split_zpl_labels(content: str) -> SplitResult:
    text = (content or "").strip()
    if not text:
        return SplitResult([], ["Arquivo vazio."])

    raw_labels = [match.group(0).strip() for match in LABEL_RE.finditer(text) if match.group(0).strip()]
    labels = [label for label in raw_labels if PRINTABLE_RE.search(label)]
    warnings: list[str] = []

    xa_count = len(re.findall(r"\^XA", text, flags=re.IGNORECASE))
    xz_count = len(re.findall(r"\^XZ", text, flags=re.IGNORECASE))
    ignored = len(raw_labels) - len(labels)
    if ignored:
        warnings.append(f"{ignored} bloco(s) ZPL de controle foram ignorados por nao conterem conteudo imprimivel.")
    if xa_count > len(raw_labels):
        warnings.append("Ha bloco(s) com ^XA sem fechamento ^XZ.")
    if xz_count > len(raw_labels):
        warnings.append("Ha fechamento(s) ^XZ sem abertura ^XA correspondente.")
    if not labels:
        if "^XA" not in text.upper():
            warnings.append("Nenhum inicio de etiqueta ^XA foi encontrado.")
        if "^XZ" not in text.upper():
            warnings.append("Nenhum fim de etiqueta ^XZ foi encontrado.")
        warnings.append("Arquivo sem blocos ZPL validos no formato ^XA ... ^XZ.")

    return SplitResult(labels, warnings)
