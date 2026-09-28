import React, { useState } from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Badge } from '@/components/common/Badge';
import { Modal } from '@/components/common/Modal';
import { mockRemovalOperations } from '@/data/mockOperations';
import { GitPullRequest, Plus, GitBranch, ArrowUpRight } from 'lucide-react';

export const RemovalOperationsPage: React.FC = () => {
  const [operations] = useState(mockRemovalOperations);
  const [isNewOpModalOpen, setIsNewOpModalOpen] = useState(false);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'merged':
        return <Badge variant="emerald" dot>Merged & Cleaned</Badge>;
      case 'in-review':
        return <Badge variant="violet" dot>PR In Review</Badge>;
      case 'prepared':
        return <Badge variant="amber" dot>PR Prepared</Badge>;
      default:
        return <Badge variant="zinc" dot>{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Automated Removal Operations"
        description="Monitor automated code elimination pipelines powered by Piranha and FlagShark, tracking refactoring pull requests and deleted dead lines."
        actions={
          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsNewOpModalOpen(true)}
            icon={<Plus className="w-3.5 h-3.5" />}
          >
            New Removal Pipeline
          </Button>
        }
      />

      {/* Operations List */}
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

      {/* New Pipeline Modal */}
      <Modal
        isOpen={isNewOpModalOpen}
        onClose={() => setIsNewOpModalOpen(false)}
        title="Configure Automated Removal Pipeline"
        description="Select refactoring tool, target permanent value, and target branch for Piranha code elimination."
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block text-zinc-300 font-medium mb-1">Target Feature Flag</label>
            <select className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500">
              <option>LEGACY_OAUTH_V1_FALLBACK (auth-identity-engine)</option>
              <option>OLD_CHECKOUT_UPSELL_CARD (core-checkout-service)</option>
              <option>COOKIE_CONSENT_MODAL_2023 (customer-portal-web)</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-zinc-300 font-medium mb-1">Refactoring Engine</label>
              <select className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500">
                <option>Uber Piranha (AST Rewrite)</option>
                <option>FlagShark CLI Scanner</option>
              </select>
            </div>
            <div>
              <label className="block text-zinc-300 font-medium mb-1">Permanent Replacement Value</label>
              <select className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500">
                <option>true (Preserve True Branch)</option>
                <option>false (Preserve False Branch)</option>
              </select>
            </div>
          </div>
          <div className="pt-3 border-t border-border flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setIsNewOpModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                alert('Pipeline triggered. Piranha AST transformation started.');
                setIsNewOpModalOpen(false);
              }}
            >
              Start Refactor Run
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
