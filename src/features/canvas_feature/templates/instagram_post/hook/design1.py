"""
Instagram Post — Hook Template — Design 1
Style: Minimalist Light, left-aligned hook text,
       'guizot labs' branding in top-left.
       Article image displayed as rectangle above title.
Optimized for 1080x1350 (4:5) ratio.
"""

import os
from PIL import Image, ImageDraw
from src.features.canvas_feature.canvas import create_canvas
from src.features.canvas_feature.text_utils import load_font, wrap_text, draw_text_block, get_text_height


class HookDesign1:
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
        bg_color = "#FFFFFF"
        img = create_canvas(self.width, self.height, bg_color)
        draw = ImageDraw.Draw(img)

        text_dark = "#000000"
        padding_x = 80
        padding_y = 80

        # --- Branding: 'guizot labs' (Top-Left) ---
        brand_font_bold = load_font("poppins_semibold", 46)
        draw.text((padding_x, padding_y), "guizot", fill=text_dark, font=brand_font_bold)
        
        brand_w_guizot = draw.textlength("guizot", font=brand_font_bold)
        brand_font_reg = load_font("poppins_regular", 46)
        draw.text((padding_x + brand_w_guizot + 8, padding_y), "labs", fill=text_dark, font=brand_font_reg)

        # --- Separator Line ---
        sep_y = padding_y + 95
        draw.line([padding_x, sep_y, self.width - padding_x, sep_y], fill=text_dark, width=1)

        # --- Footer Text (calculate early to know available space) ---
        footer_font = load_font("poppins_regular", 32)
        footer_y = self.height - 130


        # --- Hook text ---
        hook_text = self.content.get("hook_text", "Your Hook Text Here")
        text_area_width = self.width - (padding_x * 2)
        font_size = 72
        font = load_font("poppins_semibold", font_size)
        lines = wrap_text(hook_text, font, text_area_width)
        text_height = get_text_height(lines, font, line_spacing=8)

        # --- Article Image (above hook text) ---
        content_top = sep_y + 35
        content_bottom = footer_y - 20
        available_height = content_bottom - content_top

        article_img = self._load_article_image(
            max_width=self.width - (padding_x * 2),
            max_height=int(available_height - text_height - 35)
        )

        if article_img:
            img_x = padding_x
            img_y = content_top
            img.paste(article_img, (img_x, img_y), article_img)

            # Hook text below image
            text_y = img_y + article_img.height + 28
        else:
            # Center hook text vertically in available space
            text_y = content_top + (available_height - text_height) // 2

        draw_text_block(
            draw, lines, font,
            x=padding_x, y=text_y,
            color=text_dark, line_spacing=8, align="left",
        )

        # --- Footer ---
        # Bottom left
        draw.text((padding_x, footer_y), "@glabs.ai", fill=text_dark, font=footer_font)

        # Bottom right: Swipe ->
        swipe_text = "Swipe"
        swipe_w = draw.textlength(swipe_text, font=footer_font)
        arrow_gap = 12
        arrow_len = 40
        arrow_head = 10
        total_swipe_w = swipe_w + arrow_gap + arrow_len

        swipe_x = self.width - padding_x - total_swipe_w
        draw.text((swipe_x, footer_y), swipe_text, fill=text_dark, font=footer_font)

        # Arrow
        bbox = draw.textbbox((0, 0), "S", font=footer_font)
        arrow_y = footer_y + (bbox[3] - bbox[1]) // 2 + bbox[1]
        
        arrow_start_x = swipe_x + swipe_w + arrow_gap
        arrow_end_x = arrow_start_x + arrow_len

        line_w = 2
        draw.line([arrow_start_x, arrow_y, arrow_end_x, arrow_y], fill=text_dark, width=line_w)
        draw.line([arrow_end_x - arrow_head, arrow_y - arrow_head + 3, arrow_end_x, arrow_y], fill=text_dark, width=line_w)
        draw.line([arrow_end_x - arrow_head, arrow_y + arrow_head - 3, arrow_end_x, arrow_y], fill=text_dark, width=line_w)

        return img
