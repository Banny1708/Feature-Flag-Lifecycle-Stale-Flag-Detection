import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { EmptyState } from '@/components/common/EmptyState';
import { FlagStatusBadge } from '@/components/domain/FlagStatusBadge';
import { RiskBadge } from '@/components/domain/RiskBadge';
import { flagService } from '@/services/flagService';
import { repositoryService } from '@/services/repositoryService';
import { removalService } from '@/services/removalService';
import { lifecycleService } from '@/services/lifecycleService';
import { FeatureFlag, Repository, ScanResult, RemovalOperation } from '@/types';
import { Flag, AlertTriangle, ShieldCheck, Clock, ArrowRight, GitBranch, Cpu, ExternalLink, Loader2, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [scans, setScans] = useState<ScanResult[]>([]);
  const [removals, setRemovals] = useState<RemovalOperation[]>([]);
  const [tools, setTools] = useState<Array<{ name: string; available: boolean }>>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    Promise.all([
      flagService.getFeatureFlags(),
      repositoryService.getRepositories(),
      repositoryService.getScanResults(),
      removalService.getRemovalOperations(),
      lifecycleService.getToolStatus().catch(() => [] as Array<{ name: string; available: boolean }>),
    ])
      .then(([f, r, s, o, t]) => {
        if (!isMounted) return;
        setFlags(f);
        setRepos(r);
        setScans(s);
        setRemovals(o);
        setTools(t);
      })
      .catch((err: Error) => {
        if (isMounted) setError(err.message || 'Failed to load dashboard data');
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [reloadKey]);

  const staleFlags = flags.filter((f) => f.status === 'stale');
  const potentiallyStale = flags.filter((f) => f.status === 'potentially-stale');
  const activeFlags = flags.filter((f) => f.status === 'active');
  const pendingRemoval = flags.filter((f) => f.status === 'removal-pending');
  const total = flags.length;
  const pct = (n: number) => (total > 0 ? ((n / total) * 100).toFixed(1) : '0.0');

  const completedRemovals = removals.filter((o) => o.status === 'merged' || o.status === 'SUCCESS');
  const linesEliminated = completedRemovals.reduce((sum, o) => sum + (o.linesRemoved || 0), 0);
  const debtHours = completedRemovals.length * 5;

  const avgLifespanDays = (() => {
    const ages = flags
      .map((f) => {
        const t = Date.parse(f.createdAt);
        return Number.isNaN(t) ? null : Math.max(0, Math.round((Date.now() - t) / 86400000));
      })
      .filter((n): n is number => n !== null);
    if (ages.length === 0) return null;
    return Math.round(ages.reduce((a, b) => a + b, 0) / ages.length);
  })();

  const recentScans = scans.slice(0, 2);
  const lastScanAt = scans.length > 0 ? scans[0].timestamp : '';
  const openStaleFindings = scans.reduce((sum, s) => sum + (s.staleFlagsDetected || 0), 0);
  const toolAvailable = (name: string) => tools.find((t) => t.name === name)?.available;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-sm text-zinc-400 gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
        Loading live flag lifecycle data…
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Engineering Overview" description="Real-time feature flag lifecycle health." />
        <Card className="p-8 text-center space-y-3">
          <p className="text-sm text-rose-300 font-medium">Could not reach the backend API</p>
          <p className="text-xs text-zinc-400 font-mono">{error}</p>
          <Button variant="secondary" size="sm" onClick={() => setReloadKey((k) => k + 1)} icon={<RefreshCw className="w-3.5 h-3.5" />}>
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Engineering Overview"
        description="Real-time feature flag lifecycle health, AST static analysis detection, and technical debt governance."
        actions={
          <div className="flex items-center gap-2">
            <Link to="/stale-flags">
              <Button variant="danger" size="sm" icon={<AlertTriangle className="w-3.5 h-3.5" />}>
                Review {staleFlags.length} Stale Flags
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
          value={total}
          description={`Across ${repos.length} active repositories`}
          variant="indigo"
          icon={<Flag className="w-5 h-5" />}
          trend={{ value: `${repos.length} repositories`, isNeutral: true }}
        />
        <StatCard
          title="Stale Flags Identified"
          value={staleFlags.length}
          description={total > 0 ? `${pct(staleFlags.length)}% of total flag estate` : 'No flags monitored yet'}
          variant="rose"
          icon={<AlertTriangle className="w-5 h-5" />}
          trend={{ value: staleFlags.length > 0 ? 'Needs Attention' : 'All Clear', isPositive: staleFlags.length === 0 }}
        />
        <StatCard
          title="Technical Debt Reclaimed"
          value={`${debtHours} hrs`}
          description={`${linesEliminated.toLocaleString()} lines eliminated by completed removals`}
          variant="emerald"
          icon={<ShieldCheck className="w-5 h-5" />}
          trend={{ value: `${completedRemovals.length} removals completed`, isPositive: true }}
        />
        <StatCard
          title="Avg Flag Lifespan"
          value={avgLifespanDays === null ? '—' : `${avgLifespanDays} days`}
          description="Recommended max: 90 days"
          variant="amber"
          icon={<Clock className="w-5 h-5" />}
          trend={
            avgLifespanDays === null
              ? { value: 'No data', isNeutral: true }
              : { value: avgLifespanDays > 90 ? `+${avgLifespanDays - 90}d drift` : 'Within target', isPositive: avgLifespanDays <= 90 }
          }
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
                  <span className="font-mono text-zinc-400">{activeFlags.length} flags ({pct(activeFlags.length)}%)</span>
                </div>
                <div className="w-full bg-surface-200 h-2 rounded-full overflow-hidden">
                  <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${pct(activeFlags.length)}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="flex items-center gap-2 text-zinc-300">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                    Potentially Stale (Warning)
                  </span>
                  <span className="font-mono text-zinc-400">{potentiallyStale.length} flags ({pct(potentiallyStale.length)}%)</span>
                </div>
                <div className="w-full bg-surface-200 h-2 rounded-full overflow-hidden">
                  <div className="bg-amber-500 h-full rounded-full" style={{ width: `${pct(potentiallyStale.length)}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="flex items-center gap-2 text-zinc-300">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                    Confirmed Stale (Critical Tech Debt)
                  </span>
                  <span className="font-mono text-zinc-400">{staleFlags.length} flags ({pct(staleFlags.length)}%)</span>
                </div>
                <div className="w-full bg-surface-200 h-2 rounded-full overflow-hidden">
                  <div className="bg-rose-500 h-full rounded-full" style={{ width: `${pct(staleFlags.length)}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="flex items-center gap-2 text-zinc-300">
                    <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
                    Removal Pending / In PR
                  </span>
                  <span className="font-mono text-zinc-400">{pendingRemoval.length} flags ({pct(pendingRemoval.length)}%)</span>
                </div>
                <div className="w-full bg-surface-200 h-2 rounded-full overflow-hidden">
                  <div className="bg-purple-500 h-full rounded-full" style={{ width: `${pct(pendingRemoval.length)}%` }} />
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
                <span className="text-zinc-400">FlagShark Scanner:</span>
                <span className={`font-mono font-semibold ${toolAvailable('flagshark') ? 'text-indigo-300' : 'text-amber-300'}`}>
                  {tools.length === 0 ? 'Unknown' : toolAvailable('flagshark') ? 'Available' : 'Not installed'}
                </span>
              </div>
              <div className="flex justify-between items-center text-zinc-300">
                <span className="text-zinc-400">Piranha Refactor:</span>
                <span className={`font-mono ${toolAvailable('piranha') ? 'text-zinc-200' : 'text-amber-300'}`}>
                  {tools.length === 0 ? 'Unknown' : toolAvailable('piranha') ? 'Available' : 'Not installed'}
                </span>
              </div>
              <div className="flex justify-between items-center text-zinc-300">
                <span className="text-zinc-400">Last Scan:</span>
                <span className="font-mono text-zinc-200">{lastScanAt || 'Never'}</span>
              </div>
              <div className="flex justify-between items-center text-zinc-300">
                <span className="text-zinc-400">Open Stale Findings:</span>
                <span className="font-mono text-rose-300 font-semibold">{openStaleFindings} flags</span>
              </div>
            </div>

            <div className="text-xs space-y-2">
              <div className="font-semibold text-zinc-300">Recent AST Scans</div>
              {recentScans.length === 0 ? (
                <div className="text-[11px] text-zinc-400">No scans recorded yet.</div>
              ) : (
                recentScans.map((scan) => (
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
                        <span>•</span>
                        <span className="font-mono" title="Scanner engine that produced this scan">
                          {scan.scannerEngine || 'Unknown engine'}
                        </span>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono text-zinc-400">{scan.scanDurationMs}ms</span>
                  </div>
                ))
              )}
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
        {staleFlags.length === 0 ? (
          <EmptyState
            title="No stale flags"
            description="The detection engine has not confirmed any stale flags. Run a repository scan to evaluate the estate."
          />
        ) : (
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
        )}
      </Card>
    </div>
  );
};
