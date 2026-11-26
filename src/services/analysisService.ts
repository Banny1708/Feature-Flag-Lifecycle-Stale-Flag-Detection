import { CodeReference, CodePath, RiskAssessment } from '@/types';
import { apiGet, apiPost } from './apiClient';

export const analysisService = {
  async getCodeReferences(flagId: string): Promise<CodeReference[]> {
    return apiGet<CodeReference[]>(`/api/flags/${encodeURIComponent(flagId)}/references`);
  },

  async getCodePaths(flagId: string): Promise<CodePath[]> {
    return apiGet<CodePath[]>(`/api/flags/${encodeURIComponent(flagId)}/code-paths`);
  },

  async getRiskAssessments(): Promise<RiskAssessment[]> {
    return apiGet<RiskAssessment[]>('/api/risk-assessments');
  },

  async getRiskAssessmentByFlagId(flagId: string): Promise<RiskAssessment> {
    return apiGet<RiskAssessment>(`/api/flags/${encodeURIComponent(flagId)}/risk`);
  },

  /** Re-collect git + code evidence and recompute explainable risk on the backend. */
  async analyzeFlag(flagId: string): Promise<RiskAssessment> {
    return apiPost<RiskAssessment>(`/api/flags/${encodeURIComponent(flagId)}/analyze`);
  },
};
