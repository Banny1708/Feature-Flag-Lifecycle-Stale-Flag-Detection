import React from 'react';
import { cn } from '@/utils/cn';

export interface TabItem {
  id: string;
  label: string;
  count?: number;
  icon?: React.ReactNode;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onChange, className }) => {
  return (
    <div className={cn('flex items-center gap-1 border-b border-border/80 overflow-x-auto', className)}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 -mb-px transition-colors whitespace-nowrap',
              isActive
                ? 'border-indigo-500 text-indigo-400 font-semibold'
                : 'border-transparent text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
            )}
          >
            {tab.icon}
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={cn(
                  'px-1.5 py-0.2 rounded-full text-[10px] font-mono',
                  isActive ? 'bg-indigo-950 text-indigo-300 border border-indigo-800/60' : 'bg-surface-100 text-zinc-400'
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};
