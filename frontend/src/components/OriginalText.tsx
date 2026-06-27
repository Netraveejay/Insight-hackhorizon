import { useState } from 'react';
import Chip from './Chip';

interface Props {
  text: string;
  originalText?: string | null;
  language?: string;
  translated?: boolean;
}

export default function OriginalText({ text, originalText, language, translated }: Props) {
  const [showOriginal, setShowOriginal] = useState(false);

  if (!translated || !originalText) {
    return <p className="text-slate-700">{text}</p>;
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <Chip label={`translated from ${language?.toUpperCase() || '?'}`} variant="info" />
        <button
          type="button"
          onClick={() => setShowOriginal(!showOriginal)}
          className="text-xs text-slate-500 hover:text-slate-800 underline"
        >
          {showOriginal ? 'Hide original' : 'Show original'}
        </button>
      </div>
      <p className="text-slate-700">{text}</p>
      {showOriginal && (
        <p className="text-slate-500 text-sm mt-1 italic border-l-2 border-slate-200 pl-2">{originalText}</p>
      )}
    </div>
  );
}
