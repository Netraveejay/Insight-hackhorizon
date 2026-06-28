import { LogOut } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { useNavigate } from 'react-router-dom';

interface Props {
  week: string;
  weeks: string[];
  onWeekChange: (w: string) => void;
}

export default function TopBar({ week, weeks, onWeekChange }: Props) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <label htmlFor="week-select" className="text-sm text-slate-600">Week</label>
        <select
          id="week-select"
          value={week}
          onChange={(e) => onWeekChange(e.target.value)}
          className="border border-slate-300 rounded-md px-2 py-1 text-sm bg-white"
        >
          {weeks.map((w) => (
            <option key={w} value={w}>{w}</option>
          ))}
        </select>
      </div>
      <div className="flex items-center gap-3">
        {user && (
          <span className="text-xs text-slate-500 hidden sm:inline">
            {user.name}
          </span>
        )}
        <button
          onClick={handleLogout}
          className="flex items-center gap-1 px-2 py-1.5 rounded-md text-sm text-slate-500 hover:bg-slate-100"
          title="Sign out"
        >
          <LogOut size={16} />
        </button>
      </div>
    </header>
  );
}
