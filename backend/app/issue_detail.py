from __future__ import annotations

CHANNEL_LABELS = {
    "csat": "CSAT Survey",
    "guest_services_inbox": "Guest Services Inbox",
    "contact_form": "Contact Form",
    "public_review": "Public Review",
    "social": "Social Media",
    "kpi_email": "Staff KPI Email",
    "disruption_notification": "Disruption Alert",
}


def channel_label(channel: str) -> str:
    return CHANNEL_LABELS.get(channel, channel.replace("_", " ").title())


def detection_summary(det) -> list[dict]:
    """Human-readable detection signals for the issue detail panel."""
    if not det:
        return []
    signals = []
    if det.compounding:
        weeks = det.compounding.get("weeks", 3)
        signals.append(
            {
                "type": "compounding",
                "label": "Compounding",
                "description": f"Negative mentions persisted across {weeks} consecutive weeks at this site.",
            }
        )
    if det.cross_source:
        staff_neg = det.cross_source.get("staff_neg", 1)
        signals.append(
            {
                "type": "cross_source",
                "label": "Cross-source",
                "description": f"Guest complaints align with {staff_neg} staff KPI or disruption signal(s) this week.",
            }
        )
    if det.spike:
        signals.append(
            {
                "type": "spike",
                "label": "Spike",
                "description": (
                    f"Negatives rose from {det.spike.get('from', 0)} to {det.spike.get('to', 0)} "
                    "compared with the prior week."
                ),
            }
        )
    return signals


def audit_timeline(audit_rows: list[dict]) -> list[dict]:
    """Convert raw audit rows into a readable processing timeline."""
    timeline: list[dict] = []
    for row in audit_rows:
        cls = row.get("classification") or {}
        stage = cls.get("stage") or cls.get("agent", "processed")

        if stage == "ingestion":
            notes = []
            if cls.get("is_spam"):
                notes.append("spam filtered")
            if cls.get("is_duplicate"):
                notes.append("duplicate removed")
            if cls.get("pii_redacted"):
                notes.append("PII redacted")
            timeline.append(
                {
                    "stage": "Ingestion",
                    "detail": ", ".join(notes) if notes else "Accepted from source connector",
                }
            )
        elif stage == "translation":
            lang = (row.get("original_language") or "en").upper()
            if row.get("translated_text"):
                timeline.append(
                    {
                        "stage": "Translation",
                        "detail": f"Translated from {lang} to English ({row.get('translation_provider', 'provider')})",
                    }
                )
            else:
                timeline.append({"stage": "Translation", "detail": f"{lang} — no translation required"})
        elif stage == "scoring":
            theme = cls.get("primary_theme", "").replace("_", " ")
            sent = cls.get("sentiment", {})
            theme_sent = sent.get(cls.get("primary_theme", ""), "neutral")
            timeline.append(
                {
                    "stage": "Classification",
                    "detail": f"Theme: {theme} · Sentiment: {theme_sent} · Score: {row.get('score', 0):.2f}",
                    "rules_version": row.get("rules_version"),
                }
            )
        elif stage in ("clustering", "detection"):
            timeline.append(
                {
                    "stage": stage.replace("_", " ").title(),
                    "detail": "Linked to this issue cluster",
                }
            )
    return timeline
