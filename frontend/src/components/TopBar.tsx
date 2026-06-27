import { Mic, MicOff, LogOut } from 'lucide-react';
import { useState, useCallback } from 'react';
import { useAuth } from '../auth/AuthContext';
import { useNavigate } from 'react-router-dom';

interface Props {
  week: string;
  weeks: string[];
  onWeekChange: (w: string) => void;
}

export default function TopBar({ week, weeks, onWeekChange }: Props) {
  const [listening, setListening] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const toggleVoice = useCallback(() => {
    const SR = (window as unknown as { SpeechRecognition?: new () => SpeechRecognition }).SpeechRecognition
      || (window as unknown as { webkitSpeechRecognition?: new () => SpeechRecognition }).webkitSpeechRecognition;
    if (!SR) {
      alert('Speech recognition not supported. Use Ask Insight with typed input.');
      return;
    }
    if (listening) {
      setListening(false);
      return;
    }
    const rec = new SR();
    rec.lang = 'en-AU';
    rec.onresult = (e: SpeechRecognitionEvent) => {
      const transcript = e.results[0][0].transcript;
      window.location.href = `/ask?q=${encodeURIComponent(transcript)}`;
    };
    rec.onend = () => setListening(false);
    rec.start();
    setListening(true);
  }, [listening]);

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
          onClick={toggleVoice}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          listening ? 'bg-accent text-white' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
        }`}
        aria-label={listening ? 'Stop listening' : 'Start voice input'}
      >
        {listening ? <MicOff size={16} /> : <Mic size={16} />}
        {listening ? 'Listening…' : 'Voice'}
        </button>
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
