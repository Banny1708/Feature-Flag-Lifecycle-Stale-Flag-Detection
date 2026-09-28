import React from 'react';
import { cn } from '@/utils/cn';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = 'secondary',
  size = 'md',
  isLoading = false,
  icon,
  disabled,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500/50 disabled:opacity-50 disabled:cursor-not-allowed rounded-md border';

  const variantStyles = {
    primary: 'bg-indigo-600 hover:bg-indigo-500 text-white border-indigo-500/80 shadow-sm shadow-indigo-900/30',
    secondary: 'bg-surface-100 hover:bg-surface-50 text-zinc-200 border-border hover:border-border-strong',
    danger: 'bg-rose-950/60 hover:bg-rose-900/70 text-rose-200 border-rose-800/60 focus:ring-rose-500/50',
    ghost: 'bg-transparent hover:bg-surface-100 text-zinc-300 hover:text-white border-transparent',
    outline: 'bg-transparent hover:bg-surface-100/60 text-zinc-200 border-border-strong',
  };

  const sizeStyles = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    md: 'text-sm px-3.5 py-2 gap-2',
    lg: 'text-base px-4 py-2.5 gap-2.5',
  };

  return (
    <button
      className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : icon}
      {children}
    </button>
  );
};
