import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/navigation/Sidebar';
import { Topbar } from '@/components/navigation/Topbar';
import { repositoryService } from '@/services/repositoryService';
import { CheckCircle2, X, AlertTriangle } from 'lucide-react';

export const AppLayout: React.FC = () => {
  const [isScanning, setIsScanning] = useState(false);
  const [scanNotification, setScanNotification] = useState<string | null>(null);
  const [scanFailed, setScanFailed] = useState(false);

  const handleTriggerScan = async () => {
    setIsScanning(true);
    setScanNotification(null);
    setScanFailed(false);
    try {
      const repos = await repositoryService.getRepositories();
      if (repos.length === 0) {
        setScanNotification('No repositories registered — connect one before scanning.');
        setScanFailed(true);
        return;
      }
      let evaluated = 0;
      let stale = 0;
      const failures: string[] = [];
      for (const repo of repos) {
        try {
          const scan = await repositoryService.triggerScan(repo.id);
          evaluated += scan.totalFlagsDetected;
          stale += scan.staleFlagsDetected;
        } catch (err) {
          failures.push(`${repo.name}: ${err instanceof Error ? err.message : 'failed'}`);
        }
      }
      if (failures.length === repos.length) {
        setScanNotification(`Global scan failed: ${failures[0]}`);
        setScanFailed(true);
      } else {
        setScanNotification(
          `Scan complete: ${evaluated} flags evaluated across ${repos.length} repositories. ${stale} stale flags confirmed.` +
            (failures.length > 0 ? ` ${failures.length} repo(s) failed.` : '')
        );
      }
    } catch (err) {
      setScanNotification(`Global scan failed: ${err instanceof Error ? err.message : 'backend unreachable'}`);
      setScanFailed(true);
    } finally {
      setIsScanning(false);
      setTimeout(() => {
        setScanNotification(null);
      }, 8000);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-zinc-200">
      {/* Sidebar Navigation */}
      <Sidebar />

      {/* Main Workspace Area */}
      <div className="flex flex-col flex-1 min-w-0 h-full overflow-hidden">
        <Topbar onTriggerScan={handleTriggerScan} isScanning={isScanning} />

        {/* Global AST Scan Banner Notification */}
        {scanNotification && (
          <div className={`${scanFailed ? 'bg-rose-950/80 border-rose-800/80 text-rose-200' : 'bg-emerald-950/80 border-emerald-800/80 text-emerald-200'} border-b px-6 py-2.5 flex items-center justify-between text-xs animate-in fade-in duration-200`}>
            <div className="flex items-center gap-2 font-medium">
              {scanFailed ? (
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              )}
              <span>{scanNotification}</span>
            </div>
            <button
              onClick={() => setScanNotification(null)}
              className={`${scanFailed ? 'text-rose-400 hover:text-rose-200' : 'text-emerald-400 hover:text-emerald-200'} p-0.5`}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Content Scroll Viewport */}
        <main className="flex-1 overflow-y-auto p-6 bg-[#090d16]">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
