from PIL import Image, ImageDraw, ImageFont

TAPE_WIDTH_PX = 96     # 12mm at 203 DPI
LABEL_LENGTH_PX = 320  # default label length (~40mm)
BYTES_PER_ROW = TAPE_WIDTH_PX // 8  # 12

_SYSTEM_FONTS = [
    # macOS
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    # Windows
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
]


def _try_load_font(custom_path, size):
    paths = [custom_path] + _SYSTEM_FONTS if custom_path else _SYSTEM_FONTS
    for path in paths:
        if not path:
            continue
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _auto_size_font(draw, text, max_w, max_h, font_path=None):
    for size in range(80, 6, -2):
        font = _try_load_font(font_path, size)
        bbox = draw.multiline_textbbox((0, 0), text, font=font, anchor="lt")
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w <= max_w and h <= max_h:
            return font
    return ImageFont.load_default()


def create_label_image(text: str, font_path: str = None, font_size: int = None) -> Image.Image:
    """Return a 96×320 px grayscale label image ready to pack for the printer."""
    # Work in landscape orientation (as you'd read the label)
    canvas = Image.new("L", (LABEL_LENGTH_PX, TAPE_WIDTH_PX), 255)
    draw = ImageDraw.Draw(canvas)

    padding = 8
    max_w = LABEL_LENGTH_PX - padding * 2
    max_h = TAPE_WIDTH_PX - padding * 2

    if font_size is not None:
        font = _try_load_font(font_path, font_size)
    else:
        font = _auto_size_font(draw, text, max_w, max_h, font_path)

    draw.multiline_text(
        (LABEL_LENGTH_PX // 2, TAPE_WIDTH_PX // 2),
        text,
        fill=0,
        font=font,
        anchor="mm",
        align="center",
    )

    # Rotate 90° CCW → portrait (96 wide × 320 tall) for printer
    return canvas.rotate(90, expand=True)


def image_to_bytes(img: Image.Image) -> bytes:
    """Pack a 96×320 grayscale image into printer raster bytes (MSB-first, 1=black)."""
    if img.size != (TAPE_WIDTH_PX, LABEL_LENGTH_PX):
        img = img.resize((TAPE_WIDTH_PX, LABEL_LENGTH_PX), Image.LANCZOS)

    gray = img.convert("L")
    result = bytearray()

    for y in range(LABEL_LENGTH_PX):
        for x_byte in range(BYTES_PER_ROW):
            byte = 0
            for bit in range(8):
                x = x_byte * 8 + bit
                if gray.getpixel((x, y)) < 128:  # dark pixel = print
                    byte |= 1 << (7 - bit)
            result.append(byte)

    return bytes(result)
