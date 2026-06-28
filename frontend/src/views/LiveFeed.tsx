import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, FeedData } from '../api';
import Chip from '../components/Chip';
import OriginalText from '../components/OriginalText';
import GettingStarted from '../components/GettingStarted';
import { ChevronDown, ChevronRight, Filter, Inbox } from 'lucide-react';

export default function LiveFeed({ week }: { week: string }) {
  const [data, setData] = useState<FeedData | null>(null);
  const [showFiltered, setShowFiltered] = useState(false);
  const [channelFilter, setChannelFilter] = useState<string>('all');

  useEffect(() => {
    api.feed(week).then(setData);
  }, [week]);

  if (!data) return <p className="text-slate-500">Loading feed…</p>;

  if (!data.has_data) {
    return (
      <div className="space-y-6 max-w-2xl">
        <h2 className="text-xl font-bold">Live Feed — {week}</h2>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-center">
          <Inbox size={40} className="mx-auto text-amber-600 mb-3" />
          <p className="font-semibold text-slate-900">No feedback processed yet for {week}</p>
          <p className="text-sm text-slate-600 mt-2">
            Run the pipeline to ingest guest &amp; staff messages, then return here to browse the live feed.
          </p>
          <Link
            to="/agents"
            className="inline-block mt-4 bg-accent text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Run pipeline now →
          </Link>
        </div>
        <GettingStarted week={week} />
      </div>
    );
  }

  const p = data.pipeline;
  const channels = ['all', ...new Set(data.active_items.map((i) => i.channel))];
  const visible = channelFilter === 'all'
    ? data.active_items
    : data.active_items.filter((i) => i.channel === channelFilter);

  const funnelSteps = [
    { label: 'Received', value: p.total_received, color: 'bg-slate-500' },
    { label: 'Spam removed', value: p.spam_removed, color: 'bg-red-500' },
    { label: 'Duplicates removed', value: p.duplicates_removed, color: 'bg-amber-500' },
    { label: 'Active in feed', value: p.active_in_feed, color: 'bg-accent' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Live Feed — {week}</h2>
        <p className="text-sm text-slate-600 mt-1">
          Every guest &amp; staff message for this week. Items below passed ingestion filters and are used for scoring and issue detection.
        </p>
      </div>

      <GettingStarted week={week} compact />

      {/* Pipeline funnel */}
      <div className="bg-white border rounded-xl p-5">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Pipeline funnel for {week}</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {funnelSteps.map((step) => (
            <div key={step.label} className="text-center">
              <p className={`text-3xl font-bold tabular-nums ${step.value === 0 && step.label !== 'Active in feed' ? 'text-slate-300' : 'text-slate-900'}`}>
                {step.value}
              </p>
              <p className="text-xs text-slate-500 mt-1">{step.label}</p>
              <div className={`h-1 rounded-full mt-2 ${step.color} ${step.value === 0 ? 'opacity-20' : ''}`} />
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-4 mt-4 pt-4 border-t border-slate-100 text-xs text-slate-600">
          <span><strong>{p.translated}</strong> translated to English</span>
          <span><strong>{p.non_controllable}</strong> non-controllable (film choice, etc.)</span>
          <span><strong>{p.pii_redacted}</strong> PII redacted</span>
        </div>
      </div>

      {/* Source coverage */}
      <div className="bg-white border rounded-xl p-4">
        <h3 className="text-sm font-semibold text-slate-800 mb-2">Data sources</h3>
        <p className="text-xs text-slate-500 mb-3">
          Connectors that supplied feedback this run. &quot;Seed&quot; is the demo data source — in production this would be CSAT, inbox, reviews, etc.
        </p>
        {data.source_coverage.entries?.map((e) => (
          <div key={e.connector} className="flex items-center justify-between text-sm py-1">
            <span className="capitalize font-medium">{e.connector} connector</span>
            <Chip label={`${e.item_count} items · ${e.status}`} variant={e.status === 'ok' ? 'success' : 'warning'} />
          </div>
        ))}
      </div>

      {/* Channel filter */}
      <div className="flex flex-wrap gap-2 items-center">
        <Filter size={14} className="text-slate-400" />
        {channels.map((ch) => (
          <button
            key={ch}
            type="button"
            onClick={() => setChannelFilter(ch)}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              channelFilter === ch ? 'bg-accent text-white border-accent' : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'
            }`}
          >
            {ch === 'all' ? 'All channels' : ch.replace(/_/g, ' ')}
          </button>
        ))}
        <span className="text-xs text-slate-400 ml-auto">{visible.length} items</span>
      </div>

      {/* Active items */}
      <section className="space-y-2">
        {visible.map((item) => (
          <FeedCard key={item.id} item={item} />
        ))}
        {visible.length === 0 && (
          <p className="text-slate-500 text-sm text-center py-8">No items for this channel filter.</p>
        )}
      </section>

      {/* Filtered items */}
      {data.filtered_items.length > 0 && (
        <section className="border rounded-xl overflow-hidden">
          <button
            type="button"
            onClick={() => setShowFiltered(!showFiltered)}
            className="w-full flex items-center gap-2 px-4 py-3 bg-slate-50 hover:bg-slate-100 text-sm font-medium text-slate-700"
          >
            {showFiltered ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            Filtered out ({data.filtered_items.length}) — spam, duplicates, non-controllable
          </button>
          {showFiltered && (
            <div className="p-3 space-y-2 bg-slate-50/50">
              {data.filtered_items.map((item) => (
                <FeedCard key={`f-${item.id}`} item={item} muted />
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function FeedCard({ item, muted }: { item: FeedData['active_items'][0]; muted?: boolean }) {
  const date = item.ts
    ? new Date(item.ts).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })
    : '';

  return (
    <article className={`border rounded-xl p-4 text-sm ${muted ? 'bg-slate-50 border-slate-200 opacity-80' : 'bg-white'}`}>
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <Chip label={item.source_type === 'staff' ? 'Staff' : 'Guest'} variant={item.source_type === 'staff' ? 'warning' : 'default'} />
        <Chip label={item.channel_label} variant="info" />
        <span className="font-medium text-slate-800">{item.site_name}</span>
        {date && <span className="text-xs text-slate-400 ml-auto">{date}</span>}
        {item.rating != null && (
          <span className="text-xs text-amber-600 font-medium">{item.rating}/5</span>
        )}
        {item.filter_reason && <Chip label={item.filter_reason} variant="danger" />}
      </div>
      <OriginalText
        text={item.text}
        originalText={item.original_text}
        language={item.original_language}
        translated={item.translated}
      />
      {item.primary_theme && !muted && (
        <p className="text-xs text-slate-400 mt-2 capitalize">
          Theme: {item.primary_theme.replace(/_/g, ' ')}
        </p>
      )}
    </article>
  );
}
