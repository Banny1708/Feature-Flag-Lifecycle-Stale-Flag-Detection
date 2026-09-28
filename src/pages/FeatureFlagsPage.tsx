import React, { useState } from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Tabs } from '@/components/common/Tabs';
import { SearchInput } from '@/components/common/SearchInput';
import { Modal } from '@/components/common/Modal';
import { FlagStatusBadge } from '@/components/domain/FlagStatusBadge';
import { RiskBadge } from '@/components/domain/RiskBadge';
import { RolloutBar } from '@/components/domain/RolloutBar';
import { EmptyState } from '@/components/common/EmptyState';
import { FeatureFlag } from '@/types';
import { mockFeatureFlags } from '@/data/mockFeatureFlags';
import { mockRepositories } from '@/data/mockRepositories';
import { Flag, Eye, Code2, Filter, Calendar, Users, Activity } from 'lucide-react';
import { formatDate, formatCompactNumber } from '@/utils/formatters';
import { Link } from 'react-router-dom';

export const FeatureFlagsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRepo, setSelectedRepo] = useState<string>('all');
  const [selectedRisk, setSelectedRisk] = useState<string>('all');
  const [inspectFlag, setInspectFlag] = useState<FeatureFlag | null>(null);

  const tabs = [
    { id: 'all', label: 'All Flags', count: mockFeatureFlags.length },
    { id: 'active', label: 'Active', count: mockFeatureFlags.filter((f) => f.status === 'active').length },
    {
      id: 'potentially-stale',
      label: 'Potentially Stale',
      count: mockFeatureFlags.filter((f) => f.status === 'potentially-stale').length,
    },
    { id: 'stale', label: 'Stale', count: mockFeatureFlags.filter((f) => f.status === 'stale').length },
    {
      id: 'removal-pending',
      label: 'In Removal',
      count: mockFeatureFlags.filter((f) => f.status === 'removal-pending').length,
    },
    { id: 'removed', label: 'Archived', count: mockFeatureFlags.filter((f) => f.status === 'removed').length },
  ];

  const filteredFlags = mockFeatureFlags.filter((flag) => {
    // Status tab filter
    if (activeTab !== 'all' && flag.status !== activeTab) {
      return false;
    }
    // Repo filter
    if (selectedRepo !== 'all' && flag.repositoryId !== selectedRepo) {
      return false;
    }
    // Risk filter
    if (selectedRisk !== 'all' && flag.risk !== selectedRisk) {
      return false;
    }
    // Search query
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const match =
        flag.name.toLowerCase().includes(q) ||
        flag.key.toLowerCase().includes(q) ||
        flag.description.toLowerCase().includes(q) ||
        flag.tags.some((t) => t.toLowerCase().includes(q));
      if (!match) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Feature Flag Catalog"
        description="Comprehensive inventory of feature flags across all microservices, tracking rollout percentages, AST references, and lifecycle health."
        actions={
          <Button variant="secondary" size="sm" icon={<Flag className="w-3.5 h-3.5 text-indigo-400" />}>
            Export Inventory (JSON)
          </Button>
        }
      />

      {/* Tabs */}
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* Filters Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="flex-1 max-w-sm">
          <SearchInput
            value={searchQuery}
            onChange={setSearchQuery}
            placeholder="Search flag name, key, or tag..."
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-zinc-400">
            <Filter className="w-3.5 h-3.5" />
            <span>Repository:</span>
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              className="bg-surface-100 border border-border rounded px-2.5 py-1 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Repositories</option>
              {mockRepositories.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-zinc-400">
            <span>Risk:</span>
            <select
              value={selectedRisk}
              onChange={(e) => setSelectedRisk(e.target.value)}
              className="bg-surface-100 border border-border rounded px-2.5 py-1 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Levels</option>
              <option value="low">Low Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="high">High Risk</option>
              <option value="critical">Critical Risk</option>
            </select>
          </div>
        </div>
      </div>

      {/* Flags Datatable */}
      <Card>
        {filteredFlags.length === 0 ? (
          <EmptyState
            title="No matching feature flags found"
            description="Try adjusting your status tab, search query, or repository filters."
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setActiveTab('all');
                  setSearchQuery('');
                  setSelectedRepo('all');
                  setSelectedRisk('all');
                }}
              >
                Reset Filters
              </Button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-zinc-300 border-collapse">
              <thead className="bg-surface-100/80 text-zinc-400 uppercase text-[10px] font-semibold border-b border-border">
                <tr>
                  <th className="px-5 py-3">Flag Key & Name</th>
                  <th className="px-5 py-3">Repository</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Risk</th>
                  <th className="px-5 py-3">Rollout</th>
                  <th className="px-5 py-3">7d Traffic</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {filteredFlags.map((flag) => (
                  <tr key={flag.id} className="hover:bg-surface-100/50 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="font-mono text-zinc-100 font-medium">{flag.key}</div>
                      <div className="text-[11px] text-zinc-400 mt-0.5 line-clamp-1">{flag.name}</div>
                      <div className="flex gap-1.5 mt-1.5">
                        {flag.tags.map((tag) => (
                          <span
                            key={tag}
                            className="px-1.5 py-0.2 rounded bg-surface-200 border border-border text-[9px] font-mono text-zinc-400"
                          >
                            #{tag}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-zinc-300 font-mono text-[11px]">
                      {flag.repositoryName}
                    </td>
                    <td className="px-5 py-3.5">
                      <FlagStatusBadge status={flag.status} />
                    </td>
                    <td className="px-5 py-3.5">
                      <RiskBadge level={flag.risk} />
                    </td>
                    <td className="px-5 py-3.5">
                      <RolloutBar percentage={flag.metrics.rolloutPercentage} />
                    </td>
                    <td className="px-5 py-3.5 font-mono text-zinc-300">
                      {formatCompactNumber(flag.metrics.evaluationsLast7d)}
                      <span className="text-[10px] text-zinc-400 ml-1">reqs</span>
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setInspectFlag(flag)}
                          icon={<Eye className="w-3.5 h-3.5" />}
                          title="View Details"
                        >
                          Details
                        </Button>
                        <Link to="/code-analysis">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-indigo-400"
                            icon={<Code2 className="w-3.5 h-3.5" />}
                            title="Inspect AST"
                          >
                            AST
                          </Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Flag Details Modal */}
      {inspectFlag && (
        <Modal
          isOpen={!!inspectFlag}
          onClose={() => setInspectFlag(null)}
          title={inspectFlag.key}
          description={inspectFlag.name}
          maxWidth="lg"
        >
          <div className="space-y-4 text-xs">
            <div className="p-3 rounded-lg bg-surface-100 border border-border text-zinc-300 leading-relaxed">
              {inspectFlag.description}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded bg-surface-100 border border-border/80 space-y-1">
                <span className="text-zinc-400 block text-[11px]">Lifecycle Status</span>
                <FlagStatusBadge status={inspectFlag.status} />
              </div>
              <div className="p-3 rounded bg-surface-100 border border-border/80 space-y-1">
                <span className="text-zinc-400 block text-[11px]">Risk Classification</span>
                <RiskBadge level={inspectFlag.risk} />
              </div>
            </div>

            <div className="space-y-2 border-t border-border pt-3">
              <div className="flex items-center justify-between text-zinc-400">
                <span className="flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5" /> Owner:
                </span>
                <span className="text-zinc-200 font-mono">{inspectFlag.owner}</span>
              </div>
              <div className="flex items-center justify-between text-zinc-400">
                <span className="flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5" /> Created:
                </span>
                <span className="text-zinc-200 font-mono">{formatDate(inspectFlag.createdAt)}</span>
              </div>
              <div className="flex items-center justify-between text-zinc-400">
                <span className="flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5" /> Total Inactive Days:
                </span>
                <span className="text-zinc-200 font-mono font-semibold">
                  {inspectFlag.metrics.daysInactive} days
                </span>
              </div>
              <div className="flex items-center justify-between text-zinc-400">
                <span>Default AST Fallback:</span>
                <span className="text-indigo-300 font-mono bg-indigo-950/60 px-1.5 py-0.5 rounded border border-indigo-800/60">
                  {String(inspectFlag.defaultValue)}
                </span>
              </div>
            </div>

            <div className="pt-3 border-t border-border flex justify-between items-center">
              <Link to="/code-analysis" onClick={() => setInspectFlag(null)}>
                <Button variant="secondary" size="sm" icon={<Code2 className="w-3.5 h-3.5" />}>
                  Inspect in AST Explorer
                </Button>
              </Link>
              <Button variant="ghost" size="sm" onClick={() => setInspectFlag(null)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
