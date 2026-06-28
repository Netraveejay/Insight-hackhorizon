import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, OverviewData } from '../api';
import StatCard from '../components/StatCard';
import Tag from '../components/Tag';
import SlaBadge from '../components/SlaBadge';
import Chip from '../components/Chip';
import GettingStarted from '../components/GettingStarted';
import { ArrowRight } from 'lucide-react';

export default function Overview({ week }: { week: string }) {
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.overview(week).then(setData).catch((e) => setError(e.message));
  }, [week]);

  if (error) return <p className="text-red-600">Error: {error}</p>;
  if (!data) return <p className="text-slate-500">Loading overview…</p>;

  const empty = data.items_processed === 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Command Centre — {data.week}</h2>
        <p className="text-sm text-slate-600 mt-1">
          National snapshot after the latest pipeline run. Start with the hero issue, then drill into sites and reports.
        </p>
      </div>

      {empty ? (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-center">
          <p className="font-semibold text-slate-900">No data for {data.week} yet</p>
          <p className="text-sm text-slate-600 mt-2">Run the pipeline to populate this dashboard.</p>
          <Link to="/agents" className="inline-block mt-4 bg-accent text-white px-5 py-2 rounded-lg text-sm font-medium">
            Run pipeline →
          </Link>
        </div>
      ) : (
        <GettingStarted week={data.week} />
      )}

      {data.hero_issue && (
        <Link to="/issues" className="block bg-blue-50 border border-accent rounded-xl p-5 hover:shadow-md transition-shadow group">
          <p className="text-xs font-bold text-accent uppercase">Top priority this week</p>
          <div className="flex items-center gap-2 mt-2">
            <Tag priority={data.hero_issue.priority} />
            <span className="font-semibold text-lg">{data.hero_issue.site_name}</span>
            <span className="text-slate-600">— {data.hero_issue.theme.replace(/_/g, ' ')}</span>
          </div>
          {data.hero_issue.insight && (
            <p className="text-sm mt-2 text-slate-700 line-clamp-2">{data.hero_issue.insight}</p>
          )}
          {data.hero_issue.root_cause_summary && (
            <p className="text-xs mt-2 text-slate-600">
              <span className="font-medium">Root cause:</span> {data.hero_issue.root_cause_summary}
            </p>
          )}
          {data.hero_issue.sla_label && (
            <p className="text-xs mt-1">
              <SlaBadge status={data.hero_issue.sla_status} label={data.hero_issue.sla_label} />
            </p>
          )}
          <p className="text-sm text-accent font-medium mt-3 flex items-center gap-1 group-hover:gap-2 transition-all">
            View issue &amp; evidence <ArrowRight size={14} />
          </p>
        </Link>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Weighted CSAT"
          value={`${data.weighted_csat_pct}%`}
          sub="Guest survey ratings ≥4 stars"
        />
        <StatCard
          label="Open Issues"
          value={data.open_issues}
          sub="P1–P3 needing review"
          accent
        />
        <StatCard
          label="Cross-Source Flags"
          value={data.cross_source_flags}
          sub="Guest + staff alignment"
        />
        <StatCard
          label="Items Processed"
          value={data.items_processed}
          sub="Scored this week"
        />
      </div>

      {data.sla_summary && data.open_issues > 0 && (
        <section className="bg-white border rounded-xl p-4">
          <h3 className="font-semibold text-slate-800 mb-1 text-sm">SLA status</h3>
          <p className="text-xs text-slate-500 mb-3">Response and resolution clocks for open priority issues</p>
          <div className="flex flex-wrap gap-3">
            <div className="flex items-center gap-2 text-sm">
              <SlaBadge status="on_track" compact />
              <span className="text-slate-700 tabular-nums">{data.sla_summary.on_track}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <SlaBadge status="at_risk" compact />
              <span className="text-slate-700 tabular-nums">{data.sla_summary.at_risk}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <SlaBadge status="breached" compact />
              <span className="text-slate-700 tabular-nums">{data.sla_summary.breached}</span>
            </div>
          </div>
        </section>
      )}

      {data.language_mix && data.language_mix.length > 0 && (
        <section className="bg-white border rounded-xl p-4">
          <h3 className="font-semibold text-slate-800 mb-1 text-sm">Feedback by language</h3>
          <p className="text-xs text-slate-500 mb-3">Non-English items are translated before scoring</p>
          <div className="flex flex-wrap gap-2">
            {data.language_mix.map((l) => (
              <Chip
                key={l.language}
                label={`${l.language.toUpperCase()} (${l.count}${l.translated ? `, ${l.translated} translated` : ''})`}
                variant={l.language === 'en' ? 'default' : 'info'}
              />
            ))}
          </div>
        </section>
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        <section className="bg-white border rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-slate-800">Ranked actions</h3>
            <Link to="/issues" className="text-xs text-accent font-medium hover:underline">View all →</Link>
          </div>
          <p className="text-xs text-slate-500 mb-3">Sites and themes needing attention, sorted by priority</p>
          <div className="space-y-2">
            {data.ranked_actions.map((a) => (
              <Link
                key={a.cluster_id}
                to="/issues"
                className="block border rounded-lg p-3 hover:border-accent transition-colors"
              >
                <div className="flex items-start gap-2">
                  <Tag priority={a.priority} />
                  <div className="min-w-0">
                    <p className="font-medium text-sm">{a.site_name} — {a.theme.replace(/_/g, ' ')}</p>
                    <p className="text-xs text-slate-500">{a.neg} negatives</p>
                    {a.root_cause_summary && (
                      <p className="text-xs text-slate-600 mt-1 line-clamp-1">{a.root_cause_summary}</p>
                    )}
                    <div className="flex gap-1 mt-1 flex-wrap items-center">
                      {a.sla_status && <SlaBadge status={a.sla_status} compact />}
                      {a.flags?.map((f) => <Chip key={f} label={f} variant="warning" />)}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
            {data.ranked_actions.length === 0 && (
              <p className="text-sm text-slate-500">No ranked actions this week.</p>
            )}
          </div>
        </section>

        <section className="bg-white border rounded-xl p-4">
          <h3 className="font-semibold text-slate-800 mb-1">What guests praise</h3>
          <p className="text-xs text-slate-500 mb-3">Positive themes to protect and replicate</p>
          <div className="space-y-2">
            {data.positive_themes.map(([theme, count]) => (
              <div key={theme} className="flex items-center gap-3">
                <span className="text-sm w-32 truncate capitalize">{theme.replace(/_/g, ' ')}</span>
                <div className="flex-1 bg-slate-200 rounded-full h-3">
                  <div
                    className="bg-green-500 h-3 rounded-full transition-all"
                    style={{ width: `${Math.min(100, (count / (data.positive_themes[0]?.[1] || 1)) * 100)}%` }}
                  />
                </div>
                <span className="text-sm text-slate-600 w-8 tabular-nums">{count}</span>
              </div>
            ))}
            {data.positive_themes.length === 0 && (
              <p className="text-sm text-slate-500">No positive themes recorded.</p>
            )}
          </div>
        </section>
      </div>

      <div className="grid sm:grid-cols-3 gap-3">
        <QuickLink to="/feed" title="Live Feed" desc="Browse every message" />
        <QuickLink to="/reports" title="Manager Reports" desc="Download site briefs" />
        <QuickLink to="/agents" title="Agent Network" desc="Run pipeline & watch A2A" />
      </div>
    </div>
  );
}

function QuickLink({ to, title, desc }: { to: string; title: string; desc: string }) {
  return (
    <Link to={to} className="bg-white border rounded-xl p-4 hover:border-accent hover:shadow-sm transition-all group">
      <p className="font-semibold text-sm text-slate-900">{title}</p>
      <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
      <ArrowRight size={14} className="text-accent mt-2 group-hover:translate-x-0.5 transition-transform" />
    </Link>
  );
}
