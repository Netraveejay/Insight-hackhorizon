"""Extract UI references from grounded tool results."""

from __future__ import annotations

from app.schemas import SITE_BY_ID


def references_from_tools(tool_results: list[tuple[str, dict]], week: str | None = None) -> list[dict]:
    refs: list[dict] = []
    seen: set[str] = set()

    for tool_name, data in tool_results:
        w = data.get("week") or week or ""

        if tool_name == "get_negative_feedback":
            for item in data.get("items", [])[:5]:
                cid = item.get("id") or item.get("cluster_id", "")
                _add(refs, seen, {
                    "cluster_id": cid or f"neg-{item.get('site_id', '')}-{item.get('theme', '')}",
                    "site_id": item.get("site_id", ""),
                    "site_name": item.get("site_name", ""),
                    "theme": item.get("theme", ""),
                    "week": w,
                    "label": f"{item.get('site_name')} · {item.get('theme', '').replace('_', ' ')}",
                })

        elif tool_name == "get_top_issues":
            for r in data.get("overview", {}).get("ranked_actions", [])[:5]:
                _add(refs, seen, {
                    "cluster_id": r["cluster_id"],
                    "site_id": r.get("site_id", ""),
                    "site_name": r.get("site_name", ""),
                    "theme": r.get("theme", ""),
                    "week": w,
                    "label": f"{r.get('site_name')} · {r.get('theme', '').replace('_', ' ')}",
                })

        elif tool_name == "get_site":
            for c in data.get("clusters", [])[:3]:
                site = SITE_BY_ID.get(c.get("site_id", ""), {})
                _add(refs, seen, {
                    "cluster_id": c["cluster_id"],
                    "site_id": c.get("site_id", ""),
                    "site_name": data.get("site_name") or site.get("name", ""),
                    "theme": c.get("theme", ""),
                    "week": w,
                    "label": f"{data.get('site_name')} · {c.get('theme', '').replace('_', ' ')}",
                })

        elif tool_name == "get_root_cause" and data.get("found"):
            _add(refs, seen, {
                "cluster_id": data.get("cluster_id", ""),
                "site_id": "",
                "site_name": "",
                "theme": "",
                "week": w,
                "label": data.get("cluster_id", "root cause"),
            })

        elif tool_name == "get_detections":
            for d in data.get("detections", [])[:3]:
                _add(refs, seen, {
                    "cluster_id": d["cluster_id"],
                    "site_id": d.get("site_id", ""),
                    "site_name": d.get("site_name", ""),
                    "theme": d.get("theme", ""),
                    "week": d.get("week", w),
                    "label": f"{d.get('site_name')} · {d.get('theme', '').replace('_', ' ')}",
                })

    return refs[:8]


def _add(refs: list[dict], seen: set[str], ref: dict) -> None:
    key = ref.get("cluster_id") or ref.get("label", "")
    if not key or key in seen:
        return
    seen.add(key)
    refs.append(ref)
