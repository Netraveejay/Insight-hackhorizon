import Tag from './Tag';
import Chip from './Chip';
import SlaBadge from './SlaBadge';
import type { Issue } from '../api';

interface Props {
  issue: Issue;
  selected?: boolean;
  onClick?: () => void;
}

export default function IssueRow({ issue, selected, onClick }: Props) {
  const flags: { label: string; variant: 'danger' | 'warning' | 'info' }[] = [];
  if (issue.flags.cross_source) flags.push({ label: 'cross-source', variant: 'danger' });
  if (issue.flags.compounding) flags.push({ label: 'compounding', variant: 'warning' });
  if (issue.flags.spike) flags.push({ label: 'spike', variant: 'info' });
  flags.push({ label: issue.confidence_band, variant: 'default' as 'info' });

  return (
    <button
      onClick={onClick}
      className={`w-full text-left bg-white border rounded-lg p-4 transition-colors focus-visible:ring-2 focus-visible:ring-accent ${
        selected ? 'border-accent ring-1 ring-accent/30 shadow-sm' : 'border-slate-200 hover:border-accent'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <Tag priority={issue.priority} />
            <SlaBadge status={issue.sla_status} compact />
            <span className="font-semibold text-slate-900">{issue.site_name}</span>
            <span className="text-slate-500">·</span>
            <span className="text-slate-700">{issue.theme.replace(/_/g, ' ')}</span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            {issue.neg} negatives · {issue.volume} total · {issue.week}
          </p>
          {issue.root_cause_summary && (
            <p className="text-xs text-slate-600 mt-2 line-clamp-1">
              <span className="font-medium text-slate-700">Root cause:</span> {issue.root_cause_summary}
            </p>
          )}
          {issue.insight_preview && (
            <p className="text-sm text-slate-600 mt-2 line-clamp-2">{issue.insight_preview}</p>
          )}
        </div>
        <div className="flex flex-wrap gap-1 justify-end">
          {flags.map((f) => (
            <Chip key={f.label} label={f.label} variant={f.variant} />
          ))}
        </div>
      </div>
    </button>
  );
}
