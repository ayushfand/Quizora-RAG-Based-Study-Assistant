import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { HealthReport } from "../api/types";

export interface HealthState {
  health: HealthReport | null;
  loading: boolean;
  refresh: () => void;
}

/** Polls GET /api/health; safe to share across the app. */
export function useHealth(pollMs = 30000): HealthState {
  const [health, setHealth] = useState<HealthReport | null>(null);
  const [loading, setLoading] = useState(true);
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const report = await api.health();
      if (mounted.current) setHealth(report);
    } catch {
      if (mounted.current) setHealth(null);
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    void refresh();
    const timer = setInterval(() => void refresh(), pollMs);
    return () => {
      mounted.current = false;
      clearInterval(timer);
    };
  }, [refresh, pollMs]);

  return { health, loading, refresh };
}
