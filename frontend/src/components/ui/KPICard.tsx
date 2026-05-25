import { type ReactNode } from 'react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

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
    <div className={cn("bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col", className)}>
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-sm font-medium text-gray-500">{title}</h3>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <div className="text-2xl font-bold text-gray-900 mb-1">{value}</div>
      {(subtitle || trendValue) && (
        <div className="flex items-center text-xs mt-auto pt-2">
          {trendValue && (
            <span
              className={cn(
                "font-medium mr-2",
                trend === 'up' ? "text-green-600" : trend === 'down' ? "text-red-600" : "text-gray-500"
              )}
            >
              {trendValue}
            </span>
          )}
          {subtitle && <span className="text-gray-400">{subtitle}</span>}
        </div>
      )}
    </div>
  );
}
