import React, { useState } from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/common/Card';
import { CodeSnippetViewer } from '@/components/domain/CodeSnippetViewer';
import { mockCodeReferences, mockCodePaths } from '@/data/mockCodeAnalysis';
import { mockFeatureFlags } from '@/data/mockFeatureFlags';
import { Code2, Sparkles, AlertOctagon } from 'lucide-react';

export const CodeAnalysisPage: React.FC = () => {
  const [selectedFlagKey, setSelectedFlagKey] = useState<string>('DEPRECATED_STRIPE_WEBHOOK');

  const selectedFlag = mockFeatureFlags.find((f) => f.key === selectedFlagKey);
  const references = mockCodeReferences.filter(
    (r) => r.flagName === selectedFlagKey || (!selectedFlag && true)
  );
  const deadPaths = mockCodePaths.filter(
    (p) => selectedFlag && p.flagId === selectedFlag.id
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="AST Static Code Analysis"
        description="Inspect Abstract Syntax Tree references, enclosing control-flow statements, dead branch paths, and complexity reduction potential."
      />

      {/* Flag Selector Header */}
      <Card className="p-4 bg-surface-100/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-zinc-400">Target Feature Flag:</span>
            <select
              value={selectedFlagKey}
              onChange={(e) => setSelectedFlagKey(e.target.value)}
              className="bg-surface-200 border border-border rounded-md px-3 py-1.5 text-xs font-mono text-indigo-300 font-semibold focus:outline-none focus:border-indigo-500 cursor-pointer"
            >
              {mockFeatureFlags.map((flag) => (
                <option key={flag.id} value={flag.key} className="bg-surface-200 text-zinc-200">
                  {flag.key} ({flag.repositoryName})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-3 text-xs text-zinc-400">
            <span>AST References Found: <strong className="text-zinc-200 font-mono">{references.length}</strong></span>
            <span>•</span>
            <span>Dead Branches: <strong className="text-rose-400 font-mono">{deadPaths.length}</strong></span>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Code References Snippets */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
              <Code2 className="w-4 h-4 text-indigo-400" />
              AST Code References
            </h3>
            <span className="text-[11px] text-zinc-400">
              Evaluated by FlagShark Parser
            </span>
          </div>

          {references.length === 0 ? (
            <Card className="p-8 text-center text-xs text-zinc-400">
              No direct AST references found for this flag in the latest scan index.
            </Card>
          ) : (
            references.map((ref) => (
              <CodeSnippetViewer
                key={ref.id}
                filePath={ref.filePath}
                lineNumber={ref.lineNumber}
                snippet={ref.codeSnippet}
                astNodeType={ref.astNodeType}
                referenceType={ref.referenceType}
                isDeadCode={ref.referenceType === 'cleanup-candidate'}
              />
            ))
          )}
        </div>

        {/* Right Col: Dead Code Path & Complexity Elimination */}
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-1.5">
                <AlertOctagon className="w-4 h-4 text-rose-400" />
                Dead Code Path Analysis
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {deadPaths.length === 0 ? (
                <div className="text-xs text-zinc-400 text-center py-4">
                  No dead branches detected. Branch condition may still evaluate dynamically.
                </div>
              ) : (
                deadPaths.map((path) => (
                  <div key={path.id} className="space-y-2 border-b border-border/60 pb-3 last:border-none last:pb-0">
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="font-mono text-zinc-300 font-semibold">{path.branchCondition}</span>
                      <span className="px-1.5 py-0.2 rounded bg-rose-950/80 text-rose-300 border border-rose-800/60 font-mono text-[10px]">
                        Unreachable
                      </span>
                    </div>

                    <div className="p-2.5 rounded bg-[#0b0f19] border border-border text-[11px] font-mono text-rose-300/90 whitespace-pre-wrap leading-relaxed">
                      {path.deadCodeSnippet}
                    </div>

                    <div className="flex justify-between items-center text-[11px] text-zinc-400">
                      <span>Cyclomatic reduction:</span>
                      <span className="text-emerald-400 font-mono font-medium">-{path.complexityReductionScore} pts</span>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Automated Refactor Suggestion */}
          <Card className="bg-surface-100/60">
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                Piranha Refactoring Recipe
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs text-zinc-300">
              <p>
                When applying Piranha AST rewrite rule, the condition:
              </p>
              <pre className="p-2.5 rounded bg-[#0b0f19] border border-border text-indigo-300 font-mono text-[11px]">
{`piranha_rule {
  flag: "${selectedFlagKey}",
  default_value: false,
  eliminate_enclosing_blocks: true
}`}
              </pre>
              <p className="text-zinc-400 text-[11px]">
                Eliminates the guard statement, inlines the modern branch, and auto-removes unused imports.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
