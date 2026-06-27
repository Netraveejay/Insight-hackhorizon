interface Props {
  label: string;
  variant?: 'default' | 'danger' | 'success' | 'warning' | 'info';
}

const styles = {
  default: 'bg-slate-100 text-slate-700',
  danger: 'bg-red-100 text-red-800',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-amber-100 text-amber-800',
  info: 'bg-blue-100 text-blue-800',
};

export default function Chip({ label, variant = 'default' }: Props) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${styles[variant]}`}>
      {label}
    </span>
  );
}
