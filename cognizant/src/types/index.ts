export type PayerName = 
  | 'Medicare CMS'
  | 'UnitedHealthcare'
  | 'Anthem BlueCross'
  | 'Aetna Health'
  | 'Cigna Healthcare'
  | 'Humana';

export type EDIStandard = '837P' | '837I' | '837D' | 'CMS-1500' | 'UB-04';

export type ClaimStatus = 
  | 'clean' 
  | 'flagged' 
  | 'rejected' 
  | 'pending_review' 
  | 'reprocessed' 
  | 'sla_breached';

export type SLAStatus = 'on_track' | 'at_risk' | 'breached' | 'met';

export type IncidentSeverity = 'critical' | 'high' | 'medium' | 'low';

export type IncidentStatus = 'open' | 'investigating' | 'resolved' | 'escalated' | 'false_positive';

export type RuleCategory = 
  | 'npi_validation'
  | 'icd_cpt_accuracy'
  | 'timely_filing'
  | 'duplicate_detection'
  | 'high_dollar_anomaly'
  | 'coverage_eligibility'
  | 'modifier_compatibility';

export interface ServiceLineItem {
  lineNumber: number;
  cptCode: string;
  cptDescription: string;
  modifiers?: string[];
  units: number;
  charge: number;
  serviceDate: string;
  posCode: string;
  status: 'valid' | 'invalid' | 'warning';
  notes?: string;
}

export interface RuleViolation {
  ruleId: string;
  ruleCode: string;
  ruleName: string;
  category: RuleCategory;
  severity: IncidentSeverity;
  message: string;
  expectedValue?: string;
  actualValue?: string;
  segmentTarget?: string; // e.g. "NM1*85*2 (Billing Provider NPI)"
  remediationSuggestion: string;
}

export interface EDISegment {
  segmentId: string;
  element: string;
  content: string;
  hasError: boolean;
  explanation?: string;
}

export interface ClaimRecord {
  id: string; // e.g. "CLM-2026-8941"
  claimNumber: string;
  payer: PayerName;
  payerId: string;
  ediStandard: EDIStandard;
  patientId: string;
  patientName: string;
  providerNpi: string;
  providerName: string;
  providerTaxonomy: string;
  renderingNpi?: string;
  renderingProviderName?: string;
  facilityName: string;
  serviceDate: string;
  receivedAt: string;
  slaDeadline: string;
  slaRemainingMinutes: number;
  slaStatus: SLAStatus;
  status: ClaimStatus;
  billedAmount: number;
  expectedAllowedAmount: number;
  primaryDiagnosis: string; // ICD-10
  secondaryDiagnoses?: string[];
  lineItems: ServiceLineItem[];
  anomalyScore: number; // 0.00 to 1.00
  violations: RuleViolation[];
  rawEdiSnippet?: string;
  ediSegments?: EDISegment[];
}

export interface IncidentAuditLog {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  details: string;
}

export interface Incident {
  id: string; // e.g. "INC-8921"
  claimId: string;
  claimNumber: string;
  title: string;
  description: string;
  category: RuleCategory;
  severity: IncidentSeverity;
  status: IncidentStatus;
  slaStatus: SLAStatus;
  slaRemainingMinutes: number;
  payer: PayerName;
  billedAmount: number;
  detectedAt: string;
  updatedAt: string;
  assignee: {
    name: string;
    role: string;
    avatar?: string;
  };
  anomalyConfidence: number; // e.g. 0.94
  rootCauseAnalysis: {
    primaryFailure: string;
    impactDescription: string;
    affectedSubsystems: string[];
    recommendedFix: string;
  };
  claimDetails: ClaimRecord;
  auditTrail: IncidentAuditLog[];
}

export interface BatchUploadSummary {
  batchId: string;
  filename: string;
  format: EDIStandard;
  fileSizeBytes: number;
  uploadedAt: string;
  uploadedBy: string;
  totalClaims: number;
  cleanClaims: number;
  flaggedClaims: number;
  rejectedClaims: number;
  totalBilledAmount: number;
  cleanClaimRate: number;
  processingDurationMs: number;
  status: 'completed' | 'processing' | 'failed' | 'validated_with_warnings';
  criticalErrorsCount: number;
}

export interface KPIMetric {
  title: string;
  value: string | number;
  unit?: string;
  changePercent?: number;
  isPositiveChange?: boolean;
  trendText?: string;
  subtext?: string;
  status?: 'normal' | 'good' | 'warning' | 'critical' | 'info';
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  severity: IncidentSeverity;
  timestamp: string;
  read: boolean;
  link?: string;
}

export interface DQRuleConfig {
  id: string;
  code: string;
  name: string;
  category: RuleCategory;
  severity: IncidentSeverity;
  enabled: boolean;
  threshold?: number;
  description: string;
  executionCount: number;
  failureCount: number;
}

export interface SLAPolicyConfig {
  id: string;
  name: string;
  claimType: EDIStandard;
  targetMaxMinutes: number;
  warningThresholdMinutes: number;
  escalationRole: string;
  autoMitigate: boolean;
}
