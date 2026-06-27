import { ChevronDown, ChevronRight, Star } from 'lucide-react';
import { useState } from 'react';
import OriginalText from './OriginalText';
import Chip from './Chip';

export interface EvidenceItem {
  id: string;
  text: string;
  original_text: string;
  original_language: string;
  translated: boolean;
  channel: string;
  channel_label: string;
  source_type: string;
  rating: number | null;
  sentiment: string;
  urgency: string;
  ts: string;
  timeline: { stage: string; detail: string; rules_version?: string }[];
}

export default function EvidenceCard({ item }: { item: EvidenceItem }) {
  const [showAudit, setShowAudit] = useState(false);
  const date = new Date(item.ts).toLocaleDateString('en-AU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  return (
    <article className="border border-slate-200 rounded-lg overflow-hidden bg-white">
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-100 flex flex-wrap items-center gap-2">
        <Chip
          label={item.source_type === 'staff' ? 'Staff' : 'Guest'}
          variant={item.source_type === 'staff' ? 'warning' : 'info'}
        />
        <span className="text-xs font-medium text-slate-600">{item.channel_label}</span>
        <span className="text-xs text-slate-400">· {date}</span>
        {item.rating != null && (
          <span className="flex items-center gap-0.5 text-xs text-slate-500 ml-auto">
            <Star size={12} className="fill-amber-400 text-amber-400" />
            {item.rating}/5
          </span>
        )}
        {item.sentiment === 'negative' && (
          <Chip label="negative" variant="danger" />
        )}
        {item.urgency === 'high' && <Chip label="high urgency" variant="danger" />}
      </div>

      <div className="px-4 py-3 text-sm">
        <OriginalText
          text={item.text}
          originalText={item.original_text}
          language={item.original_language}
          translated={item.translated}
        />
      </div>

      <button
        type="button"
        onClick={() => setShowAudit(!showAudit)}
        className="w-full flex items-center gap-1.5 px-4 py-2 text-xs text-slate-500 hover:bg-slate-50 border-t border-slate-100"
      >
        {showAudit ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        Processing audit · {item.id}
      </button>

      {showAudit && (
        <ol className="px-4 pb-3 space-y-2 border-t border-slate-100 bg-slate-50/50">
          {item.timeline.map((step, i) => (
            <li key={i} className="flex gap-2 text-xs pt-2">
              <span className="font-semibold text-slate-700 shrink-0 w-24">{step.stage}</span>
              <span className="text-slate-600">
                {step.detail}
                {step.rules_version && (
                  <span className="text-slate-400"> · rules v{step.rules_version}</span>
                )}
              </span>
            </li>
          ))}
        </ol>
      )}
    </article>
  );
}
