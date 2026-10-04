import { RemovalOperation, VerificationResult } from '@/types';
import { mockRemovalOperations } from '@/data/mockOperations';
import { mockVerificationResults } from '@/data/mockVerification';
import { apiGet, apiPost, backendFirst, simulateFetch } from './apiClient';

export const removalService = {
  async getRemovalOperations(): Promise<RemovalOperation[]> {
    return backendFirst(
      () => apiGet<RemovalOperation[]>('/api/removals'),
      () => simulateFetch(mockRemovalOperations)
    );
  },

  async getVerificationResults(): Promise<VerificationResult[]> {
    return backendFirst(
      () => apiGet<VerificationResult[]>('/api/verifications'),
      () => simulateFetch(mockVerificationResults)
    );
  },

  async getVerificationByOperationId(opId: string): Promise<VerificationResult | undefined> {
    return backendFirst(
      () => apiGet<VerificationResult>(`/api/removals/${encodeURIComponent(opId)}/verification`),
      async () => {
        const results = await simulateFetch(mockVerificationResults);
        return results.find((r) => r.operationId === opId);
      }
    ).catch(() => undefined);
  },

  /**
   * User-confirmed removal: backend creates a Git safety branch, runs Piranha,
   * runs tests/coverage and returns the persisted operation + SUCCESS/FAILED/UNVERIFIED.
   * Throws with the backend message (e.g. Piranha UNAVAILABLE) on failure.
   */
  async removeFlag(flagId: string, targetBranch = 'main'): Promise<RemovalOperation> {
    return apiPost<RemovalOperation>(`/api/flags/${encodeURIComponent(flagId)}/remove`, {
      flag_id: flagId,
      target_branch: targetBranch,
      tool_target: 'Piranha',
    });
  },
};
