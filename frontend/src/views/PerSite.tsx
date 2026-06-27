import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Download } from 'lucide-react';
import { api, Site } from '../api';
import { useAuth } from '../auth/AuthContext';

export default function PerSite({ week }: { week: string }) {
  const { user } = useAuth();
  const [sites, setSites] = useState<Site[]>([]);
  const [selected, setSelected] = useState('');
  const [report, setReport] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.sites().then((d) => {
      setSites(d.sites);
      const defaultSite = user?.site_id && d.sites.find((s) => s.id === user.site_id)
        ? user.site_id
        : d.sites[0]?.id || '';
      setSelected(defaultSite);
    });
  }, [user?.site_id]);

  useEffect(() => {
    if (selected) api.siteReport(selected, week).then(setReport);
  }, [selected, week]);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <h2 className="text-xl font-bold">Per-Site Report</h2>
        <Link
          to="/reports"
          className="flex items-center gap-1.5 text-sm font-medium text-accent hover:underline"
        >
          <Download size={16} />
          Download HTML report
        </Link>
      </div>
      <select
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        className="border rounded-md px-3 py-2 text-sm"
        disabled={user?.role === 'manager' && !!user.site_id}
      >
        {sites.map((s) => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
      </select>

      {report && (
        <div className="bg-white border rounded-lg p-4 space-y-4">
          <p className="text-sm text-slate-500">
            Delivered to: {String((report.site as Site).email)} · {String(report.note)}
          </p>
          <p className="text-xs text-blue-700 bg-blue-50 rounded px-2 py-1 inline-block">
            Full formatted report available under Manager Reports → Download
          </p>
          <p className="text-sm">Feedback count: {String(report.feedback_count)}</p>
          {(report.clusters as Record<string, unknown>[])?.map((c, i) => (
            <div key={i} className="border rounded p-3 text-sm">
              <p className="font-medium">{String(c.theme).replace(/_/g, ' ')} — {String(c.neg)} neg</p>
              {(c.insight as { insight?: string } | null)?.insight && (
                <p className="text-slate-600 mt-1">{(c.insight as { insight: string }).insight}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
