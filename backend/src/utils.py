from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import unicodedata


OUTPUT_SUBDIRS = {
    "conciliados": "conciliados",
    "revisar": "revisar",
    "pendentes": "pendentes",
    "relatorios": "relatorios",
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFD", str(value))
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = value.upper()
    value = re.sub(r"[^A-Z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_cep(value: str | None) -> str:
    if not value:
        return ""
    digits = re.sub(r"\D", "", str(value))
    return digits[:8]


def only_digits(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\D", "", str(value))


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    candidates = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ]
    raw = value.strip()
    for fmt in candidates:
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.replace(tzinfo=None)
        except ValueError:
            continue
    return None


def ensure_output_dirs(base_dir: Path) -> dict[str, Path]:
    dirs = {}
    for key, folder_name in OUTPUT_SUBDIRS.items():
        path = base_dir / folder_name
        path.mkdir(parents=True, exist_ok=True)
        dirs[key] = path
    return dirs
