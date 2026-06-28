from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FeedbackRaw(Base):
    __tablename__ = "feedback_raw"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    source_type: Mapped[str] = mapped_column(String)
    channel: Mapped[str] = mapped_column(String)
    site_id: Mapped[str] = mapped_column(String, index=True)
    ts: Mapped[datetime] = mapped_column(DateTime)
    week: Mapped[str] = mapped_column(String, index=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)


class FeedbackTranslated(Base):
    __tablename__ = "feedback_translated"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    site_id: Mapped[str] = mapped_column(String, index=True)
    week: Mapped[str] = mapped_column(String, index=True)
    original_text: Mapped[str] = mapped_column(Text)
    original_language: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    translated: Mapped[bool] = mapped_column(Boolean, default=False)
    translation_provider: Mapped[str] = mapped_column(String)
    translation_confidence: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)


class FeedbackScored(Base):
    __tablename__ = "feedback_scored"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    site_id: Mapped[str] = mapped_column(String, index=True)
    week: Mapped[str] = mapped_column(String, index=True)
    primary_theme: Mapped[str] = mapped_column(String, index=True)
    themes: Mapped[list] = mapped_column(JSON)
    sentiment: Mapped[dict] = mapped_column(JSON)
    urgency: Mapped[str] = mapped_column(String)
    relevant: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float] = mapped_column(Float)
    rules_version: Mapped[str] = mapped_column(String)
    channel: Mapped[str] = mapped_column(String)
    source_type: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)


class ClusterRow(Base):
    __tablename__ = "clusters"
    __table_args__ = (Index("ix_clusters_site_theme_week", "site_id", "theme", "week"),)

    cluster_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    site_id: Mapped[str] = mapped_column(String)
    theme: Mapped[str] = mapped_column(String)
    week: Mapped[str] = mapped_column(String)
    volume: Mapped[int] = mapped_column(Integer)
    neg: Mapped[int] = mapped_column(Integer)
    pos: Mapped[int] = mapped_column(Integer)
    net_sentiment: Mapped[float] = mapped_column(Float)
    confidence_band: Mapped[str] = mapped_column(String)
    item_ids: Mapped[list] = mapped_column(JSON)
    source_type: Mapped[str] = mapped_column(String, default="guest")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class DetectionRow(Base):
    __tablename__ = "detections"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    cluster_id: Mapped[str] = mapped_column(String, index=True)
    spike: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    compounding: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cross_source: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    priority: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class InsightRow(Base):
    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    cluster_id: Mapped[str] = mapped_column(String, index=True)
    insight: Mapped[str] = mapped_column(Text)
    evidence_sample: Mapped[list] = mapped_column(JSON)
    owner_suggested: Mapped[str] = mapped_column(String)
    rules_version: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    draft_source: Mapped[str] = mapped_column(String, default="template")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class AlertRow(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    week: Mapped[str] = mapped_column(String, index=True)
    alert_type: Mapped[str] = mapped_column(String)
    site_id: Mapped[str] = mapped_column(String)
    theme: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str] = mapped_column(Text)
    priority: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditRecordRow(Base):
    __tablename__ = "audit_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    item_id: Mapped[str] = mapped_column(String, index=True)
    snapshot_at_ingest: Mapped[dict] = mapped_column(JSON)
    original_text: Mapped[str] = mapped_column(Text, default="")
    original_language: Mapped[str] = mapped_column(String, default="en")
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    translation_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    classification: Mapped[dict] = mapped_column(JSON)
    score: Mapped[float] = mapped_column(Float)
    rules_version: Mapped[str] = mapped_column(String)
    confidence_band: Mapped[str | None] = mapped_column(String, nullable=True)
    review_override: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SourceCoverageRow(Base):
    __tablename__ = "source_coverage"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    connector: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LanguageStatsRow(Base):
    __tablename__ = "language_stats"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    week: Mapped[str] = mapped_column(String, index=True)
    language: Mapped[str] = mapped_column(String)
    count: Mapped[int] = mapped_column(Integer)
    translated_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    cadence: Mapped[str] = mapped_column(String, default="manual")
    week: Mapped[str] = mapped_column(String)
    rules_version: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="completed")
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DistributionLogRow(Base):
    __tablename__ = "distribution_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    target_type: Mapped[str] = mapped_column(String)
    target: Mapped[str] = mapped_column(String)
    payload_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GeneratedReportRow(Base):
    __tablename__ = "generated_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    week: Mapped[str] = mapped_column(String, index=True)
    report_type: Mapped[str] = mapped_column(String)  # site | digest
    site_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String)
    recipient_email: Mapped[str] = mapped_column(String)
    file_name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentMessageRow(Base):
    __tablename__ = "agent_messages"
    __table_args__ = (
        Index("ix_agent_messages_correlation_ts", "correlation_id", "ts"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    correlation_id: Mapped[str] = mapped_column(String, index=True)
    from_agent: Mapped[str] = mapped_column(String)
    to_agent: Mapped[str] = mapped_column(String)
    intent: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String)
    payload_ref: Mapped[str | None] = mapped_column(String, nullable=True)


class TriggerRow(Base):
    __tablename__ = "triggers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, index=True)
    source: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class AgentRunRow(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    trigger_id: Mapped[str] = mapped_column(String, index=True)
    goal: Mapped[str] = mapped_column(Text)
    runner: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, index=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ReasoningStepRow(Base):
    __tablename__ = "reasoning_steps"
    __table_args__ = (Index("ix_reasoning_steps_run_step", "run_id", "step_no"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    step_no: Mapped[int] = mapped_column(Integer)
    agent: Mapped[str] = mapped_column(String)
    phase: Mapped[str] = mapped_column(String)
    thought: Mapped[str] = mapped_column(Text)
    action: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
