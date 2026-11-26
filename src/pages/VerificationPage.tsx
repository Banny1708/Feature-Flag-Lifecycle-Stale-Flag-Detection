import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { Card } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { Button } from '@/components/common/Button';
import { EmptyState } from '@/components/common/EmptyState';
import { removalService } from '@/services/removalService';
import { VerificationResult, VerificationStatus } from '@/types';
import { CheckCircle2, XCircle, Terminal, ShieldCheck, RefreshCw, Loader2, MinusCircle } from 'lucide-react';
import { formatDate } from '@/utils/formatters';

function statusIcon(status: VerificationStatus) {
  switch (status) {
    case 'passed':
      return <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />;
    case 'failed':
      return <XCircle className="w-5 h-5 text-rose-400 shrink-0" />;
    case 'running':
      return <Loader2 className="w-5 h-5 text-amber-400 shrink-0 animate-spin" />;
    default:
      return <MinusCircle className="w-5 h-5 text-zinc-500 shrink-0" />;
  }
}

function statusColor(status: VerificationStatus) {
  switch (status) {
    case 'passed':
      return 'text-emerald-400';
    case 'failed':
      return 'text-rose-400';
    case 'running':
      return 'text-amber-400';
    default:
      return 'text-zinc-400';
  }
}

export const VerificationPage: React.FC = () => {
  const [results, setResults] = useState<VerificationResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    removalService
      .getVerificationResults()
      .then((data) => {
        if (isMounted) setResults(data);
      })
      .catch((err: Error) => {
        if (isMounted) setError(err.message || 'Failed to load verification results');
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [reloadKey]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-sm text-zinc-400 gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
        Loading verification results…
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Post-Removal Verification Pipeline" description="Automated sanity verification of Piranha code deletions." />
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
        title="Post-Removal Verification Pipeline"
        description="Automated sanity verification ensuring that Piranha and FlagShark AST code deletions produce valid syntax, compile cleanly, and pass all regression test suites."
        actions={
          <Button variant="secondary" size="sm" onClick={() => setReloadKey((k) => k + 1)} icon={<RefreshCw className="w-3.5 h-3.5" />}>
            Refresh Results
          </Button>
        }
      />

      {results.length === 0 ? (
        <EmptyState
          title="No verification results yet"
          description="Verification records appear here after a removal operation completes its build and test checks."
        />
      ) : (
        <div className="space-y-5">
          {results.map((result) => (
            <Card key={result.id} className="p-5">
              <div className="space-y-4">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/80 pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-zinc-100 font-bold text-sm">{result.flagName}</span>
                      {result.testSuiteStatus === 'passed' && result.buildStatus === 'passed' ? (
                        <Badge variant="emerald" size="sm" dot>
                          All Checks Passed
                        </Badge>
                      ) : (
                        <Badge variant={result.testSuiteStatus === 'failed' || result.buildStatus === 'failed' ? 'rose' : 'amber'} size="sm" dot>
                          {result.testSuiteStatus === 'failed' || result.buildStatus === 'failed' ? 'Checks Failed' : 'Verification Pending'}
                        </Badge>
                      )}
                    </div>
                    <div className="text-xs text-zinc-400 mt-0.5">
                      Repository: <span className="font-mono text-zinc-300">{result.repositoryName}</span> • Verified at {formatDate(result.verifiedAt)}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-mono text-zinc-400">Operation:</span>
                    <span className="font-mono text-indigo-300 bg-surface-100 px-2 py-0.5 rounded border border-border text-xs">
                      {result.operationId}
                    </span>
                  </div>
                </div>

                {/* Status Checks Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-3 rounded-lg bg-surface-100/70 border border-border/70 flex items-center gap-3">
                    {statusIcon(result.buildStatus)}
                    <div>
                      <div className="text-xs font-semibold text-zinc-200">Build Verification</div>
                      <div className={`text-[11px] font-mono ${statusColor(result.buildStatus)}`}>
                        {result.buildStatus}
                        {result.diffAnalysis.syntaxValid ? ' · syntax valid' : ' · syntax unconfirmed'}
                      </div>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-surface-100/70 border border-border/70 flex items-center gap-3">
                    {statusIcon(result.testSuiteStatus)}
                    <div>
                      <div className="text-xs font-semibold text-zinc-200">Test Suite Execution</div>
                      <div className={`text-[11px] font-mono ${statusColor(result.testSuiteStatus)}`}>
                        {result.testSuiteStatus}
                        {result.diffAnalysis.regressionDetected ? ' · regression detected' : ''}
                      </div>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-surface-100/70 border border-border/70 flex items-center gap-3">
                    <ShieldCheck className="w-5 h-5 text-indigo-400 shrink-0" />
                    <div>
                      <div className="text-xs font-semibold text-zinc-200">AST Invariant Check</div>
                      <div className={`text-[11px] font-mono ${statusColor(result.astValidationStatus)}`}>
                        {result.astValidationStatus} · {result.diffAnalysis.unresolvedReferences} unresolved refs
                      </div>
                    </div>
                  </div>
                </div>

                {/* Summary Description */}
                <p className="text-xs text-zinc-300 bg-surface-200/40 p-3 rounded border border-border/60">
                  {result.summary}
                </p>

                {/* Terminal Output Log */}
                {result.testOutputSummary && (
                  <div className="rounded-lg bg-[#0b0f19] border border-border p-3 text-xs font-mono text-zinc-300">
                    <div className="flex items-center gap-1.5 text-zinc-500 mb-2 border-b border-border/60 pb-1.5">
                      <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                      <span>CI Runner Execution Log</span>
                    </div>
                    <pre className="text-emerald-400/90 whitespace-pre-wrap">{result.testOutputSummary}</pre>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
