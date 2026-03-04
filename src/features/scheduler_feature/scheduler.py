"""
Scheduler Feature — CSV-based Content Schedule Board

Reads a CSV file with one-time scheduled content generation jobs.
Each row contains a prompt and a scheduled datetime. When the time comes,
the pipeline runs and sends content to Telegram for approval.

CSV Format:
    prompt,scheduled_time,status,last_run
    "some prompt",2026-03-05 09:00,pending,
"""

import os
import csv
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from src.features.base_feature import BaseFeature


# ── Constants ──────────────────────────────────────────────────────────

DEFAULT_CSV_PATH = os.path.join("src", "inputs", "schedule.csv")
DATETIME_FORMAT = "%Y-%m-%d %H:%M"


class SchedulerFeature(BaseFeature):
    """
    Reads a CSV schedule board and creates one-time APScheduler jobs
    for each pending row with a future scheduled_time.
    """

    def __init__(self, csv_path: str = None):
        self.csv_path = csv_path or DEFAULT_CSV_PATH
        self.scheduler = AsyncIOScheduler()
        self._bot = None
        self._chat_id = None

    def execute(self, *args, **kwargs):
        """Not used directly — use start() instead."""
        pass

    def load_csv(self) -> List[Dict[str, Any]]:
        """
        Read the CSV and return a list of dicts with row index.
        Only includes 'pending' rows with a future scheduled_time.
        """
        if not os.path.exists(self.csv_path):
            print(f"  ⚠️  Schedule CSV not found: {self.csv_path}")
            return []

        jobs = []
        now = datetime.now()

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                status = (row.get("status") or "").strip().lower()
                prompt = (row.get("prompt") or "").strip().strip('"')
                scheduled_str = (row.get("scheduled_time") or "").strip()

                if not prompt or not scheduled_str:
                    continue

                if status != "pending":
                    continue

                try:
                    scheduled_time = datetime.strptime(scheduled_str, DATETIME_FORMAT)
                except ValueError:
                    print(f"  ⚠️  Row {i+1}: Invalid datetime '{scheduled_str}' — skipping")
                    continue

                # Skip past entries
                if scheduled_time <= now:
                    print(f"  ⏭️  Row {i+1}: '{prompt[:50]}...' — scheduled in the past, skipping")
                    continue

                jobs.append({
                    "row_index": i,
                    "prompt": prompt,
                    "scheduled_time": scheduled_time,
                })

        return jobs

    def load_all_rows(self) -> List[Dict[str, Any]]:
        """
        Read ALL rows from the CSV (for /schedule display).
        """
        if not os.path.exists(self.csv_path):
            return []

        rows = []
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                rows.append({
                    "row_index": i,
                    "prompt": (row.get("prompt") or "").strip().strip('"'),
                    "scheduled_time": (row.get("scheduled_time") or "").strip(),
                    "status": (row.get("status") or "").strip(),
                    "last_run": (row.get("last_run") or "").strip(),
                })
        return rows

    def update_csv_status(self, row_index: int, status: str, last_run: str = ""):
        """
        Update the status and last_run fields for a specific row in the CSV.
        """
        if not os.path.exists(self.csv_path):
            return

        rows = []
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # row_index is 0-based data row, but rows[0] is the header
        data_row_index = row_index + 1

        if data_row_index < len(rows):
            # CSV columns: prompt, scheduled_time, status, last_run
            while len(rows[data_row_index]) < 4:
                rows[data_row_index].append("")
            rows[data_row_index][2] = status
            rows[data_row_index][3] = last_run

        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        print(f"  📝 CSV row {row_index+1} updated: status={status}")

    async def _run_scheduled_job(self, row_index: int, prompt: str):
        """
        Called by APScheduler when a job fires.
        Runs the pipeline and sends content to Telegram for approval.
        """
        from src.features.telegram_feature.telegram_bot import (
            run_pipeline,
            send_scheduled_content,
        )

        print(f"\n{'='*50}")
        print(f"  ⏰ SCHEDULED JOB FIRED — Row {row_index+1}")
        print(f"  📝 Prompt: {prompt[:100]}...")
        print(f"{'='*50}")

        # Update status
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update_csv_status(row_index, "waiting_approval", now_str)

        try:
            await send_scheduled_content(
                bot=self._bot,
                chat_id=self._chat_id,
                prompt=prompt,
                csv_row_index=row_index,
                scheduler=self,
            )
        except Exception as e:
            print(f"  ❌ Scheduled job error: {e}")
            self.update_csv_status(row_index, "error", now_str)

    async def start(self, bot, chat_id: str):
        """
        Start the scheduler with all pending future jobs.
        Called after the Telegram bot Application is initialized.

        Args:
            bot: The telegram.Bot instance
            chat_id: Target Telegram chat ID
        """
        self._bot = bot
        self._chat_id = int(chat_id)

        jobs = self.load_csv()

        if not jobs:
            print("\n📅 Scheduler: No pending future jobs found in CSV.")
            print(f"   CSV path: {self.csv_path}")
            self.scheduler.start()
            return

        print(f"\n📅 Scheduler: Loading {len(jobs)} job(s) from CSV...")

        for job in jobs:
            self.scheduler.add_job(
                self._run_scheduled_job,
                trigger=DateTrigger(run_date=job["scheduled_time"]),
                args=[job["row_index"], job["prompt"]],
                id=f"schedule_row_{job['row_index']}",
                name=f"Row {job['row_index']+1}: {job['prompt'][:40]}",
            )
            print(
                f"  📌 Scheduled: Row {job['row_index']+1} "
                f"→ {job['scheduled_time'].strftime(DATETIME_FORMAT)} "
                f"— \"{job['prompt'][:50]}...\""
            )

        self.scheduler.start()
        print(f"✅ Scheduler started with {len(jobs)} job(s).\n")
