import { Repository, ScanResult } from '@/types';
import { mockRepositories } from '@/data/mockRepositories';
import { mockScanResults } from '@/data/mockScanResults';
import { apiGet, apiPost, backendFirst, simulateFetch } from './apiClient';

export const repositoryService = {
  async getRepositories(): Promise<Repository[]> {
    return backendFirst(
      () => apiGet<Repository[]>('/api/repositories'),
      () => simulateFetch(mockRepositories)
    );
  },

  async getRepositoryById(id: string): Promise<Repository | undefined> {
    return backendFirst(
      () => apiGet<Repository>(`/api/repositories/${encodeURIComponent(id)}`),
      async () => {
        const repos = await simulateFetch(mockRepositories);
        return repos.find((r) => r.id === id);
      }
    ).catch(() => undefined);
  },

  async getScanResults(): Promise<ScanResult[]> {
    return backendFirst(
      () => apiGet<ScanResult[]>('/api/scans'),
      () => simulateFetch(mockScanResults)
    );
  },

  /** Trigger a real backend detection scan. Throws with the backend message on failure. */
  async triggerScan(repositoryId: string): Promise<ScanResult> {
    return apiPost<ScanResult>('/api/scans', { repository_id: repositoryId });
  },
};
