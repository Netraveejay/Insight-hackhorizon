import { useEffect, useState } from 'react';
import { api } from '../api';

export default function Rules() {
  const [rules, setRules] = useState<Record<string, unknown> | null>(null);
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [staffWeight, setStaffWeight] = useState(0.9);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.rules().then((r) => {
      setRules(r);
      setWeights(r.channel_weights as Record<string, number>);
      setStaffWeight(r.staff_weight as number);
    });
  }, []);

  const handleRescore = async () => {
    setLoading(true);
    try {
      const res = await api.rescore({ channel_weights: weights, staff_weight: staffWeight });
      setResult(res);
      setRules(res.config as Record<string, unknown>);
    } finally {
      setLoading(false);
    }
  };

  if (!rules) return <p className="text-slate-500">Loading rules…</p>;

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-xl font-bold">Rules Engine</h2>
      <p className="text-sm text-slate-600">
        Version <strong>{String(rules.version)}</strong> — edit weights and re-score with no rebuild.
      </p>

      <section className="bg-white border rounded-lg p-4 space-y-4">
        <h3 className="font-semibold">Channel Weights</h3>
        {Object.entries(weights).map(([ch, w]) => (
          <div key={ch} className="flex items-center gap-4">
            <label className="text-sm w-40">{ch}</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={w}
              onChange={(e) => setWeights({ ...weights, [ch]: parseFloat(e.target.value) })}
              className="flex-1"
            />
            <span className="text-sm w-8">{w.toFixed(1)}</span>
          </div>
        ))}

        <div className="flex items-center gap-4">
          <label className="text-sm w-40">Staff weight</label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={staffWeight}
            onChange={(e) => setStaffWeight(parseFloat(e.target.value))}
            className="flex-1"
          />
          <span className="text-sm w-8">{staffWeight.toFixed(1)}</span>
        </div>

        <button
          onClick={handleRescore}
          disabled={loading}
          className="bg-accent text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-accent/90 disabled:opacity-50"
        >
          {loading ? 'Re-scoring…' : `Re-score against v${rules.version}`}
        </button>
      </section>

      {result && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm">
          <p className="font-medium text-green-800">
            Re-scored to v{String((result.config as Record<string, unknown>).version)} — no rebuild required
          </p>
          <pre className="mt-2 text-xs overflow-auto">{JSON.stringify(result.pipeline, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
