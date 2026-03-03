"""
Instagram Post — Content Template — Design 1
Style: Light/warm bg, title + description layout,
       coral accent elements.
Optimized for 1080x1350 (4:5) ratio.
"""

from PIL import Image, ImageDraw
from src.core.canvas import create_canvas
from src.core.text_utils import load_font, wrap_text, draw_text_block, get_text_height


class ContentDesign1:
    def __init__(self, ratio: dict, content: dict):
        self.width = ratio["width"]
        self.height = ratio["height"]
        self.content = content

    def render(self) -> Image.Image:
        # --- Background: warm off-white ---
        bg_color = "#F5F0EB"
        img = create_canvas(self.width, self.height, bg_color)
        draw = ImageDraw.Draw(img)

        accent_color = "#E17055"
        text_dark = "#2D3436"
        text_muted = "#636E72"

        # --- Left accent stripe ---
        stripe_width = 18
        stripe_x = 80
        stripe_top = 180
        stripe_bottom = self.height - 180
        draw.rectangle(
            [stripe_x, stripe_top, stripe_x + stripe_width, stripe_bottom],
            fill=accent_color,
        )

        # --- Layout ---
        padding_left = stripe_x + stripe_width + 50
        padding_right = 100
        text_area_width = self.width - padding_left - padding_right

        # --- Title ---
        title_text = self.content.get("title", "Title Goes Here")
        title_font = load_font("poppins_semibold", 56)
        title_lines = wrap_text(title_text, title_font, text_area_width)

        title_y = 260
        title_end_y = draw_text_block(
            draw,
            title_lines,
            title_font,
            x=padding_left,
            y=title_y,
            color=text_dark,
            line_spacing=16,
            align="left",
        )

        # --- Accent divider ---
        divider_y = title_end_y + 25
        divider_width = 80
        draw.rectangle(
            [padding_left, divider_y, padding_left + divider_width, divider_y + 6],
            fill=accent_color,
        )

        # --- Description ---
        desc_text = self.content.get("description", "Description text goes here.")
        desc_font = load_font("poppins_regular", 34)
        desc_lines = wrap_text(desc_text, desc_font, text_area_width)

        desc_y = divider_y + 45
        draw_text_block(
            draw,
            desc_lines,
            desc_font,
            x=padding_left,
            y=desc_y,
            color=text_muted,
            line_spacing=14,
            align="left",
        )

        # --- Top-right corner circle ---
        circle_radius = 55
        circle_x = self.width - 115
        circle_y = 115
        draw.ellipse(
            [
                circle_x - circle_radius,
                circle_y - circle_radius,
                circle_x + circle_radius,
                circle_y + circle_radius,
            ],
            fill=accent_color,
        )

        # --- Bottom accent bar ---
        badge_w = 120
        badge_h = 8
        badge_x = padding_left
        badge_y = self.height - 130
        draw.rectangle(
            [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
            fill=accent_color,
        )

        return img
