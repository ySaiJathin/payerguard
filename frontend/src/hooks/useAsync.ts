import { useCallback, useEffect, useState } from 'react';
import { NotComputedError } from '../services/apiClient';

/**
 * Result of a single backend read.
 *
 * `notComputed` is separate from `error` on purpose: an endpoint answering 404
 * because its pipeline stage has not been run is an expected, reportable state
 * of this system, not a fault. Components render it as "not computed yet" with
 * the backend's own explanation, so nothing is ever filled in with a zero or a
 * placeholder to keep a chart looking populated.
 */
export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  /** Set only for genuine failures (network down, 5xx, 422). */
  error: string | null;
  /** Set when the artifact does not exist yet; carries the backend's detail. */
  notComputed: string | null;
  reload: () => void;
}

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notComputed, setNotComputed] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setNotComputed(null);

    fn()
      .then((result) => {
        if (cancelled) return;
        setData(result);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setData(null);
        if (err instanceof NotComputedError) {
          setNotComputed(err.detail || 'This artifact has not been computed yet.');
        } else {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  return { data, loading, error, notComputed, reload };
}
