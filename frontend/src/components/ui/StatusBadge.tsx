import { cn } from './kpiUtils';

interface StatusBadgeProps {
  status: 'green' | 'yellow' | 'red' | 'neutral';
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const statusConfig = {
    green: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
    yellow: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
    red: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
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
