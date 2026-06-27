import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { Lock } from 'lucide-react';

export default function Login() {
  const { login, user } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await login(username.trim().toLowerCase(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-blue-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-accent text-white mb-4">
            <Lock size={28} />
          </div>
          <h1 className="text-2xl font-bold text-white">Insight</h1>
          <p className="text-slate-400 text-sm mt-1">Cinema Operations Intelligence</p>
        </div>

        <form onSubmit={submit} className="bg-white rounded-2xl shadow-xl p-8 space-y-5">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-slate-700 mb-1">Username</label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-accent focus:border-accent outline-none"
              placeholder="admin or harbourview"
              required
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-accent focus:border-accent outline-none"
              required
            />
          </div>

          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-accent text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-60 transition-colors"
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>

          <div className="border-t pt-4 mt-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Demo accounts</p>
            <div className="text-xs text-slate-600 space-y-1.5 bg-slate-50 rounded-lg p-3">
              <p><strong>admin</strong> / insight2026 — HQ, all reports &amp; digest</p>
              <p><strong>harbourview</strong> / site2026 — Harbourview site manager</p>
              <p><strong>northgate</strong> / site2026 — Northgate site manager</p>
            </div>
          </div>
        </form>

        <p className="text-center text-slate-500 text-xs mt-6">Internal use only · Inform, not act</p>
      </div>
    </div>
  );
}
