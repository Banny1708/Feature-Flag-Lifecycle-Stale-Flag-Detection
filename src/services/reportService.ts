import { Report, EvidenceRecord } from '@/types';
import { mockReports } from '@/data/mockReports';
import { mockEvidenceRecords } from '@/data/mockEvidence';
import { API_BASE_URL, backendFirst, simulateFetch } from './apiClient';
import { apiGet } from './apiClient';

export const reportService = {
  async getReports(): Promise<Report[]> {
    return backendFirst(
      () => apiGet<Report[]>('/api/reports'),
      () => simulateFetch(mockReports)
    );
  },

  async getEvidenceRecords(flagId?: string): Promise<EvidenceRecord[]> {
    if (flagId) {
      return backendFirst(
        () => apiGet<EvidenceRecord[]>(`/api/flags/${encodeURIComponent(flagId)}/evidence`),
        async () =>
          (await simulateFetch(mockEvidenceRecords)).filter((e) => e.flagId === flagId)
      );
    }
    return simulateFetch(mockEvidenceRecords);
  },

  /** Direct download URL for a persisted backend report (json/csv). */
  downloadUrl(reportId: string): string {
    return `${API_BASE_URL}/api/reports/${encodeURIComponent(reportId)}/download`;
  },
};
