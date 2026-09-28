import React from 'react';
import { cn } from '@/utils/cn';

export interface RolloutBarProps {
  percentage: number;
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

export const RolloutBar: React.FC<RolloutBarProps> = ({ percentage, showLabel = true, size = 'sm' }) => {
  const getBarColor = (val: number) => {
    if (val === 100) return 'bg-emerald-500';
    if (val > 50) return 'bg-indigo-500';
    if (val > 0) return 'bg-amber-500';
    return 'bg-zinc-600';
  };

  const height = size === 'sm' ? 'h-1.5' : 'h-2.5';

  return (
    <div className="flex items-center gap-2">
      <div className={cn('w-20 bg-surface-200 rounded-full overflow-hidden border border-border/40', height)}>
        <div
          className={cn('h-full transition-all duration-300', getBarColor(percentage))}
          style={{ width: `${Math.min(Math.max(percentage, 0), 100)}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-mono text-zinc-300 w-9 text-right font-medium">
          {percentage}%
        </span>
      )}
    </div>
  );
};
