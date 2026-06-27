from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Reference data (fictional sites only) ───────────────────────────────────

SITES = [
    {"id": "harbourview", "name": "Harbourview", "email": "harbourview@insight-ops.internal"},
    {"id": "northgate", "name": "Northgate", "email": "northgate@insight-ops.internal"},
    {"id": "riverside", "name": "Riverside", "email": "riverside@insight-ops.internal"},
    {"id": "eastfield", "name": "Eastfield", "email": "eastfield@insight-ops.internal"},
    {"id": "parkland", "name": "Parkland", "email": "parkland@insight-ops.internal"},
    {"id": "westgate", "name": "Westgate", "email": "westgate@insight-ops.internal"},
    {"id": "lakeside", "name": "Lakeside", "email": "lakeside@insight-ops.internal"},
    {"id": "hillcrest", "name": "Hillcrest", "email": "hillcrest@insight-ops.internal"},
    {"id": "southbank", "name": "Southbank", "email": "southbank@insight-ops.internal"},
    {"id": "cityplaza", "name": "Cityplaza", "email": "cityplaza@insight-ops.internal"},
    {"id": "greenwood", "name": "Greenwood", "email": "greenwood@insight-ops.internal"},
    {"id": "baytown", "name": "Baytown", "email": "baytown@insight-ops.internal"},
    {"id": "fairmont", "name": "Fairmont", "email": "fairmont@insight-ops.internal"},
    {"id": "oakridge", "name": "Oakridge", "email": "oakridge@insight-ops.internal"},
    {"id": "sunset", "name": "Sunset", "email": "sunset@insight-ops.internal"},
    {"id": "meadowbrook", "name": "Meadowbrook", "email": "meadowbrook@insight-ops.internal"},
    {"id": "kingsway", "name": "Kingsway", "email": "kingsway@insight-ops.internal"},
    {"id": "pinehurst", "name": "Pinehurst", "email": "pinehurst@insight-ops.internal"},
    {"id": "crestwood", "name": "Crestwood", "email": "crestwood@insight-ops.internal"},
    {"id": "maplewood", "name": "Maplewood", "email": "maplewood@insight-ops.internal"},
    {"id": "brookside", "name": "Brookside", "email": "brookside@insight-ops.internal"},
]

SITE_BY_ID = {s["id"]: s for s in SITES}

GUEST_CHANNELS = ("csat", "guest_services_inbox", "contact_form", "public_review", "social")
STAFF_CHANNELS = ("kpi_email", "disruption_notification")
ALL_CHANNELS = GUEST_CHANNELS + STAFF_CHANNELS


# ── Agent I/O contracts ─────────────────────────────────────────────────────

class RawFeedbackItem(BaseModel):
    source_type: Literal["guest", "staff"]
    channel: str
    site_id: str
    ts: datetime
    week: str
    rating: int | None = None
    theme_hint: str | None = None
    sentiment_hint: str | None = None
    lang_hint: str | None = None  # seed/eval only
    text: str


class IngestedItem(RawFeedbackItem):
    id: str
    channel_weight: float
    is_duplicate: bool
    is_spam: bool
    pii_redacted: bool


class TranslatedItem(IngestedItem):
    original_text: str
    original_language: str
    translated: bool
    text: str  # English working text
    translation_provider: str
    translation_confidence: Literal["high", "low"]


class ScoredItem(TranslatedItem):
    themes: list[str]
    primary_theme: str
    sentiment: dict[str, Literal["positive", "negative", "neutral"]]
    urgency: Literal["normal", "high"]
    relevant: bool
    score: float
    rules_version: str


class Cluster(BaseModel):
    cluster_id: str
    site_id: str
    theme: str
    week: str
    volume: int
    neg: int
    pos: int
    net_sentiment: float
    confidence_band: Literal["high", "medium", "low"]
    item_ids: list[str]
    source_type: Literal["guest", "staff", "mixed"] = "guest"


class Detection(BaseModel):
    cluster_id: str
    spike: dict[str, Any] | None = None
    compounding: dict[str, Any] | None = None
    cross_source: dict[str, Any] | None = None
    priority: Literal["P1", "P2", "P3"] | None = None
    root_cause: dict[str, Any] | None = None
    sla: dict[str, Any] | None = None


class Insight(BaseModel):
    cluster_id: str
    insight: str
    evidence_sample: list[str]
    owner_suggested: str
    rules_version: str
    status: Literal["draft_recommendation"] = "draft_recommendation"
    draft_source: Literal["llm", "template"] = "template"


class AuditRecord(BaseModel):
    item_id: str
    snapshot_at_ingest: dict[str, Any]
    original_text: str
    original_language: str
    translated_text: str | None
    translation_provider: str | None
    classification: dict[str, Any]
    score: float
    rules_version: str
    confidence_band: str | None = None
    review_override: dict[str, Any] | None = None


class LanguageStat(BaseModel):
    language: str
    count: int
    translated_count: int


class LanguageStatsReport(BaseModel):
    run_id: str
    week: str
    languages: list[LanguageStat]
    total_items: int


class SourceCoverageEntry(BaseModel):
    connector: str
    status: Literal["ok", "partial", "failed"]
    item_count: int = 0
    message: str = ""


class SourceCoverageReport(BaseModel):
    run_id: str
    entries: list[SourceCoverageEntry]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PipelineRunResult(BaseModel):
    run_id: str
    week: str
    items_ingested: int
    items_translated: int
    items_scored: int
    clusters: int
    detections: int
    insights: int
    rules_version: str
    steps: list[dict[str, Any]] = Field(default_factory=list)
    hero_cluster_id: str | None = None
    outputs: list[dict[str, Any]] = Field(default_factory=list)
    explanation: dict[str, Any] | None = None


class StepExplanation(BaseModel):
    id: str
    label: str
    what_happened: str
    why_it_matters: str
    input_label: str
    output_label: str
    highlights: list[str] = Field(default_factory=list)


class HeroExplanation(BaseModel):
    cluster_id: str
    site_name: str
    theme_label: str
    priority: str
    headline: str
    story: str
    reasons: list[str]
    next_views: list[str] = Field(default_factory=list)


class PipelineExplanation(BaseModel):
    headline: str
    summary: str
    audience_note: str = "Internal operations intelligence — informs staff, never contacts guests."
    steps: list[StepExplanation]
    hero: HeroExplanation | None = None
    glossary: dict[str, str] = Field(default_factory=dict)


class AskRequest(BaseModel):
    question: str
    week: str | None = None


class AskResponse(BaseModel):
    answer: str
    references: list[str]


class RulesRescoreRequest(BaseModel):
    channel_weights: dict[str, float] | None = None
    staff_weight: float | None = None
    confidence_bands: dict[str, int] | None = None
    detection: dict[str, int] | None = None
