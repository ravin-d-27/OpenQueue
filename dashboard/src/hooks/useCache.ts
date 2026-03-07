import { useEffect, useCallback, useRef } from 'react';

export function useAutoRefresh(callback: () => void, interval: number = 30000) {
  const savedCallback = useRef(callback);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  const tick = useCallback(() => {
    savedCallback.current();
  }, []);

  useEffect(() => {
    tick();
    timerRef.current = setInterval(tick, interval);
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [interval, tick]);
}

export function useCache<T>(key: string, fetchFn: () => Promise<T>, ttl: number = 60000) {
  const cacheKey = `oq_cache_${key}`;
  
  const getCached = useCallback((): { data: T | null; timestamp: number } | null => {
    if (typeof window === 'undefined') return null;
    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        return JSON.parse(cached);
      }
    } catch {
      // Ignore parse errors
    }
    return null;
  }, [cacheKey]);

  const setCache = useCallback((data: T) => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(cacheKey, JSON.stringify({ data, timestamp: Date.now() }));
    } catch {
      // Ignore storage errors
    }
  }, [cacheKey]);

  const fetchData = useCallback(async (): Promise<{ data: T | null; isStale: boolean }> => {
    const cached = getCached();
    const now = Date.now();
    
    // Return cached data if valid
    if (cached && (now - cached.timestamp) < ttl) {
      return { data: cached.data, isStale: false };
    }
    
    // Return stale data if available (for offline/failed fetches)
    if (cached) {
      try {
        const freshData = await fetchFn();
        setCache(freshData);
        return { data: freshData, isStale: false };
      } catch {
        return { data: cached.data, isStale: true };
      }
    }
    
    // No cache, try to fetch
    try {
      const data = await fetchFn();
      setCache(data);
      return { data, isStale: false };
    } catch {
      return { data: null, isStale: true };
    }
  }, [getCached, setCache, ttl, fetchFn]);

  const clearCache = useCallback(() => {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(cacheKey);
  }, [cacheKey]);

  return { fetchData, clearCache, getCached };
}
