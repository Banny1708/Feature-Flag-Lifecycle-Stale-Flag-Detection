import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Modal } from '@/components/common/Modal';
import { EmptyState } from '@/components/common/EmptyState';
import { ScanStatusBadge } from '@/components/domain/ScanStatusBadge';
import { repositoryService } from '@/services/repositoryService';
import { Repository } from '@/types';
import { ExternalLink, RefreshCw, Plus, GitBranch, FolderGit2, Loader2 } from 'lucide-react';
import { formatDate, formatNumber } from '@/utils/formatters';

export const RepositoriesPage: React.FC = () => {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [scanningRepoId, setScanningRepoId] = useState<string | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [connectName, setConnectName] = useState('');
  const [connectPath, setConnectPath] = useState('');
  const [connectUrl, setConnectUrl] = useState('');
  const [connectBranch, setConnectBranch] = useState('main');
  const [connectLanguage, setConnectLanguage] = useState('TypeScript');
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  const load = () => setReloadKey((k) => k + 1);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    repositoryService
      .getRepositories()
      .then((data) => {
        if (isMounted) setRepositories(data);
      })
      .catch((err: Error) => {
        if (isMounted) setError(err.message || 'Failed to load repositories');
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [reloadKey]);

  const handleScanRepo = async (repoId: string) => {
    setScanningRepoId(repoId);
    setScanError(null);
    try {
      const scan = await repositoryService.triggerScan(repoId);
      setRepositories((prev) =>
        prev.map((r) =>
          r.id === repoId
            ? {
                ...r,
                scanStatus: scan.status === 'failed' ? 'failed' : 'completed',
                lastScannedAt: scan.timestamp,
                totalFlags: scan.totalFlagsDetected,
                staleFlags: scan.staleFlagsDetected,
              }
            : r
        )
      );
      if (scan.status === 'failed') {
        setScanError(`Scan of ${scan.repositoryName} reported failure. Check backend logs for the FlagShark output.`);
      }
    } catch (err) {
      setScanError(err instanceof Error ? err.message : 'Scan failed');
    } finally {
      setScanningRepoId(null);
    }
  };

  const handleConnect = async () => {
    if (!connectName.trim()) {
      setConnectError('Repository name is required.');
      return;
    }
    setIsConnecting(true);
    setConnectError(null);
    try {
      await repositoryService.connectRepository({
        name: connectName.trim(),
        url: connectUrl.trim() || undefined,
        local_path: connectPath.trim() || undefined,
        default_branch: connectBranch.trim() || 'main',
        language: connectLanguage,
      });
      setIsConnectModalOpen(false);
      setConnectName('');
      setConnectPath('');
      setConnectUrl('');
      setConnectBranch('main');
      load();
    } catch (err) {
      setConnectError(err instanceof Error ? err.message : 'Failed to connect repository');
    } finally {
      setIsConnecting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-sm text-zinc-400 gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
        Loading monitored repositories…
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Monitored Repositories" description="Source code repositories linked for continuous feature flag AST scanning." />
        <Card className="p-8 text-center space-y-3">
          <p className="text-sm text-rose-300 font-medium">Could not reach the backend API</p>
          <p className="text-xs text-zinc-400 font-mono">{error}</p>
          <Button variant="secondary" size="sm" onClick={load} icon={<RefreshCw className="w-3.5 h-3.5" />}>
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Monitored Repositories"
        description="Source code repositories linked for continuous feature flag AST scanning, dead branch identification, and Piranha refactoring."
        actions={
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              setConnectError(null);
              setIsConnectModalOpen(true);
            }}
            icon={<Plus className="w-3.5 h-3.5" />}
          >
            Connect Repository
          </Button>
        }
      />

      {scanError && (
        <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-800/60 text-xs text-rose-200 font-mono">
          {scanError}
        </div>
      )}

      {repositories.length === 0 ? (
        <EmptyState
          title="No repositories monitored"
          description="Connect a repository to enable FlagShark AST scanning and flag discovery."
          action={
            <Button variant="primary" size="sm" onClick={() => setIsConnectModalOpen(true)} icon={<Plus className="w-3.5 h-3.5" />}>
              Connect Repository
            </Button>
          }
        />
      ) : (
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
      )}

      {/* Connect Repo Modal */}
      <Modal
        isOpen={isConnectModalOpen}
        onClose={() => setIsConnectModalOpen(false)}
        title="Connect Git Repository"
        description="Link a repository checkout to enable FlagShark AST scanning."
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block text-zinc-300 font-medium mb-1">Repository Name</label>
            <input
              type="text"
              value={connectName}
              onChange={(e) => setConnectName(e.target.value)}
              placeholder="core-checkout-service"
              className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-zinc-300 font-medium mb-1">Git Repository URL</label>
            <input
              type="text"
              value={connectUrl}
              onChange={(e) => setConnectUrl(e.target.value)}
              placeholder="https://github.com/org/repo-name"
              className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500"
            />
            <p className="mt-1 text-[11px] text-zinc-400">
              Paste a public GitHub URL and FlagOps will clone it into its own workspace. Cloning may take up
              to a minute — do not close this dialog while it is working.
            </p>
          </div>
          <div>
            <label className="block text-zinc-300 font-medium mb-1">Local Checkout Path (optional alternative)</label>
            <input
              type="text"
              value={connectPath}
              onChange={(e) => setConnectPath(e.target.value)}
              placeholder="/srv/workspaces/my-repo"
              className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 font-mono focus:outline-none focus:border-indigo-500"
            />
            <p className="mt-1 text-[11px] text-zinc-400">
              Only needed if you already have the repository checked out on the backend machine. When both
              are given, the local path is used and no clone happens.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-zinc-300 font-medium mb-1">Default Branch</label>
              <input
                type="text"
                value={connectBranch}
                onChange={(e) => setConnectBranch(e.target.value)}
                className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-zinc-300 font-medium mb-1">Primary Language</label>
              <select
                value={connectLanguage}
                onChange={(e) => setConnectLanguage(e.target.value)}
                className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500"
              >
                <option>TypeScript</option>
                <option>JavaScript</option>
                <option>Java</option>
                <option>Go</option>
                <option>Python</option>
              </select>
            </div>
          </div>
          {isConnecting && connectUrl.trim() && !connectPath.trim() && (
            <div className="p-2.5 rounded bg-indigo-950/50 border border-indigo-800/60 text-indigo-200 text-[11px]">
              Cloning repository — this may take up to a minute. Please wait…
            </div>
          )}
          {connectError && (
            <div className="p-2.5 rounded bg-rose-950/50 border border-rose-800/60 text-rose-200 font-mono text-[11px]">
              {connectError}
            </div>
          )}
          <div className="pt-3 border-t border-border flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setIsConnectModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" isLoading={isConnecting} onClick={handleConnect}>
              Add Repository
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
