import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Download } from 'lucide-react';
import { api } from '../api';

export default function Digest({ week }: { week: string }) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.digest(week).then(setData);
  }, [week]);

  if (!data) return <p className="text-slate-500">Loading digest…</p>;

  const priorities = (data.action_priorities as { cluster_id: string; insight: string; owner: string }[]) || [];
  const siteTable = (data.per_site_table as { site_id: string; name: string; total_volume: number; total_neg: number; top_theme: string }[]) || [];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <h2 className="text-xl font-bold">{String(data.title)}</h2>
        <Link
          to="/reports"
          className="flex items-center gap-1.5 text-sm font-medium text-accent hover:underline"
        >
          <Download size={16} />
          Download executive digest
        </Link>
      </div>

      <section className="bg-white border rounded-lg p-4">
        <h3 className="font-semibold mb-3">Action Priorities</h3>
        {priorities.map((p) => (
          <div key={p.cluster_id} className="border-l-4 border-accent pl-3 mb-3">
            <p className="text-sm">{p.insight}</p>
            <p className="text-xs text-slate-500 mt-1">Owner: {p.owner}</p>
          </div>
        ))}
      </section>

      <section className="bg-white border rounded-lg overflow-hidden">
        <h3 className="font-semibold p-4 border-b">Per-Site Summary</h3>
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="text-left p-3">Site</th>
              <th className="text-right p-3">Volume</th>
              <th className="text-right p-3">Negatives</th>
              <th className="text-left p-3">Top Theme</th>
            </tr>
          </thead>
          <tbody>
            {siteTable.map((s) => (
              <tr key={s.site_id} className="border-t">
                <td className="p-3">{s.name}</td>
                <td className="p-3 text-right">{s.total_volume}</td>
                <td className="p-3 text-right">{s.total_neg}</td>
                <td className="p-3">{s.top_theme?.replace(/_/g, ' ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
