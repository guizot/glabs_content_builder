"""
Text utilities — font loading, text wrapping, and drawing text blocks.
"""

import os
from PIL import ImageFont, ImageDraw

# Base directory: go up from src/features/canvas_feature/ → src/features/ → src/ → project root → assets/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

# Font file mapping
FONT_FILES = {
    "poppins_light": "Poppins-Light.ttf",
    "poppins_regular": "Poppins-Regular.ttf",
    "poppins_medium": "Poppins-Medium.ttf",
    "poppins_semibold": "Poppins-SemiBold.ttf",
    "poppins_bold": "Poppins-Bold.ttf",
    "inter": "Inter-Variable.ttf",
}


def load_font(name: str = "poppins_regular", size: int = 40) -> ImageFont.FreeTypeFont:
    """
    Load a font by its shorthand name and size.
    Falls back to default if not found.
    """
    filename = FONT_FILES.get(name)
    if filename is None:
        raise ValueError(
            f"Unknown font '{name}'. Available: {', '.join(FONT_FILES.keys())}"
        )

    font_path = os.path.join(FONTS_DIR, filename)
    if not os.path.exists(font_path):
        print(f"  ⚠️  Font file not found: {font_path}, using default")
        return ImageFont.load_default()

    return ImageFont.truetype(font_path, size)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """
    Word-wrap text to fit within max_width pixels.
    Returns a list of lines.
    """
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = font.getbbox(test_line)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def get_text_height(
    lines: list[str], font: ImageFont.FreeTypeFont, line_spacing: int = 10
) -> int:
    """Calculate total height of a block of wrapped text."""
    if not lines:
        return 0

    total = 0
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        total += bbox[3] - bbox[1]
        if i < len(lines) - 1:
            total += line_spacing

    return total


def draw_text_block(
    draw: ImageDraw.Draw,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    color: str = "#FFFFFF",
    line_spacing: int = 10,
    align: str = "left",
    max_width: int = None,
) -> int:
    """
    Draw a block of pre-wrapped text lines.
    Returns the y position after the last line.

    align: "left", "center", or "right"
    max_width: required for center/right alignment
    """
    current_y = y

    for line in lines:
        bbox = font.getbbox(line)
        line_height = bbox[3] - bbox[1]
        line_width = bbox[2] - bbox[0]

        if align == "center" and max_width:
            draw_x = x + (max_width - line_width) // 2
        elif align == "right" and max_width:
            draw_x = x + max_width - line_width
        else:
            draw_x = x

        draw.text((draw_x, current_y), line, fill=color, font=font)
        current_y += line_height + line_spacing

    return current_y
