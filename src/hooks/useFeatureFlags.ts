import { useState, useEffect } from 'react';
import { FeatureFlag } from '@/types';
import { flagService, FlagFilterOptions } from '@/services/flagService';

export function useFeatureFlags(filters?: FlagFilterOptions) {
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);

    flagService
      .getFeatureFlags(filters)
      .then((data) => {
        if (isMounted) {
          setFlags(data);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (isMounted) {
          setError(err.message || 'Failed to fetch feature flags');
        }
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [filters?.status, filters?.repositoryId, filters?.searchQuery]);

  return { flags, isLoading, error, refetch: () => flagService.getFeatureFlags(filters) };
}
