import { Link } from 'react-router-dom';
import { ArrowRight, Play, AlertTriangle, Download } from 'lucide-react';

interface Props {
  week: string;
  compact?: boolean;
}

export default function GettingStarted({ week, compact }: Props) {
  const steps = [
    { icon: Play, label: 'Run the pipeline', desc: 'Process all feedback for the week', to: '/pipeline' },
    { icon: AlertTriangle, label: 'Review issues', desc: 'See P1 priorities & evidence', to: '/issues' },
    { icon: Download, label: 'Download reports', desc: 'Site manager HTML reports', to: '/reports' },
  ];

  if (compact) {
    return (
      <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 text-sm text-slate-700 flex flex-wrap items-center gap-2">
        <span className="font-medium text-slate-900">New here?</span>
        <Link to="/pipeline" className="text-accent font-medium hover:underline">Run pipeline</Link>
        <span className="text-slate-400">→</span>
        <Link to="/issues" className="text-accent font-medium hover:underline">Check issues</Link>
        <span className="text-slate-400">→</span>
        <Link to="/reports" className="text-accent font-medium hover:underline">Get reports</Link>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-2xl p-6">
      <p className="text-blue-300 text-xs font-semibold uppercase tracking-wider">Getting started</p>
      <h3 className="text-lg font-bold mt-1">How Insight works for week {week}</h3>
      <p className="text-slate-300 text-sm mt-2 max-w-2xl">
        Guest and staff feedback flows through eight agents — ingest, score, detect issues, and generate manager reports.
        Follow these steps to see the full system in action.
      </p>
      <div className="grid sm:grid-cols-3 gap-3 mt-5">
        {steps.map(({ icon: Icon, label, desc, to }, i) => (
          <Link
            key={to}
            to={to}
            className="bg-white/10 hover:bg-white/15 rounded-xl p-4 transition-colors group"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="w-6 h-6 rounded-full bg-accent text-white text-xs font-bold flex items-center justify-center">
                {i + 1}
              </span>
              <Icon size={16} className="text-blue-300" />
            </div>
            <p className="font-semibold text-sm">{label}</p>
            <p className="text-xs text-slate-400 mt-1">{desc}</p>
            <ArrowRight size={14} className="text-blue-400 mt-2 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        ))}
      </div>
    </div>
  );
}
