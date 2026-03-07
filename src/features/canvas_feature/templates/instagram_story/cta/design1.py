"""
Instagram Story — CTA Template — Design 1
Style: Plain white background, centered branding (small),
       subtitle + large bold CTA text + pill buttons + handle.
Optimized for 1080x1920 (9:16) ratio.
"""

from PIL import Image, ImageDraw
from src.features.canvas_feature.canvas import create_canvas, draw_rounded_rect
from src.features.canvas_feature.text_utils import load_font, wrap_text, draw_text_block, get_text_height


class CtaDesign1:
    def __init__(self, ratio: dict, content: dict):
        self.width = ratio["width"]
        self.height = ratio["height"]
        self.content = content

    def render(self) -> Image.Image:
        # --- Background: Plain Black ---
        img = create_canvas(self.width, self.height, "#FFFFFF")
        draw = ImageDraw.Draw(img)

        text_dark = "#000000"
        center_x = self.width // 2

        # --- Branding: 'guizot labs' (Centered, small) ---
        brand_font_bold = load_font("poppins_semibold", 46)
        brand_font_reg = load_font("poppins_regular", 46)

        brand_bold_text = "guizot"
        brand_reg_text = "labs"
        spacing = 6

        brand_bold_w = draw.textlength(brand_bold_text, font=brand_font_bold)
        brand_reg_w = draw.textlength(brand_reg_text, font=brand_font_reg)
        total_brand_w = brand_bold_w + spacing + brand_reg_w
        brand_x = center_x - total_brand_w // 2
        brand_y = 120

        draw.text((brand_x, brand_y), brand_bold_text, fill=text_dark, font=brand_font_bold)
        draw.text((brand_x + brand_bold_w + spacing, brand_y), brand_reg_text, fill=text_dark, font=brand_font_reg)

        # --- Subtitle (centered) ---
        subtitle_text = self.content.get("subtitle", "")
        subtitle_font = load_font("poppins_regular", 40)
        text_area_width = self.width - 180

        if subtitle_text:
            subtitle_lines = wrap_text(subtitle_text, subtitle_font, text_area_width)
            subtitle_height = get_text_height(subtitle_lines, subtitle_font, line_spacing=8)
        else:
            subtitle_lines = []
            subtitle_height = 0

        # --- CTA Text (large, bold, centered) ---
        cta_text = self.content.get("cta_text", "Your CTA Text Here")
        cta_font = load_font("poppins_bold", 88)
        cta_lines = wrap_text(cta_text, cta_font, text_area_width)
        cta_height = get_text_height(cta_lines, cta_font, line_spacing=12)

        # --- Buttons ---
        buttons = ["Share", "Save"]
        btn_font = load_font("poppins_regular", 32)
        btn_padding_x = 44
        btn_padding_y = 16
        btn_spacing = 28
        btn_radius = 32

        # Measure buttons
        btn_sizes = []
        for btn_text in buttons:
            tw = draw.textlength(btn_text, font=btn_font)
            bw = int(tw + btn_padding_x * 2)
            ascent, descent = btn_font.getmetrics()
            bh = ascent + descent + btn_padding_y * 2
            btn_sizes.append((bw, bh, btn_text))

        total_btn_w = sum(s[0] for s in btn_sizes) + btn_spacing * (len(btn_sizes) - 1)
        btn_h = btn_sizes[0][1] if btn_sizes else 0

        # --- Vertical layout: center the content block ---
        content_top = 220
        footer_y = self.height - 160

        gap_subtitle_cta = 35 if subtitle_text else 0
        gap_cta_btn = 60
        total_content_h = subtitle_height + gap_subtitle_cta + cta_height + gap_cta_btn + btn_h
        available_h = footer_y - content_top
        start_y = content_top + (available_h - total_content_h) // 2

        # Draw subtitle
        current_y = start_y
        if subtitle_lines:
            draw_text_block(
                draw, subtitle_lines, subtitle_font,
                x=90, y=current_y,
                color=text_dark, line_spacing=8,
                align="center", max_width=text_area_width,
            )
            current_y += subtitle_height + gap_subtitle_cta

        # Draw CTA text
        draw_text_block(
            draw, cta_lines, cta_font,
            x=90, y=current_y,
            color=text_dark, line_spacing=12,
            align="center", max_width=text_area_width,
        )
        current_y += cta_height + gap_cta_btn

        # Draw buttons
        btn_start_x = center_x - total_btn_w // 2
        bx = btn_start_x
        for bw, bh, btn_text in btn_sizes:
            draw_rounded_rect(
                draw,
                (bx, current_y, bx + bw, current_y + bh),
                radius=btn_radius,
                outline=text_dark,
                width=2,
            )
            tw = draw.textlength(btn_text, font=btn_font)
            ascent, _ = btn_font.getmetrics()
            tx = bx + (bw - tw) // 2
            ty = current_y + btn_padding_y
            draw.text((tx, ty), btn_text, fill=text_dark, font=btn_font)
            bx += bw + btn_spacing

        # --- Handle (bottom center) ---
        handle_font = load_font("poppins_regular", 34)
        handle_text = "@glabs.ai"
        handle_w = draw.textlength(handle_text, font=handle_font)
        draw.text((center_x - handle_w // 2, footer_y), handle_text, fill=text_dark, font=handle_font)

        return img
