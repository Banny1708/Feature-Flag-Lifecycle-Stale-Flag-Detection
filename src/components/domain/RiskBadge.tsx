import React from 'react';
import { RiskLevel } from '@/types';
import { Badge } from '@/components/common/Badge';
import { AlertTriangle, ShieldCheck, ShieldAlert, AlertOctagon } from 'lucide-react';

export interface RiskBadgeProps {
  level: RiskLevel;
  size?: 'sm' | 'md';
  showIcon?: boolean;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, size = 'sm', showIcon = true }) => {
  const config: Record<
    RiskLevel,
    { label: string; variant: 'emerald' | 'amber' | 'rose' | 'zinc'; icon: React.ReactNode }
  > = {
    low: {
      label: 'Low Risk',
      variant: 'emerald',
      icon: <ShieldCheck className="w-3 h-3" />,
    },
    medium: {
      label: 'Medium Risk',
      variant: 'amber',
      icon: <AlertTriangle className="w-3 h-3" />,
    },
    high: {
      label: 'High Risk',
      variant: 'rose',
      icon: <ShieldAlert className="w-3 h-3" />,
    },
    critical: {
      label: 'Critical Risk',
      variant: 'rose',
      icon: <AlertOctagon className="w-3 h-3" />,
    },
  };

  const item = config[level] || { label: level, variant: 'zinc', icon: null };

  return (
    <Badge variant={item.variant} size={size} className="gap-1.5 uppercase font-mono tracking-wider">
      {showIcon && item.icon}
      {item.label}
    </Badge>
  );
};
