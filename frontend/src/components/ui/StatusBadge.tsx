import { cn } from './KPICard';

interface StatusBadgeProps {
  status: 'green' | 'yellow' | 'red' | 'neutral';
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const statusConfig = {
    green: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30' },
    yellow: { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30' },
    red: { bg: 'bg-rose-500/15', text: 'text-rose-400', border: 'border-rose-500/30' },
    neutral: { bg: 'bg-elevated', text: 'text-muted', border: 'border-line' },
  };

  const config = statusConfig[status] || statusConfig.neutral;

  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
        config.bg,
        config.text,
        config.border,
        className
      )}
    >
      {label || (status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown')}
    </span>
  );
}
