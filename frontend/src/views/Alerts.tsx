import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, AlertsData } from '../api';
import Tag from '../components/Tag';
import Chip from '../components/Chip';
import SlaBadge from '../components/SlaBadge';
import { Bell, MessageSquare, ExternalLink } from 'lucide-react';

export default function Alerts({ week }: { week: string }) {
  const [data, setData] = useState<AlertsData | null>(null);

  useEffect(() => {
    api.alerts(week).then(setData);
  }, [week]);

  if (!data) return <p className="text-slate-500">Loading alerts…</p>;

  const formattedDate = (iso: string) =>
    new Date(iso).toLocaleString('en-AU', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
    });

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Teams Alerts — {week}</h2>
        <p className="text-sm text-slate-600 mt-1">{data.description}</p>
      </div>

      <div className={`rounded-xl border p-4 flex gap-3 ${data.teams_webhook_configured ? 'bg-green-50 border-green-200' : 'bg-slate-50 border-slate-200'}`}>
        <MessageSquare className="shrink-0 text-slate-600" size={22} />
        <div className="text-sm">
          <p className="font-semibold text-slate-900">
            {data.teams_webhook_configured ? 'Teams webhook active' : 'Simulated delivery (in-app inbox)'}
          </p>
          <p className="text-slate-600 mt-1">
            {data.teams_webhook_configured
              ? 'Alerts are posted to your Microsoft Teams channel and mirrored here.'
              : 'Set TEAMS_WEBHOOK_URL in backend/.env to post alerts to a real Teams channel. Until then, this page is the operations alert inbox.'}
          </p>
          <p className="text-xs text-slate-500 mt-2">
            Alerts are generated from the weekly pipeline run.{' '}
            <Link to="/agents" className="text-accent hover:underline">Re-run pipeline</Link>
            {' '}after loading production feedback via <code className="text-[11px]">FEEDBACK_FILE_PATH</code>.
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {data.alerts.map((a) => (
          <article key={a.id} className="bg-white border rounded-xl p-4">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                <Bell size={18} className="text-accent" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  {a.priority && <Tag priority={a.priority} />}
                  {a.sla_status && <SlaBadge status={a.sla_status} compact />}
                  <Chip label={a.type.replace(/_/g, ' ')} variant={a.type.includes('cross') ? 'danger' : 'warning'} />
                  {a.delivered_to_teams && <Chip label="Sent to Teams" variant="success" />}
                </div>
                <p className="font-medium text-slate-900 mt-2">{a.message}</p>
                {a.root_cause_summary && (
                  <p className="text-xs text-slate-600 mt-1">Root cause: {a.root_cause_summary}</p>
                )}
                <p className="text-xs text-slate-500 mt-1">
                  {a.site_name}
                  {a.theme_label && ` · ${a.theme_label}`}
                  {' · '}
                  {formattedDate(a.created_at)}
                </p>
                <Link to="/issues" className="text-xs text-accent font-medium mt-2 inline-flex items-center gap-1 hover:underline">
                  View issue detail <ExternalLink size={12} />
                </Link>
              </div>
            </div>
          </article>
        ))}
        {data.alerts.length === 0 && (
          <p className="text-slate-500 text-center py-8 bg-white border rounded-xl">
            No alerts this week — run the pipeline after detection flags issues.
          </p>
        )}
      </div>
    </div>
  );
}
