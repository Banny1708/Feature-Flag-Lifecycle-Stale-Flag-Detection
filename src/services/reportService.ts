import { Report, EvidenceRecord } from '@/types';
import { API_BASE_URL, apiGet, apiPost } from './apiClient';

export const reportService = {
  async getReports(): Promise<Report[]> {
    return apiGet<Report[]>('/api/reports');
  },

  async getEvidenceRecords(flagId?: string): Promise<EvidenceRecord[]> {
    if (flagId) {
      return apiGet<EvidenceRecord[]>(`/api/flags/${encodeURIComponent(flagId)}/evidence`);
    }
    return apiGet<EvidenceRecord[]>('/api/evidence');
  },

  async generateReport(title: string, type = 'stale-summary', repositoryId?: string): Promise<Report> {
    return apiPost<Report>('/api/reports', {
      title,
      type,
      repository_id: repositoryId ?? null,
    });
  },

  /** Direct download URL for a persisted backend report (json/csv). */
  downloadUrl(reportId: string): string {
    return `${API_BASE_URL}/api/reports/${encodeURIComponent(reportId)}/download`;
  },
};
