import { RemovalOperation, VerificationResult } from '@/types';
import { mockRemovalOperations } from '@/data/mockOperations';
import { mockVerificationResults } from '@/data/mockVerification';
import { simulateFetch } from './apiClient';

export const removalService = {
  async getRemovalOperations(): Promise<RemovalOperation[]> {
    return simulateFetch(mockRemovalOperations);
  },

  async getVerificationResults(): Promise<VerificationResult[]> {
    return simulateFetch(mockVerificationResults);
  },

  async getVerificationByOperationId(opId: string): Promise<VerificationResult | undefined> {
    const results = await simulateFetch(mockVerificationResults);
    return results.find((r) => r.operationId === opId);
  },
};
