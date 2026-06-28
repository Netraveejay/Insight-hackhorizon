import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Crown, Search, Trophy, ChevronDown, ChevronRight, Info } from 'lucide-react';
import { api, LeaderboardEntry } from '../api';
import StatCard from '../components/StatCard';

function scoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-600';
  if (score >= 60) return 'text-amber-600';
  return 'text-red-600';
}

function scoreBar(score: number): string {
  if (score >= 80) return 'bg-emerald-500';
  if (score >= 60) return 'bg-amber-500';
  return 'bg-red-500';
}

export default function Leaderboard({ week }: { week: string }) {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.leaderboard>> | null>(null);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    api.leaderboard(week).then(setData).catch((e) => setError(e.message));
  }, [week]);

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = search.trim().toLowerCase();
    if (!q) return data.entries;
    return data.entries.filter((e) => {
      const haystack = [
        e.theatre_name,
        e.region,
        ...e.sites.map((s) => s.site_name),
      ].join(' ').toLowerCase();
      return haystack.includes(q);
    });
  }, [data, search]);

  const toggleExpand = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (error) return <p className="text-red-600">Error: {error}</p>;
  if (!data) return <p className="text-slate-500">Loading leaderboard…</p>;

  const top = data.entries.find((e) => e.badge === 'top');

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Theatre Leaderboard — {data.week}</h2>
        <p className="text-sm text-slate-600 mt-1 max-w-3xl">
          Compare theatre operators on how efficiently they resolve guest feedback issues.
          Each theatre operates a <strong>different number of sites</strong> — scores are averaged
          across their estate so you can benchmark fairly.
        </p>
      </div>

      {top && (
        <div className="bg-gradient-to-r from-amber-50 to-yellow-50 border border-amber-200 rounded-xl p-5 flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex items-center gap-3">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-400 text-white shadow-md">
              <Crown size={24} />
            </span>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-amber-700">#1 This week</p>
              <p className="text-xl font-bold text-slate-900">{top.theatre_name}</p>
              <p className="text-sm text-slate-600">
                {top.region} · {top.site_count} site{top.site_count !== 1 ? 's' : ''} ·{' '}
                <span className={`font-semibold ${scoreColor(top.efficiency_score)}`}>
                  {top.efficiency_score} efficiency
                </span>
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid sm:grid-cols-3 gap-4">
        <StatCard label="Theatres ranked" value={data.total_theatres} sub="Operators compared" />
        <StatCard
          label="Sites in network"
          value={data.total_sites}
          sub="Counts vary per theatre"
          accent
        />
        <StatCard
          label="Leader"
          value={data.top_theatre_name ?? '—'}
          sub={top ? `${top.efficiency_score} pts` : undefined}
        />
      </div>

      <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search theatre, region, or site…"
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
          />
        </div>
        <p className="text-xs text-slate-500">
          {filtered.length} of {data.entries.length} theatres
        </p>
      </div>

      <div className="bg-blue-50 border border-blue-100 rounded-lg px-4 py-3 flex gap-2 text-sm text-slate-700">
        <Info size={16} className="text-blue-500 shrink-0 mt-0.5" />
        <p>{data.methodology}</p>
      </div>

      <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="text-left p-3 w-12">#</th>
              <th className="text-left p-3">Theatre</th>
              <th className="text-center p-3 hidden md:table-cell">Sites</th>
              <th className="text-right p-3">Efficiency</th>
              <th className="text-right p-3 hidden lg:table-cell">SLA</th>
              <th className="text-right p-3 hidden lg:table-cell">Resolved</th>
              <th className="text-right p-3 hidden sm:table-cell">CSAT</th>
              <th className="text-right p-3 hidden xl:table-cell">Trend</th>
              <th className="p-3 w-8" />
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={9} className="p-8 text-center text-slate-500">
                  No theatres match &ldquo;{search}&rdquo;
                </td>
              </tr>
            )}
            {filtered.map((entry) => (
              <TheatreRow
                key={entry.theatre_id}
                entry={entry}
                expanded={expanded.has(entry.theatre_id)}
                onToggle={() => toggleExpand(entry.theatre_id)}
              />
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-slate-500">
        Site-level detail available by expanding a theatre row. For per-site reports see{' '}
        <Link to="/sites" className="text-accent hover:underline">Per-Site</Link>.
      </p>
    </div>
  );
}

function TheatreRow({
  entry,
  expanded,
  onToggle,
}: {
  entry: LeaderboardEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        className={`border-t cursor-pointer hover:bg-slate-50 transition-colors ${
          entry.badge === 'top' ? 'bg-amber-50/50' : ''
        }`}
        onClick={onToggle}
      >
        <td className="p-3 font-bold text-slate-700">
          <span className="inline-flex items-center gap-1">
            {entry.rank}
            {entry.badge === 'top' && <Trophy size={14} className="text-amber-500" />}
          </span>
        </td>
        <td className="p-3">
          <p className="font-semibold text-slate-900">{entry.theatre_name}</p>
          <p className="text-xs text-slate-500">{entry.region}</p>
        </td>
        <td className="p-3 text-center hidden md:table-cell">
          <span className="inline-flex items-center justify-center min-w-[2rem] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-xs font-medium">
            {entry.site_count}
          </span>
        </td>
        <td className="p-3 text-right">
          <div className="flex flex-col items-end gap-1">
            <span className={`font-bold ${scoreColor(entry.efficiency_score)}`}>
              {entry.efficiency_score}
            </span>
            <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${scoreBar(entry.efficiency_score)}`}
                style={{ width: `${Math.min(entry.efficiency_score, 100)}%` }}
              />
            </div>
          </div>
        </td>
        <td className="p-3 text-right hidden lg:table-cell text-slate-600">
          {entry.sla_compliance_pct}%
        </td>
        <td className="p-3 text-right hidden lg:table-cell text-slate-600">
          {entry.issue_handling_pct}%
        </td>
        <td className="p-3 text-right hidden sm:table-cell text-slate-600">
          {entry.csat_pct}%
        </td>
        <td className="p-3 text-right hidden xl:table-cell">
          <span className={entry.improvement_pct > 0 ? 'text-emerald-600' : 'text-slate-500'}>
            {entry.improvement_pct > 0 ? '+' : ''}{entry.improvement_pct}%
          </span>
        </td>
        <td className="p-3 text-slate-400">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-slate-50/80">
          <td colSpan={9} className="px-4 py-3">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Sites under {entry.theatre_name} ({entry.site_count})
            </p>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {entry.sites.map((site) => (
                <div
                  key={site.site_id}
                  className="bg-white border rounded-lg px-3 py-2 text-xs"
                >
                  <div className="flex justify-between items-start gap-2">
                    <span className="font-medium text-slate-800">{site.site_name}</span>
                    <span className={`font-bold ${scoreColor(site.efficiency_score)}`}>
                      {site.efficiency_score}
                    </span>
                  </div>
                  <p className="text-slate-500 mt-1">
                    SLA {site.sla_compliance_pct}% · Handling {site.issue_handling_pct}% ·{' '}
                    {site.open_issues} open issue{site.open_issues !== 1 ? 's' : ''}
                    {site.open_p1 > 0 && (
                      <span className="text-red-600 font-medium"> · {site.open_p1} P1</span>
                    )}
                  </p>
                </div>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
