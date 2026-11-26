import { RemovalOperation, VerificationResult } from '@/types';
import { apiGet, apiPost } from './apiClient';

export interface DryRunResult extends RemovalOperation {
  plannedFiles?: string[];
}

export const removalService = {
  async getRemovalOperations(): Promise<RemovalOperation[]> {
    return apiGet<RemovalOperation[]>('/api/removals');
  },

  async getVerificationResults(): Promise<VerificationResult[]> {
    return apiGet<VerificationResult[]>('/api/verifications');
  },

  async getVerificationByOperationId(opId: string): Promise<VerificationResult> {
    return apiGet<VerificationResult>(`/api/removals/${encodeURIComponent(opId)}/verification`);
  },

  /**
   * Plan a removal without touching the repository.
   * Returns planned files/lines; the repo is never modified.
   */
  async dryRun(flagId: string, targetBranch = 'main'): Promise<DryRunResult> {
    return apiPost<DryRunResult>('/api/removals/dry-run', {
      flag_id: flagId,
      target_branch: targetBranch,
    });
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

  /** Restore the pre-removal safety branch. Returns the rollback operation info. */
  async rollbackRemoval(removalId: string): Promise<{ rollback_operation_id: string; restored_branch: string }> {
    return apiPost(`/api/removals/${encodeURIComponent(removalId)}/rollback`);
  },
};
