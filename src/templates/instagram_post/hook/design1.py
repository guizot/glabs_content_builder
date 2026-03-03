"""
Instagram Post — Hook Template — Design 1
Style: Light/warm bg, left-aligned bold hook text,
       coral accent stripe + corner circle.
Optimized for 1080x1350 (4:5) ratio.
"""

from PIL import Image, ImageDraw
from src.core.canvas import create_canvas
from src.core.text_utils import load_font, wrap_text, draw_text_block, get_text_height


class HookDesign1:
    def __init__(self, ratio: dict, content: dict):
        self.width = ratio["width"]
        self.height = ratio["height"]
        self.content = content

    def render(self) -> Image.Image:
        # --- Background: warm off-white ---
        bg_color = "#F5F0EB"
        img = create_canvas(self.width, self.height, bg_color)
        draw = ImageDraw.Draw(img)

        accent_color = "#E17055"  # coral/terracotta

        # --- Left accent stripe ---
        stripe_width = 18
        stripe_x = 80
        stripe_top = 180
        stripe_bottom = self.height - 180
        draw.rectangle(
            [stripe_x, stripe_top, stripe_x + stripe_width, stripe_bottom],
            fill=accent_color,
        )

        # --- Hook text (left-aligned, right of stripe) ---
        hook_text = self.content.get("hook_text", "Your Hook Text Here")

        padding_left = stripe_x + stripe_width + 50
        padding_right = 100
        text_area_width = self.width - padding_left - padding_right

        font_size = 68
        font = load_font("poppins_semibold", font_size)
        lines = wrap_text(hook_text, font, text_area_width)

        text_height = get_text_height(lines, font, line_spacing=18)
        start_y = (self.height - text_height) // 2

        draw_text_block(
            draw,
            lines,
            font,
            x=padding_left,
            y=start_y,
            color="#2D3436",
            line_spacing=18,
            align="left",
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

        return img
