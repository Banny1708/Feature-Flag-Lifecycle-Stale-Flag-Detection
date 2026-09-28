import React, { useState } from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Badge } from '@/components/common/Badge';
import { Sliders, GitBranch, Save, CheckCircle2 } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [isSaved, setIsSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <PageHeader
        title="System & Governance Settings"
        description="Configure AST engine thresholds, automated Piranha cleanup rules, and external telemetry integration endpoints."
        actions={
          <Button
            variant="primary"
            size="sm"
            onClick={handleSave}
            icon={isSaved ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Save className="w-3.5 h-3.5" />}
          >
            {isSaved ? 'Settings Saved!' : 'Save Configuration'}
          </Button>
        }
      />

      <form onSubmit={handleSave} className="space-y-6">
        {/* Staleness Rules & Thresholds */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-indigo-400" />
              <CardTitle>Stale Flag Detection Thresholds</CardTitle>
            </div>
            <Badge variant="emerald" size="sm">Heuristics Engine</Badge>
          </CardHeader>
          <CardContent className="space-y-4 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-zinc-300 font-medium mb-1">
                  100% Rollout Staleness Window (Days)
                </label>
                <input
                  type="number"
                  defaultValue={60}
                  className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500 font-mono"
                />
                <p className="text-[11px] text-zinc-400 mt-1">
                  Flags at 100% rollout exceeding this duration are flagged as permanent candidates.
                </p>
              </div>

              <div>
                <label className="block text-zinc-300 font-medium mb-1">
                  Zero Traffic Inactivity Window (Days)
                </label>
                <input
                  type="number"
                  defaultValue={90}
                  className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500 font-mono"
                />
                <p className="text-[11px] text-zinc-400 mt-1">
                  Flags with 0 evaluation requests logged for this period trigger dead-code warnings.
                </p>
              </div>

              <div>
                <label className="block text-zinc-300 font-medium mb-1">
                  Release Flag Max Operational Lifespan (Days)
                </label>
                <input
                  type="number"
                  defaultValue={90}
                  className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500 font-mono"
                />
                <p className="text-[11px] text-zinc-400 mt-1">
                  Maximum allowable time before a release toggle is auto-marked stale.
                </p>
              </div>

              <div>
                <label className="block text-zinc-300 font-medium mb-1">
                  AST Static Scanner Engine
                </label>
                <select className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500">
                  <option>FlagShark Multi-Language Parser</option>
                  <option>Tree-sitter AST Analyzer</option>
                  <option>Uber Piranha Pre-Pass</option>
                </select>
                <p className="text-[11px] text-zinc-400 mt-1">
                  Underlying engine utilized for AST traversal and control flow graphs.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Integration Credentials (Mocked for Dev) */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-indigo-400" />
              <CardTitle>Git & Refactoring Integrations</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 text-xs">
            <div>
              <label className="block text-zinc-300 font-medium mb-1">
                GitHub Personal Access Token (for Automated Pull Requests)
              </label>
              <input
                type="password"
                defaultValue="ghp_mocktokenforfeatureflagcapstone2026"
                className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 font-mono focus:outline-none focus:border-indigo-500"
              />
              <p className="text-[11px] text-zinc-400 mt-1">
                Used by the future TypeScript backend to invoke Piranha and open cleanup PRs.
              </p>
            </div>

            <div>
              <label className="block text-zinc-300 font-medium mb-1">
                Slack / Teams Webhook for Stale Flag Digest
              </label>
              <input
                type="text"
                placeholder="https://hooks.slack.com/services/..."
                defaultValue="https://hooks.slack.com/services/T00/B00/flagops-alerts"
                className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
};
