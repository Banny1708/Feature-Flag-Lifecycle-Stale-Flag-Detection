import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Badge } from '@/components/common/Badge';
import { lifecycleService, SystemSettings } from '@/services/lifecycleService';
import { Sliders, GitBranch, Save, CheckCircle2, Loader2, RefreshCw } from 'lucide-react';

const ENGINE_OPTIONS = [
  'FlagShark Multi-Language Parser',
  'Tree-sitter AST Analyzer',
  'Uber Piranha Pre-Pass',
];

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    lifecycleService
      .getSettings()
      .then((s) => {
        if (isMounted) setSettings(s);
      })
      .catch((err: Error) => {
        if (isMounted) setError(err.message || 'Failed to load settings');
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [reloadKey]);

  const set = <K extends keyof SystemSettings>(key: K, value: SystemSettings[K]) => {
    setSettings((prev) => (prev ? { ...prev, [key]: value } : prev));
    setIsSaved(false);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      const updated = await lifecycleService.updateSettings({
        stale_days_threshold: Number(settings.stale_days_threshold),
        warn_days_threshold: Number(settings.warn_days_threshold),
        scanner_engine: settings.scanner_engine,
        github_token: settings.github_token,
        slack_webhook: settings.slack_webhook,
      });
      setSettings(updated);
      setIsSaved(true);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading || !settings) {
    if (error) {
      return (
        <div className="space-y-6 max-w-4xl">
          <PageHeader title="System & Governance Settings" description="Configure AST engine thresholds and integrations." />
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
      <div className="flex items-center justify-center py-24 text-sm text-zinc-400 gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
        Loading system settings…
      </div>
    );
  }

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
            isLoading={isSaving}
            icon={isSaved ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Save className="w-3.5 h-3.5" />}
          >
            {isSaved ? 'Settings Saved!' : 'Save Configuration'}
          </Button>
        }
      />

      {saveError && (
        <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-800/60 text-xs text-rose-200 font-mono">
          {saveError}
        </div>
      )}

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
                  min={1}
                  value={settings.stale_days_threshold}
                  onChange={(e) => set('stale_days_threshold', Number(e.target.value))}
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
                  min={1}
                  value={settings.warn_days_threshold}
                  onChange={(e) => set('warn_days_threshold', Number(e.target.value))}
                  className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500 font-mono"
                />
                <p className="text-[11px] text-zinc-400 mt-1">
                  Flags with 0 evaluation requests logged for this period trigger dead-code warnings.
                </p>
              </div>

              <div>
                <label className="block text-zinc-300 font-medium mb-1">
                  AST Static Scanner Engine
                </label>
                <select
                  value={ENGINE_OPTIONS.includes(settings.scanner_engine) ? settings.scanner_engine : ENGINE_OPTIONS[0]}
                  onChange={(e) => set('scanner_engine', e.target.value)}
                  className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 focus:outline-none focus:border-indigo-500"
                >
                  {ENGINE_OPTIONS.map((opt) => (
                    <option key={opt}>{opt}</option>
                  ))}
                </select>
                <p className="text-[11px] text-zinc-400 mt-1">
                  Underlying engine utilized for AST traversal and control flow graphs.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Integration Credentials */}
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
                value={settings.github_token}
                onChange={(e) => set('github_token', e.target.value)}
                placeholder="ghp_… (optional, stored server-side)"
                autoComplete="off"
                className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 font-mono focus:outline-none focus:border-indigo-500"
              />
              <p className="text-[11px] text-zinc-400 mt-1">
                Stored in the backend database (never in source code) and used for automated cleanup PRs.
              </p>
            </div>

            <div>
              <label className="block text-zinc-300 font-medium mb-1">
                Slack / Teams Webhook for Stale Flag Digest
              </label>
              <input
                type="text"
                value={settings.slack_webhook}
                onChange={(e) => set('slack_webhook', e.target.value)}
                placeholder="https://hooks.slack.com/services/..."
                className="w-full px-3 py-2 bg-surface-100 border border-border rounded text-zinc-200 font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
};
