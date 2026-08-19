import { ClaimStatus, IncidentSeverity, IncidentStatus, SLAStatus } from '../types';

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num);
}

export function formatPercent(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`;
}

export function formatDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(d);
  } catch {
    return isoString;
  }
}

export function formatShortDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(d);
  } catch {
    return isoString;
  }
}

export function formatDurationMinutes(minutes: number): string {
  if (minutes <= 0) return 'Breached';
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hrs === 0) return `${mins}m`;
  return `${hrs}h ${mins}m`;
}

export function getSeverityColor(severity: IncidentSeverity): {
  bg: string;
  text: string;
  border: string;
  badge: 'danger' | 'warning' | 'info' | 'neutral';
} {
  switch (severity) {
    case 'critical':
      return { bg: 'bg-rose-950/60', text: 'text-rose-400', border: 'border-rose-800/60', badge: 'danger' };
    case 'high':
      return { bg: 'bg-amber-950/60', text: 'text-amber-400', border: 'border-amber-800/60', badge: 'warning' };
    case 'medium':
      return { bg: 'bg-yellow-950/60', text: 'text-yellow-400', border: 'border-yellow-800/60', badge: 'warning' };
    case 'low':
      return { bg: 'bg-sky-950/60', text: 'text-sky-400', border: 'border-sky-800/60', badge: 'info' };
  }
}

export function getSLAStatusBadge(slaStatus: SLAStatus): {
  label: string;
  variant: 'success' | 'warning' | 'danger' | 'neutral';
  color: string;
} {
  switch (slaStatus) {
    case 'on_track':
      return { label: 'On Track', variant: 'success', color: 'text-emerald-400' };
    case 'at_risk':
      return { label: 'At Risk (<30m)', variant: 'warning', color: 'text-amber-400' };
    case 'breached':
      return { label: 'SLA Breached', variant: 'danger', color: 'text-rose-400' };
    case 'met':
      return { label: 'SLA Met', variant: 'neutral', color: 'text-slate-400' };
  }
}

export function getClaimStatusBadge(status: ClaimStatus): {
  label: string;
  variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
} {
  switch (status) {
    case 'clean':
      return { label: 'Clean Claim', variant: 'success' };
    case 'flagged':
      return { label: 'DQ Flagged', variant: 'warning' };
    case 'rejected':
      return { label: 'Rejected', variant: 'danger' };
    case 'pending_review':
      return { label: 'In Review', variant: 'info' };
    case 'reprocessed':
      return { label: 'Reprocessed', variant: 'neutral' };
    case 'sla_breached':
      return { label: 'SLA Breached', variant: 'danger' };
  }
}

export function getIncidentStatusBadge(status: IncidentStatus): {
  label: string;
  variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
} {
  switch (status) {
    case 'open':
      return { label: 'Open', variant: 'danger' };
    case 'investigating':
      return { label: 'Investigating', variant: 'warning' };
    case 'resolved':
      return { label: 'Resolved', variant: 'success' };
    case 'escalated':
      return { label: 'Escalated to Provider', variant: 'danger' };
    case 'false_positive':
      return { label: 'False Positive', variant: 'neutral' };
  }
}
