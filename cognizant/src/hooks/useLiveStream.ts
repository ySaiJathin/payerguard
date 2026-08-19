import { useState, useEffect, useCallback, useRef } from 'react';
import { ClaimRecord } from '../types';
import { generateRandomClaim } from '../services/streamSimulatorService';

export interface UseLiveStreamOptions {
  autoStart?: boolean;
  intervalMs?: number;
  maxStoredClaims?: number;
  initialClaims?: ClaimRecord[];
}

export function useLiveStream({
  autoStart = true,
  intervalMs = 2500,
  maxStoredClaims = 60,
  initialClaims = [],
}: UseLiveStreamOptions = {}) {
  const [claims, setClaims] = useState<ClaimRecord[]>(initialClaims);
  const [isRunning, setIsRunning] = useState<boolean>(autoStart);
  const [speed, setSpeed] = useState<number>(intervalMs);
  const [stats, setStats] = useState({
    totalIngested: 0,
    cleanCount: 0,
    flaggedCount: 0,
    rejectedCount: 0,
    avgLatencyMs: 142,
    throughputPerSec: 1.2,
  });

  const timerRef = useRef<number | null>(null);

  const addClaim = useCallback((newClaim: ClaimRecord) => {
    setClaims((prev) => [newClaim, ...prev.slice(0, maxStoredClaims - 1)]);
    setStats((prev) => ({
      totalIngested: prev.totalIngested + 1,
      cleanCount: prev.cleanCount + (newClaim.status === 'clean' ? 1 : 0),
      flaggedCount: prev.flaggedCount + (newClaim.status === 'flagged' ? 1 : 0),
      rejectedCount: prev.rejectedCount + (newClaim.status === 'rejected' ? 1 : 0),
      avgLatencyMs: Math.floor(130 + Math.random() * 40),
      throughputPerSec: Math.round((1000 / speed) * 10) / 10,
    }));
  }, [maxStoredClaims, speed]);

  const injectAnomaly = useCallback((anomalyType: string) => {
    const anomalousClaim = generateRandomClaim(anomalyType);
    addClaim(anomalousClaim);
    return anomalousClaim;
  }, [addClaim]);

  useEffect(() => {
    if (!isRunning) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    timerRef.current = window.setInterval(() => {
      const claim = generateRandomClaim();
      addClaim(claim);
    }, speed);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRunning, speed, addClaim]);

  const toggleRunning = () => setIsRunning((prev) => !prev);
  const clearStream = () => setClaims([]);

  return {
    claims,
    isRunning,
    speed,
    stats,
    setSpeed,
    toggleRunning,
    clearStream,
    injectAnomaly,
  };
}
