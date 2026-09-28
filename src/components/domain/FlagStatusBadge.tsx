import React from 'react';
import { FeatureFlagStatus } from '@/types';
import { Badge } from '@/components/common/Badge';

export interface FlagStatusBadgeProps {
  status: FeatureFlagStatus;
  size?: 'sm' | 'md';
}

export const FlagStatusBadge: React.FC<FlagStatusBadgeProps> = ({ status, size = 'sm' }) => {
  const config: Record<FeatureFlagStatus, { label: string; variant: 'emerald' | 'amber' | 'rose' | 'violet' | 'zinc' }> = {
    active: { label: 'Active', variant: 'emerald' },
    'potentially-stale': { label: 'Potentially Stale', variant: 'amber' },
    stale: { label: 'Stale', variant: 'rose' },
    'removal-pending': { label: 'Removal Pending', variant: 'violet' },
    removed: { label: 'Removed', variant: 'zinc' },
  };

  const item = config[status] || { label: status, variant: 'zinc' };

  return (
    <Badge variant={item.variant} size={size} dot>
      {item.label}
    </Badge>
  );
};
