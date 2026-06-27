from __future__ import annotations

import json
from pathlib import Path

from app.connectors.base import FeedbackConnector
from app.schemas import RawFeedbackItem, SourceCoverageEntry


class SeedConnector(FeedbackConnector):
    name = "seed"

    def __init__(self, seed_path: Path | None = None):
        if seed_path is None:
            seed_path = Path(__file__).resolve().parent.parent / "seed" / "data" / "feedback.json"
        self.seed_path = seed_path

    def fetch(self, week: str | None = None) -> tuple[list[RawFeedbackItem], SourceCoverageEntry]:
        if not self.seed_path.exists():
            return [], SourceCoverageEntry(
                connector=self.name,
                status="failed",
                item_count=0,
                message=f"Seed file not found: {self.seed_path}. Run 'make seed' first.",
            )
        with open(self.seed_path) as f:
            raw = json.load(f)
        items = [RawFeedbackItem.model_validate(r) for r in raw]
        if week:
            items = [i for i in items if i.week == week]
        return items, SourceCoverageEntry(
            connector=self.name,
            status="ok",
            item_count=len(items),
            message="Seed data loaded successfully",
        )
