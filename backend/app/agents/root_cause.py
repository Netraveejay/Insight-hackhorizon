from __future__ import annotations

from collections import Counter

from app.rules import RulesConfig
from app.schemas import Cluster, Detection, ScoredItem

# Theme-level default root cause taxonomy (operations-owned, rules-aligned)
THEME_ROOT_CAUSES: dict[str, dict] = {
    "projection_quality": {
        "category": "Equipment — projection",
        "default": "Projector lamp degradation, alignment drift, or brightness calibration",
        "keywords": {
            "lamp": "Projector lamp nearing end-of-life or misaligned",
            "dim": "Low lamp output or incorrect brightness setting",
            "dark": "Lamp output insufficient or auditorium lighting interference",
            "flicker": "Unstable lamp power or failing bulb",
            "blurry": "Focus alignment or lens contamination",
            "focus": "Projector focus out of calibration",
            "washed": "Incorrect colour/contrast calibration",
        },
    },
    "ticketing_queue": {
        "category": "Operations — front of house",
        "default": "Insufficient staffing or POS throughput at peak times",
        "keywords": {
            "queue": "Queue management — understaffed peak windows",
            "wait": "Transaction time exceeds guest tolerance",
            "slow": "POS or concession staffing bottleneck",
            "ticket": "Ticketing system delay or training gap",
        },
    },
    "f_and_b": {
        "category": "Concessions — product & prep",
        "default": "Food holding time, prep batching, or equipment temperature",
        "keywords": {
            "cold": "Product held too long or warmer malfunction",
            "lukewarm": "Holding cabinet temperature below standard",
            "popcorn": "Popper batch timing or stale product rotation",
            "coffee": "Machine maintenance or bean/milk supply",
        },
    },
    "cleanliness": {
        "category": "Facilities — hygiene",
        "default": "Cleaning cadence or staffing gap in auditorium/foyer",
        "keywords": {
            "dirty": "Missed cleaning cycle or spill response delay",
            "sticky": "Auditorium cleaning not completed between sessions",
            "smell": "Waste removal or restroom maintenance",
        },
    },
    "staff_service": {
        "category": "People — guest service",
        "default": "Training, staffing levels, or escalation handling",
        "keywords": {
            "rude": "Service behaviour — coaching required",
            "unhelpful": "Knowledge gap or empowerment to resolve",
        },
    },
    "audio_sound": {
        "category": "Equipment — audio",
        "default": "Speaker, amplifier, or soundtrack sync issue",
        "keywords": {
            "volume": "Audio level calibration",
            "muffled": "Speaker fault or obstruction",
            "cut out": "Amplifier or distribution failure",
        },
    },
}


class RootCauseAgent:
    """Deterministic root-cause analysis from theme, evidence text, and detection signals."""

    def run(
        self,
        cluster: Cluster,
        detection: Detection,
        scored_items: list[ScoredItem],
        rules: RulesConfig,
    ) -> dict:
        theme_cfg = THEME_ROOT_CAUSES.get(
            cluster.theme,
            {
                "category": "Operations — general",
                "default": f"Recurring guest friction at site for {cluster.theme.replace('_', ' ')}",
                "keywords": {},
            },
        )

        neg_texts = [
            s.text.lower()
            for s in scored_items
            if s.id in cluster.item_ids
            and s.sentiment.get(s.primary_theme) == "negative"
        ]
        combined = " ".join(neg_texts)

        matched: list[str] = []
        for keyword, cause in theme_cfg.get("keywords", {}).items():
            if keyword in combined:
                matched.append(cause)

        if matched:
            summary = matched[0]
            if len(matched) > 1:
                summary += f" Secondary factor: {matched[1].lower()}"
        else:
            summary = theme_cfg["default"]

        factors: list[str] = []
        if detection.compounding:
            weeks = detection.compounding.get("weeks", 3)
            factors.append(f"Recurring for {weeks} weeks — not an isolated incident")
        if detection.cross_source:
            factors.append("Staff KPI/disruption signals confirm guest complaints")
        if detection.spike:
            factors.append(
                f"Volume spike ({detection.spike.get('from', 0)} → {detection.spike.get('to', cluster.neg)} negatives)"
            )
        if cluster.source_type == "mixed":
            factors.append("Both guest and staff sources contributing")

        staff_evidence = [s for s in scored_items if s.id in cluster.item_ids and s.source_type == "staff"]
        if staff_evidence:
            factors.append(f"{len(staff_evidence)} staff report(s) in cluster")

        confidence = "high" if detection.cross_source and detection.compounding else "medium"
        if matched and detection.compounding:
            confidence = "high"
        elif not matched:
            confidence = "low"

        return {
            "category": theme_cfg["category"],
            "summary": summary,
            "contributing_factors": factors,
            "confidence": confidence,
            "evidence_keywords": list(dict.fromkeys(k for k in theme_cfg.get("keywords", {}) if k in combined))[:5],
        }
