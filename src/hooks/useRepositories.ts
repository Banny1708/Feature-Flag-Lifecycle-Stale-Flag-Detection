import { useState, useEffect } from 'react';
import { Repository } from '@/types';
import { repositoryService } from '@/services/repositoryService';

export function useRepositories() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);

    repositoryService
      .getRepositories()
      .then((data) => {
        if (isMounted) {
          setRepositories(data);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (isMounted) {
          setError(err.message || 'Failed to fetch repositories');
        }
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return { repositories, isLoading, error };
}
