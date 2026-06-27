interface Props {
  status?: string | null;
  label?: string | null;
  compact?: boolean;
}

const styles: Record<string, string> = {
  on_track: 'bg-green-100 text-green-800 border-green-200',
  at_risk: 'bg-amber-100 text-amber-900 border-amber-200',
  breached: 'bg-red-100 text-red-800 border-red-200',
};

export default function SlaBadge({ status, label, compact }: Props) {
  if (!status) return null;
  const text = compact
    ? status.replace('_', ' ')
    : label || status.replace('_', ' ');
  return (
    <span
      className={`inline-flex px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide border ${
        styles[status] || 'bg-slate-100 text-slate-600 border-slate-200'
      }`}
      title={label || undefined}
    >
      {text}
    </span>
  );
}
