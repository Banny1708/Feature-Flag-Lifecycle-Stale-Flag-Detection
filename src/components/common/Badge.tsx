import React from 'react';
import { cn } from '@/utils/cn';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'emerald' | 'amber' | 'rose' | 'violet' | 'blue' | 'zinc';
  size?: 'sm' | 'md';
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  className,
  variant = 'zinc',
  size = 'sm',
  dot = false,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center font-medium rounded-full border';

  const variantStyles = {
    emerald: 'bg-emerald-950/50 text-emerald-300 border-emerald-800/60',
    amber: 'bg-amber-950/50 text-amber-300 border-amber-800/60',
    rose: 'bg-rose-950/50 text-rose-300 border-rose-800/60',
    violet: 'bg-purple-950/50 text-purple-300 border-purple-800/60',
    blue: 'bg-blue-950/50 text-blue-300 border-blue-800/60',
    zinc: 'bg-surface-50 text-zinc-300 border-border-strong',
  };

  const dotColors = {
    emerald: 'bg-emerald-400',
    amber: 'bg-amber-400',
    rose: 'bg-rose-400',
    violet: 'bg-purple-400',
    blue: 'bg-blue-400',
    zinc: 'bg-zinc-400',
  };

  const sizeStyles = {
    sm: 'text-xs px-2.5 py-0.5 gap-1.5',
    md: 'text-sm px-3 py-1 gap-2',
  };

  return (
    <span className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)} {...props}>
      {dot && <span className={cn('w-1.5 h-1.5 rounded-full', dotColors[variant])} />}
      {children}
    </span>
  );
};
