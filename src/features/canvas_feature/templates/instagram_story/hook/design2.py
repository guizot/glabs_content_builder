"""
Instagram Story — Hook Template — Design 2
Style: Minimalist Dark, left-aligned hook text,
       'guizot labs' branding in top-left.
       Article image displayed as rectangle above title.
Optimized for 1080x1920 (9:16) ratio.
"""

import os
from PIL import Image, ImageDraw
from src.features.canvas_feature.canvas import create_canvas
from src.features.canvas_feature.text_utils import load_font, wrap_text, draw_text_block, get_text_height


class HookDesign2:
    def __init__(self, ratio: dict, content: dict):
        self.width = ratio["width"]
        self.height = ratio["height"]
        self.content = content

    def _load_article_image(self, max_width: int, max_height: int) -> Image.Image | None:
        """Load the article image, always fill max_width (cover-fit), capped at max_height."""
        image_path = self.content.get("image_path")
        if not image_path or not os.path.exists(image_path):
            return None

        try:
            img = Image.open(image_path).convert("RGBA")

            # Always scale to fill max_width
            scale = max_width / img.width
            new_width = max_width
            new_height = int(img.height * scale)

            # Cap height — if too tall, crop vertically
            if new_height > max_height:
                img = img.resize((new_width, new_height), Image.LANCZOS)
                # Center crop vertically
                top = (new_height - max_height) // 2
                img = img.crop((0, top, max_width, top + max_height))
            else:
                img = img.resize((new_width, new_height), Image.LANCZOS)

            return img
        except Exception as e:
            print(f"  ⚠️ Warning: Could not load article image: {e}")
            return None

    def render(self) -> Image.Image:
        # --- Background: Deep Black ---
        bg_color = "#000000"
        img = create_canvas(self.width, self.height, bg_color)
        draw = ImageDraw.Draw(img)

        text_white = "#FFFFFF"
        padding_x = 90
        padding_y = 150

        # --- Branding: 'guizot labs' (Top-Left) ---
        brand_font_bold = load_font("poppins_semibold", 48)
        draw.text((padding_x, padding_y), "guizot", fill=text_white, font=brand_font_bold)
        
        brand_w_guizot = draw.textlength("guizot", font=brand_font_bold)
        brand_font_reg = load_font("poppins_regular", 48)
        draw.text((padding_x + brand_w_guizot + 10, padding_y), "labs", fill=text_white, font=brand_font_reg)

        # --- Separator Line ---
        sep_y = padding_y + 100
        draw.line([padding_x, sep_y, self.width - padding_x, sep_y], fill=text_white, width=1)

        # --- Footer Text (calculate early to know available space) ---
        footer_font = load_font("poppins_regular", 38)
        footer_y = self.height - 220

        # --- Accent decoration: Corner accents ---
        accent_len = 50
        accent_thickness = 3
        draw.line([self.width - 90, self.height - 170 - accent_len, self.width - 90, self.height - 170], fill=text_white, width=accent_thickness)
        draw.line([self.width - 90 - accent_len, self.height - 170, self.width - 90, self.height - 170], fill=text_white, width=accent_thickness)

        # --- Hook text ---
        hook_text = self.content.get("hook_text", "Your Hook Text Here")
        text_area_width = self.width - (padding_x * 2)
        font_size = 76
        font = load_font("poppins_semibold", font_size)
        lines = wrap_text(hook_text, font, text_area_width)
        text_height = get_text_height(lines, font, line_spacing=10)

        # --- Article Image (above hook text) ---
        content_top = sep_y + 40
        content_bottom = footer_y - 30
        available_height = content_bottom - content_top

        article_img = self._load_article_image(
            max_width=self.width - (padding_x * 2),
            max_height=int(available_height - text_height - 40)
        )

        if article_img:
            img_x = padding_x
            img_y = content_top
            img.paste(article_img, (img_x, img_y), article_img)

            # Hook text below image
            text_y = img_y + article_img.height + 32
        else:
            # Center hook text vertically in available space
            text_y = content_top + (available_height - text_height) // 2

        draw_text_block(
            draw, lines, font,
            x=padding_x, y=text_y,
            color=text_white, line_spacing=10, align="left",
        )

        # --- Footer ---
        draw.text((padding_x, footer_y), "guizot.framer.ai", fill=text_white, font=footer_font)

        return img
