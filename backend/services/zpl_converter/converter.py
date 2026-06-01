from __future__ import annotations

from dataclasses import dataclass, field
import base64
import re
import zlib

from reportlab.graphics.barcode import code128
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from PIL import Image


TOKEN_RE = re.compile(r"\^([A-Z0-9]{1,2})([^^]*)", re.IGNORECASE | re.DOTALL)
GRAPHIC_RE = re.compile(
    r"[\^~]DG([^,]+),(\d+),(\d+),(.+?)(?=(?:[\^~]DG)|(?:\^XA)|\Z)",
    re.IGNORECASE | re.DOTALL,
)
UNSUPPORTED_IMPORTANT = {"GF", "BQ", "BX", "B3", "B7", "BD", "BQN"}
DELETE_GRAPHIC_RE = re.compile(r"\^ID([^,^]+)", re.IGNORECASE)


@dataclass
class RenderSettings:
    width_mm: float = 100
    height_mm: float = 150
    dpi: int = 203

    @property
    def page_width(self) -> float:
        return self.width_mm * mm

    @property
    def page_height(self) -> float:
        return self.height_mm * mm

    def dots_to_pt(self, value: int | float) -> float:
        return (float(value) / max(self.dpi, 1)) * 25.4 * mm


@dataclass
class RenderResult:
    converted: bool
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class GraphicAsset:
    name: str
    image: Image.Image
    width_dots: int
    height_dots: int


@dataclass
class _State:
    x: int = 0
    y: int = 0
    font_h: int = 28
    font_w: int = 24
    barcode_height: int = 100
    pending_barcode: bool = False
    field_data: str = ""
    drawn: int = 0
    unsupported: set[str] = field(default_factory=set)


def _numbers(value: str) -> list[int]:
    found = re.findall(r"-?\d+", value or "")
    return [int(item) for item in found]


def _clean_field_data(value: str) -> str:
    return (value or "").replace("\\&", "\n").replace("^", "").strip()


def _normalize_graphic_name(value: str) -> str:
    return (value or "").strip().upper().replace("\\", "/")


def _decode_hex_graphic(data: str, total_bytes: int) -> bytes:
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", data or "")
    if len(cleaned) % 2:
        cleaned = cleaned[:-1]
    raw = bytes.fromhex(cleaned) if cleaned else b""
    return raw[:total_bytes]


def _decode_z64_graphic(data: str, total_bytes: int) -> bytes:
    match = re.search(r":Z64:([^:^\s]+)", data or "", flags=re.IGNORECASE)
    if not match:
        return _decode_hex_graphic(data, total_bytes)
    compressed = base64.b64decode(match.group(1))
    raw = zlib.decompress(compressed)
    return raw[:total_bytes]


def _graphic_bytes_to_image(raw: bytes, bytes_per_row: int, total_bytes: int) -> Image.Image:
    if bytes_per_row <= 0:
        raise ValueError("bytes_per_row invalido no grafico ZPL.")
    rows = max(1, total_bytes // bytes_per_row)
    width = bytes_per_row * 8
    image = Image.new("1", (width, rows), 1)
    pixels = image.load()
    for y in range(rows):
        row_start = y * bytes_per_row
        for byte_index in range(bytes_per_row):
            if row_start + byte_index >= len(raw):
                continue
            value = raw[row_start + byte_index]
            for bit in range(8):
                if value & (0x80 >> bit):
                    pixels[(byte_index * 8) + bit, y] = 0
    return image.convert("L")


def parse_graphic_assets(content: str) -> tuple[dict[str, GraphicAsset], list[str]]:
    assets: dict[str, GraphicAsset] = {}
    warnings: list[str] = []
    for match in GRAPHIC_RE.finditer(content or ""):
        name = _normalize_graphic_name(match.group(1))
        total_bytes = int(match.group(2))
        bytes_per_row = int(match.group(3))
        data = match.group(4).strip()
        try:
            raw = _decode_z64_graphic(data, total_bytes) if ":Z64:" in data.upper() else _decode_hex_graphic(data, total_bytes)
            image = _graphic_bytes_to_image(raw, bytes_per_row, total_bytes)
            assets[name] = GraphicAsset(
                name=name,
                image=image,
                width_dots=bytes_per_row * 8,
                height_dots=max(1, total_bytes // bytes_per_row),
            )
        except Exception as exc:  # noqa: BLE001 - report bad graphics without stopping the file.
            warnings.append(f"Grafico ZPL {name or 'sem_nome'} nao pode ser decodificado: {exc}")
    return assets, warnings


def update_graphic_assets(
    graphics: dict[str, GraphicAsset],
    content: str,
) -> tuple[dict[str, GraphicAsset], list[str]]:
    next_graphics = dict(graphics)
    parsed, warnings = parse_graphic_assets(content)
    next_graphics.update(parsed)
    for match in DELETE_GRAPHIC_RE.finditer(content or ""):
        name = _normalize_graphic_name(match.group(1))
        next_graphics.pop(name, None)
    return next_graphics, warnings


def _y_from_top(settings: RenderSettings, zpl_y: int, height_pt: float = 0) -> float:
    return settings.page_height - settings.dots_to_pt(zpl_y) - height_pt


def _draw_text(c: Canvas, settings: RenderSettings, state: _State, text: str) -> None:
    font_size = max(5, settings.dots_to_pt(state.font_h) * 0.82)
    leading = max(font_size * 1.08, settings.dots_to_pt(state.font_h))
    x = settings.dots_to_pt(state.x)
    y = _y_from_top(settings, state.y, font_size)
    c.setFont("Helvetica", font_size)
    for line in (text.splitlines() or [""]):
        c.drawString(x, y, line[:180])
        y -= leading
    state.drawn += 1


def _draw_barcode(c: Canvas, settings: RenderSettings, state: _State, value: str) -> None:
    value = value.strip()
    if not value:
        return
    height = max(settings.dots_to_pt(state.barcode_height), 8 * mm)
    barcode = code128.Code128(value, barHeight=height, humanReadable=False)
    x = settings.dots_to_pt(state.x)
    y = _y_from_top(settings, state.y, height)
    max_width = settings.page_width - x - (2 * mm)
    scale = min(max_width / barcode.width, 1.8) if barcode.width else 1
    c.saveState()
    c.translate(x, y)
    c.scale(max(scale, 0.35), 1)
    barcode.drawOn(c, 0, 0)
    c.restoreState()
    c.setFont("Helvetica", 7)
    c.drawCentredString(x + min(barcode.width * scale, max_width) / 2, y - 9, value[:80])
    state.drawn += 1


def _draw_box(c: Canvas, settings: RenderSettings, state: _State, args: str) -> None:
    nums = _numbers(args)
    if len(nums) < 2:
        return
    width = settings.dots_to_pt(max(nums[0], 1))
    height = settings.dots_to_pt(max(nums[1], 1))
    thickness = settings.dots_to_pt(max(nums[2] if len(nums) >= 3 else 2, 1))
    x = settings.dots_to_pt(state.x)
    y = _y_from_top(settings, state.y, height)
    c.setLineWidth(thickness)
    if height <= thickness * 1.5:
        c.line(x, y, x + width, y)
    elif width <= thickness * 1.5:
        c.line(x, y, x, y + height)
    else:
        c.rect(x, y, width, height, stroke=1, fill=0)
    state.drawn += 1


def _draw_graphic(
    c: Canvas,
    settings: RenderSettings,
    state: _State,
    args: str,
    graphics: dict[str, GraphicAsset],
) -> bool:
    parts = [part.strip() for part in (args or "").split(",")]
    name = _normalize_graphic_name(parts[0] if parts else "")
    asset = graphics.get(name)
    if not asset:
        return False
    x_mul = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 1
    y_mul = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 1
    width = settings.dots_to_pt(asset.width_dots * max(x_mul, 1))
    height = settings.dots_to_pt(asset.height_dots * max(y_mul, 1))
    x = settings.dots_to_pt(state.x)
    y = _y_from_top(settings, state.y, height)
    c.drawImage(ImageReader(asset.image), x, y, width=width, height=height, mask="auto")
    state.drawn += 1
    return True


def render_label_on_canvas(
    c: Canvas,
    zpl: str,
    settings: RenderSettings,
    label_index: int,
    graphics: dict[str, GraphicAsset] | None = None,
) -> RenderResult:
    state = _State()
    warnings: list[str] = []
    graphics = graphics or {}

    try:
        for raw_cmd, args in TOKEN_RE.findall(zpl or ""):
            cmd = raw_cmd.upper()
            args = (args or "").strip()

            if cmd in {"XA", "XZ", "FS", "CI", "LH", "LT", "LS", "PW", "LL", "PR", "MD", "MM", "MN"}:
                continue
            if cmd in {"FO", "FT"}:
                nums = _numbers(args)
                if len(nums) >= 2:
                    state.x, state.y = max(nums[0], 0), max(nums[1], 0)
                continue
            if cmd.startswith("A"):
                nums = _numbers(args)
                if len(nums) >= 2:
                    state.font_h = max(nums[-2], 8)
                    state.font_w = max(nums[-1], 8)
                elif nums:
                    state.font_h = max(nums[-1], 8)
                continue
            if cmd == "BY":
                nums = _numbers(args)
                if len(nums) >= 3:
                    state.barcode_height = max(nums[2], 20)
                continue
            if cmd == "BC":
                nums = _numbers(args)
                if nums:
                    state.barcode_height = max(nums[0], 20)
                state.pending_barcode = True
                continue
            if cmd == "GB":
                _draw_box(c, settings, state, args)
                continue
            if cmd == "XG":
                if not _draw_graphic(c, settings, state, args, graphics):
                    state.unsupported.add(f"XG:{_normalize_graphic_name(args.split(',')[0])}")
                continue
            if cmd == "FD":
                state.field_data = _clean_field_data(args)
                if state.pending_barcode:
                    _draw_barcode(c, settings, state, state.field_data)
                    state.pending_barcode = False
                else:
                    _draw_text(c, settings, state, state.field_data)
                continue
            if cmd in UNSUPPORTED_IMPORTANT or cmd.startswith("B"):
                state.unsupported.add(cmd)

        if state.unsupported:
            warnings.append(
                f"Etiqueta {label_index}: comando(s) ZPL com suporte limitado: "
                + ", ".join(sorted(state.unsupported))
            )
        if state.drawn == 0:
            return RenderResult(
                converted=False,
                warnings=warnings,
                error="Nenhum elemento renderizavel suportado foi encontrado na etiqueta.",
            )
        return RenderResult(converted=True, warnings=warnings)
    except Exception as exc:  # noqa: BLE001 - keep batch conversion resilient.
        return RenderResult(converted=False, warnings=warnings, error=str(exc))
