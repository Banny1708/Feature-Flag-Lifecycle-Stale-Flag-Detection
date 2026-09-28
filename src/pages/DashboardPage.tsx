import React from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { FlagStatusBadge } from '@/components/domain/FlagStatusBadge';
import { RiskBadge } from '@/components/domain/RiskBadge';
import { mockFeatureFlags } from '@/data/mockFeatureFlags';
import { mockScanResults } from '@/data/mockScanResults';
import { Flag, AlertTriangle, ShieldCheck, Clock, ArrowRight, GitBranch, Cpu, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const staleFlags = mockFeatureFlags.filter((f) => f.status === 'stale');
  const potentiallyStale = mockFeatureFlags.filter((f) => f.status === 'potentially-stale');
  const activeFlags = mockFeatureFlags.filter((f) => f.status === 'active');
  const pendingRemoval = mockFeatureFlags.filter((f) => f.status === 'removal-pending');

  return (
    <div className="space-y-6">
      <PageHeader
        title="Engineering Overview"
        description="Real-time feature flag lifecycle health, AST static analysis detection, and technical debt governance."
        actions={
          <div className="flex items-center gap-2">
            <Link to="/stale-flags">
              <Button variant="danger" size="sm" icon={<AlertTriangle className="w-3.5 h-3.5" />}>
                Review 24 Stale Flags
              </Button>
            </Link>
            <Link to="/removal-operations">
              <Button variant="secondary" size="sm" icon={<Cpu className="w-3.5 h-3.5" />}>
                Active Removal Pipelines
              </Button>
            </Link>
          </div>
        }
      />

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Monitored Flags"
          value={98}
          description="Across 5 active repositories"
          variant="indigo"
          icon={<Flag className="w-5 h-5" />}
          trend={{ value: '+4 this month', isNeutral: true }}
        />
        <StatCard
          title="Stale Flags Identified"
          value={24}
          description="24.4% of total flag estate"
          variant="rose"
          icon={<AlertTriangle className="w-5 h-5" />}
          trend={{ value: 'Needs Attention', isPositive: false }}
        />
        <StatCard
          title="Technical Debt Reclaimed"
          value="110 hrs"
          description="3,240 lines eliminated by Piranha"
          variant="emerald"
          icon={<ShieldCheck className="w-5 h-5" />}
          trend={{ value: '+28 hrs this quarter', isPositive: true }}
        />
        <StatCard
          title="Avg Flag Lifespan"
          value="142 days"
          description="Recommended max: 90 days"
          variant="amber"
          icon={<Clock className="w-5 h-5" />}
          trend={{ value: '+18d drift', isPositive: false }}
        />
      </div>

      {/* Distribution & Health Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Lifecycle Status Distribution */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div>
              <CardTitle>Flag Lifecycle Distribution</CardTitle>
              <p className="text-xs text-zinc-400 mt-0.5">Distribution of all monitored feature flags by operational phase</p>
            </div>
            <Link to="/flags" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
              View All <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="flex items-center gap-2 text-zinc-300">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                    Active / Healthy
                  </span>
                  <span className="font-mono text-zinc-400">54 flags (55.1%)</span>
                </div>
                <div className="w-full bg-surface-200 h-2 rounded-full overflow-hidden">
                  <div className="bg-emerald-500 h-full rounded-full" style={{ width: '55.1%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="flex items-center gap-2 text-zinc-300">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                    Potentially Stale (Warning)
                  </span>
                  <span className="font-mono text-zinc-400">16 flags (16.3%)</span>
                </div>
                <div className="w-full bg-surface-200 h-2 rounded-full overflow-hidden">
                  <div className="bg-amber-500 h-full rounded-full" style={{ width: '16.3%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="flex items-center gap-2 text-zinc-300">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                    Confirmed Stale (Critical Tech Debt)
                  </span>
                  <span className="font-mono text-zinc-400">24 flags (24.4%)</span>
                </div>
                <div className="w-full bg-surface-200 h-2 rounded-full overflow-hidden">
                  <div className="bg-rose-500 h-full rounded-full" style={{ width: '24.4%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="flex items-center gap-2 text-zinc-300">
                    <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
                    Removal Pending / In PR
                  </span>
                  <span className="font-mono text-zinc-400">4 flags (4.2%)</span>
                </div>
                <div className="w-full bg-surface-200 h-2 rounded-full overflow-hidden">
                  <div className="bg-purple-500 h-full rounded-full" style={{ width: '4.2%' }} />
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-border grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="p-2.5 rounded bg-surface-100/60 border border-border/60">
                <div className="text-base font-bold text-emerald-400">{activeFlags.length}</div>
                <div className="text-[11px] text-zinc-400">Active Flags</div>
              </div>
              <div className="p-2.5 rounded bg-surface-100/60 border border-border/60">
                <div className="text-base font-bold text-amber-400">{potentiallyStale.length}</div>
                <div className="text-[11px] text-zinc-400">Warning</div>
              </div>
              <div className="p-2.5 rounded bg-surface-100/60 border border-border/60">
                <div className="text-base font-bold text-rose-400">{staleFlags.length}</div>
                <div className="text-[11px] text-zinc-400">Confirmed Stale</div>
              </div>
              <div className="p-2.5 rounded bg-surface-100/60 border border-border/60">
                <div className="text-base font-bold text-purple-400">{pendingRemoval.length}</div>
                <div className="text-[11px] text-zinc-400">In Pipeline</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Scan Engine Status & Quick Stats */}
        <Card>
          <CardHeader>
            <CardTitle>AST Detection Health</CardTitle>
            <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Live
            </span>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-3 rounded-lg border border-border bg-surface-100/60 text-xs space-y-2">
              <div className="flex justify-between items-center text-zinc-300">
                <span className="text-zinc-400">Engine Engine:</span>
                <span className="font-mono text-indigo-300 font-semibold">FlagShark v1.4</span>
              </div>
              <div className="flex justify-between items-center text-zinc-300">
                <span className="text-zinc-400">Piranha Refactor:</span>
                <span className="font-mono text-zinc-200">v0.3.1 Enabled</span>
              </div>
              <div className="flex justify-between items-center text-zinc-300">
                <span className="text-zinc-400">Last Global Scan:</span>
                <span className="font-mono text-zinc-200">Today, 16:45 UTC</span>
              </div>
              <div className="flex justify-between items-center text-zinc-300">
                <span className="text-zinc-400">Unreachable Nodes:</span>
                <span className="font-mono text-rose-300 font-semibold">38 AST blocks</span>
              </div>
            </div>

            <div className="text-xs space-y-2">
              <div className="font-semibold text-zinc-300">Recent AST Scans</div>
              {mockScanResults.slice(0, 2).map((scan) => (
                <div
                  key={scan.id}
                  className="p-2.5 rounded border border-border/70 bg-surface-200/50 flex items-center justify-between"
                >
                  <div>
                    <div className="font-medium text-zinc-200 text-xs truncate max-w-[150px]">
                      {scan.repositoryName}
                    </div>
                    <div className="text-[10px] text-zinc-400 flex items-center gap-1.5 mt-0.5">
                      <GitBranch className="w-3 h-3" />
                      <span>{scan.branch}</span>
                      <span>•</span>
                      <span className="text-rose-400 font-medium">{scan.staleFlagsDetected} stale</span>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-400">{scan.scanDurationMs}ms</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Critical Stale Flags Table */}
      <Card>
        <CardHeader>
          <div>
            <CardTitle>High-Priority Stale Flags Requiring Action</CardTitle>
            <p className="text-xs text-zinc-400 mt-0.5">
              Identified by AST dead code detection and zero production traffic logs
            </p>
          </div>
          <Link to="/stale-flags">
            <Button variant="secondary" size="sm" icon={<ExternalLink className="w-3.5 h-3.5" />}>
              Open Triage Board
            </Button>
          </Link>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-300 border-collapse">
            <thead className="bg-surface-100/80 text-zinc-400 uppercase text-[10px] font-semibold border-b border-border">
              <tr>
                <th className="px-5 py-3">Flag Name & Key</th>
                <th className="px-5 py-3">Repository</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Risk Level</th>
                <th className="px-5 py-3">Days Stale</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {staleFlags.map((flag) => (
                <tr key={flag.id} className="hover:bg-surface-100/50 transition-colors">
                  <td className="px-5 py-3.5">
                    <div className="font-medium text-zinc-200">{flag.name}</div>
                    <div className="font-mono text-[11px] text-zinc-400 mt-0.5">{flag.key}</div>
                  </td>
                  <td className="px-5 py-3.5 text-zinc-300 font-mono text-[11px]">
                    {flag.repositoryName}
                  </td>
                  <td className="px-5 py-3.5">
                    <FlagStatusBadge status={flag.status} />
                  </td>
                  <td className="px-5 py-3.5">
                    <RiskBadge level={flag.risk} />
                  </td>
                  <td className="px-5 py-3.5 font-mono text-zinc-300">
                    {flag.metrics.daysInactive}d inactive
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <Link to="/code-analysis">
                      <Button variant="ghost" size="sm" className="text-indigo-400 hover:text-indigo-300">
                        Inspect AST
                      </Button>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
