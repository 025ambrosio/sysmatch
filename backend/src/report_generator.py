from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


def save_reports(rows: list[dict], output_dir: str | Path) -> tuple[Path, Path]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = path / f"conciliacao_{timestamp}.csv"
    xlsx_path = path / f"conciliacao_{timestamp}.xlsx"

    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False)
    return csv_path, xlsx_path
