import { FeatureFlag, FeatureFlagStatus } from '@/types';
import { mockFeatureFlags } from '@/data/mockFeatureFlags';
import { simulateFetch } from './apiClient';

export interface FlagFilterOptions {
  status?: FeatureFlagStatus | 'all';
  repositoryId?: string;
  searchQuery?: string;
}

export const flagService = {
  async getFeatureFlags(filters?: FlagFilterOptions): Promise<FeatureFlag[]> {
    let flags = await simulateFetch(mockFeatureFlags);

    if (filters?.status && filters.status !== 'all') {
      flags = flags.filter((f) => f.status === filters.status);
    }

    if (filters?.repositoryId && filters.repositoryId !== 'all') {
      flags = flags.filter((f) => f.repositoryId === filters.repositoryId);
    }

    if (filters?.searchQuery) {
      const q = filters.searchQuery.toLowerCase();
      flags = flags.filter(
        (f) =>
          f.name.toLowerCase().includes(q) ||
          f.key.toLowerCase().includes(q) ||
          f.description.toLowerCase().includes(q) ||
          f.tags.some((t) => t.toLowerCase().includes(q))
      );
    }

    return flags;
  },

  async getFlagById(id: string): Promise<FeatureFlag | undefined> {
    const flags = await simulateFetch(mockFeatureFlags);
    return flags.find((f) => f.id === id);
  },

  async getStaleFlags(): Promise<FeatureFlag[]> {
    const flags = await simulateFetch(mockFeatureFlags);
    return flags.filter((f) => f.status === 'stale' || f.status === 'potentially-stale');
  },
};
