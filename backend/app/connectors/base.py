from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas import RawFeedbackItem, SourceCoverageEntry


class FeedbackConnector(ABC):
    name: str

    @abstractmethod
    def fetch(self, week: str | None = None) -> tuple[list[RawFeedbackItem], SourceCoverageEntry]:
        """Return raw items and coverage status for this connector."""
        ...


class ProductionConnectorStub(FeedbackConnector):
    """Stub for production sources — M365 Graph, Google Reviews API, social listening."""

    def __init__(self, name: str, source_label: str):
        self.name = name
        self.source_label = source_label

    def fetch(self, week: str | None = None) -> tuple[list[RawFeedbackItem], SourceCoverageEntry]:
        # TODO: implement M365 Graph service account for inbox/KPI/disruption
        # TODO: implement review API/crawler for Google
        # TODO: implement social-listening provider
        return [], SourceCoverageEntry(
            connector=self.name,
            status="failed",
            item_count=0,
            message=f"Production connector '{self.source_label}' not configured — using seed data only",
        )
