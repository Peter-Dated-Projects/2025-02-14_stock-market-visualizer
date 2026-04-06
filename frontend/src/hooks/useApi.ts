'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiGet } from '@/lib/api';

interface UseApiOptions {
  /** Auto-fetch on mount */
  immediate?: boolean;
  /** Polling interval in ms (0 = disabled) */
  pollInterval?: number;
}

interface UseApiReturn<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  refetch: () => Promise<void>;
}

/**
 * Generic data-fetching hook with polling support.
 */
export function useApi<T>(
  path: string,
  options: UseApiOptions = { immediate: true, pollInterval: 0 },
): UseApiReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiGet<T>(path);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    if (options.immediate !== false) {
      fetchData();
    }
  }, [fetchData, options.immediate]);

  useEffect(() => {
    if (options.pollInterval && options.pollInterval > 0) {
      intervalRef.current = setInterval(fetchData, options.pollInterval);
      return () => {
        if (intervalRef.current) clearInterval(intervalRef.current);
      };
    }
  }, [fetchData, options.pollInterval]);

  return { data, error, loading, refetch: fetchData };
}
