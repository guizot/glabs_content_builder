"""
Telegram Bot Feature — Plug-and-Play Integration for Content Builder

This feature creates a Telegram bot that:
1. Listens for user messages containing content generation prompts
2. Runs the full generation pipeline (scrape → LLM → canvas)
3. Sends the generated images back as a media group in the chat

Commands:
    /start  — Welcome message with usage instructions
    /help   — Same help info
    Any other text message is treated as a content generation prompt.
"""

import os
import sys
import shutil
import asyncio
from datetime import datetime
from typing import List

from telegram import Update, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from src.features.base_feature import BaseFeature
from src.features.scraper_feature.scraper import ScraperFeature
from src.features.llm_feature.llm import LLMFeature
from src.features.canvas_feature.canvas import CanvasFeature


# ── Constants ──────────────────────────────────────────────────────────

WELCOME_TEXT = (
    "👋 *Welcome to Content Builder Bot!*\n\n"
    "Send me a content generation prompt and I'll create "
    "beautiful social‑media images for you.\n\n"
    "*Example prompt:*\n"
    "```\n"
    "create instagram story that has 1 hook and 5 content\n"
    "make the title catchy and interesting\n"
    "using design2 from this article:\n"
    "https://example.com/article\n"
    "```\n\n"
    "📌 *Commands*\n"
    "/start — Show this welcome message\n"
    "/help  — Show this welcome message"
)


# ── Pipeline runner (sync, called from the async handler) ──────────────

def run_pipeline(user_prompt: str, output_dir: str) -> List[str]:
    """
    Runs the full generation pipeline synchronously and returns a list
    of output image paths.
    """
    scraper = ScraperFeature()
    llm = LLMFeature()
    canvas = CanvasFeature()

    print("\n[Telegram Pipeline] Step 1 — Scraping context URLs...")
    scrape_result = scraper.execute(user_prompt, output_dir)
    context = scrape_result["context"]
    article_image_path = scrape_result["image_path"]

    print("[Telegram Pipeline] Step 2 — LLM generation...")
    batch_data = llm.execute(user_prompt, context)

    if not batch_data:
        return []

    # Inject article image path into hook items so design2 can use it
    if article_image_path:
        for item in batch_data:
            if item.get("template") == "hook":
                item.setdefault("content", {})["image_path"] = article_image_path

    print("[Telegram Pipeline] Step 3 — Canvas rendering...")
    output_paths = canvas.execute(batch_data, output_dir)

    return output_paths


# ── Handlers ───────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start and /help commands."""
    await update.message.reply_text(WELCOME_TEXT, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle any non‑command text message.
    Treats the entire message as a content generation prompt.
    """
    user_prompt = update.message.text.strip()

    if not user_prompt:
        await update.message.reply_text("⚠️ Please send a non-empty prompt.")
        return

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "User"

    print(f"\n{'='*50}")
    print(f"  🤖 Telegram request from {user_name} (ID: {user_id})")
    print(f"  📝 Prompt: {user_prompt[:120]}...")
    print(f"{'='*50}")

    # Acknowledge receipt
    status_msg = await update.message.reply_text(
        "⏳ *Processing your request...*\n\n"
        "This may take a minute. I'll send the images when they're ready!",
        parse_mode="Markdown",
    )

    # Prepare unique output folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("outputs", f"telegram_{user_id}_{timestamp}")

    try:
        # Run the heavy pipeline in a thread so we don't block the event loop
        loop = asyncio.get_event_loop()
        output_paths = await loop.run_in_executor(
            None, run_pipeline, user_prompt, output_dir
        )

        if not output_paths:
            await status_msg.edit_text(
                "❌ *Generation failed.*\n"
                "The AI could not produce valid content from your prompt. "
                "Please try rephrasing.",
                parse_mode="Markdown",
            )
            return

        # Send images
        await status_msg.edit_text(
            f"✅ *Done!* Sending {len(output_paths)} image(s)...",
            parse_mode="Markdown",
        )

        if len(output_paths) == 1:
            with open(output_paths[0], "rb") as photo:
                await update.message.reply_photo(photo=photo)
        else:
            # Telegram allows max 10 media per group
            for chunk_start in range(0, len(output_paths), 10):
                chunk = output_paths[chunk_start : chunk_start + 10]
                media_group = []
                for path in chunk:
                    with open(path, "rb") as f:
                        photo_bytes = f.read()
                    media_group.append(InputMediaPhoto(media=photo_bytes))

                await update.message.reply_media_group(media=media_group)

        await status_msg.edit_text(
            f"🎉 *All {len(output_paths)} image(s) sent successfully!*",
            parse_mode="Markdown",
        )

    except Exception as e:
        print(f"  ❌ Telegram pipeline error: {e}")
        await status_msg.edit_text(
            f"❌ *An error occurred:*\n`{str(e)}`",
            parse_mode="Markdown",
        )

    finally:
        # Clean up temp output directory
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
            print(f"  🧹 Cleaned up temp folder: {output_dir}")


# ── Feature class (follows BaseFeature pattern) ───────────────────────

class TelegramBotFeature(BaseFeature):
    """
    Plug-and-play Telegram bot feature.
    Call .execute(token) to start the bot in long-polling mode.
    """

    def __init__(self, token: str = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")

    def execute(self, *args, **kwargs):
        """
        Start the Telegram bot. This call is **blocking** — it runs until
        the process is terminated (Ctrl-C / SIGINT).
        """
        if not self.token:
            print("❌ No Telegram bot token supplied. "
                  "Set TELEGRAM_BOT_TOKEN in .env or pass it to the constructor.")
            sys.exit(1)

        print("=" * 50)
        print("  🤖 CONTENT BUILDER — Telegram Bot Mode")
        print("=" * 50)
        print(f"  Token: {self.token[:8]}...{self.token[-4:]}")
        print("  Waiting for messages...")
        print("=" * 50)

        app = Application.builder().token(self.token).build()

        # Register handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", start_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Start long-polling
        app.run_polling(allowed_updates=Update.ALL_TYPES)
