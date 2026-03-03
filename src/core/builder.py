"""
Builder — reads a JSON batch file and dispatches each item
to the correct design class for rendering.
"""

import json
import os
from src.config.ratios import get_ratio
from src.config.templates import get_design_class
from src.core.canvas import save_image
from src.core.validator import validate_content


def build_from_json(json_path: str, output_dir: str = "outputs"):
    """
    Main orchestrator. Reads the JSON batch file and generates
    one image per entry.
    """
    # Load JSON
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            items = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in '{json_path}'")
        print(f"   Details: {str(e)}")
        return
    except Exception as e:
        print(f"❌ Error reading file: {str(e)}")
        return

    if not isinstance(items, list):
        items = [items]

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    print(f"📦 Building {len(items)} image(s)...\n")

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
