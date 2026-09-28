import React from 'react';
import { cn } from '@/utils/cn';
import { Inbox } from 'lucide-react';

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon = <Inbox className="w-8 h-8 text-zinc-500" />,
  action,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-12 text-center rounded-lg border border-dashed border-border/80 bg-surface-200/30',
        className
      )}
    >
      <div className="p-3 rounded-full bg-surface-100 border border-border text-zinc-400 mb-3">
        {icon}
      </div>
      <h4 className="text-sm font-semibold text-zinc-200">{title}</h4>
      <p className="text-xs text-zinc-400 max-w-sm mt-1 mb-4">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
