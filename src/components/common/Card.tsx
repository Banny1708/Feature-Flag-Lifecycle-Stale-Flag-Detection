import React from 'react';
import { cn } from '@/utils/cn';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverEffect?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, className, hoverEffect = false, ...props }) => (
  <div
    className={cn(
      'rounded-lg border border-border bg-surface text-zinc-100 shadow-sm',
      hoverEffect && 'transition-all duration-200 hover:border-border-strong hover:bg-surface-100/50',
      className
    )}
    {...props}
  >
    {children}
  </div>
);

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ children, className, ...props }) => (
  <div className={cn('p-5 border-b border-border/60 flex items-center justify-between', className)} {...props}>
    {children}
  </div>
);

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({ children, className, ...props }) => (
  <h3 className={cn('text-base font-semibold text-zinc-100 tracking-tight', className)} {...props}>
    {children}
  </h3>
);

export const CardDescription: React.FC<React.HTMLAttributes<HTMLParagraphElement>> = ({ children, className, ...props }) => (
  <p className={cn('text-xs text-zinc-400 mt-0.5', className)} {...props}>
    {children}
  </p>
);

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ children, className, ...props }) => (
  <div className={cn('p-5', className)} {...props}>
    {children}
  </div>
);

export const CardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ children, className, ...props }) => (
  <div className={cn('px-5 py-3.5 bg-surface-200/50 border-t border-border/60 flex items-center justify-between', className)} {...props}>
    {children}
  </div>
);
