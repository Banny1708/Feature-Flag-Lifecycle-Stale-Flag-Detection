import { FeatureFlag, FeatureFlagStatus } from '@/types';
import { apiGet } from './apiClient';

export interface FlagFilterOptions {
  status?: FeatureFlagStatus | 'all';
  repositoryId?: string;
  searchQuery?: string;
}

export const flagService = {
  /** Server-filtered flag inventory. Throws when the backend is unreachable. */
  async getFeatureFlags(filters?: FlagFilterOptions): Promise<FeatureFlag[]> {
    return apiGet<FeatureFlag[]>('/api/flags', {
      status: filters?.status ?? 'all',
      repositoryId: filters?.repositoryId ?? 'all',
      searchQuery: filters?.searchQuery ?? '',
    });
  },

  async getFlagById(id: string): Promise<FeatureFlag> {
    return apiGet<FeatureFlag>(`/api/flags/${encodeURIComponent(id)}`);
  },

  async getStaleFlags(): Promise<FeatureFlag[]> {
    return apiGet<FeatureFlag[]>('/api/flags/stale');
  },
};
