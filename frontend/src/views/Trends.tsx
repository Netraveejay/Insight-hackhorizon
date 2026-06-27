import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { api } from '../api';

export default function Trends({ week }: { week: string }) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.trends(week).then(setData);
  }, [week]);

  if (!data) return <p className="text-slate-500">Loading trends…</p>;

  const series = (data.compounding_series as { week: string; theme: string; guest_neg: number; staff_neg: number }[]) || [];
  const projection = series.filter((s) => s.theme === 'projection_quality');
  const trajectories = (data.theme_trajectories as { theme: string; direction: string; series: { week: string; neg: number }[] }[]) || [];

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold">Trends — {week}</h2>

      <section className="bg-white border rounded-lg p-4">
        <h3 className="font-semibold mb-4">Compounding: Projection Quality (Guest vs Staff)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={projection}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="week" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="guest_neg" stroke="#2563eb" name="Guest negatives" strokeWidth={2} />
            <Line type="monotone" dataKey="staff_neg" stroke="#2563eb" name="Staff KPI flags" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </section>

      <section className="bg-white border rounded-lg overflow-hidden">
        <h3 className="font-semibold p-4 border-b">National Theme Trajectories</h3>
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="text-left p-3">Theme</th>
              <th className="text-left p-3">Direction</th>
              <th className="text-left p-3">Latest Neg</th>
            </tr>
          </thead>
          <tbody>
            {trajectories.map((t) => (
              <tr key={t.theme} className="border-t">
                <td className="p-3">{t.theme.replace(/_/g, ' ')}</td>
                <td className="p-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    t.direction === 'rising' ? 'bg-red-100 text-red-800' :
                    t.direction === 'falling' ? 'bg-green-100 text-green-800' :
                    'bg-slate-100 text-slate-700'
                  }`}>
                    {t.direction}
                  </span>
                </td>
                <td className="p-3">{t.series[t.series.length - 1]?.neg ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
