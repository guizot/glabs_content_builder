"""
Canvas utilities — create base images, draw gradients, save output.
"""

from PIL import Image, ImageDraw


def create_canvas(width: int, height: int, bg_color: str = "#000000") -> Image.Image:
    """Create a new RGBA canvas with a solid background color."""
    img = Image.new("RGBA", (width, height), bg_color)
    return img


def draw_vertical_gradient(
    img: Image.Image,
    color_top: tuple,
    color_bottom: tuple,
) -> Image.Image:
    """
    Draw a smooth vertical gradient from color_top to color_bottom
    directly onto the given image.
    """
    width, height = img.size
    draw = ImageDraw.Draw(img)

    for y in range(height):
        ratio = y / height
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    return img


def draw_rounded_rect(
    draw: ImageDraw.Draw,
    xy: tuple,
    radius: int,
    fill: str = None,
    outline: str = None,
    width: int = 1,
):
    """Draw a rounded rectangle. xy = (x0, y0, x1, y1)."""
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def save_image(img: Image.Image, path: str, quality: int = 95):
    """Save image as PNG (ignoring quality for PNG) or JPG."""
    if path.lower().endswith(".jpg") or path.lower().endswith(".jpeg"):
        img = img.convert("RGB")
        img.save(path, "JPEG", quality=quality)
    else:
        img.save(path, "PNG")
    print(f"  ✅ Saved: {path}")
