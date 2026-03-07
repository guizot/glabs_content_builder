"""
Telegram Bot Feature — Plug-and-Play Integration for Content Builder

This feature creates a Telegram bot that:
1. Listens for user messages containing content generation prompts
2. Runs the full generation pipeline (scrape → LLM → canvas)
3. Sends the generated images back as a media group in the chat
4. Presents Approve / Reject / Regenerate inline buttons for user approval
5. Supports scheduled content from the SchedulerFeature

Commands:
    /start    — Welcome message with usage instructions
    /help     — Same help info
    /schedule — Show the content schedule board
    Any other text message is treated as a content generation prompt.
"""

import os
import sys
import shutil
import asyncio
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

from telegram import Update, Bot, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from src.features.base_feature import BaseFeature
from src.features.scraper_feature.scraper import ScraperFeature
from src.features.llm_feature.llm import LLMFeature
from src.features.canvas_feature.canvas import CanvasFeature
from src.features.repliz_feature.repliz import ReplizFeature
from src.features.image_gen_feature.image_gen import ImageGenFeature


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
    "/start    — Show this welcome message\n"
    "/help     — Show this welcome message\n"
    "/schedule — Show the content schedule board"
)

# Inline keyboard for approval
APPROVAL_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✅ Approve", callback_data="approve"),
        InlineKeyboardButton("❌ Reject", callback_data="reject"),
    ],
    [
        InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate"),
    ],
])

# ── In-memory pending approval store ──────────────────────────────────
# Key: (chat_id, approval_message_id) → dict with session info
pending_approvals: Dict[tuple, Dict[str, Any]] = {}

# ── Reference to the scheduler (set by main.py) ──────────────────────
_scheduler_ref = None


def set_scheduler_ref(scheduler):
    """Set the scheduler reference so approval callbacks can update CSV."""
    global _scheduler_ref
    _scheduler_ref = scheduler


# ── Pipeline runner (sync, called from the async handler) ──────────────

def run_pipeline(user_prompt: str, output_dir: str) -> tuple[List[str], str]:
    """
    Runs the full generation pipeline synchronously and returns a tuple
    of (output_paths, generated_caption).
    """
    scraper = ScraperFeature()
    llm = LLMFeature()
    canvas = CanvasFeature()

    print("\n[Telegram Pipeline] Step 1 — Scraping context URLs...")
    scrape_result = scraper.execute(user_prompt, output_dir)
    context = scrape_result["context"]
    article_image_path = scrape_result["image_path"]

    print("[Telegram Pipeline] Step 2 — LLM generation...")
    llm_payload = llm.execute(user_prompt, context)

    if not llm_payload or not llm_payload.get("slides"):
        return [], ""

    batch_data = llm_payload.get("slides", [])
    generated_caption = llm_payload.get("caption", "")
    image_prompt = llm_payload.get("image_prompt", "")

    # Step 2.5 — Optional Image Generation
    if image_prompt:
        print(f"[Telegram Pipeline] Step 2.5 — Image generation requested: {image_prompt[:50]}...")
        image_gen = ImageGenFeature()
        generated_image_path = image_gen.execute(image_prompt, output_dir)
        if generated_image_path:
            # Override scraped image with the newly generated image
            article_image_path = generated_image_path

    # Inject article/generated image path into hook items so design2 can use it
    if article_image_path:
        for item in batch_data:
            if item.get("template") == "hook":
                item.setdefault("content", {})["image_path"] = article_image_path

    print("[Telegram Pipeline] Step 3 — Canvas rendering...")
    output_paths = canvas.execute(batch_data, output_dir)

    return output_paths, generated_caption


# ── Helper: send images to a chat ──────────────────────────────────────

async def _send_images_to_chat(bot: Bot, chat_id: int, output_paths: List[str]) -> List[str]:
    """Send generated images to a Telegram chat and return their file_ids."""
    file_ids = []
    if len(output_paths) == 1:
        with open(output_paths[0], "rb") as photo:
            msg = await bot.send_photo(chat_id=chat_id, photo=photo)
            file_ids.append(msg.photo[-1].file_id)
    else:
        # Telegram allows max 10 media per group
        for chunk_start in range(0, len(output_paths), 10):
            chunk = output_paths[chunk_start : chunk_start + 10]
            media_group = []
            for path in chunk:
                with open(path, "rb") as f:
                    photo_bytes = f.read()
                media_group.append(InputMediaPhoto(media=photo_bytes))
            msgs = await bot.send_media_group(chat_id=chat_id, media=media_group)
            file_ids.extend([m.photo[-1].file_id for m in msgs])
    return file_ids


async def _send_approval_keyboard(
    bot: Bot,
    chat_id: int,
    num_images: int,
    user_prompt: str,
    output_dir: str,
    output_paths: List[str],
    file_ids: List[str],
    user_id: int,
    user_name: str,
    csv_row_index: Optional[int] = None,
    scheduler=None,
    generated_caption: str = "",
):
    """
    Send the approval message with inline buttons and register the session.
    Works for both on-demand (user chat) and scheduled content.
    """
    source_label = "📅 Scheduled" if csv_row_index is not None else "💬 On-demand"

    approval_msg = await bot.send_message(
        chat_id=chat_id,
        text=(
            f"📋 *Content Preview Ready!*\n\n"
            f"🖼 {num_images} image(s) generated.\n"
            f"📌 Source: {source_label}\n"
            f"What would you like to do?"
        ),
        parse_mode="Markdown",
        reply_markup=APPROVAL_KEYBOARD,
    )

    # Store pending state
    pending_approvals[(chat_id, approval_msg.message_id)] = {
        "user_prompt": user_prompt,
        "output_dir": output_dir,
        "output_paths": output_paths,
        "file_ids": file_ids,
        "user_id": user_id,
        "user_name": user_name,
        "csv_row_index": csv_row_index,
        "scheduler": scheduler,
        "generated_caption": generated_caption,
    }

    print(f"  📋 Approval requested — message_id={approval_msg.message_id}")


# ── Public helper for scheduler ────────────────────────────────────────

async def send_scheduled_content(
    bot: Bot,
    chat_id: int,
    prompt: str,
    csv_row_index: int,
    scheduler,
):
    """
    Called by the SchedulerFeature when a job fires.
    Runs the pipeline and sends images with approval buttons.
    """
    user_id = chat_id  # scheduled content is attributed to the chat
    user_name = "Scheduler"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("outputs", f"scheduled_{csv_row_index}_{timestamp}")

    # Notify the chat
    status_msg = await bot.send_message(
        chat_id=chat_id,
        text=(
            "⏰ *Scheduled content generating...*\n\n"
            f"📝 _{prompt[:100]}{'...' if len(prompt) > 100 else ''}_\n\n"
            "This may take a minute."
        ),
        parse_mode="Markdown",
    )

    try:
        loop = asyncio.get_event_loop()
        output_paths, generated_caption = await loop.run_in_executor(
            None, run_pipeline, prompt, output_dir
        )

        if not output_paths:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text="❌ *Scheduled generation failed.*\nCould not produce content.",
                parse_mode="Markdown",
            )
            return

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=f"✅ *Done!* Sending {len(output_paths)} image(s)...",
            parse_mode="Markdown",
        )

        file_ids = await _send_images_to_chat(bot, chat_id, output_paths)
        await _send_approval_keyboard(
            bot=bot,
            chat_id=chat_id,
            num_images=len(output_paths),
            user_prompt=prompt,
            output_dir=output_dir,
            output_paths=output_paths,
            file_ids=file_ids,
            user_id=user_id,
            user_name=user_name,
            csv_row_index=csv_row_index,
            scheduler=scheduler,
            generated_caption=generated_caption,
        )

    except Exception as e:
        print(f"  ❌ Scheduled content error: {e}")
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=f"❌ *Scheduled content error:*\n`{str(e)}`",
            parse_mode="Markdown",
        )
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)


# ── Handlers ───────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start and /help commands."""
    await update.message.reply_text(WELCOME_TEXT, parse_mode="Markdown")


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /schedule command — show the content schedule board."""
    if _scheduler_ref is None:
        await update.message.reply_text(
            "⚠️ Scheduler is not active.", parse_mode="Markdown"
        )
        return

    rows = _scheduler_ref.load_all_rows()

    if not rows:
        await update.message.reply_text(
            "📅 *Schedule Board*\n\nNo entries found in CSV.",
            parse_mode="Markdown",
        )
        return

    # Status emoji mapping
    status_emoji = {
        "pending": "⏳",
        "waiting_approval": "🔔",
        "approved": "✅",
        "rejected": "❌",
        "error": "⚠️",
    }

    lines = ["📅 *Content Schedule Board*\n"]
    for row in rows:
        emoji = status_emoji.get(row["status"].lower(), "❓")
        prompt_short = row["prompt"][:50] + ("..." if len(row["prompt"]) > 50 else "")
        last_run = f" — Last: {row['last_run']}" if row["last_run"] else ""

        lines.append(
            f"{row['row_index']+1}\\. {emoji} `{row['scheduled_time']}`\n"
            f"   _{prompt_short}_\n"
            f"   Status: *{row['status']}*{last_run}\n"
        )

    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown"
    )


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
    chat_id = update.effective_chat.id

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
        output_paths, generated_caption = await loop.run_in_executor(
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

        # Update status
        await status_msg.edit_text(
            f"✅ *Done!* Sending {len(output_paths)} image(s)...",
            parse_mode="Markdown",
        )

        # Send images + approval buttons
        file_ids = await _send_images_to_chat(update.get_bot(), chat_id, output_paths)
        await _send_approval_keyboard(
            bot=update.get_bot(),
            chat_id=chat_id,
            num_images=len(output_paths),
            user_prompt=user_prompt,
            output_dir=output_dir,
            output_paths=output_paths,
            file_ids=file_ids,
            user_id=user_id,
            user_name=user_name,
            generated_caption=generated_caption,
        )

    except Exception as e:
        print(f"  ❌ Telegram pipeline error: {e}")
        await status_msg.edit_text(
            f"❌ *An error occurred:*\n`{str(e)}`",
            parse_mode="Markdown",
        )
        # Clean up on error
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)


async def handle_approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle inline button presses: approve / reject / regenerate.
    """
    query = update.callback_query
    await query.answer()  # acknowledge the button press

    chat_id = query.message.chat_id
    message_id = query.message.message_id
    action = query.data

    # Look up the pending session
    session_key = (chat_id, message_id)
    session = pending_approvals.get(session_key)

    if not session:
        await query.edit_message_text(
            "⚠️ This approval session has expired or was already handled.",
        )
        return

    user_prompt = session["user_prompt"]
    output_dir = session["output_dir"]
    user_name = session["user_name"]
    user_id = session["user_id"]
    csv_row_index = session.get("csv_row_index")
    scheduler = session.get("scheduler") or _scheduler_ref

    # ── Approve ────────────────────────────────────────────────────────
    if action == "approve":
        print(f"  ✅ Content APPROVED by {user_name} (ID: {user_id})")

        # Call Repliz to get accounts
        repliz = ReplizFeature()
        accounts = repliz.get_accounts()

        if not accounts:
            await query.edit_message_text(
                "✅ *Content Approved!*\n\n⚠️ No connected Repliz accounts found! "
                "Please configure your REPLIZ_ACCESS_KEY.",
                parse_mode="Markdown",
            )
            # Finish cleanly since we can't post
            if csv_row_index is not None and scheduler:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                scheduler.update_csv_status(csv_row_index, "approved", now_str)

            if os.path.exists(output_dir):
                shutil.rmtree(output_dir, ignore_errors=True)
            del pending_approvals[session_key]
            return

        # Create inline keyboard for account selection
        keyboard = []
        for acc in accounts:
            keyboard.append([InlineKeyboardButton(f"📱 {acc['name']} ({acc['type']})", callback_data=f"repliz_{acc['_id']}")])

        if len(accounts) > 1:
            keyboard.append([InlineKeyboardButton("🌐 Post to All Accounts", callback_data="repliz_all")])

        keyboard.append([InlineKeyboardButton("❌ Cancel Posting", callback_data="repliz_cancel")])

        await query.edit_message_text(
            "✅ *Content Approved!*\n\n"
            "Where would you like to schedule this post? (It will post instantly)",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # ── Repliz Action ──────────────────────────────────────────────────
    elif action.startswith("repliz_"):
        target = action.replace("repliz_", "")
        if target == "cancel":
            await query.edit_message_text("❌ Scheduled posting cancelled (Content remains approved).", parse_mode="Markdown")
        else:
            await query.edit_message_text("⏳ *Publishing via Repliz...*", parse_mode="Markdown")

            repliz = ReplizFeature()
            accounts = repliz.get_accounts()
            account_ids = []
            if target == "all":
                account_ids = [acc["_id"] for acc in accounts]
            else:
                account_ids = [target]

            # Upload local files to Catbox.moe for public URLs accessible by Facebook
            file_urls = []
            for path in session.get("output_paths", []):
                try:
                    with open(path, "rb") as f:
                        resp = requests.post(
                            "https://catbox.moe/user/api.php", 
                            data={"reqtype": "fileupload"}, 
                            files={"fileToUpload": f}
                        )
                        resp.raise_for_status()
                        url = resp.text.strip()
                        file_urls.append({"type": "image", "url": url})
                except Exception as e:
                    print(f"Error uploading file {path} to catbox: {e}")

            if file_urls:
                # Use LLM-generated caption, fallback to user prompt
                final_text = session.get("generated_caption") or user_prompt
                success = repliz.create_schedule(
                    account_ids,
                    text=final_text,
                    media_urls=file_urls
                )
                if success:
                    await query.edit_message_text("✅ *Successfully posted to social media via Repliz!*", parse_mode="Markdown")
                else:
                    await query.edit_message_text("❌ *Failed to post. Check logs for details.*", parse_mode="Markdown")
            else:
                await query.edit_message_text("❌ *No valid images found to post.*", parse_mode="Markdown")

        # Update CSV if this was a scheduled job
        if csv_row_index is not None and scheduler:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            scheduler.update_csv_status(csv_row_index, "approved", now_str)

        # Clean up temp folder
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
            print(f"  🧹 Cleaned up: {output_dir}")

        del pending_approvals[session_key]

    # ── Reject ─────────────────────────────────────────────────────────
    elif action == "reject":
        print(f"  ❌ Content REJECTED by {user_name} (ID: {user_id})")

        await query.edit_message_text(
            "❌ *Content Rejected.*\n\n"
            "The content has been discarded. "
            "Send a new prompt whenever you're ready!",
            parse_mode="Markdown",
        )

        # Update CSV if this was a scheduled job
        if csv_row_index is not None and scheduler:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            scheduler.update_csv_status(csv_row_index, "rejected", now_str)

        # Clean up temp folder
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
            print(f"  🧹 Cleaned up: {output_dir}")

        del pending_approvals[session_key]

    # ── Regenerate ─────────────────────────────────────────────────────
    elif action == "regenerate":
        print(f"  🔄 Content REGENERATION requested by {user_name} (ID: {user_id})")

        await query.edit_message_text(
            "🔄 *Regenerating content...*\n\n"
            "Please wait while I create new images with the same prompt.",
            parse_mode="Markdown",
        )

        # Remove old session
        del pending_approvals[session_key]

        # Clean up old temp folder
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
            print(f"  🧹 Cleaned up old folder: {output_dir}")

        # New output folder
        new_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_output_dir = os.path.join("outputs", f"telegram_{user_id}_{new_timestamp}")

        try:
            loop = asyncio.get_event_loop()
            new_output_paths, generated_caption = await loop.run_in_executor(
                None, run_pipeline, user_prompt, new_output_dir
            )

            if not new_output_paths:
                await update.effective_chat.send_message(
                    "❌ *Regeneration failed.*\n"
                    "The AI could not produce valid content. "
                    "Please try sending a new prompt.",
                    parse_mode="Markdown",
                )
                return

            # Send new images + new approval buttons
            bot = update.get_bot()
            file_ids = await _send_images_to_chat(bot, chat_id, new_output_paths)
            await _send_approval_keyboard(
                bot=bot,
                chat_id=chat_id,
                num_images=len(new_output_paths),
                user_prompt=user_prompt,
                output_dir=new_output_dir,
                output_paths=new_output_paths,
                file_ids=file_ids,
                user_id=user_id,
                user_name=user_name,
                csv_row_index=csv_row_index,
                scheduler=scheduler,
                generated_caption=generated_caption,
            )

        except Exception as e:
            print(f"  ❌ Regeneration error: {e}")
            await update.effective_chat.send_message(
                f"❌ *Regeneration error:*\n`{str(e)}`",
                parse_mode="Markdown",
            )
            if os.path.exists(new_output_dir):
                shutil.rmtree(new_output_dir, ignore_errors=True)


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

        Optional kwargs:
            scheduler: SchedulerFeature instance to start alongside the bot
            chat_id: Telegram chat ID for scheduled content delivery
        """
        scheduler = kwargs.get("scheduler")
        chat_id = kwargs.get("chat_id")

        if not self.token:
            print("❌ No Telegram bot token supplied. "
                  "Set TELEGRAM_BOT_TOKEN in .env or pass it to the constructor.")
            sys.exit(1)

        print("=" * 50)
        print("  🤖 CONTENT BUILDER — Telegram Bot Mode")
        print("=" * 50)
        print(f"  Token: {self.token[:8]}...{self.token[-4:]}")
        if chat_id:
            print(f"  Chat ID: {chat_id}")
        print("  Waiting for messages...")
        print("=" * 50)

        app = Application.builder().token(self.token).build()

        # Set global scheduler reference
        if scheduler:
            set_scheduler_ref(scheduler)

        # Register handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", start_command))
        app.add_handler(CommandHandler("schedule", schedule_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CallbackQueryHandler(handle_approval_callback))

        # Start scheduler via post_init if provided
        if scheduler and chat_id:
            async def post_init(application: Application):
                await scheduler.start(application.bot, chat_id)

            app.post_init = post_init

        render_external_url = os.getenv("RENDER_EXTERNAL_URL")

        if render_external_url:
            port = int(os.getenv("PORT", "10000"))
            print(f"🤖 Content Builder bot is starting webhook on port {port}...")
            app.run_webhook(
                listen="0.0.0.0",
                port=port,
                webhook_url=render_external_url,
                allowed_updates=Update.ALL_TYPES
            )
        else:
            print("🤖 Content Builder bot is running in polling mode...")
            # Start long-polling
            app.run_polling(allowed_updates=Update.ALL_TYPES)
