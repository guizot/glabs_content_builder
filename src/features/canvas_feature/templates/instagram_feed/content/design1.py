"""
Instagram Feed (Square) — Content Template — Design 1
Style: Minimalist Light, logo top-left,
       title + description below logo.
Optimized for 1080x1080 (1:1) ratio.
"""

from PIL import Image, ImageDraw
from src.features.canvas_feature.canvas import create_canvas
from src.features.canvas_feature.text_utils import load_font, wrap_text, draw_text_block, get_text_height


class ContentDesign1:
    def __init__(self, ratio: dict, content: dict):
        self.width = ratio["width"]
        self.height = ratio["height"]
        self.content = content

    def render(self) -> Image.Image:
        # --- Background: Deep Black ---
        bg_color = "#FFFFFF"
        img = create_canvas(self.width, self.height, bg_color)
        draw = ImageDraw.Draw(img)

        text_dark = "#000000"
        text_muted = "#555555"

        # --- Branding: 'guizot labs' (Top-Left) ---
        padding_x = 70
        padding_y = 70
        
        brand_font_bold = load_font("poppins_semibold", 44)
        draw.text((padding_x, padding_y), "guizot", fill=text_dark, font=brand_font_bold)
        
        brand_w_guizot = draw.textlength("guizot", font=brand_font_bold)
        brand_font_reg = load_font("poppins_regular", 44)
        draw.text((padding_x + brand_w_guizot + 8, padding_y), "labs", fill=text_dark, font=brand_font_reg)

        # --- Separator Line ---
        draw.line([padding_x, padding_y + 90, self.width - padding_x, padding_y + 90], fill=text_dark, width=1)

        # --- Layout ---
        content_y = padding_y + 155
        text_area_width = self.width - (padding_x * 2)

        # --- Title ---
        title_text = self.content.get("title", "Title Goes Here")
        title_font = load_font("poppins_semibold", 52)
        title_lines = wrap_text(title_text, title_font, text_area_width)

        title_end_y = draw_text_block(
            draw,
            title_lines,
            title_font,
            x=padding_x,
            y=content_y,
            color=text_dark,
            line_spacing=6,
            align="left",
        )

        # --- Description ---
        desc_text = self.content.get("description", "Description text goes here.")
        desc_font = load_font("poppins_regular", 34)
        desc_lines = wrap_text(desc_text, desc_font, text_area_width)

        desc_y = title_end_y + 30
        draw_text_block(
            draw,
            desc_lines,
            desc_font,
            x=padding_x,
            y=desc_y,
            color=text_muted,
            line_spacing=14,
            align="left",
        )

        # --- Footer ---
        footer_font = load_font("poppins_regular", 28)
        footer_y = self.height - 120

        # Bottom left
        draw.text((padding_x, footer_y), "@glabs.ai", fill=text_dark, font=footer_font)

        # Bottom right: Swipe ->
        swipe_text = "Swipe"
        swipe_w = draw.textlength(swipe_text, font=footer_font)
        arrow_gap = 10
        arrow_len = 36
        arrow_head = 8
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
        draw.line([arrow_end_x - arrow_head, arrow_y - arrow_head + 2, arrow_end_x, arrow_y], fill=text_dark, width=line_w)
        draw.line([arrow_end_x - arrow_head, arrow_y + arrow_head - 2, arrow_end_x, arrow_y], fill=text_dark, width=line_w)


        return img
