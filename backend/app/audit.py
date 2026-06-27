from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AuditRecordRow
from app.schemas import AuditRecord, IngestedItem, ScoredItem, TranslatedItem


def _audit_id(item_id: str, run_id: str, suffix: str = "") -> str:
    return hashlib.sha256(f"{item_id}:{run_id}:{suffix}".encode()).hexdigest()[:16]


def write_ingest_audit(db: Session, run_id: str, item: IngestedItem) -> AuditRecord:
    record = AuditRecord(
        item_id=item.id,
        snapshot_at_ingest=item.model_dump(mode="json"),
        original_text=item.text,
        original_language="unknown",
        translated_text=None,
        translation_provider=None,
        classification={"stage": "ingestion", "is_duplicate": item.is_duplicate, "is_spam": item.is_spam},
        score=0.0,
        rules_version="",
        confidence_band=None,
    )
    row = AuditRecordRow(
        id=_audit_id(item.id, run_id, "ingest"),
        run_id=run_id,
        item_id=item.id,
        snapshot_at_ingest=record.snapshot_at_ingest,
        original_text=item.text,
        original_language="unknown",
        classification=record.classification,
        score=0.0,
        rules_version="",
    )
    db.merge(row)
    return record


def write_translation_audit(db: Session, run_id: str, item: TranslatedItem) -> AuditRecord:
    record = AuditRecord(
        item_id=item.id,
        snapshot_at_ingest=item.model_dump(mode="json"),
        original_text=item.original_text,
        original_language=item.original_language,
        translated_text=item.text if item.translated else None,
        translation_provider=item.translation_provider,
        classification={
            "stage": "translation",
            "translated": item.translated,
            "translation_confidence": item.translation_confidence,
        },
        score=0.0,
        rules_version="",
    )
    row = AuditRecordRow(
        id=_audit_id(item.id, run_id, "translate"),
        run_id=run_id,
        item_id=item.id,
        snapshot_at_ingest=record.snapshot_at_ingest,
        original_text=item.original_text,
        original_language=item.original_language,
        translated_text=item.text if item.translated else None,
        translation_provider=item.translation_provider,
        classification=record.classification,
        score=0.0,
        rules_version="",
    )
    db.merge(row)
    return record


def write_score_audit(
    db: Session,
    run_id: str,
    item: ScoredItem,
    confidence_band: str | None = None,
) -> AuditRecord:
    record = AuditRecord(
        item_id=item.id,
        snapshot_at_ingest=item.model_dump(mode="json"),
        original_text=item.original_text,
        original_language=item.original_language,
        translated_text=item.text if item.translated else None,
        translation_provider=item.translation_provider,
        classification={
            "stage": "scoring",
            "themes": item.themes,
            "primary_theme": item.primary_theme,
            "sentiment": item.sentiment,
            "urgency": item.urgency,
            "relevant": item.relevant,
        },
        score=item.score,
        rules_version=item.rules_version,
        confidence_band=confidence_band,
    )
    row = AuditRecordRow(
        id=_audit_id(item.id, run_id, "score"),
        run_id=run_id,
        item_id=item.id,
        snapshot_at_ingest=record.snapshot_at_ingest,
        original_text=item.original_text,
        original_language=item.original_language,
        translated_text=item.text if item.translated else None,
        translation_provider=item.translation_provider,
        classification=record.classification,
        score=record.score,
        rules_version=record.rules_version,
        confidence_band=confidence_band,
    )
    db.merge(row)
    return record


def write_lineage(db: Session, run_id: str, agent: str, entity_id: str, payload: dict) -> None:
    row = AuditRecordRow(
        id=_audit_id(f"{agent}:{entity_id}", run_id),
        run_id=run_id,
        item_id=entity_id,
        snapshot_at_ingest=payload,
        original_text=payload.get("original_text", ""),
        original_language=payload.get("original_language", "en"),
        classification={"agent": agent, "timestamp": datetime.utcnow().isoformat()},
        score=0.0,
        rules_version=payload.get("rules_version", ""),
        confidence_band=payload.get("confidence_band"),
    )
    db.merge(row)
