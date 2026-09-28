import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/utils/cn';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  maxWidth = 'md',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const widthStyles = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div
        className={cn(
          'w-full rounded-lg bg-surface border border-border-strong shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150',
          widthStyles[maxWidth]
        )}
      >
        <div className="px-5 py-4 border-b border-border/80 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-zinc-100">{title}</h3>
            {description && <p className="text-xs text-zinc-400 mt-0.5">{description}</p>}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-zinc-400 hover:text-white hover:bg-surface-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
};
