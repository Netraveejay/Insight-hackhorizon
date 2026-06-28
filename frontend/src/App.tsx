import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useState } from 'react';
import { AuthProvider } from './auth/AuthContext';
import ProtectedLayout from './auth/ProtectedLayout';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import ChatWidget from './components/ChatWidget';
import Login from './views/Login';
import AgentNetwork from './views/AgentNetwork';
import AgentActivity from './views/AgentActivity';
import Overview from './views/Overview';
import LiveFeed from './views/LiveFeed';
import Issues from './views/Issues';
import Trends from './views/Trends';
import Digest from './views/Digest';
import PerSite from './views/PerSite';
import Reports from './views/Reports';
import Alerts from './views/Alerts';
import Rules from './views/Rules';
import Leaderboard from './views/Leaderboard';

const WEEKS = ['2026-W22', '2026-W23', '2026-W24', '2026-W25', '2026-W26'];

function AppShell() {
  const [week, setWeek] = useState('2026-W26');

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar week={week} weeks={WEEKS} onWeekChange={setWeek} />
        <main className="flex-1 p-4 md:p-6 overflow-auto">
          <Routes>
            <Route path="/agents" element={<AgentNetwork week={week} />} />
            <Route path="/activity" element={<AgentActivity week={week} />} />
            <Route path="/assistant" element={<Overview week={week} />} />
            <Route path="/" element={<Overview week={week} />} />
            <Route path="/feed" element={<LiveFeed week={week} />} />
            <Route path="/issues" element={<Issues week={week} />} />
            <Route path="/trends" element={<Trends week={week} />} />
            <Route path="/digest" element={<Digest week={week} />} />
            <Route path="/leaderboard" element={<Leaderboard week={week} />} />
            <Route path="/sites" element={<PerSite week={week} />} />
            <Route path="/reports" element={<Reports week={week} />} />
            <Route path="/alerts" element={<Alerts week={week} />} />
            <Route path="/rules" element={<Rules />} />
          </Routes>
        </main>
        <ChatWidget week={week} />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedLayout />}>
            <Route path="/*" element={<AppShell />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
