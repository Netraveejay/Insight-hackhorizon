from __future__ import annotations

from app.a2a.types import AgentDefinition

# Layout: pipeline flows left→right on top row; insight branch below; chat agents bottom-left
AGENT_REGISTRY: list[AgentDefinition] = [
    AgentDefinition(id="orchestrator", name="Orchestrator", type="orchestrator", role="Sequences pipeline stages", layout_x=480, layout_y=30),
    AgentDefinition(id="connector", name="Data Connector", type="connector", role="Fetches raw feedback", layout_x=40, layout_y=120),
    AgentDefinition(id="ingestion", name="Ingestion", type="deterministic", role="Dedupe · spam · PII", layout_x=160, layout_y=120),
    AgentDefinition(id="translation", name="Translation", type="deterministic", role="Multilingual → English", layout_x=280, layout_y=120),
    AgentDefinition(id="scoring", name="Scoring", type="deterministic", role="Themes & sentiment", layout_x=400, layout_y=120),
    AgentDefinition(id="clustering", name="Clustering", type="deterministic", role="Site × theme × week", layout_x=520, layout_y=120),
    AgentDefinition(id="detection", name="Detection", type="deterministic", role="Spike · compounding", layout_x=640, layout_y=120),
    AgentDefinition(id="root_cause", name="Root Cause", type="deterministic", role="Keyword taxonomy", layout_x=760, layout_y=120),
    AgentDefinition(id="sla", name="SLA Tracker", type="deterministic", role="Response clocks", layout_x=880, layout_y=120),
    AgentDefinition(id="insight", name="Insight", type="llm", role="Draft recommendations", layout_x=640, layout_y=230),
    AgentDefinition(id="output", name="Output", type="deterministic", role="Alerts & reports", layout_x=760, layout_y=230),
    AgentDefinition(id="explainability", name="Explainability", type="deterministic", role="Pipeline narrative", layout_x=880, layout_y=230),
    AgentDefinition(id="assistant", name="Assistant", type="assistant", role="Grounded Q&A · voice", layout_x=40, layout_y=340),
    AgentDefinition(id="planner", name="Planner", type="llm", role="Plans retrieval tools", layout_x=120, layout_y=420),
    AgentDefinition(id="investigator", name="Investigator", type="llm", role="Auto P1 investigations", layout_x=260, layout_y=420),
    AgentDefinition(id="coordinator", name="Coordinator", type="coordinator", role="Routes & validates queries", layout_x=400, layout_y=340),
    AgentDefinition(id="critic", name="Critic", type="llm", role="Reviews answers · drafts", layout_x=540, layout_y=420),
]

PIPELINE_EDGES: list[tuple[str, str]] = [
    ("orchestrator", "connector"),
    ("connector", "ingestion"),
    ("ingestion", "translation"),
    ("translation", "scoring"),
    ("scoring", "clustering"),
    ("clustering", "detection"),
    ("detection", "root_cause"),
    ("root_cause", "sla"),
    ("detection", "insight"),
    ("insight", "output"),
    ("output", "explainability"),
    ("assistant", "planner"),
    ("planner", "coordinator"),
    ("assistant", "critic"),
    ("critic", "planner"),
    ("critic", "assistant"),
    ("investigator", "coordinator"),
    ("coordinator", "investigator"),
    ("assistant", "coordinator"),
    ("coordinator", "scoring"),
    ("coordinator", "clustering"),
    ("coordinator", "detection"),
    ("coordinator", "root_cause"),
    ("coordinator", "sla"),
    ("coordinator", "translation"),
    ("coordinator", "ingestion"),
]

_REGISTRY = {a.id: a for a in AGENT_REGISTRY}


def get_agent(agent_id: str) -> AgentDefinition | None:
    return _REGISTRY.get(agent_id)


def list_agents() -> list[AgentDefinition]:
    return list(AGENT_REGISTRY)
