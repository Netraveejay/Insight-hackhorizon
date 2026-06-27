"""Load feedback from a user-provided JSON file (production import path)."""

from __future__ import annotations

import json
from pathlib import Path

from app.connectors.base import FeedbackConnector
from app.schemas import RawFeedbackItem, SourceCoverageEntry


class FileConnector(FeedbackConnector):
    """Read real feedback exports — same JSON schema as seed data."""

    name = "file"

    def __init__(self, file_path: Path):
        self.file_path = file_path

    def fetch(self, week: str | None = None) -> tuple[list[RawFeedbackItem], SourceCoverageEntry]:
        if not self.file_path.exists():
            return [], SourceCoverageEntry(
                connector=self.name,
                status="failed",
                item_count=0,
                message=f"Feedback file not found: {self.file_path}",
            )
        with open(self.file_path) as f:
            raw = json.load(f)
        items = [RawFeedbackItem.model_validate(r) for r in raw]
        if week:
            items = [i for i in items if i.week == week]
        return items, SourceCoverageEntry(
            connector=self.name,
            status="ok",
            item_count=len(items),
            message=f"Loaded from {self.file_path.name}",
        )
