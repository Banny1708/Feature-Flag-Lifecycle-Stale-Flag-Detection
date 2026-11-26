import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { EmptyState } from '@/components/common/EmptyState';
import { RiskBadge } from '@/components/domain/RiskBadge';
import { Modal } from '@/components/common/Modal';
import { flagService } from '@/services/flagService';
import { analysisService } from '@/services/analysisService';
import { removalService, DryRunResult } from '@/services/removalService';
import { lifecycleService, SystemSettings } from '@/services/lifecycleService';
import { FeatureFlag, RiskAssessment } from '@/types';
import { AlertTriangle, Trash2, Code2, CheckSquare, ArrowRight, Loader2, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatDate } from '@/utils/formatters';

export const StaleFlagsPage: React.FC = () => {
  const [staleFlags, setStaleFlags] = useState<FeatureFlag[]>([]);
  const [risks, setRisks] = useState<RiskAssessment[]>([]);
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [selectedFlagKeys, setSelectedFlagKeys] = useState<string[]>([]);
  const [removalModalFlag, setRemovalModalFlag] = useState<FeatureFlag | null>(null);
  const [permanentValue, setPermanentValue] = useState<'true' | 'false'>('false');
  const [dryRun, setDryRun] = useState<DryRunResult | null>(null);
  const [isDryRunning, setIsDryRunning] = useState(false);
  const [isRemoving, setIsRemoving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [modalSuccess, setModalSuccess] = useState<string | null>(null);
  const [bulkStatus, setBulkStatus] = useState<string | null>(null);
  const [isBulking, setIsBulking] = useState(false);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    Promise.all([
      flagService.getStaleFlags(),
      analysisService.getRiskAssessments().catch(() => [] as RiskAssessment[]),
      lifecycleService.getSettings().catch(() => null),
    ])
      .then(([flags, r, s]) => {
        if (!isMounted) return;
        setStaleFlags(flags);
        setRisks(r);
        setSettings(s);
      })
      .catch((err: Error) => {
        if (isMounted) setError(err.message || 'Failed to load stale flags');
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [reloadKey]);

  const toggleSelect = (key: string) => {
    setSelectedFlagKeys((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const selectAll = () => {
    if (selectedFlagKeys.length === staleFlags.length) {
      setSelectedFlagKeys([]);
    } else {
      setSelectedFlagKeys(staleFlags.map((f) => f.key));
    }
  };

  const openRemovalModal = (flag: FeatureFlag) => {
    setRemovalModalFlag(flag);
    setPermanentValue(String(flag.defaultValue) === 'true' ? 'true' : 'false');
    setDryRun(null);
    setModalError(null);
    setModalSuccess(null);
  };

  const runDryRun = async () => {
    if (!removalModalFlag) return;
    setIsDryRunning(true);
    setModalError(null);
    try {
      const plan = await removalService.dryRun(removalModalFlag.id);
      setDryRun(plan);
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Dry run failed');
    } finally {
      setIsDryRunning(false);
    }
  };

  const confirmRemoval = async () => {
    if (!removalModalFlag) return;
    setIsRemoving(true);
    setModalError(null);
    try {
      const op = await removalService.removeFlag(removalModalFlag.id);
      setModalSuccess(
        `Removal ${op.verificationStatus ?? op.status}: ${op.filesAffected} file(s) changed. Safety branch ${op.safetyBranch || 'recorded'}.`
      );
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Removal failed');
    } finally {
      setIsRemoving(false);
    }
  };

  const queueSelected = async () => {
    setIsBulking(true);
    setBulkStatus(null);
    const lines: string[] = [];
    for (const key of selectedFlagKeys) {
      const flag = staleFlags.find((f) => f.key === key);
      if (!flag) continue;
      try {
        const plan = await removalService.dryRun(flag.id);
        lines.push(`${key}: dry-run OK, ${plan.filesAffected} file(s), ~${plan.linesRemoved} lines`);
      } catch (err) {
        lines.push(`${key}: dry-run FAILED — ${err instanceof Error ? err.message : 'error'}`);
      }
    }
    setBulkStatus(lines.join('\n'));
    setIsBulking(false);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-sm text-zinc-400 gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
        Loading stale flag triage data…
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Stale Flag Detection & Triage" description="Flags identified as technical debt candidates." />
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
        title="Stale Flag Detection & Triage"
        description="Flags identified as technical debt candidates based on AST static analysis, invariant condition detection, and production telemetry zero-activity."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={selectAll}
              icon={<CheckSquare className="w-3.5 h-3.5" />}
            >
              {selectedFlagKeys.length === staleFlags.length && staleFlags.length > 0 ? 'Deselect All' : 'Select All'}
            </Button>
            <Button
              variant="danger"
              size="sm"
              disabled={selectedFlagKeys.length === 0}
              isLoading={isBulking}
              onClick={queueSelected}
              icon={<Trash2 className="w-3.5 h-3.5" />}
            >
              Dry-Run Selected ({selectedFlagKeys.length})
            </Button>
          </div>
        }
      />

      {/* Staleness Rules Banner */}
      <div className="p-4 rounded-lg bg-surface-100/70 border border-border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs text-zinc-300">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded bg-amber-950/60 border border-amber-800/60 text-amber-400 mt-0.5">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div>
            <div className="font-semibold text-zinc-200">Automated Staleness Heuristics Active</div>
            <p className="text-zinc-400 mt-0.5">
              {settings
                ? `Flags at 100% rollout inactive for ≥${settings.stale_days_threshold} days, or inactive for ≥${settings.warn_days_threshold} days with zero evaluations, are flagged as removal candidates.`
                : 'Staleness thresholds are configured on the Settings page and enforced by the backend detection engine.'}
            </p>
          </div>
        </div>
        <Link to="/settings" className="shrink-0 text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium">
          Configure Thresholds <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {bulkStatus && (
        <div className="p-3 rounded-lg bg-surface-100/70 border border-border text-[11px] font-mono text-zinc-300 whitespace-pre-wrap">
          {bulkStatus}
        </div>
      )}

      {/* Stale Flags List */}
      {staleFlags.length === 0 ? (
        <EmptyState
          title="No stale flags detected"
          description="No flags are currently classified as stale or potentially stale. Run an analysis to re-evaluate the estate."
        />
      ) : (
        <div className="space-y-4">
          {staleFlags.map((flag) => {
            const isSelected = selectedFlagKeys.includes(flag.key);
            const riskAssessment = risks.find((r) => r.flagId === flag.id);

            return (
              <Card
                key={flag.id}
                className={`p-5 transition-all duration-150 ${
                  isSelected ? 'border-indigo-500/80 bg-surface-100/70' : 'hover:border-border-strong'
                }`}
              >
                <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                  {/* Checkbox and Flag Info */}
                  <div className="flex items-start gap-3.5 flex-1">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelect(flag.key)}
                      className="mt-1 h-4 w-4 rounded bg-surface-200 border-border text-indigo-600 focus:ring-indigo-500/50 cursor-pointer"
                    />
                    <div className="space-y-1.5 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-zinc-100 font-semibold text-sm">{flag.key}</span>
                        <RiskBadge level={flag.risk} />
                        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-surface-200 border border-border text-zinc-400">
                          {flag.repositoryName}
                        </span>
                      </div>

                      <p className="text-xs text-zinc-300 leading-relaxed max-w-3xl">
                        {flag.description}
                      </p>

                      {/* Staleness Indicators / Evidence */}
                      <div className="flex flex-wrap items-center gap-3 pt-2 text-[11px] text-zinc-400 font-mono">
                        <span className="flex items-center gap-1 text-rose-400 font-medium">
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                          {flag.metrics.daysInactive} days inactive
                        </span>
                        <span>•</span>
                        <span>Rollout: {flag.metrics.rolloutPercentage}%</span>
                        <span>•</span>
                        <span>Owner: {flag.owner}</span>
                        {flag.staleSince && (
                          <>
                            <span>•</span>
                            <span>Stale since: {formatDate(flag.staleSince)}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Risk and Action Side */}
                  <div className="flex lg:flex-col items-center lg:items-end justify-between gap-3 shrink-0 pt-2 lg:pt-0 border-t lg:border-t-0 border-border/60">
                    {riskAssessment && (
                      <div className="text-right">
                        <div className="text-[11px] text-zinc-400">Blast Radius Score</div>
                        <div className="text-sm font-bold font-mono text-rose-300">
                          {riskAssessment.blastRadiusScore} / 100
                        </div>
                      </div>
                    )}

                    <div className="flex items-center gap-2">
                      <Link to="/code-analysis">
                        <Button variant="secondary" size="sm" icon={<Code2 className="w-3.5 h-3.5" />}>
                          Inspect AST
                        </Button>
                      </Link>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => openRemovalModal(flag)}
                        icon={<Trash2 className="w-3.5 h-3.5" />}
                      >
                        Queue Piranha PR
                      </Button>
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Confirmation Modal */}
      {removalModalFlag && (
        <Modal
          isOpen={!!removalModalFlag}
          onClose={() => setRemovalModalFlag(null)}
          title="Queue Flag for Automated Removal"
          description="Prepare an automated refactoring pull request using Uber Piranha."
        >
          <div className="space-y-4 text-xs">
            <p className="text-zinc-300">
              You are queueing <code className="font-mono text-indigo-300 bg-surface-100 px-1 py-0.5 rounded">{removalModalFlag.key}</code> for removal.
              The AST engine will eliminate the flag conditional expression, preserve the chosen permanent branch, and generate a pull request for team review.
            </p>
            <div className="p-3 rounded bg-surface-100 border border-border space-y-2">
              <div className="flex justify-between">
                <span className="text-zinc-400">Refactoring Tool:</span>
                <span className="text-zinc-200 font-mono font-medium">Uber Piranha (AST)</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-400">Target Permanent Value:</span>
                <select
                  value={permanentValue}
                  onChange={(e) => setPermanentValue(e.target.value as 'true' | 'false')}
                  className="bg-surface-200 border border-border rounded px-2 py-1 text-xs font-mono text-emerald-400 focus:outline-none focus:border-indigo-500"
                >
                  <option value="true">true (Graduated)</option>
                  <option value="false">false (Retired)</option>
                </select>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Verification:</span>
                <span className="text-zinc-200 font-mono">Automated CI Build & Tests</span>
              </div>
            </div>
            {!dryRun && (
              <Button variant="secondary" size="sm" isLoading={isDryRunning} onClick={runDryRun}>
                Run Dry-Run First
              </Button>
            )}
            {dryRun && (
              <div className="p-3 rounded bg-surface-100 border border-border text-[11px] font-mono text-zinc-300">
                <div className="text-emerald-400 font-semibold mb-1">Dry-run plan (no changes made)</div>
                <div>Files: {(dryRun.plannedFiles ?? []).join(', ') || '—'}</div>
                <div>
                  ~{dryRun.linesRemoved} lines removed · {dryRun.filesAffected} file(s) affected
                </div>
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
              <Button variant="ghost" size="sm" onClick={() => setRemovalModalFlag(null)}>
                {modalSuccess ? 'Close' : 'Cancel'}
              </Button>
              {!modalSuccess && (
                <Button variant="primary" size="sm" isLoading={isRemoving} onClick={confirmRemoval}>
                  Confirm & Create PR
                </Button>
              )}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
