"""
Content Builder v2 — Plug-and-Play Modular Orchestrator

Usage (Generate JSON + Images from prompt):
    python main.py --prompt src/inputs/prompt.txt

Usage (Generate Images strictly from existing JSON file):
    python main.py --input src/inputs/sample_batch.json

Usage (Launch Telegram Bot):
    python main.py --telegram
"""

import argparse
import sys
import os
import json
from datetime import datetime

# Ensure the project root is in the path so `src.` imports work
sys.path.insert(0, os.path.dirname(__file__))

from src.features.scraper_feature.scraper import ScraperFeature
from src.features.llm_feature.llm import LLMFeature
from src.features.canvas_feature.canvas import CanvasFeature
from src.features.telegram_feature.telegram_bot import TelegramBotFeature


def validate_file(path: str) -> None:
    if not os.path.exists(path):
        print(f"❌ Input file not found: {path}")
        sys.exit(1)


def full_generation_pipeline(prompt_path: str, output_dir: str):
    """
    Executes the full AI pipeline: text prompt -> scraper context -> LLM JSON -> Rendered Images.
    """
    validate_file(prompt_path)
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        user_prompt = f.read().strip()
        
    if not user_prompt:
        print(f"❌ Prompt file is empty: {prompt_path}")
        sys.exit(1)

    print(f"  📝 Reading prompt from: {prompt_path}")
    print(f"  >> \"{user_prompt[:100]}...\"" if len(user_prompt) > 100 else f"  >> \"{user_prompt}\"")

    # Plug and Play Instances
    scraper = ScraperFeature()
    llm = LLMFeature()
    canvas = CanvasFeature()

    # Add unique subfolder
    timestamp_for_folder = datetime.now().strftime("%d %B %Y %H:%M:%S")
    final_output = os.path.join(output_dir, timestamp_for_folder)

    print("\n[Step 1 - ScraperFeature] Scraping context URLs...")
    scrape_result = scraper.execute(user_prompt, final_output)
    context = scrape_result["context"]
    article_image_path = scrape_result["image_path"]

    print("\n[Step 2 - LLMFeature] Translating prompt into structured Content Builder JSON...")
    batch_data = llm.execute(user_prompt, context)
    
    if not batch_data:
        print("❌ Generation failed at LLM phase. Exiting.")
        sys.exit(1)

    # # Save generated JSON for caching / review
    # timestamp_for_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    # json_out_path = f"src/inputs/generated_{timestamp_for_file}.json"
    # 
    # with open(json_out_path, "w", encoding="utf-8") as f:
    #     json.dump(batch_data, f, indent=4)
    #     
    # print(f"  ✅ Saved generated JSON Payload: {json_out_path}")

    # Inject article image path into hook items so design2 can use it
    if article_image_path:
        for item in batch_data:
            if item.get("template") == "hook":
                item.setdefault("content", {})["image_path"] = article_image_path

    print("\n[Step 3 - CanvasFeature] Dispatching payload to Canvas Component...")
    canvas.execute(batch_data, final_output)


def json_only_pipeline(json_path: str, output_dir: str):
    """
    Executes only the Canvas image generation step from an existing JSON file.
    """
    validate_file(json_path)
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            batch_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in '{json_path}'")
        print(f"   Details: {str(e)}")
        sys.exit(1)
    
    canvas = CanvasFeature()
    
    timestamp = datetime.now().strftime("%d %B %Y %H:%M:%S")
    final_output = os.path.join(output_dir, timestamp)

    canvas.execute(batch_data, final_output)


def main():
    parser = argparse.ArgumentParser(
        description="📸 Content Builder v2 — Plug-and-Play AI Content Generator"
    )
    # Give the user the choice between the text-to-image AI pipeline or direct json-to-image renderer.
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--prompt",
        type=str,
        help="Path to the user prompt text file (Launch full text-to-images AI pipeline)",
    )
    group.add_argument(
        "--input",
        type=str,
        help="Path to JSON batch file (Launch JSON-to-images direct pipeline)",
    )
    group.add_argument(
        "--telegram",
        action="store_true",
        help="Launch the Telegram bot (reads TELEGRAM_BOT_TOKEN from .env)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs",
        help="Output directory (default: outputs/)",
    )

    args = parser.parse_args()

    print("=" * 50)
    print("  📸 CONTENT BUILDER v2 (Modular)")
    print("=" * 50)
    print(f"  Output Base: {args.output}")
    print("=" * 50)
    print()

    # Determine pipeline logic branch
    if args.telegram:
        from dotenv import load_dotenv
        load_dotenv()
        bot = TelegramBotFeature()
        bot.execute()
    elif args.prompt:
        full_generation_pipeline(args.prompt, args.output)
    elif args.input:
        json_only_pipeline(args.input, args.output)


if __name__ == "__main__":
    main()
