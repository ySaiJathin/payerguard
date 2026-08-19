/**
 * UI-only types.
 *
 * Everything domain-shaped now lives in `types/api.ts`, transcribed from the
 * backend's Pydantic schemas. What used to be here described a different
 * product -- an EDI clearinghouse with SLA turnaround tracking -- and was
 * removed wholesale rather than adapted:
 *
 *   PayerName, EDIStandard, EDISegment, ClaimRecord, ServiceLineItem,
 *   RuleViolation, RuleCategory, ClaimStatus, SLAStatus, SLAPolicyConfig,
 *   DQRuleConfig, BatchUploadSummary, IncidentSeverity, IncidentStatus,
 *   IncidentAuditLog, Incident
 *
 * None of those had a backend counterpart. PayerGuard reads a CMS Medicare
 * RIF file, never an EDI transaction; it has no SLA field (the dataset cannot
 * support one); its incidents are window-grain with computed numeric scores,
 * not claim-grain with a severity enum; and its quality rules are defined in
 * code with no configuration API.
 */

export interface KPIMetric {
  title: string;
  value: string | number;
  unit?: string;
  subtext?: string;
  status?: 'normal' | 'good' | 'warning' | 'critical' | 'info';
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  link?: string;
  /** UI urgency only -- unrelated to the backend's computed severity score. */
  severity?: 'critical' | 'high' | 'normal';
}
