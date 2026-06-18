import { type ReactNode } from 'react';
import { cn } from './kpiUtils';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  className?: string;
}

export function KPICard({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendValue,
  className,
}: KPICardProps) {
  return (
    <div className={cn("bg-card border border-line rounded-xl p-6 shadow-sm flex flex-col", className)}>
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-sm font-medium text-muted">{title}</h3>
        {icon && <div className="text-brand">{icon}</div>}
      </div>
      <div className="text-2xl font-bold text-ink mb-1">{value}</div>
      {(subtitle || trendValue) && (
        <div className="flex items-center text-xs mt-auto pt-2">
          {trendValue && (
            <span
              className={cn(
                "font-medium mr-2",
                trend === 'up' ? "text-emerald-600" : trend === 'down' ? "text-rose-600" : "text-subtle"
              )}
            >
              {trendValue}
            </span>
          )}
          {subtitle && <span className="text-subtle">{subtitle}</span>}
        </div>
      )}
    </div>
  );
}
