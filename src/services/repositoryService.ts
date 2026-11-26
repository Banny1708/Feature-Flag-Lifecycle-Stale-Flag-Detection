import { Repository, ScanResult } from '@/types';
import { apiGet, apiPost } from './apiClient';

export interface ConnectRepositoryBody {
  name: string;
  url?: string;
  local_path?: string;
  default_branch?: string;
  language?: string;
  owner?: string;
}

export const repositoryService = {
  async getRepositories(): Promise<Repository[]> {
    return apiGet<Repository[]>('/api/repositories');
  },

  async getRepositoryById(id: string): Promise<Repository> {
    return apiGet<Repository>(`/api/repositories/${encodeURIComponent(id)}`);
  },

  async getScanResults(): Promise<ScanResult[]> {
    return apiGet<ScanResult[]>('/api/scans');
  },

  /** Register a repository for monitoring. Throws with the backend message on failure. */
  async connectRepository(body: ConnectRepositoryBody): Promise<Repository> {
    return apiPost<Repository>('/api/repositories', body);
  },

  /** Trigger a real backend detection scan. Throws with the backend message on failure. */
  async triggerScan(repositoryId: string): Promise<ScanResult> {
    return apiPost<ScanResult>('/api/scans', { repository_id: repositoryId });
  },
};
