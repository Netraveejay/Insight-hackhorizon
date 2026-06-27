import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Radio, AlertTriangle, TrendingUp,
  FileText, MapPin, Bell, Sliders, MessageCircleQuestion, Zap, Download,
} from 'lucide-react';

const links = [
  { to: '/pipeline', icon: Zap, label: 'Pipeline Run' },
  { to: '/reports', icon: Download, label: 'Manager Reports' },
  { to: '/', icon: LayoutDashboard, label: 'Overview' },
  { to: '/feed', icon: Radio, label: 'Live Feed' },
  { to: '/issues', icon: AlertTriangle, label: 'Issues' },
  { to: '/trends', icon: TrendingUp, label: 'Trends' },
  { to: '/digest', icon: FileText, label: 'Weekly Digest' },
  { to: '/sites', icon: MapPin, label: 'Per-Site' },
  { to: '/alerts', icon: Bell, label: 'Teams Alerts' },
  { to: '/rules', icon: Sliders, label: 'Rules Engine' },
  { to: '/ask', icon: MessageCircleQuestion, label: 'Ask Insight' },
];

export default function Sidebar() {
  return (
    <aside className="w-56 bg-slate-900 text-white flex-shrink-0 hidden md:flex flex-col">
      <div className="p-4 border-b border-slate-700">
        <h1 className="text-lg font-bold tracking-tight">
          <span className="text-accent">Insight</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">Cinema Operations Intelligence</p>
      </div>
      <nav className="flex-1 p-2 space-y-0.5">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                isActive ? 'bg-accent text-white' : 'text-slate-300 hover:bg-slate-800'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="p-3 text-xs text-slate-500 border-t border-slate-700">
        Inform, not act · Internal only
      </div>
    </aside>
  );
}
