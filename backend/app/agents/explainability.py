from __future__ import annotations

from collections import Counter

from app.schemas import (
    SITE_BY_ID,
    Cluster,
    Detection,
    HeroExplanation,
    IngestedItem,
    Insight,
    PipelineExplanation,
    ScoredItem,
    StepExplanation,
    TranslatedItem,
)


class ExplainabilityAgent:
    """Deterministic explainability — plain-language narrative for pipeline runs."""

    def run(
        self,
        week: str,
        run_id: str,
        rules_version: str,
        cadence: str,
        ingested: list[IngestedItem],
        translated: list[TranslatedItem],
        scored: list[ScoredItem],
        current_clusters: list[Cluster],
        detections: list[Detection],
        insights: list[Insight],
        alerts_count: int,
        hero_cluster_id: str | None,
    ) -> PipelineExplanation:
        week_items = [i for i in ingested if i.week == week]
        spam = sum(1 for i in week_items if i.is_spam)
        dupes = sum(1 for i in week_items if i.is_duplicate)
        pii = sum(1 for i in week_items if i.pii_redacted)
        scored_week = [s for s in scored if s.week == week and s.relevant and not s.is_spam and not s.is_duplicate]
        non_relevant = sum(1 for s in scored if s.week == week and not s.relevant)
        translated_week = [t for t in translated if t.week == week and t.translated]
        lang_counts = Counter(t.original_language for t in translated if t.week == week and t.translated)

        p1 = [d for d in detections if d.priority == "P1"]
        cross = sum(1 for d in detections if d.cross_source)
        compound = sum(1 for d in detections if d.compounding)

        steps = [
            self._explain_ingest(len(week_items), spam, dupes, pii, cadence),
            self._explain_translate(len(translated_week), lang_counts),
            self._explain_score(len(scored_week), non_relevant, rules_version),
            self._explain_cluster(len(current_clusters), week),
            self._explain_detect(len(detections), len(p1), cross, compound),
            self._explain_insight(len(insights)),
            self._explain_output(alerts_count, len(detections)),
        ]

        hero = self._explain_hero(hero_cluster_id, current_clusters, detections, insights)

        headline = self._headline(len(week_items), len(p1), hero)
        summary = self._summary(
            week, len(week_items), len(scored_week), len(current_clusters), len(p1), hero, alerts_count
        )

        return PipelineExplanation(
            headline=headline,
            summary=summary,
            steps=steps,
            hero=hero,
            glossary={
                "Cross-source": "Guest complaints confirmed by a separate staff KPI or disruption signal in the same week.",
                "Compounding": "The same site×theme issue has negative mentions across multiple consecutive weeks.",
                "Cluster": "Grouped feedback for one cinema site, one theme, and one week.",
                "P1": "Highest priority — needs leadership attention within 48 hours.",
            },
        )

    def _headline(self, ingested: int, p1_count: int, hero: HeroExplanation | None) -> str:
        if hero:
            return (
                f"{ingested} messages processed → {p1_count} critical alert"
                f"{'s' if p1_count != 1 else ''}: {hero.site_name} {hero.theme_label}"
            )
        return f"{ingested} messages processed → {p1_count} critical alerts for operations review"

    def _summary(
        self,
        week: str,
        ingested: int,
        scored: int,
        clusters: int,
        p1_count: int,
        hero: HeroExplanation | None,
        alerts: int,
    ) -> str:
        parts = [
            f"For week {week}, the pipeline collected {ingested} guest and staff messages across 21 cinema sites.",
            f"After cleaning spam and duplicates, {scored} relevant items were scored into {clusters} site×theme clusters.",
        ]
        if hero:
            parts.append(
                f"The Explainability Agent flagged {hero.site_name} ({hero.theme_label}) as {hero.priority} "
                f"because guest complaints align with staff signals — not a one-off review."
            )
        parts.append(
            f"{alerts} Teams alerts and an executive digest were queued for internal distribution only."
        )
        return " ".join(parts)

    def _explain_ingest(
        self, total: int, spam: int, dupes: int, pii: int, cadence: str
    ) -> StepExplanation:
        kept = total - spam - dupes
        highlights = [
            f"{total} raw messages loaded from the seed connector",
            f"{spam} spam review-bomb filtered" if spam else "No spam bombs detected",
            f"{dupes} duplicate texts removed" if dupes else "No duplicate texts",
            f"{pii} items had personal details redacted" if pii else "No PII redaction needed",
        ]
        return StepExplanation(
            id="ingest",
            label="Ingestion Agent",
            what_happened=(
                f"Loaded {total} messages from CSAT surveys, inbox, public reviews, social, and staff KPI emails. "
                f"Removed {spam + dupes} unusable items and redacted private details where found."
            ),
            why_it_matters=(
                "Operations teams only see trustworthy, de-duplicated feedback. "
                "Spam bombs and repeated copy-paste reviews would otherwise skew priorities."
            ),
            input_label="Raw feedback (7 channels)",
            output_label=f"{kept} clean messages",
            highlights=highlights,
        )

    def _explain_translate(self, count: int, langs: Counter) -> StepExplanation:
        lang_str = ", ".join(f"{k.upper()} ({v})" for k, v in langs.most_common()) if langs else "none"
        return StepExplanation(
            id="translate",
            label="Translation Agent",
            what_happened=(
                f"Detected non-English text and translated {count} item{'s' if count != 1 else ''} to English. "
                f"Original wording is kept for audit. Languages: {lang_str or 'all English'}."
            ),
            why_it_matters=(
                "Scoring and clustering run on one language so themes are comparable across sites. "
                "Multilingual guest voice is not lost — originals remain in the Live Feed."
            ),
            input_label="Clean messages",
            output_label=f"{count} translated · originals retained",
            highlights=[
                "Language detection is automatic",
                "English text passes through unchanged",
                "Translated items show an Original text toggle in Live Feed",
            ],
        )

    def _explain_score(self, scored: int, skipped: int, rules_version: str) -> StepExplanation:
        return StepExplanation(
            id="score",
            label="Scoring Agent",
            what_happened=(
                f"Applied rules v{rules_version} to label each message with themes (e.g. projection, F&B), "
                f"sentiment, and urgency. {scored} relevant items scored; {skipped} marked non-controllable or filtered."
            ),
            why_it_matters=(
                "This is the classification layer — every downstream alert depends on consistent theme and sentiment tags. "
                "Rules are transparent and adjustable in the Rules Engine view."
            ),
            input_label="English working text",
            output_label=f"{scored} scored items",
            highlights=[
                "Deterministic lexicon + rules (no black box)",
                "Staff KPI emails weighted higher than casual social posts",
                "Disruption notifications get high urgency",
            ],
        )

    def _explain_cluster(self, clusters: int, week: str) -> StepExplanation:
        return StepExplanation(
            id="cluster",
            label="Clustering Agent",
            what_happened=(
                f"Grouped scored items into {clusters} clusters — one per cinema site, theme, and week ({week}). "
                "Each cluster counts volume, positive/negative mentions, and confidence."
            ),
            why_it_matters=(
                "Individual reviews are noisy. Clustering surfaces patterns: "
                "'Harbourview · projection quality · this week' is one actionable unit."
            ),
            input_label="Scored items",
            output_label=f"{clusters} clusters",
            highlights=[
                "Site × theme × week is the standard operations grain",
                "Mixed guest+staff clusters flagged when both sources contribute",
            ],
        )

    def _explain_detect(
        self, total: int, p1: int, cross: int, compound: int
    ) -> StepExplanation:
        return StepExplanation(
            id="detect",
            label="Detection Agent",
            what_happened=(
                f"Scanned clusters for three risk patterns: spikes, multi-week compounding ({compound}), "
                f"and cross-source confirmation ({cross}). Raised {total} flags including {p1} P1 critical."
            ),
            why_it_matters=(
                "A single bad review is not an incident. P1 fires when guests AND staff agree something is wrong "
                "and the issue has persisted — the highest-confidence signal in the system."
            ),
            input_label="Clusters (current + history)",
            output_label=f"{total} detections ({p1} P1)",
            highlights=[
                "Spike: negatives jumped vs last week",
                "Compounding: same issue across 3+ weeks",
                "Cross-source: guest complaints + staff KPI alignment",
            ],
        )

    def _explain_insight(self, count: int) -> StepExplanation:
        return StepExplanation(
            id="insight",
            label="Insight Agent",
            what_happened=(
                f"Drafted {count} internal recommendation{'s' if count != 1 else ''} for P1–P3 issues. "
                "Suggests an owner (e.g. Technical Operations) and next step — never guest-facing text."
            ),
            why_it_matters=(
                "Turns a detection flag into an actionable brief for site and HQ teams. "
                "Uses an LLM when configured; falls back to templates offline."
            ),
            input_label="Priority detections",
            output_label=f"{count} draft recommendations",
            highlights=[
                "Internal review only — status: draft_recommendation",
                "Evidence item IDs linked for audit trail",
            ],
        )

    def _explain_output(self, alerts: int, issues: int) -> StepExplanation:
        return StepExplanation(
            id="output",
            label="Output & Distribution",
            what_happened=(
                f"Published {issues} prioritised issues, sent {alerts} Teams alerts, "
                "generated 22 downloadable HTML reports (21 sites + executive digest), "
                "and queued distribution to manager inboxes."
            ),
            why_it_matters=(
                "The pipeline ends where human judgment begins. "
                "Insight informs — it does not auto-reply to guests or trigger refunds."
            ),
            input_label="Insights + detections",
            output_label=f"{alerts} alerts · 1 digest · 21 site reports",
            highlights=[
                "Teams alerts for P1/P2 cross-source and compounding",
                "Per-site reports fan out to site manager inboxes (logged only in demo)",
            ],
        )

    def _explain_hero(
        self,
        hero_cluster_id: str | None,
        clusters: list[Cluster],
        detections: list[Detection],
        insights: list[Insight],
    ) -> HeroExplanation | None:
        if not hero_cluster_id:
            return None

        cluster = next((c for c in clusters if c.cluster_id == hero_cluster_id), None)
        detection = next((d for d in detections if d.cluster_id == hero_cluster_id), None)
        insight = next((i for i in insights if i.cluster_id == hero_cluster_id), None)
        if not cluster or not detection:
            return None

        site_name = SITE_BY_ID.get(cluster.site_id, {}).get("name", cluster.site_id)
        theme_label = cluster.theme.replace("_", " ").title()
        reasons: list[str] = []

        if detection.compounding:
            weeks = detection.compounding.get("weeks", 3)
            reasons.append(
                f"Compounding: negative {theme_label} mentions at {site_name} for {weeks} consecutive weeks."
            )
        if detection.cross_source:
            staff_neg = detection.cross_source.get("staff_neg", 1)
            reasons.append(
                f"Cross-source: {cluster.neg} guest negatives plus staff KPI/disruption signals ({staff_neg} staff mentions)."
            )
        if detection.spike:
            reasons.append(
                f"Spike: negatives rose from {detection.spike.get('from', 0)} to {detection.spike.get('to', cluster.neg)} vs prior week."
            )
        if not reasons:
            reasons.append(f"{cluster.neg} negative guest mentions with high-confidence clustering.")

        story = insight.insight if insight else (
            f"{site_name} {theme_label} is the top priority because multiple independent signals agree."
        )

        return HeroExplanation(
            cluster_id=hero_cluster_id,
            site_name=site_name,
            theme_label=theme_label,
            priority=detection.priority or "P1",
            headline=f"Why {site_name} · {theme_label} is {detection.priority or 'P1'}",
            story=story,
            reasons=reasons,
            next_views=["Issues — full ranked list with audit trail", "Live Feed — original guest quotes", "Alerts — Teams notifications sent"],
        )
