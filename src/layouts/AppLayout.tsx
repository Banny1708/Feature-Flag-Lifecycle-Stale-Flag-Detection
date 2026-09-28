import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/navigation/Sidebar';
import { Topbar } from '@/components/navigation/Topbar';
import { CheckCircle2, X } from 'lucide-react';

export const AppLayout: React.FC = () => {
  const [isScanning, setIsScanning] = useState(false);
  const [scanNotification, setScanNotification] = useState<string | null>(null);

  const handleTriggerScan = () => {
    setIsScanning(true);
    setTimeout(() => {
      setIsScanning(false);
      setScanNotification('FlagShark AST Scan complete: 98 flags evaluated across 5 repositories. 24 stale flags confirmed.');
      setTimeout(() => {
        setScanNotification(null);
      }, 6000);
    }, 2000);
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
          <div className="bg-emerald-950/80 border-b border-emerald-800/80 px-6 py-2.5 flex items-center justify-between text-xs text-emerald-200 animate-in fade-in duration-200">
            <div className="flex items-center gap-2 font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{scanNotification}</span>
            </div>
            <button
              onClick={() => setScanNotification(null)}
              className="text-emerald-400 hover:text-emerald-200 p-0.5"
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
