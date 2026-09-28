import { Report, EvidenceRecord } from '@/types';
import { mockReports } from '@/data/mockReports';
import { mockEvidenceRecords } from '@/data/mockEvidence';
import { simulateFetch } from './apiClient';

export const reportService = {
  async getReports(): Promise<Report[]> {
    return simulateFetch(mockReports);
  },

  async getEvidenceRecords(): Promise<EvidenceRecord[]> {
    return simulateFetch(mockEvidenceRecords);
  },
};
