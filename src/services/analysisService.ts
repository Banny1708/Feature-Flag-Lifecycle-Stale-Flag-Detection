import { CodeReference, CodePath, RiskAssessment } from '@/types';
import { mockCodeReferences, mockCodePaths } from '@/data/mockCodeAnalysis';
import { mockRiskAssessments } from '@/data/mockOperations';
import { simulateFetch } from './apiClient';

export const analysisService = {
  async getCodeReferences(flagId?: string): Promise<CodeReference[]> {
    const refs = await simulateFetch(mockCodeReferences);
    if (flagId) {
      return refs.filter((r) => r.flagId === flagId);
    }
    return refs;
  },

  async getCodePaths(flagId?: string): Promise<CodePath[]> {
    const paths = await simulateFetch(mockCodePaths);
    if (flagId) {
      return paths.filter((p) => p.flagId === flagId);
    }
    return paths;
  },

  async getRiskAssessments(): Promise<RiskAssessment[]> {
    return simulateFetch(mockRiskAssessments);
  },

  async getRiskAssessmentByFlagId(flagId: string): Promise<RiskAssessment | undefined> {
    const risks = await simulateFetch(mockRiskAssessments);
    return risks.find((r) => r.flagId === flagId);
  },
};
