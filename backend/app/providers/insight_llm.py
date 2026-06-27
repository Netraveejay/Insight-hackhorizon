from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas import SITE_BY_ID, Cluster, Detection, Insight


class InsightLLM(ABC):
    @abstractmethod
    def draft(
        self,
        cluster: Cluster,
        detection: Detection | None,
        sample_texts: list[str],
        rules_version: str,
    ) -> Insight:
        ...


OWNER_MAP = {
    "projection_quality": "Technical Operations",
    "audio_sound": "Technical Operations",
    "f_and_b": "Concessions Manager",
    "cleanliness": "Site Manager",
    "staff_service": "Guest Services Lead",
    "ticketing_queue": "Front of House Manager",
    "booking_app": "Digital Product",
    "value_pricing": "Commercial",
    "comfort_seating": "Facilities",
    "accessibility": "Guest Services Lead",
}


class TemplateInsightLLM(InsightLLM):
    def draft(
        self,
        cluster: Cluster,
        detection: Detection | None,
        sample_texts: list[str],
        rules_version: str,
    ) -> Insight:
        site_name = SITE_BY_ID.get(cluster.site_id, {}).get("name", cluster.site_id)
        theme_label = cluster.theme.replace("_", " ").title()
        trends: list[str] = []
        if detection:
            if detection.compounding:
                trends.append(f"compounding over {detection.compounding.get('weeks', 3)} weeks")
            if detection.cross_source:
                trends.append("cross-source staff confirmation")
            if detection.spike:
                trends.append(f"spike from {detection.spike.get('from')} to {detection.spike.get('to')} negatives")

        trend_str = ", ".join(trends) if trends else f"{cluster.neg} negative mentions"
        owner = OWNER_MAP.get(cluster.theme, "Site Manager")

        insight = (
            f"At {site_name}, {theme_label} shows {trend_str}. "
            f"Recommend {owner} inspect root cause and brief the site team within 48 hours. "
            f"Internal review only — do not contact guests."
        )
        words = insight.split()
        if len(words) > 60:
            insight = " ".join(words[:60])

        return Insight(
            cluster_id=cluster.cluster_id,
            insight=insight,
            evidence_sample=[],
            owner_suggested=owner,
            rules_version=rules_version,
            draft_source="template",
        )


class OpenAIInsightLLM(InsightLLM):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def draft(
        self,
        cluster: Cluster,
        detection: Detection | None,
        sample_texts: list[str],
        rules_version: str,
    ) -> Insight:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            site_name = SITE_BY_ID.get(cluster.site_id, {}).get("name", cluster.site_id)
            theme_label = cluster.theme.replace("_", " ").title()
            owner = OWNER_MAP.get(cluster.theme, "Site Manager")

            system = (
                "You draft internal recommendations for cinema operations staff ONLY. "
                "Never address guests. Never claim actions were taken. Max 60 words. "
                "Name site, theme, trend, and a concrete next step. Suggest an internal owner."
            )
            user = (
                f"Site: {site_name}, Theme: {theme_label}, Week: {cluster.week}, "
                f"Negatives: {cluster.neg}, Detection: {detection.model_dump() if detection else 'none'}, "
                f"Sample feedback: {' | '.join(sample_texts[:3])}"
            )
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=120,
            )
            text = resp.choices[0].message.content or ""
            words = text.split()
            if len(words) > 60:
                text = " ".join(words[:60])

            return Insight(
                cluster_id=cluster.cluster_id,
                insight=text,
                evidence_sample=[],
                owner_suggested=owner,
                rules_version=rules_version,
                draft_source="llm",
            )
        except Exception:
            return TemplateInsightLLM().draft(cluster, detection, sample_texts, rules_version)


def get_insight_llm(api_key: str) -> InsightLLM:
    if api_key:
        return OpenAIInsightLLM(api_key)
    return TemplateInsightLLM()
