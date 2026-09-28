import React, { useState } from 'react';
import { Search, Play, Bell, GitBranch, RefreshCw } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { Badge } from '@/components/common/Badge';

export interface TopbarProps {
  onTriggerScan?: () => void;
  isScanning?: boolean;
}

export const Topbar: React.FC<TopbarProps> = ({ onTriggerScan, isScanning = false }) => {
  const [selectedRepo, setSelectedRepo] = useState('all');

  return (
    <header className="h-16 bg-[#0d121c] border-b border-border px-6 flex items-center justify-between shrink-0 select-none">
      {/* Search & Repo Context */}
      <div className="flex items-center gap-4 flex-1 max-w-xl">
        <div className="relative w-72">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-zinc-400" />
          <input
            type="text"
            placeholder="Search flags, code references, or repos..."
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-surface-100 border border-border rounded-md text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50"
          />
          <kbd className="absolute right-2.5 top-2 px-1.5 py-0.5 text-[10px] font-mono text-zinc-400 bg-surface-200 border border-border rounded">
            ⌘K
          </kbd>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-zinc-400 border-l border-border pl-4">
          <GitBranch className="w-3.5 h-3.5 text-zinc-400" />
          <select
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            className="bg-transparent text-zinc-300 text-xs focus:outline-none cursor-pointer font-medium"
          >
            <option value="all" className="bg-surface-200">All Repositories (5)</option>
            <option value="core-checkout-service" className="bg-surface-200">core-checkout-service</option>
            <option value="api-gateway" className="bg-surface-200">api-gateway</option>
            <option value="customer-portal-web" className="bg-surface-200">customer-portal-web</option>
            <option value="auth-identity-engine" className="bg-surface-200">auth-identity-engine</option>
            <option value="billing-analytics-worker" className="bg-surface-200">billing-analytics-worker</option>
          </select>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        <Badge variant="emerald" size="sm" dot>
          Production Envoy
        </Badge>

        <Button
          variant="primary"
          size="sm"
          onClick={onTriggerScan}
          isLoading={isScanning}
          icon={isScanning ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
        >
          {isScanning ? 'Scanning AST...' : 'Run AST Scan'}
        </Button>

        <div className="h-6 w-px bg-border/80 mx-1" />

        <button
          className="relative p-2 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-surface-100 transition-colors"
          title="Alerts"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500" />
        </button>

        <div className="flex items-center gap-2 pl-2 border-l border-border">
          <div className="w-7 h-7 rounded-full bg-indigo-900/60 border border-indigo-500/50 flex items-center justify-center text-xs font-semibold text-indigo-200">
            DE
          </div>
          <div className="hidden lg:block text-left text-xs leading-tight">
            <div className="font-medium text-zinc-200">DevOps Lead</div>
            <div className="text-[10px] text-zinc-400">admin@acme.internal</div>
          </div>
        </div>
      </div>
    </header>
  );
};
