import React from 'react';
import { Search, X } from 'lucide-react';
import { cn } from '@/utils/cn';

export interface SearchInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  value: string;
  onChange: (value: string) => void;
  onClear?: () => void;
  placeholder?: string;
}

export const SearchInput: React.FC<SearchInputProps> = ({
  value,
  onChange,
  onClear,
  placeholder = 'Search...',
  className,
  ...props
}) => {
  return (
    <div className={cn('relative flex items-center', className)}>
      <Search className="absolute left-3 w-4 h-4 text-zinc-400 pointer-events-none" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-9 pr-8 py-1.5 text-xs bg-surface-100 border border-border rounded-md text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition-colors"
        {...props}
      />
      {value && (
        <button
          type="button"
          onClick={() => {
            onChange('');
            onClear?.();
          }}
          className="absolute right-2.5 text-zinc-400 hover:text-white p-0.5 rounded"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};
