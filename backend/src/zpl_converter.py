from __future__ import annotations

from pathlib import Path


def convert_zpl_to_image(zpl_file: str | Path, output_dir: str | Path | None = None) -> Path | None:
    """Convert ZPL to an image and return the generated path.

    MVP placeholder. This is where Labelary API or a local renderer should be
    integrated for labels that contain compressed images such as :Z64: blocks.
    Returning None tells the caller to continue with text extraction fallback.
    """
    _ = Path(zpl_file)
    _ = Path(output_dir) if output_dir else None
    return None
