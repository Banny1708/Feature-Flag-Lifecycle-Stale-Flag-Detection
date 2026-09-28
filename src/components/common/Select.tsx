import React from 'react';
import { cn } from '@/utils/cn';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[];
  label?: string;
}

export const Select: React.FC<SelectProps> = ({ options, label, className, ...props }) => {
  return (
    <div className="flex flex-col gap-1">
      {label && <label className="text-xs font-medium text-zinc-400">{label}</label>}
      <select
        className={cn(
          'px-3 py-1.5 text-xs bg-surface-100 border border-border rounded-md text-zinc-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 cursor-pointer',
          className
        )}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} className="bg-surface-200 text-zinc-200">
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
};
