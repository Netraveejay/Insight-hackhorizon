interface Props {
  priority: string;
}

export default function Tag({ priority }: Props) {
  const colors: Record<string, string> = {
    P1: 'bg-accent text-white',
    P2: 'bg-orange-500 text-white',
    P3: 'bg-slate-500 text-white',
  };
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-bold ${colors[priority] || 'bg-slate-400 text-white'}`}>
      {priority}
    </span>
  );
}
