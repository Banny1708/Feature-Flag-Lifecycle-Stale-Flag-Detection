import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Badge } from '@/components/common/Badge';
import { Modal } from '@/components/common/Modal';
import { EmptyState } from '@/components/common/EmptyState';
import { removalService, DryRunResult } from '@/services/removalService';
import { flagService } from '@/services/flagService';
import { RemovalOperation, FeatureFlag } from '@/types';
import { GitPullRequest, Plus, GitBranch, ArrowUpRight, Loader2, RefreshCw, History } from 'lucide-react';

export const RemovalOperationsPage: React.FC = () => {
  const [operations, setOperations] = useState<RemovalOperation[]>([]);
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [isNewOpModalOpen, setIsNewOpModalOpen] = useState(false);
  const [selectedFlagId, setSelectedFlagId] = useState('');
  const [dryRun, setDryRun] = useState<DryRunResult | null>(null);
  const [isWorking, setIsWorking] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [modalSuccess, setModalSuccess] = useState<string | null>(null);
  const [rollbackingId, setRollbackingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    Promise.all([removalService.getRemovalOperations(), flagService.getStaleFlags()])
      .then(([ops, f]) => {
        if (!isMounted) return;
        setOperations(ops);
        setFlags(f);
        if (f.length > 0 && !selectedFlagId) setSelectedFlagId(f[0].id);
      })
      .catch((err: Error) => {
        if (isMounted) setError(err.message || 'Failed to load removal operations');
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'merged':
      case 'SUCCESS':
        return <Badge variant="emerald" dot>{status === 'SUCCESS' ? 'Removal Verified' : 'Merged & Cleaned'}</Badge>;
      case 'in-review':
        return <Badge variant="violet" dot>PR In Review</Badge>;
      case 'prepared':
      case 'RUNNING':
      case 'PENDING':
        return <Badge variant="amber" dot>{status === 'prepared' ? 'PR Prepared' : status}</Badge>;
      case 'failed':
      case 'FAILED':
        return <Badge variant="rose" dot>Failed</Badge>;
      case 'ROLLED_BACK':
        return <Badge variant="blue" dot>Rolled Back</Badge>;
      default:
        return <Badge variant="zinc" dot>{status}</Badge>;
    }
  };

  const openModal = () => {
    setDryRun(null);
    setModalError(null);
    setModalSuccess(null);
    setIsNewOpModalOpen(true);
  };

  const runDryRun = async () => {
    if (!selectedFlagId) return;
    setIsWorking(true);
    setModalError(null);
    try {
      setDryRun(await removalService.dryRun(selectedFlagId));
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Dry run failed');
    } finally {
      setIsWorking(false);
    }
  };

  const startRemoval = async () => {
    if (!selectedFlagId) return;
    setIsWorking(true);
    setModalError(null);
    try {
      const op = await removalService.removeFlag(selectedFlagId);
      setModalSuccess(`Removal ${op.verificationStatus ?? op.status}: ${op.filesAffected} file(s) changed.`);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Removal failed');
    } finally {
      setIsWorking(false);
    }
  };

  const rollback = async (op: RemovalOperation) => {
    setRollbackingId(op.id);
    setActionError(null);
    try {
      const res = await removalService.rollbackRemoval(op.id);
      setReloadKey((k) => k + 1);
      setActionError(null);
      void res;
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Rollback failed');
    } finally {
      setRollbackingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-sm text-zinc-400 gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
        Loading removal operations…
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Automated Removal Operations" description="Monitor automated code elimination pipelines." />
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
        title="Automated Removal Operations"
        description="Monitor automated code elimination pipelines powered by Piranha and FlagShark, tracking refactoring pull requests and deleted dead lines."
        actions={
          <Button
            variant="primary"
            size="sm"
            onClick={openModal}
            icon={<Plus className="w-3.5 h-3.5" />}
          >
            New Removal Pipeline
          </Button>
        }
      />

      {actionError && (
        <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-800/60 text-xs text-rose-200 font-mono">
          {actionError}
        </div>
      )}

      {operations.length === 0 ? (
        <EmptyState
          title="No removal operations yet"
          description="Dry-run or remove a stale flag to create the first recorded operation. Every run, diff, and verification is persisted."
        />
      ) : (
        <div className="space-y-4">
          {operations.map((op) => (
            <Card key={op.id} className="p-5">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div className="space-y-2 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-zinc-100 font-bold text-sm">{op.flagName}</span>
                    {getStatusBadge(op.status)}
                    <Badge variant="blue" size="sm" className="font-mono text-[10px]">
                      Tool: {op.toolTarget}
                    </Badge>
                    {op.operationType && (
                      <Badge variant="zinc" size="sm" className="font-mono text-[10px]">
                        {op.operationType}
                      </Badge>
                    )}
                    {op.cleanupStatus && (
                      <Badge
                        variant={op.cleanupStatus === 'APPLIED' || op.cleanupStatus === 'DRY_RUN' ? 'emerald' : op.cleanupStatus === 'UNSUPPORTED' || op.cleanupStatus === 'NO_CHANGES' ? 'amber' : 'zinc'}
                        size="sm"
                        className="font-mono text-[10px]"
                      >
                        Cleanup: {op.cleanupStatus}
                      </Badge>
                    )}
                  </div>

                  <div className="flex items-center gap-3 text-xs text-zinc-400">
                    <span className="font-mono text-zinc-300">{op.repositoryName}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <GitBranch className="w-3.5 h-3.5 text-zinc-400" />
                      Target: <span className="font-mono text-zinc-200">{op.targetBranch}</span>
                    </span>
                    <span>•</span>
                    <span>Initiated by {op.executedBy}</span>
                  </div>

                  {op.diffSummary && (
                    <p className="text-xs text-zinc-300 bg-surface-100 p-2.5 rounded border border-border/70 max-w-3xl">
                      {op.diffSummary}
                    </p>
                  )}

                  <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono text-zinc-400">
                    {op.verificationStatus && (
                      <span>Verification: <span className="text-zinc-200">{op.verificationStatus}</span></span>
                    )}
                    {op.safetyBranch && (
                      <span>Safety branch: <span className="text-indigo-300">{op.safetyBranch}</span></span>
                    )}
                  </div>
                </div>

                {/* Metrics & PR Link */}
                <div className="flex items-center gap-6 shrink-0 pt-3 lg:pt-0 border-t lg:border-t-0 border-border/60">
                  <div className="text-center font-mono">
                    <div className="text-sm font-semibold text-rose-400">-{op.linesRemoved}</div>
                    <div className="text-[10px] text-zinc-400">Lines Deleted</div>
                  </div>
                  <div className="text-center font-mono">
                    <div className="text-sm font-semibold text-emerald-400">+{op.linesAdded}</div>
                    <div className="text-[10px] text-zinc-400">Lines Added</div>
                  </div>
                  <div className="text-center font-mono">
                    <div className="text-sm font-semibold text-zinc-200">{op.filesAffected}</div>
                    <div className="text-[10px] text-zinc-400">Files Touched</div>
                  </div>

                  {op.safetyBranch && (op.status === 'SUCCESS' || op.status === 'merged') && (
                    <Button
                      variant="secondary"
                      size="sm"
                      isLoading={rollbackingId === op.id}
                      onClick={() => rollback(op)}
                      icon={<History className="w-3.5 h-3.5" />}
                    >
                      Rollback
                    </Button>
                  )}

                  {op.prUrl && (
                    <a
                      href={op.prUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 text-xs font-medium hover:bg-indigo-600/30 transition-colors"
                    >
                      <GitPullRequest className="w-3.5 h-3.5" />
                      PR #{op.prNumber}
                      <ArrowUpRight className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* New Pipeline Modal */}
      <Modal
        isOpen={isNewOpModalOpen}
        onClose={() => setIsNewOpModalOpen(false)}
        title="Configure Automated Removal Pipeline"
        description="Select a stale flag, preview the dry-run plan, then execute the Piranha removal."
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block text-zinc-300 font-medium mb-1">Target Feature Flag</label>
            {flags.length === 0 ? (
              <p className="text-zinc-400">No stale flags available. Run detection first.</p>
            ) : (
              <select
                value={selectedFlagId}
                onChange={(e) => {
                  setSelectedFlagId(e.target.value);
                  setDryRun(null);
                  setModalError(null);
                  setModalSuccess(null);
                }}
                className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500"
              >
                {flags.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.key} ({f.repositoryName})
                  </option>
                ))}
              </select>
            )}
          </div>
          {!dryRun && (
            <Button variant="secondary" size="sm" isLoading={isWorking} disabled={!selectedFlagId} onClick={runDryRun}>
              Preview Dry-Run
            </Button>
          )}
          {dryRun && (
            <div className="p-3 rounded bg-surface-100 border border-border text-[11px] font-mono text-zinc-300">
              <div className="text-emerald-400 font-semibold mb-1">Dry-run plan (no changes made)</div>
              <div>Files: {(dryRun.plannedFiles ?? []).join(', ') || '—'}</div>
              <div>~{dryRun.linesRemoved} lines removed · {dryRun.filesAffected} file(s) affected</div>
            </div>
          )}
          {modalError && (
            <div className="p-2.5 rounded bg-rose-950/50 border border-rose-800/60 text-rose-200 font-mono text-[11px]">
              {modalError}
            </div>
          )}
          {modalSuccess && (
            <div className="p-2.5 rounded bg-emerald-950/50 border border-emerald-800/60 text-emerald-200 font-mono text-[11px]">
              {modalSuccess}
            </div>
          )}
          <div className="pt-3 border-t border-border flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setIsNewOpModalOpen(false)}>
              {modalSuccess ? 'Close' : 'Cancel'}
            </Button>
            {!modalSuccess && (
              <Button variant="primary" size="sm" isLoading={isWorking} disabled={!selectedFlagId} onClick={startRemoval}>
                Start Refactor Run
              </Button>
            )}
          </div>
        </div>
      </Modal>
    </div>
  );
};
