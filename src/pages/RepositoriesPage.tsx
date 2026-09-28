import React, { useState } from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Modal } from '@/components/common/Modal';
import { ScanStatusBadge } from '@/components/domain/ScanStatusBadge';
import { mockRepositories } from '@/data/mockRepositories';
import { ExternalLink, RefreshCw, Plus, GitBranch, FolderGit2 } from 'lucide-react';
import { formatDate, formatNumber } from '@/utils/formatters';

export const RepositoriesPage: React.FC = () => {
  const [repositories, setRepositories] = useState(mockRepositories);
  const [scanningRepoId, setScanningRepoId] = useState<string | null>(null);
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);

  const handleScanRepo = (repoId: string) => {
    setScanningRepoId(repoId);
    setTimeout(() => {
      setRepositories((prev) =>
        prev.map((r) =>
          r.id === repoId
            ? { ...r, scanStatus: 'completed', lastScannedAt: new Date().toISOString() }
            : r
        )
      );
      setScanningRepoId(null);
    }, 1500);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Monitored Repositories"
        description="Source code repositories linked for continuous feature flag AST scanning, dead branch identification, and Piranha refactoring."
        actions={
          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsConnectModalOpen(true)}
            icon={<Plus className="w-3.5 h-3.5" />}
          >
            Connect Repository
          </Button>
        }
      />

      {/* Repositories Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {repositories.map((repo) => {
          const isScanningThis = scanningRepoId === repo.id || repo.scanStatus === 'scanning';

          return (
            <Card key={repo.id} hoverEffect className="flex flex-col justify-between">
              <div>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded bg-surface-100 border border-border text-zinc-300">
                      <FolderGit2 className="w-4 h-4 text-indigo-400" />
                    </div>
                    <div>
                      <CardTitle className="text-sm font-semibold">{repo.name}</CardTitle>
                      <span className="text-[11px] text-zinc-400 font-normal">{repo.owner}</span>
                    </div>
                  </div>
                  <ScanStatusBadge status={isScanningThis ? 'scanning' : repo.scanStatus} />
                </CardHeader>

                <CardContent className="space-y-3.5 pt-3">
                  <div className="flex items-center justify-between text-xs text-zinc-400">
                    <span className="flex items-center gap-1.5">
                      <GitBranch className="w-3.5 h-3.5 text-zinc-400" />
                      Branch: <span className="text-zinc-200 font-mono">{repo.defaultBranch}</span>
                    </span>
                    <span className="px-2 py-0.5 rounded bg-surface-100 border border-border/60 text-[10px] text-zinc-300 font-medium">
                      {repo.language}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 p-2.5 rounded bg-surface-100/60 border border-border/50 text-center">
                    <div>
                      <div className="text-xs font-semibold text-zinc-200">{repo.totalFlags}</div>
                      <div className="text-[10px] text-zinc-400">Total Flags</div>
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-emerald-400">{repo.activeFlags}</div>
                      <div className="text-[10px] text-zinc-400">Active</div>
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-rose-400">{repo.staleFlags}</div>
                      <div className="text-[10px] text-zinc-400">Stale</div>
                    </div>
                  </div>

                  <div className="text-[11px] text-zinc-400 flex items-center justify-between">
                    <span>Lines of Code:</span>
                    <span className="font-mono text-zinc-300">{formatNumber(repo.linesOfCode)}</span>
                  </div>

                  <div className="text-[11px] text-zinc-400 flex items-center justify-between">
                    <span>Last AST Scan:</span>
                    <span className="font-mono text-zinc-300">{formatDate(repo.lastScannedAt)}</span>
                  </div>
                </CardContent>
              </div>

              {/* Card Footer Actions */}
              <div className="p-3.5 bg-surface-200/40 border-t border-border/60 flex items-center justify-between gap-2">
                <a
                  href={repo.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  GitHub
                </a>
                <Button
                  variant="secondary"
                  size="sm"
                  isLoading={isScanningThis}
                  onClick={() => handleScanRepo(repo.id)}
                  icon={<RefreshCw className="w-3.5 h-3.5" />}
                >
                  Scan AST
                </Button>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Connect Repo Modal Placeholder */}
      <Modal
        isOpen={isConnectModalOpen}
        onClose={() => setIsConnectModalOpen(false)}
        title="Connect Git Repository"
        description="Link a GitHub or GitLab repository to enable FlagShark AST scanning."
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block text-zinc-300 font-medium mb-1">Git Repository URL</label>
            <input
              type="text"
              placeholder="https://github.com/org/repo-name"
              className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-zinc-300 font-medium mb-1">Default Branch</label>
              <input
                type="text"
                defaultValue="main"
                className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-zinc-300 font-medium mb-1">Primary Language</label>
              <select className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500">
                <option>TypeScript / JavaScript</option>
                <option>Java</option>
                <option>Go</option>
                <option>Python</option>
              </select>
            </div>
          </div>
          <div className="pt-3 border-t border-border flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setIsConnectModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                alert('Repository connected in demo mode.');
                setIsConnectModalOpen(false);
              }}
            >
              Add Repository
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
