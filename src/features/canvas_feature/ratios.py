"""
Image size presets for different social media formats.
Each ratio defines width, height, and a human-readable label.
"""

RATIOS = {
    "instagram_post": {
        "width": 1080,
        "height": 1350,
        "label": "Instagram Post (4:5)",
    },
    "instagram_story": {
        "width": 1080,
        "height": 1920,
        "label": "Instagram Story (9:16)",
    },
    "instagram_feed": {
        "width": 1080,
        "height": 1080,
        "label": "Instagram Feed Post (1:1)",
    },
}


def get_ratio(name: str) -> dict:
    """Get a ratio preset by name. Raises KeyError if not found."""
    if name not in RATIOS:
        available = ", ".join(RATIOS.keys())
        raise KeyError(f"Unknown ratio '{name}'. Available: {available}")
    return RATIOS[name]
