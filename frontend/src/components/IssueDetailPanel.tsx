import Tag from './Tag';
import SlaBadge from './SlaBadge';
import EvidenceCard from './EvidenceCard';
import { AlertTriangle, User, Search } from 'lucide-react';
import type { IssueDetail } from '../api';

interface Props {
  detail: IssueDetail;
  onInvestigate?: () => void;
  investigating?: boolean;
}

export default function IssueDetailPanel({ detail, onInvestigate, investigating }: Props) {
  const rec = detail.recommendation;

  return (
    <div className="bg-white border rounded-xl shadow-sm overflow-hidden sticky top-4">
      <div className="px-5 py-4 border-b border-slate-100 bg-slate-50">
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <Tag priority={detail.priority} />
          {detail.sla && <SlaBadge status={detail.sla.status} label={detail.sla.label} />}
          <h3 className="font-bold text-slate-900">{detail.site_name}</h3>
          <span className="text-slate-400">·</span>
          <span className="text-slate-700">{detail.theme_label}</span>
        </div>
        <p className="text-sm text-slate-500">
          {detail.neg} negative · {detail.pos} positive · {detail.volume} total · {detail.week}
          {' · '}
          <span className="capitalize">{detail.confidence_band} confidence</span>
        </p>
        {onInvestigate && (
          <button
            type="button"
            onClick={onInvestigate}
            disabled={investigating}
            className="mt-3 flex items-center gap-2 text-sm bg-accent text-white px-3 py-1.5 rounded-lg disabled:opacity-60"
          >
            <Search size={14} />
            {investigating ? 'Investigating…' : 'Investigate with agent'}
          </button>
        )}
      </div>

      {detail.root_cause && (
        <div className="px-5 py-4 border-b border-slate-100 space-y-2">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <Search size={12} />
            Root cause analysis
          </p>
          <p className="text-xs text-slate-500">{detail.root_cause.category}</p>
          <p className="text-sm text-slate-800 leading-relaxed">{detail.root_cause.summary}</p>
          {detail.root_cause.contributing_factors.length > 0 && (
            <ul className="text-xs text-slate-600 space-y-1 list-disc list-inside">
              {detail.root_cause.contributing_factors.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          )}
          <p className="text-[10px] text-slate-400 capitalize">
            Confidence: {detail.root_cause.confidence}
          </p>
        </div>
      )}

      {detail.sla && (
        <div className="px-5 py-3 border-b border-slate-100 bg-slate-50/80 text-xs text-slate-600 space-y-1">
          <p className="font-semibold text-slate-700">SLA clock</p>
          <p>{detail.sla.label}</p>
          <p>
            Acknowledge within {detail.sla.response_hours}h · Resolve within {detail.sla.resolution_hours}h
          </p>
        </div>
      )}

      {detail.signals.length > 0 && (
        <div className="px-5 py-4 border-b border-slate-100 space-y-2">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Why this was flagged</p>
          {detail.signals.map((s) => (
            <div key={s.type} className="flex gap-2 text-sm">
              <AlertTriangle size={16} className="text-amber-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-medium text-slate-800">{s.label}</span>
                <p className="text-slate-600 text-xs mt-0.5">{s.description}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {rec.text && (
        <div className="px-5 py-4 border-b border-amber-100 bg-amber-50/80">
          <p className="text-[10px] font-bold text-amber-800 uppercase tracking-wider mb-2">
            Internal recommendation · draft only
          </p>
          <p className="text-sm text-slate-800 leading-relaxed">{rec.text}</p>
          <div className="flex items-center gap-1.5 mt-3 text-xs text-slate-600">
            <User size={12} />
            <span>Owner: <strong>{rec.owner}</strong></span>
            <span className="text-slate-400">·</span>
            <span className="capitalize">{rec.draft_source} generated</span>
          </div>
        </div>
      )}

      <div className="px-5 py-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Supporting feedback
          </p>
          <span className="text-xs text-slate-400">{detail.evidence_count} items in cluster</span>
        </div>
        <div className="space-y-3 max-h-[28rem] overflow-y-auto pr-1">
          {detail.evidence.map((item) => (
            <EvidenceCard key={item.id} item={item} />
          ))}
          {detail.evidence.length === 0 && (
            <p className="text-sm text-slate-500">No feedback items linked to this cluster.</p>
          )}
        </div>
      </div>
    </div>
  );
}
