import React from 'react';
import { Breadcrumbs } from '@/components/navigation/Breadcrumbs';

export interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  showBreadcrumbs?: boolean;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  actions,
  showBreadcrumbs = true,
}) => {
  return (
    <div className="mb-6">
      {showBreadcrumbs && <Breadcrumbs />}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100">{title}</h1>
          {description && <p className="text-xs text-zinc-400 mt-1 max-w-2xl">{description}</p>}
        </div>
        {actions && <div className="flex items-center gap-2.5 shrink-0">{actions}</div>}
      </div>
    </div>
  );
};
