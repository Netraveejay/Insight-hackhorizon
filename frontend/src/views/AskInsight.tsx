import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Mic, Volume2 } from 'lucide-react';
import { api } from '../api';

const QUICK_QUESTIONS = [
  'What are the top complaints this week?',
  'Tell me about Harbourview projection issues',
  'Any cross-source flags?',
  'What positive themes are trending?',
  'Play daily briefing',
];

export default function AskInsight({ week }: { week: string }) {
  const [searchParams] = useSearchParams();
  const [question, setQuestion] = useState(searchParams.get('q') || '');
  const [answer, setAnswer] = useState('');
  const [refs, setRefs] = useState<string[]>([]);
  const [listening, setListening] = useState(false);

  const ask = useCallback(async (q: string) => {
    if (!q.trim()) return;
    const res = await api.ask(q, week);
    setAnswer(res.answer);
    setRefs(res.references);
    if ('speechSynthesis' in window) {
      const u = new SpeechSynthesisUtterance(res.answer);
      u.lang = 'en-AU';
      window.speechSynthesis.speak(u);
    }
  }, [week]);

  useEffect(() => {
    const q = searchParams.get('q');
    if (q) ask(q);
  }, [searchParams, ask]);

  const startListening = () => {
    const SR = (window as unknown as { SpeechRecognition?: new () => SpeechRecognition }).SpeechRecognition
      || (window as unknown as { webkitSpeechRecognition?: new () => SpeechRecognition }).webkitSpeechRecognition;
    if (!SR) {
      alert('Speech recognition not supported in this browser. Please type your question.');
      return;
    }
    const rec = new SR();
    rec.lang = 'en-AU';
    rec.onresult = (e: SpeechRecognitionEvent) => {
      const t = e.results[0][0].transcript;
      setQuestion(t);
      ask(t);
    };
    rec.onend = () => setListening(false);
    rec.start();
    setListening(true);
  };

  const playBriefing = () => ask('Play daily briefing');

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-xl font-bold">Ask Insight</h2>
      <p className="text-sm text-slate-600">Grounded answers from computed pipeline data. Internal use only.</p>

      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && ask(question)}
          placeholder="Ask about complaints, sites, themes…"
          className="flex-1 border rounded-md px-3 py-2 text-sm"
        />
        <button
          onClick={() => ask(question)}
          className="bg-accent text-white px-4 py-2 rounded-md text-sm font-medium"
        >
          Ask
        </button>
        <button
          onClick={startListening}
          className={`p-2 rounded-md border ${listening ? 'bg-accent text-white' : 'bg-white'}`}
          aria-label="Voice input"
        >
          <Mic size={18} />
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {QUICK_QUESTIONS.map((q) => (
          <button
            key={q}
            onClick={() => { setQuestion(q); ask(q); }}
            className="text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-full"
          >
            {q}
          </button>
        ))}
      </div>

      <button
        onClick={playBriefing}
        className="flex items-center gap-2 text-sm text-accent font-medium hover:underline"
      >
        <Volume2 size={16} /> Play daily briefing
      </button>

      {answer && (
        <div className="bg-white border rounded-lg p-4">
          <p className="text-slate-800">{answer}</p>
          {refs.length > 0 && (
            <p className="text-xs text-slate-400 mt-2">References: {refs.join(', ')}</p>
          )}
        </div>
      )}
    </div>
  );
}
