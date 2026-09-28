import React, { useState } from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { RiskBadge } from '@/components/domain/RiskBadge';
import { Modal } from '@/components/common/Modal';
import { mockFeatureFlags } from '@/data/mockFeatureFlags';
import { mockRiskAssessments } from '@/data/mockOperations';
import { AlertTriangle, Trash2, Code2, CheckSquare, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatDate } from '@/utils/formatters';

export const StaleFlagsPage: React.FC = () => {
  const staleFlags = mockFeatureFlags.filter(
    (f) => f.status === 'stale' || f.status === 'potentially-stale'
  );

  const [selectedFlagKeys, setSelectedFlagKeys] = useState<string[]>([]);
  const [removalModalFlag, setRemovalModalFlag] = useState<string | null>(null);

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
              {selectedFlagKeys.length === staleFlags.length ? 'Deselect All' : 'Select All'}
            </Button>
            <Button
              variant="danger"
              size="sm"
              disabled={selectedFlagKeys.length === 0}
              onClick={() => alert(`Queuing ${selectedFlagKeys.length} flags for Piranha automated cleanup.`)}
              icon={<Trash2 className="w-3.5 h-3.5" />}
            >
              Queue Selected ({selectedFlagKeys.length}) for Removal
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
              Flags are flagged stale when evaluated at 100% rollout for &gt;60 days, receiving 0 production evaluations for &gt;90 days, or when AST branches evaluate statically to dead code.
            </p>
          </div>
        </div>
        <Link to="/settings" className="shrink-0 text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium">
          Configure Thresholds <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Stale Flags List */}
      <div className="space-y-4">
        {staleFlags.map((flag) => {
          const isSelected = selectedFlagKeys.includes(flag.key);
          const riskAssessment = mockRiskAssessments.find((r) => r.flagId === flag.id);

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
                      onClick={() => setRemovalModalFlag(flag.key)}
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
              You are queueing <code className="font-mono text-indigo-300 bg-surface-100 px-1 py-0.5 rounded">{removalModalFlag}</code> for removal.
              The AST engine will eliminate the flag conditional expression, preserve the chosen permanent branch, and generate a pull request for team review.
            </p>
            <div className="p-3 rounded bg-surface-100 border border-border space-y-2">
              <div className="flex justify-between">
                <span className="text-zinc-400">Refactoring Tool:</span>
                <span className="text-zinc-200 font-mono font-medium">Uber Piranha (AST)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Target Permanent Value:</span>
                <span className="text-emerald-400 font-mono font-medium">true (Graduated)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Verification:</span>
                <span className="text-zinc-200 font-mono">Automated CI Build & Tests</span>
              </div>
            </div>
            <div className="pt-3 border-t border-border flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setRemovalModalFlag(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  alert(`Removal operation created for ${removalModalFlag}. Check Removal Operations tab.`);
                  setRemovalModalFlag(null);
                }}
              >
                Confirm & Create PR
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
