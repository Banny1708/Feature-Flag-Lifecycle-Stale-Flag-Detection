import { Repository, ScanResult } from '@/types';
import { mockRepositories } from '@/data/mockRepositories';
import { mockScanResults } from '@/data/mockScanResults';
import { simulateFetch } from './apiClient';

export const repositoryService = {
  async getRepositories(): Promise<Repository[]> {
    return simulateFetch(mockRepositories);
  },

  async getRepositoryById(id: string): Promise<Repository | undefined> {
    const repos = await simulateFetch(mockRepositories);
    return repos.find((r) => r.id === id);
  },

  async getScanResults(): Promise<ScanResult[]> {
    return simulateFetch(mockScanResults);
  },
};
