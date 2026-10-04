import { CodeReference, CodePath, RiskAssessment } from '@/types';
import { mockCodeReferences, mockCodePaths } from '@/data/mockCodeAnalysis';
import { mockRiskAssessments } from '@/data/mockOperations';
import { apiGet, apiPost, backendFirst, simulateFetch } from './apiClient';

export const analysisService = {
  async getCodeReferences(flagId?: string): Promise<CodeReference[]> {
    if (flagId) {
      return backendFirst(
        () => apiGet<CodeReference[]>(`/api/flags/${encodeURIComponent(flagId)}/references`),
        async () => (await simulateFetch(mockCodeReferences)).filter((r) => r.flagId === flagId)
      );
    }
    // No backend "list all references" endpoint; serve bundled data.
    return simulateFetch(mockCodeReferences);
  },

  async getCodePaths(flagId?: string): Promise<CodePath[]> {
    if (flagId) {
      return backendFirst(
        () => apiGet<CodePath[]>(`/api/flags/${encodeURIComponent(flagId)}/code-paths`),
        async () => (await simulateFetch(mockCodePaths)).filter((p) => p.flagId === flagId)
      );
    }
    return simulateFetch(mockCodePaths);
  },

  async getRiskAssessments(): Promise<RiskAssessment[]> {
    return simulateFetch(mockRiskAssessments);
  },

  async getRiskAssessmentByFlagId(flagId: string): Promise<RiskAssessment | undefined> {
    return backendFirst(
      () => apiGet<RiskAssessment>(`/api/flags/${encodeURIComponent(flagId)}/risk`),
      async () => {
        const risks = await simulateFetch(mockRiskAssessments);
        return risks.find((r) => r.flagId === flagId);
      }
    ).catch(() => undefined);
  },

  /** Re-collect git + code evidence and recompute explainable risk on the backend. */
  async analyzeFlag(flagId: string): Promise<RiskAssessment> {
    return apiPost<RiskAssessment>(`/api/flags/${encodeURIComponent(flagId)}/analyze`);
  },
};
