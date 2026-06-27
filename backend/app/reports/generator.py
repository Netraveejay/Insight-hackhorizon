from __future__ import annotations

import html
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import GeneratedReportRow
from app.schemas import SITE_BY_ID, SITES, Cluster, Detection, Insight, ScoredItem, SourceCoverageReport


def _esc(text: str) -> str:
    return html.escape(str(text))


def _priority_badge(priority: str | None) -> str:
    if not priority:
        return ""
    colors = {"P1": "#dc2626", "P2": "#ea580c", "P3": "#ca8a04"}
    color = colors.get(priority, "#64748b")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">{_esc(priority)}</span>'


def _base_styles() -> str:
    return """
    body { font-family: 'Segoe UI', system-ui, sans-serif; color: #1e293b; margin: 0; line-height: 1.5; }
    .page { max-width: 800px; margin: 0 auto; padding: 40px 48px; }
    .header { border-bottom: 3px solid #2563eb; padding-bottom: 20px; margin-bottom: 28px; }
    .brand { font-size: 11px; font-weight: 700; color: #2563eb; letter-spacing: 0.08em; text-transform: uppercase; }
    h1 { font-size: 26px; margin: 8px 0 4px; color: #0f172a; }
    .meta { font-size: 13px; color: #64748b; }
    h2 { font-size: 14px; font-weight: 700; color: #334155; text-transform: uppercase; letter-spacing: 0.05em; margin: 28px 0 12px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; }
    .summary-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; margin: 12px 0; }
    th { text-align: left; background: #f1f5f9; padding: 10px 12px; font-weight: 600; border-bottom: 2px solid #e2e8f0; }
    td { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
    td.recommendation { line-height: 1.5; white-space: normal; word-wrap: break-word; }
    .rec-owner { font-size: 11px; color: #64748b; margin-top: 6px; }
    .digest-page { max-width: 960px; }
    .issue-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; }
    .issue-card.p1 { border-left: 4px solid #dc2626; }
    .issue-card.p2 { border-left: 4px solid #ea580c; }
    .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; }
    .stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0; }
    .stat { background: #f8fafc; border-radius: 8px; padding: 12px; text-align: center; }
    .stat .val { font-size: 22px; font-weight: 700; color: #2563eb; }
    .stat .lbl { font-size: 11px; color: #64748b; text-transform: uppercase; }
    @media print { .page { padding: 24px; } }
    """


class ReportGenerator:
    """Generate downloadable HTML reports for site managers and HQ."""

    def generate_site_report(
        self,
        db: Session,
        run_id: str,
        site_id: str,
        week: str,
        clusters: list[Cluster],
        detections: list[Detection],
        insights: list[Insight],
        scored: list[ScoredItem],
    ) -> GeneratedReportRow:
        site = SITE_BY_ID.get(site_id, {"id": site_id, "name": site_id, "email": ""})
        site_clusters = [c for c in clusters if c.site_id == site_id and c.week == week]
        det_map = {d.cluster_id: d for d in detections}
        ins_map = {i.cluster_id: i for i in insights}
        site_scored = [s for s in scored if s.site_id == site_id and s.week == week]

        csat = [s for s in site_scored if s.channel == "csat" and s.rating is not None]
        csat_pct = round(100 * sum(1 for s in csat if s.rating >= 4) / len(csat), 1) if csat else None

        priority_clusters = []
        for c in sorted(site_clusters, key=lambda x: -x.neg):
            d = det_map.get(c.cluster_id)
            if d and d.priority:
                priority_clusters.append((c, d, ins_map.get(c.cluster_id)))

        issue_html = ""
        for c, d, ins in priority_clusters:
            flags = []
            if d.cross_source:
                flags.append("Cross-source")
            if d.compounding:
                flags.append("Compounding")
            if d.spike:
                flags.append("Spike")
            cls = "p1" if d.priority == "P1" else "p2" if d.priority == "P2" else ""
            issue_html += f"""
            <div class="issue-card {cls}">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <strong>{_esc(c.theme.replace('_', ' ').title())}</strong>
                {_priority_badge(d.priority)}
              </div>
              <p style="margin:0 0 8px;font-size:13px;color:#475569">{c.neg} negative · {c.volume} total mentions · {', '.join(flags) or 'elevated volume'}</p>
              {f'<p style="margin:0;font-size:13px"><strong>Recommendation:</strong> {_esc(ins.insight)}</p><p style="margin:4px 0 0;font-size:12px;color:#64748b">Owner: {_esc(ins.owner_suggested)}</p>' if ins else ''}
            </div>"""

        pos_themes: dict[str, int] = {}
        for s in site_scored:
            if s.sentiment.get(s.primary_theme) == "positive":
                pos_themes[s.primary_theme] = pos_themes.get(s.primary_theme, 0) + 1
        pos_html = "".join(
            f"<li>{_esc(t.replace('_', ' ').title())} — {n} positive mentions</li>"
            for t, n in sorted(pos_themes.items(), key=lambda x: -x[1])[:5]
        ) or "<li>No standout positive themes this week</li>"

        generated = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")
        body = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{_esc(site['name'])} Weekly Report — {week}</title>
<style>{_base_styles()}</style></head><body>
<div class="page">
  <div class="header">
    <div class="brand">Insight · Cinema Operations Intelligence</div>
    <h1>{_esc(site['name'])} — Weekly Site Report</h1>
    <p class="meta">Week {week} · Generated {generated} · Recipient: {_esc(site['email'])}</p>
  </div>

  <div class="summary-box">
    <strong>Executive summary</strong>
    <p style="margin:8px 0 0;font-size:14px">
      This week Insight processed <strong>{len(site_scored)}</strong> feedback items for {_esc(site['name'])}.
      {f' Weighted CSAT: <strong>{csat_pct}%</strong>.' if csat_pct is not None else ''}
      <strong>{len(priority_clusters)}</strong> issue{'s' if len(priority_clusters) != 1 else ''} require internal review.
    </p>
  </div>

  <div class="stat-grid">
    <div class="stat"><div class="val">{len(site_scored)}</div><div class="lbl">Items</div></div>
    <div class="stat"><div class="val">{sum(c.neg for c in site_clusters)}</div><div class="lbl">Negatives</div></div>
    <div class="stat"><div class="val">{len(priority_clusters)}</div><div class="lbl">Priority issues</div></div>
  </div>

  <h2>Priority issues &amp; recommendations</h2>
  {issue_html or '<p style="color:#64748b;font-size:13px">No priority issues flagged this week.</p>'}

  <h2>Positive highlights</h2>
  <ul style="font-size:13px;color:#475569">{pos_html}</ul>

  <div class="footer">
    <strong>INTERNAL USE ONLY</strong> — This report informs site management. Do not forward to guests.
    Do not contact guests based on this report. Run ID: {_esc(run_id)}.
    <br>To save as PDF: open this file in a browser and use Print → Save as PDF.
  </div>
</div></body></html>"""

        return self._save_report(
            db, run_id, week, "site", site_id,
            f"{site['name']} Weekly Report — {week}",
            site["email"],
            f"{site_id}-weekly-{week}.html",
            body,
        )

    def generate_digest_report(
        self,
        db: Session,
        run_id: str,
        week: str,
        clusters: list[Cluster],
        detections: list[Detection],
        insights: list[Insight],
        scored: list[ScoredItem],
        coverage: SourceCoverageReport,
    ) -> GeneratedReportRow:
        det_map = {d.cluster_id: d for d in detections}
        ins_map = {i.cluster_id: i for i in insights}

        ranked = []
        for c in clusters:
            d = det_map.get(c.cluster_id)
            if d and d.priority:
                ranked.append((c, d, ins_map.get(c.cluster_id)))
        ranked.sort(key=lambda x: ({"P1": 0, "P2": 1, "P3": 2}.get(x[1].priority or "P9", 9), -x[0].neg))

        priorities_html = ""
        for c, d, ins in ranked[:15]:
            site_name = SITE_BY_ID.get(c.site_id, {}).get("name", c.site_id)
            rec_text = ins.insight if ins else "—"
            owner = ins.owner_suggested if ins else ""
            rc = (d.root_cause or {}).get("summary", "—")
            sla_label = (d.sla or {}).get("label", "—")
            priorities_html += f"""
            <tr>
              <td>{_priority_badge(d.priority)}</td>
              <td><strong>{_esc(site_name)}</strong><br><span style="color:#64748b">{_esc(c.theme.replace('_', ' '))}</span></td>
              <td style="text-align:center">{c.neg}</td>
              <td style="font-size:13px">{_esc(rc)}</td>
              <td style="font-size:12px;color:#475569">{_esc(sla_label)}</td>
              <td class="recommendation">
                {_esc(rec_text)}
                {f'<div class="rec-owner">Owner: {_esc(owner)} · Internal draft only</div>' if owner else ''}
              </td>
            </tr>"""

        site_rows = ""
        for site in SITES:
            sc = [c for c in clusters if c.site_id == site["id"]]
            if not sc:
                continue
            top = max(sc, key=lambda c: c.neg)
            site_rows += f"""
            <tr>
              <td>{_esc(site['name'])}</td>
              <td style="text-align:center">{sum(c.volume for c in sc)}</td>
              <td style="text-align:center">{sum(c.neg for c in sc)}</td>
              <td>{_esc(top.theme.replace('_', ' ')) if top.neg else '—'}</td>
            </tr>"""

        generated = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")
        body = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Executive Digest — {week}</title>
<style>{_base_styles()}</style></head><body>
<div class="page digest-page">
  <div class="header">
    <div class="brand">Insight · Cinema Operations Intelligence</div>
    <h1>Weekly Executive Digest</h1>
    <p class="meta">Week {week} · All 21 sites · Generated {generated}</p>
  </div>

  <div class="summary-box">
    <strong>National overview</strong>
    <p style="margin:8px 0 0;font-size:14px">
      {len(scored)} items scored nationally · {len([d for d in detections if d.priority])} open priority issues ·
      {sum(1 for d in detections if d.cross_source)} cross-source confirmations.
    </p>
  </div>

  <h2>Top action priorities</h2>
  <table>
    <thead><tr><th>Priority</th><th>Site · Theme</th><th>Neg</th><th>Root cause</th><th>SLA</th><th>Recommendation</th></tr></thead>
    <tbody>{priorities_html or '<tr><td colspan="6">No priorities</td></tr>'}</tbody>
  </table>

  <h2>Per-site summary</h2>
  <table>
    <thead><tr><th>Site</th><th>Volume</th><th>Negatives</th><th>Top friction theme</th></tr></thead>
    <tbody>{site_rows}</tbody>
  </table>

  <div class="footer">
    <strong>CONFIDENTIAL — EXECUTIVE USE ONLY</strong> · Run ID: {_esc(run_id)} ·
    Source coverage: {len(coverage.entries)} connector(s).
    <br>Print → Save as PDF to download a PDF copy.
  </div>
</div></body></html>"""

        return self._save_report(
            db, run_id, week, "digest", None,
            f"Executive Digest — {week}",
            "executive@insight-ops.internal",
            f"executive-digest-{week}.html",
            body,
        )

    def _save_report(
        self,
        db: Session,
        run_id: str,
        week: str,
        report_type: str,
        site_id: str | None,
        title: str,
        recipient_email: str,
        file_name: str,
        html_body: str,
    ) -> GeneratedReportRow:
        settings = get_settings()
        out_dir = settings.resolved_reports_path / week
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / file_name
        path.write_text(html_body, encoding="utf-8")

        row = GeneratedReportRow(
            id=str(uuid.uuid4())[:16],
            run_id=run_id,
            week=week,
            report_type=report_type,
            site_id=site_id,
            title=title,
            recipient_email=recipient_email,
            file_name=file_name,
        )
        db.add(row)
        return row

    def generate_all(
        self,
        db: Session,
        run_id: str,
        week: str,
        clusters: list[Cluster],
        detections: list[Detection],
        insights: list[Insight],
        scored: list[ScoredItem],
        coverage: SourceCoverageReport,
    ) -> list[GeneratedReportRow]:
        reports: list[GeneratedReportRow] = []
        reports.append(
            self.generate_digest_report(db, run_id, week, clusters, detections, insights, scored, coverage)
        )
        for site in SITES:
            reports.append(
                self.generate_site_report(
                    db, run_id, site["id"], week, clusters, detections, insights, scored
                )
            )
        return reports
