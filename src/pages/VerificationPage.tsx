import React from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { Card } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { Button } from '@/components/common/Button';
import { mockVerificationResults } from '@/data/mockVerification';
import { CheckCircle2, Terminal, ShieldCheck, RefreshCw } from 'lucide-react';
import { formatDate } from '@/utils/formatters';

export const VerificationPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Post-Removal Verification Pipeline"
        description="Automated sanity verification ensuring that Piranha and FlagShark AST code deletions produce valid syntax, compile cleanly, and pass all regression test suites."
        actions={
          <Button variant="secondary" size="sm" icon={<RefreshCw className="w-3.5 h-3.5" />}>
            Re-run Verification Suite
          </Button>
        }
      />

      <div className="space-y-5">
        {mockVerificationResults.map((result) => (
          <Card key={result.id} className="p-5">
            <div className="space-y-4">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/80 pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-zinc-100 font-bold text-sm">{result.flagName}</span>
                    <Badge variant="emerald" size="sm" dot>
                      All Checks Passed
                    </Badge>
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
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                  <div>
                    <div className="text-xs font-semibold text-zinc-200">Build Verification</div>
                    <div className="text-[11px] text-emerald-400 font-mono">0 compile errors</div>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-surface-100/70 border border-border/70 flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                  <div>
                    <div className="text-xs font-semibold text-zinc-200">Test Suite Execution</div>
                    <div className="text-[11px] text-emerald-400 font-mono">100% tests passing</div>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-surface-100/70 border border-border/70 flex items-center gap-3">
                  <ShieldCheck className="w-5 h-5 text-indigo-400 shrink-0" />
                  <div>
                    <div className="text-xs font-semibold text-zinc-200">AST Invariant Check</div>
                    <div className="text-[11px] text-indigo-300 font-mono">Syntax tree clean</div>
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
    </div>
  );
};
