import React from 'react';
import { Card } from './Card';
import { cn } from '@/utils/cn';

export interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  trend?: {
    value: string;
    isPositive?: boolean;
    isNeutral?: boolean;
  };
  icon?: React.ReactNode;
  variant?: 'default' | 'emerald' | 'amber' | 'rose' | 'indigo';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  description,
  trend,
  icon,
  variant = 'default',
}) => {
  const iconColors = {
    default: 'text-zinc-400 bg-surface-100 border-border',
    emerald: 'text-emerald-400 bg-emerald-950/40 border-emerald-800/40',
    amber: 'text-amber-400 bg-amber-950/40 border-amber-800/40',
    rose: 'text-rose-400 bg-rose-950/40 border-rose-800/40',
    indigo: 'text-indigo-400 bg-indigo-950/40 border-indigo-800/40',
  };

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">{title}</span>
          <div className="text-2xl font-bold text-zinc-100 tracking-tight mt-1">{value}</div>
        </div>
        {icon && (
          <div className={cn('p-2.5 rounded-lg border flex items-center justify-center', iconColors[variant])}>
            {icon}
          </div>
        )}
      </div>
      {(description || trend) && (
        <div className="mt-3.5 pt-3 border-t border-border/40 flex items-center gap-2 text-xs">
          {trend && (
            <span
              className={cn(
                'font-medium',
                trend.isNeutral
                  ? 'text-zinc-400'
                  : trend.isPositive
                  ? 'text-emerald-400'
                  : 'text-rose-400'
              )}
            >
              {trend.value}
            </span>
          )}
          {description && <span className="text-zinc-400">{description}</span>}
        </div>
      )}
    </Card>
  );
};
