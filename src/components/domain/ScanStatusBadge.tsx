import React from 'react';
import { ScanStatus } from '@/types';
import { Badge } from '@/components/common/Badge';
import { Loader2 } from 'lucide-react';

export interface ScanStatusBadgeProps {
  status: ScanStatus;
  size?: 'sm' | 'md';
}

export const ScanStatusBadge: React.FC<ScanStatusBadgeProps> = ({ status, size = 'sm' }) => {
  switch (status) {
    case 'scanning':
      return (
        <Badge variant="blue" size={size} className="gap-1.5 font-medium">
          <Loader2 className="w-3 h-3 animate-spin text-blue-400" />
          Scanning...
        </Badge>
      );
    case 'completed':
      return (
        <Badge variant="emerald" size={size} dot>
          Scanned
        </Badge>
      );
    case 'failed':
      return (
        <Badge variant="rose" size={size} dot>
          Scan Failed
        </Badge>
      );
    case 'queued':
      return (
        <Badge variant="amber" size={size} dot>
          Scan Queued
        </Badge>
      );
    case 'idle':
    default:
      return (
        <Badge variant="zinc" size={size} dot>
          Idle
        </Badge>
      );
  }
};
