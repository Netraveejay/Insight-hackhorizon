import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Bot, ChevronDown, ChevronUp, Loader2, MessageCircle, Mic, MicOff,
  Radio, Send, Volume2, VolumeX, User, X,
} from 'lucide-react';
import { api, A2AMessage, ChatMessage } from '../api';

interface Props {
  week: string;
}

const SpeechRecognitionCtor =
  typeof window !== 'undefined'
    ? (window as unknown as { SpeechRecognition?: new () => SpeechRecognition }).SpeechRecognition
      || (window as unknown as { webkitSpeechRecognition?: new () => SpeechRecognition }).webkitSpeechRecognition
    : undefined;

const INTENT_BADGE: Record<string, string> = {
  query: 'bg-blue-100 text-blue-800',
  response: 'bg-emerald-100 text-emerald-800',
  alert: 'bg-amber-100 text-amber-800',
  handoff: 'bg-indigo-100 text-indigo-800',
  status: 'bg-slate-100 text-slate-600',
};

export default function ChatWidget({ week }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [speakAnswers, setSpeakAnswers] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceMode, setVoiceMode] = useState(!!SpeechRecognitionCtor);
  const [autoSendVoice, setAutoSendVoice] = useState(true);
  const [correlationId, setCorrelationId] = useState<string | undefined>();
  const [chatMode, setChatMode] = useState<'ai' | 'offline' | null>(null);
  const [aiModel, setAiModel] = useState<string | null>(null);
  const [a2aTrace, setA2aTrace] = useState<A2AMessage[]>([]);
  const [showTrace, setShowTrace] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const traceRef = useRef<HTMLDivElement>(null);
  const recRef = useRef<SpeechRecognition | null>(null);
  const activeCidRef = useRef<string | undefined>();

  useEffect(() => {
    api.assistantSuggestions().then((r) => setSuggestions(r.questions)).catch(() => null);
    api.assistantStatus().then((s) => {
      setChatMode(s.ai_enabled ? 'ai' : 'offline');
      setAiModel(s.model);
    }).catch(() => setChatMode('offline'));
  }, []);

  useEffect(() => {
    if (!open) return;
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamBuffer, open]);

  useEffect(() => {
    activeCidRef.current = correlationId;
  }, [correlationId]);

  useEffect(() => {
    if (!open) return;
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = import.meta.env.VITE_API_URL
      ? new URL(import.meta.env.VITE_API_URL).host
      : window.location.host;
    const path = import.meta.env.VITE_API_URL ? '/a2a/ws' : '/api/a2a/ws';
    const ws = new WebSocket(`${proto}://${host}${path}`);
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as A2AMessage & { type?: string };
        if (data.type === 'ping') return;
        const cid = activeCidRef.current;
        if (!cid || data.correlation_id === cid) {
          setA2aTrace((prev) => [...prev.slice(-49), data]);
        }
      } catch {
        /* ignore */
      }
    };
    return () => ws.close();
  }, [open]);

  useEffect(() => {
    if (traceRef.current) traceRef.current.scrollTop = traceRef.current.scrollHeight;
  }, [a2aTrace]);

  const speak = useCallback((text: string) => {
    if (!speakAnswers || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'en-AU';
    u.rate = 0.95;
    window.speechSynthesis.speak(u);
  }, [speakAnswers]);

  const loadA2a = useCallback(async (cid: string) => {
    const hist = await api.a2aMessages(cid).catch(() => null);
    if (hist) setA2aTrace(hist.messages);
  }, []);

  const send = useCallback(async (text: string) => {
    const q = text.trim();
    if (!q || loading) return;
    setInput('');
    const userMsg: ChatMessage = { role: 'user', content: q };
    const nextHistory = [...messages, userMsg];
    setMessages(nextHistory);
    setLoading(true);
    setStreamBuffer('');
    setA2aTrace([]);

    try {
      const streamed = await api.assistantChatStream(
        nextHistory.map(({ role, content }) => ({ role, content })),
        week,
        correlationId,
        (token) => setStreamBuffer((b) => b + token),
      );
      if (streamed?.answer) {
        setCorrelationId(streamed.correlationId);
        activeCidRef.current = streamed.correlationId;
        if (streamed.mode) setChatMode(streamed.mode as 'ai' | 'offline');
        await loadA2a(streamed.correlationId);
        setMessages((m) => [
          ...m,
          { role: 'assistant', content: streamed.answer, references: streamed.references },
        ]);
        speak(streamed.answer);
      } else {
        const res = await api.assistantChat(
          nextHistory.map(({ role, content }) => ({ role, content })),
          week,
          correlationId,
        );
        setCorrelationId(res.a2a_correlation_id);
        activeCidRef.current = res.a2a_correlation_id;
        await loadA2a(res.a2a_correlation_id);
        setMessages((m) => [
          ...m,
          { role: 'assistant', content: res.answer, references: res.references },
        ]);
        speak(res.answer);
      }
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: e instanceof Error ? e.message : 'Something went wrong.' },
      ]);
    } finally {
      setLoading(false);
      setStreamBuffer('');
    }
  }, [messages, week, correlationId, loading, speak, loadA2a]);

  const toggleMic = () => {
    if (!SpeechRecognitionCtor) return;
    if (listening) {
      recRef.current?.stop();
      setListening(false);
      return;
    }
    const rec = new SpeechRecognitionCtor();
    rec.lang = 'en-AU';
    (rec as SpeechRecognition & { interimResults: boolean; continuous: boolean }).continuous = false;
    (rec as SpeechRecognition & { interimResults: boolean }).interimResults = true;
    rec.onresult = (e: SpeechRecognitionEvent) => {
      const t = Array.from(e.results)
        .map((r) => r[0].transcript)
        .join('');
      setInput(t);
      if (e.results[e.results.length - 1]?.isFinal && autoSendVoice) {
        send(t);
      }
    };
    (rec as SpeechRecognition & { onerror: (() => void) | null }).onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    rec.start();
    recRef.current = rec;
    setListening(true);
  };

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-accent text-white shadow-lg hover:scale-105 transition-transform flex items-center justify-center group"
          aria-label="Open Insight Assistant"
        >
          <MessageCircle size={26} />
          {SpeechRecognitionCtor && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-white" title="Voice supported" />
          )}
        </button>
      )}

      {open && (
        <div className="fixed bottom-6 right-6 z-50 w-[min(440px,calc(100vw-2rem))] h-[min(680px,calc(100vh-4rem))] flex flex-col bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-slate-800 to-slate-700 text-white shrink-0">
            <div className="flex items-center gap-2">
              <div className={`w-9 h-9 rounded-full bg-accent flex items-center justify-center ${listening ? 'animate-pulse ring-2 ring-green-400' : ''}`}>
                <Bot size={18} />
              </div>
              <div>
                <p className="text-sm font-semibold flex items-center gap-2">
                  Insight Assistant
                  {chatMode === 'ai' && (
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-purple-500/90 text-white">
                      AI{aiModel ? ` · ${aiModel}` : ''}
                    </span>
                  )}
                  {chatMode === 'offline' && (
                    <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-slate-600 text-slate-200" title="Set OPENAI_API_KEY in backend .env for real AI">
                      Offline
                    </span>
                  )}
                </p>
                <p className="text-[10px] text-slate-300">
                  Week {week}
                  {listening && ' · 🎤 Listening…'}
                  {loading && !listening && (chatMode === 'ai' ? ' · AI thinking…' : ' · Fetching data…')}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {SpeechRecognitionCtor && (
                <button
                  type="button"
                  onClick={() => setVoiceMode(!voiceMode)}
                  className={`p-1.5 rounded-lg text-xs ${voiceMode ? 'bg-green-600' : 'hover:bg-slate-600'}`}
                  title="Voice mode"
                >
                  <Radio size={14} />
                </button>
              )}
              <button type="button" onClick={() => setOpen(false)} className="p-1.5 hover:bg-slate-600 rounded-lg" aria-label="Close">
                <X size={18} />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-slate-50 min-h-0">
            {messages.length === 0 && (
              <div className="text-center py-6 space-y-2">
                <p className="text-slate-600 text-sm font-medium">Ask anything about this week&apos;s insights</p>
                <p className="text-slate-400 text-xs">
                  {chatMode === 'ai'
                    ? 'Ask naturally — the AI will fetch live data and answer in plain language'
                    : 'Offline mode — add OPENAI_API_KEY to backend .env for a real AI chatbot'}
                </p>
              </div>
            )}
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} onSpeak={speakAnswers ? undefined : (t) => {
                if ('speechSynthesis' in window) {
                  const u = new SpeechSynthesisUtterance(t);
                  u.lang = 'en-AU';
                  window.speechSynthesis.speak(u);
                }
              }} />
            ))}
            {loading && streamBuffer && (
              <div className="flex gap-2">
                <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center shrink-0">
                  <Bot size={14} className="text-white" />
                </div>
                <div className="bg-white border rounded-2xl px-3 py-2 text-sm text-slate-800 max-w-[85%]">
                  {streamBuffer}
                  <span className="animate-pulse text-accent">▌</span>
                </div>
              </div>
            )}
            {loading && !streamBuffer && (
              <div className="flex items-center gap-2 text-slate-500 text-xs px-2">
                <Loader2 size={14} className="animate-spin text-accent" />
                {chatMode === 'ai' ? 'AI selecting tools and reasoning…' : 'Looking up grounded data…'}
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="border-t bg-white shrink-0">
            <button
              type="button"
              onClick={() => setShowTrace(!showTrace)}
              className="w-full flex items-center justify-between px-3 py-2 text-xs text-slate-600 hover:bg-slate-50"
            >
              <span className="font-medium flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                Agent workflow ({a2aTrace.length} steps)
              </span>
              <span className="flex items-center gap-2">
                {correlationId && (
                  <Link to={`/activity?run=${correlationId}`} className="text-accent hover:underline text-[10px]" onClick={(e) => e.stopPropagation()}>
                    View trace →
                  </Link>
                )}
                {showTrace ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
              </span>
            </button>
            {showTrace && (
              <div ref={traceRef} className="max-h-32 overflow-y-auto px-3 pb-2 space-y-1.5 border-t border-slate-100">
                {a2aTrace.length === 0 && (
                  <p className="text-slate-400 text-[10px] py-2 text-center">Send a question to watch agents collaborate</p>
                )}
                {a2aTrace.map((m, i) => (
                  <div key={m.id} className="flex gap-2 items-start text-[10px]">
                    <span className="w-4 h-4 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center shrink-0 text-[8px] font-bold">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1 flex-wrap">
                        <span className="font-medium text-slate-700">{m.from_agent}</span>
                        <span className="text-slate-400">→</span>
                        <span className="font-medium text-slate-700">{m.to_agent}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${INTENT_BADGE[m.intent] || INTENT_BADGE.status}`}>
                          {m.intent}
                        </span>
                      </div>
                      <p className={`text-slate-600 mt-0.5 ${m.intent === 'alert' ? 'text-amber-700' : ''}`}>
                        {m.summary}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {messages.length === 0 && (
            <div className="flex flex-wrap gap-1.5 px-3 py-2 border-t bg-white shrink-0">
              {suggestions.slice(0, 5).map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => send(q)}
                  className="text-[10px] bg-blue-50 hover:bg-blue-100 text-blue-800 px-2 py-1 rounded-full border border-blue-100"
                >
                  {q.length > 36 ? `${q.slice(0, 36)}…` : q}
                </button>
              ))}
            </div>
          )}

          <div className="p-3 border-t bg-white shrink-0 space-y-2">
            {voiceMode && SpeechRecognitionCtor && (
              <button
                type="button"
                onClick={toggleMic}
                className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  listening
                    ? 'bg-red-500 text-white animate-pulse'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200'
                }`}
              >
                {listening ? <MicOff size={18} /> : <Mic size={18} />}
                {listening ? 'Stop listening' : 'Tap to speak'}
              </button>
            )}
            <div className="flex gap-1.5 items-end">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && send(input)}
                placeholder={listening ? 'Listening…' : 'Ask about issues, sites, comments…'}
                className="flex-1 border border-slate-300 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-accent/30 focus:border-accent"
              />
              <button
                type="button"
                onClick={() => send(input)}
                disabled={loading}
                className="bg-accent text-white p-2.5 rounded-xl disabled:opacity-50"
                aria-label="Send"
              >
                <Send size={16} />
              </button>
              <button
                type="button"
                onClick={() => setSpeakAnswers(!speakAnswers)}
                className={`p-2.5 rounded-xl border ${speakAnswers ? 'bg-green-100 border-green-300 text-green-700' : 'bg-white border-slate-300'}`}
                title={speakAnswers ? 'Speaking answers ON' : 'Speak answers OFF'}
              >
                {speakAnswers ? <Volume2 size={16} /> : <VolumeX size={16} />}
              </button>
            </div>
            {SpeechRecognitionCtor && (
              <label className="text-[9px] text-slate-400 flex items-center gap-1">
                <input type="checkbox" checked={autoSendVoice} onChange={(e) => setAutoSendVoice(e.target.checked)} />
                Auto-send when voice finishes
              </label>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function MessageBubble({ msg, onSpeak }: { msg: ChatMessage; onSpeak?: (t: string) => void }) {
  return (
    <div className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : ''}`}>
      {msg.role === 'assistant' && (
        <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center shrink-0">
          <Bot size={14} className="text-white" />
        </div>
      )}
      <div
        className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
          msg.role === 'user' ? 'bg-accent text-white' : 'bg-white border border-slate-200 text-slate-800'
        }`}
      >
        <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
        {msg.role === 'assistant' && onSpeak && (
          <button type="button" onClick={() => onSpeak(msg.content)} className="text-[9px] text-accent mt-1 hover:underline">
            🔊 Read aloud
          </button>
        )}
        {msg.references && msg.references.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5 pt-1.5 border-t border-slate-100">
            {msg.references.map((ref) => (
              <Link
                key={ref.cluster_id || ref.label}
                to="/issues"
                state={{ clusterId: ref.cluster_id }}
                className="text-[9px] bg-blue-50 hover:bg-blue-100 px-2 py-0.5 rounded-full text-blue-800"
              >
                {ref.label || ref.cluster_id}
              </Link>
            ))}
          </div>
        )}
      </div>
      {msg.role === 'user' && (
        <div className="w-7 h-7 rounded-full bg-slate-300 flex items-center justify-center shrink-0">
          <User size={14} className="text-white" />
        </div>
      )}
    </div>
  );
}
