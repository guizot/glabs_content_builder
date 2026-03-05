import os
from typing import List, Dict, Any
from PIL import Image, ImageDraw

from src.features.base_feature import BaseFeature
from src.features.canvas_feature.ratios import get_ratio
from src.features.canvas_feature.template_registry import get_design_class

# --- Canvas Utilities ---

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

# --- Validator Utilities ---

LIMITS = {
    # --- Instagram Post (1080x1350) ---
    ("instagram_post", "hook"):    {"hook_text": 120},
    ("instagram_post", "content"): {"title": 80, "description": 400},

    # --- Instagram Story (1080x1920) ---
    ("instagram_story", "hook"):    {"hook_text": 150},
    ("instagram_story", "content"): {"title": 100, "description": 550},

    # --- Instagram Feed (1080x1080) ---
    ("instagram_feed", "hook"):    {"hook_text": 100},
    ("instagram_feed", "content"): {"title": 70, "description": 350},

    # --- CTA (all ratios) ---
    ("instagram_post", "cta"):  {"subtitle": 30, "cta_text": 70},
    ("instagram_story", "cta"): {"subtitle": 30, "cta_text": 85},
    ("instagram_feed", "cta"):  {"subtitle": 30, "cta_text": 60},
}


def validate_content(ratio: str, template: str, content: dict, item_name: str = "") -> dict:
    """
    Validate content fields against character limits.
    Truncates with '…' and prints a warning for any overflow.
    Returns the cleaned content dict (original is not mutated).
    """
    limits = LIMITS.get((ratio, template))
    if not limits:
        return content

    cleaned = dict(content)
    prefix = f"  ⚠️  [{item_name}] " if item_name else "  ⚠️  "

    for field, max_chars in limits.items():
        value = cleaned.get(field, "")
        if len(value) > max_chars:
            print(
                f"{prefix}'{field}' exceeds {max_chars} chars "
                f"({len(value)} chars). Note: Text might overflow."
            )

    return cleaned


class CanvasFeature(BaseFeature):
    """
    CanvasFeature takes a list of JSON-defined items (from LLMFeature or a file),
    validates constraints, delegates to the correct template layout logic,
    and returns a list of resulting file paths where the images are saved.
    """
    
    def execute(self, items: List[Dict[str, Any]], output_dir: str = "outputs") -> List[str]:
        """
        Inputs:
            - items (List[Dict]): A batch of content pieces.
            - output_dir (str): output target directory for generated images.
        Outputs:
            - A list of output paths generated during execution.
        """
        if not isinstance(items, list):
            items = [items]

        os.makedirs(output_dir, exist_ok=True)
        print(f"📦 Building {len(items)} image(s)...\n")

        output_paths = []

        for i, item in enumerate(items, start=1):
            try:
                ratio_name = item.get("ratio", "instagram_post")
                template_name = item.get("template", "hook")
                design_name = item.get("design", "design1")
                output_name = item.get("output_name", f"output_{i}")
                content = item.get("content", {})

                print(f"[{i}/{len(items)}] {output_name}")
                print(f"  Ratio: {ratio_name} | Template: {template_name} | Design: {design_name}")

                # Resolve ratio
                ratio = get_ratio(ratio_name)

                # Validate content fields
                content = validate_content(ratio_name, template_name, content, item_name=output_name)

                # Resolve design class (now ratio-aware)
                DesignClass = get_design_class(ratio_name, template_name, design_name)

                # Instantiate and render
                designer = DesignClass(ratio=ratio, content=content)
                img = designer.render()

                # Save
                output_path = os.path.join(output_dir, f"{output_name}.png")
                save_image(img, output_path)
                output_paths.append(output_path)
                print()

            except KeyError as e:
                # Strip extra quotes from KeyError message
                clean_error = str(e).strip("'")
                print(f"  ❌ Error: {clean_error}")
                print("  Skipping this item...\n")
            except Exception as e:
                print(f"  ❌ Unexpected Error: {str(e)}")
                print("  Skipping this item...\n")

        print(f"🎉 Done! Processed {len(items)} image(s). All successful ones saved to: {output_dir}/")
        
        return output_paths
