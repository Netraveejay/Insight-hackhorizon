from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class RulesConfig(BaseModel):
    version: str
    channel_weights: dict[str, float]
    staff_weight: float = 0.9
    confidence_bands: dict[str, int]
    high_urgency_keywords: list[str]
    detection: dict[str, int]
    sla: dict[str, dict[str, int]] = Field(
        default_factory=lambda: {
            "P1": {"response_hours": 4, "resolution_hours": 48},
            "P2": {"response_hours": 24, "resolution_hours": 72},
            "P3": {"response_hours": 48, "resolution_hours": 168},
        }
    )
    themes: dict[str, list[str]]
    relevance_filter: dict[str, list[str]]
    site_size_weights: dict[str, float] = Field(default_factory=dict)
    sentiment: dict[str, list[str]] = Field(default_factory=dict)
    translation: dict[str, Any] = Field(default_factory=lambda: {"target_language": "en", "low_confidence_flag_below": 0.6})

    def channel_weight_for(self, channel: str, source_type: str) -> float:
        if source_type == "staff":
            return self.staff_weight
        return self.channel_weights.get(channel, 0.5)

    def site_size_weight(self, site_id: str) -> float:
        return self.site_size_weights.get(site_id, 1.0)

    def confidence_band_for(self, volume: int) -> str:
        high = self.confidence_bands.get("high", 20)
        medium = self.confidence_bands.get("medium", 8)
        if volume >= high:
            return "high"
        if volume >= medium:
            return "medium"
        return "low"


_loaded_path: Path | None = None
_cached_config: RulesConfig | None = None


def load_rules(path: Path | None = None) -> RulesConfig:
    global _loaded_path, _cached_config
    from app.config import get_settings

    settings = get_settings()
    rules_path = path or settings.resolved_rules_path
    if _cached_config is not None and _loaded_path == rules_path:
        return _cached_config

    with open(rules_path) as f:
        data = yaml.safe_load(f)
    config = RulesConfig.model_validate(data)
    _loaded_path = rules_path
    _cached_config = config
    return config


def save_rules(config: RulesConfig, path: Path | None = None) -> Path:
    global _loaded_path, _cached_config
    from app.config import get_settings

    settings = get_settings()
    rules_path = path or settings.resolved_rules_path
    data = config.model_dump()
    with open(rules_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    _loaded_path = rules_path
    _cached_config = config
    return rules_path


def apply_rescore_overrides(base: RulesConfig, overrides: dict[str, Any]) -> RulesConfig:
    data = base.model_dump()
    if overrides.get("channel_weights"):
        data["channel_weights"].update(overrides["channel_weights"])
    if overrides.get("staff_weight") is not None:
        data["staff_weight"] = overrides["staff_weight"]
    if overrides.get("confidence_bands"):
        data["confidence_bands"].update(overrides["confidence_bands"])
    if overrides.get("detection"):
        data["detection"].update(overrides["detection"])
    # Bump patch version for audit trail
    parts = data["version"].split(".")
    if len(parts) == 2:
        data["version"] = f"{parts[0]}.{int(parts[1]) + 1}"
    else:
        data["version"] = f"{data['version']}.1"
    return RulesConfig.model_validate(data)


def invalidate_cache():
    global _loaded_path, _cached_config
    _loaded_path = None
    _cached_config = None
