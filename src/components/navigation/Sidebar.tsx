import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  GitFork,
  Flag,
  AlertTriangle,
  Code2,
  Trash2,
  CheckCircle2,
  FileText,
  Settings,
  Cpu,
} from 'lucide-react';
import { cn } from '@/utils/cn';

interface NavItem {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeVariant?: 'emerald' | 'amber' | 'rose' | 'violet';
}

const navItems: NavItem[] = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Repositories', path: '/repositories', icon: GitFork, badge: '5' },
  { name: 'Feature Flags', path: '/flags', icon: Flag, badge: '98' },
  { name: 'Stale Flags', path: '/stale-flags', icon: AlertTriangle, badge: '24', badgeVariant: 'rose' },
  { name: 'Code Analysis', path: '/code-analysis', icon: Code2 },
  { name: 'Removal Operations', path: '/removal-operations', icon: Trash2, badge: '3', badgeVariant: 'violet' },
  { name: 'Verification', path: '/verification', icon: CheckCircle2 },
  { name: 'Evidence & Reports', path: '/reports', icon: FileText },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 h-screen bg-[#0d121c] border-r border-border flex flex-col shrink-0 select-none">
      {/* Brand Header */}
      <div className="h-16 px-5 border-b border-border/80 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 font-bold shadow-inner">
          <Cpu className="w-4 h-4" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-sm text-zinc-100 tracking-tight">FlagOps</span>
            <span className="text-[10px] font-mono uppercase bg-indigo-950/60 text-indigo-300 border border-indigo-800/40 px-1 py-0.2 rounded font-semibold">
              v2.0
            </span>
          </div>
          <p className="text-[11px] text-zinc-400 font-normal truncate">AST Flag Governance</p>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
          Core Lifecycle
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors group',
                isActive
                  ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-surface-100/60 border border-transparent'
              )
            }
          >
            {({ isActive }) => (
              <>
                <div className="flex items-center gap-2.5">
                  <item.icon
                    className={cn(
                      'w-4 h-4 transition-colors',
                      isActive ? 'text-indigo-400' : 'text-zinc-400 group-hover:text-zinc-300'
                    )}
                  />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span
                    className={cn(
                      'px-1.5 py-0.2 text-[10px] font-mono rounded font-medium',
                      item.badgeVariant === 'rose'
                        ? 'bg-rose-950/80 text-rose-300 border border-rose-800/50'
                        : item.badgeVariant === 'violet'
                        ? 'bg-purple-950/80 text-purple-300 border border-purple-800/50'
                        : 'bg-surface-100 text-zinc-400'
                    )}
                  >
                    {item.badge}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </div>

      {/* System Engine Health Card */}
      <div className="p-3 border-t border-border/80 bg-surface-200/40">
        <div className="p-3 rounded-lg border border-border bg-[#090d16] text-xs">
          <div className="flex items-center justify-between text-zinc-400 mb-1.5">
            <span className="flex items-center gap-1.5 text-[11px] font-medium text-zinc-300">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Engine Pipeline
            </span>
            <span className="font-mono text-[10px] text-zinc-400">Ready</span>
          </div>
          <div className="space-y-1 text-[11px] text-zinc-400">
            <div className="flex justify-between">
              <span>AST Scanner:</span>
              <span className="text-zinc-300 font-mono">FlagShark</span>
            </div>
            <div className="flex justify-between">
              <span>Refactor Tool:</span>
              <span className="text-zinc-300 font-mono">Piranha</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
