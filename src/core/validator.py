"""
Content field validation — character limits and auto-truncation.
Prevents text overflow in rendered images.
Limits are defined per (ratio, template) combination.
"""

# Max character limits per (ratio, template)
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
            truncated = value[: max_chars - 1].rstrip() + "…"
            print(
                f"{prefix}'{field}' exceeds {max_chars} chars "
                f"({len(value)} chars) → truncated"
            )
            cleaned[field] = truncated

    return cleaned
