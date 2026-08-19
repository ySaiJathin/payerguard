export type DashboardSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type DashboardIncidentStatus = 'Detected' | 'Investigating' | 'Awaiting Review' | 'Resolved';

export interface DashboardIncidentItem {
  id: string;
  type: string;
  affectedClaims: number;
  severity: DashboardSeverity;
  slaRisk: string;
  slaRiskPercent: number;
  status: DashboardIncidentStatus;
  time: string;
  payer: string;
  financialImpact: number;
  summary: string;
}

export interface VolumeTrendPoint {
  time: string;
  processed: number;
  flagged: number;
  cleanRate: number;
  latencyMs: number;
}

export interface DQTrendPoint {
  time: string;
  score: number;
  target: number;
  completeness: number;
  validity: number;
  accuracy: number;
  timeliness: number;
}

export interface AnomalyTrendPoint {
  time: string;
  npiErrors: number;
  codeUnbundling: number;
  duplicateClaims: number;
  timelyFiling: number;
  modifierIssues: number;
  total: number;
}

export interface SLARiskTrendPoint {
  time: string;
  riskScore: number;
  atRiskCount: number;
  breachedCount: number;
  avgTurnaroundMins: number;
}

export interface ClaimAmountBracket {
  range: string;
  count: number;
  percentage: number;
  totalAmount: number;
  anomalyRate: number;
  color: string;
}

export interface SeverityDistributionItem {
  severity: DashboardSeverity;
  count: number;
  percentage: number;
  affectedClaims: number;
  valueAtRisk: number;
  avgResolutionTime: string;
  color: string;
  badgeVariant: 'danger' | 'warning' | 'info' | 'neutral';
}

export interface SystemStatusItem {
  name: string;
  status: 'Healthy' | 'Active' | 'Ready' | 'Degraded';
  state: 'healthy' | 'active' | 'ready' | 'degraded';
  metricLabel: string;
  metricValue: string;
  secondaryInfo: string;
  iconName: string;
}

// 1. KPI Cards data
export const mockDashboardKPIs = {
  dataQualityScore: {
    title: 'Data Quality Score',
    value: '94.2%',
    target: 'Target ≥ 95.0%',
    changePercent: 1.4,
    isPositiveGood: true,
    trendLabel: 'vs last 24h',
    subtext: '+1.4% improvement',
    status: 'good' as const,
  },
  activeAnomalies: {
    title: 'Active Anomalies',
    value: '12',
    unit: 'anomalies',
    changePercent: -20.0,
    isPositiveGood: true, // Decreasing anomalies is good
    trendLabel: 'vs yesterday',
    subtext: '4 High / Critical',
    status: 'warning' as const,
  },
  criticalIncidents: {
    title: 'Critical Incidents',
    value: '3',
    unit: 'urgent',
    changePercent: 50.0,
    isPositiveGood: false,
    trendLabel: 'needs triage',
    subtext: '2 At SLA Risk (<30m)',
    status: 'critical' as const,
  },
  slaRisk: {
    title: 'SLA Risk',
    value: '18%',
    target: 'Threshold ≤ 10%',
    changePercent: -2.5,
    isPositiveGood: true, // Decreasing risk is good
    trendLabel: 'improving',
    subtext: '1 Breached ticket',
    status: 'warning' as const,
  },
  claimsProcessed: {
    title: 'Claims Processed',
    value: '125,430',
    unit: 'claims',
    changePercent: 8.4,
    isPositiveGood: true,
    trendLabel: 'vs avg daily',
    subtext: '$74.8M Total Billed',
    status: 'info' as const,
  },
  claimsAffected: {
    title: 'Claims Affected',
    value: '2,841',
    unit: 'claims',
    changePercent: -14.2,
    isPositiveGood: true,
    trendLabel: '2.26% error rate',
    subtext: '$1.42M Value at Risk',
    status: 'critical' as const,
  },
};

// 2. Charts Data

// A. Claims Volume Trend (Hourly 24h & 7d)
export const mockVolumeTrend24h: VolumeTrendPoint[] = [
  { time: '00:00', processed: 4200, flagged: 95, cleanRate: 97.7, latencyMs: 140 },
  { time: '02:00', processed: 3800, flagged: 72, cleanRate: 98.1, latencyMs: 135 },
  { time: '04:00', processed: 5100, flagged: 110, cleanRate: 97.8, latencyMs: 148 },
  { time: '06:00', processed: 7900, flagged: 195, cleanRate: 97.5, latencyMs: 165 },
  { time: '08:00', processed: 14500, flagged: 380, cleanRate: 97.4, latencyMs: 210 },
  { time: '10:00', processed: 18900, flagged: 520, cleanRate: 97.2, latencyMs: 245 },
  { time: '12:00', processed: 17400, flagged: 410, cleanRate: 97.6, latencyMs: 205 },
  { time: '14:00', processed: 16800, flagged: 370, cleanRate: 97.8, latencyMs: 190 },
  { time: '16:00', processed: 15200, flagged: 310, cleanRate: 98.0, latencyMs: 180 },
  { time: '18:00', processed: 11400, flagged: 210, cleanRate: 98.2, latencyMs: 155 },
  { time: '20:00', processed: 8600, flagged: 135, cleanRate: 98.4, latencyMs: 142 },
  { time: '22:00', processed: 6530, flagged: 94, cleanRate: 98.6, latencyMs: 138 },
];

export const mockVolumeTrend7d: VolumeTrendPoint[] = [
  { time: 'Mon', processed: 118400, flagged: 2950, cleanRate: 97.5, latencyMs: 185 },
  { time: 'Tue', processed: 132600, flagged: 3120, cleanRate: 97.6, latencyMs: 192 },
  { time: 'Wed', processed: 141200, flagged: 3200, cleanRate: 97.7, latencyMs: 198 },
  { time: 'Thu', processed: 138900, flagged: 2840, cleanRate: 98.0, latencyMs: 175 },
  { time: 'Fri', processed: 125430, flagged: 2841, cleanRate: 97.7, latencyMs: 168 },
  { time: 'Sat', processed: 58200, flagged: 980, cleanRate: 98.3, latencyMs: 135 },
  { time: 'Sun', processed: 42100, flagged: 640, cleanRate: 98.5, latencyMs: 128 },
];

// B. Data Quality Trend
export const mockDataQualityTrend24h: DQTrendPoint[] = [
  { time: '00:00', score: 91.8, target: 95.0, completeness: 98.5, validity: 94.2, accuracy: 91.0, timeliness: 99.2 },
  { time: '02:00', score: 92.1, target: 95.0, completeness: 98.7, validity: 94.5, accuracy: 91.5, timeliness: 99.4 },
  { time: '04:00', score: 91.5, target: 95.0, completeness: 98.2, validity: 93.8, accuracy: 90.8, timeliness: 99.1 },
  { time: '06:00', score: 92.4, target: 95.0, completeness: 98.9, validity: 94.8, accuracy: 92.0, timeliness: 99.5 },
  { time: '08:00', score: 93.0, target: 95.0, completeness: 99.1, validity: 95.2, accuracy: 92.8, timeliness: 99.6 },
  { time: '10:00', score: 92.6, target: 95.0, completeness: 98.8, validity: 94.9, accuracy: 92.2, timeliness: 99.3 },
  { time: '12:00', score: 93.4, target: 95.0, completeness: 99.2, validity: 95.6, accuracy: 93.1, timeliness: 99.7 },
  { time: '14:00', score: 93.8, target: 95.0, completeness: 99.4, validity: 96.0, accuracy: 93.7, timeliness: 99.7 },
  { time: '16:00', score: 93.5, target: 95.0, completeness: 99.3, validity: 95.8, accuracy: 93.2, timeliness: 99.6 },
  { time: '18:00', score: 94.0, target: 95.0, completeness: 99.5, validity: 96.2, accuracy: 94.0, timeliness: 99.8 },
  { time: '20:00', score: 94.1, target: 95.0, completeness: 99.6, validity: 96.3, accuracy: 94.1, timeliness: 99.8 },
  { time: '22:00', score: 94.2, target: 95.0, completeness: 99.6, validity: 96.5, accuracy: 94.3, timeliness: 99.9 },
];

export const mockDataQualityTrend7d: DQTrendPoint[] = [
  { time: 'Mon', score: 91.2, target: 95.0, completeness: 98.0, validity: 93.5, accuracy: 90.2, timeliness: 99.0 },
  { time: 'Tue', score: 92.0, target: 95.0, completeness: 98.4, validity: 94.2, accuracy: 91.4, timeliness: 99.2 },
  { time: 'Wed', score: 92.8, target: 95.0, completeness: 98.8, validity: 95.0, accuracy: 92.3, timeliness: 99.4 },
  { time: 'Thu', score: 93.5, target: 95.0, completeness: 99.1, validity: 95.7, accuracy: 93.2, timeliness: 99.6 },
  { time: 'Fri', score: 94.2, target: 95.0, completeness: 99.6, validity: 96.5, accuracy: 94.3, timeliness: 99.9 },
  { time: 'Sat', score: 94.8, target: 95.0, completeness: 99.7, validity: 97.0, accuracy: 95.0, timeliness: 99.9 },
  { time: 'Sun', score: 95.1, target: 95.0, completeness: 99.8, validity: 97.4, accuracy: 95.4, timeliness: 100.0 },
];

// C. Anomaly Trend
export const mockAnomalyTrend24h: AnomalyTrendPoint[] = [
  { time: '00:00', npiErrors: 4, codeUnbundling: 8, duplicateClaims: 3, timelyFiling: 1, modifierIssues: 3, total: 19 },
  { time: '02:00', npiErrors: 3, codeUnbundling: 6, duplicateClaims: 2, timelyFiling: 1, modifierIssues: 2, total: 14 },
  { time: '04:00', npiErrors: 5, codeUnbundling: 9, duplicateClaims: 4, timelyFiling: 2, modifierIssues: 4, total: 24 },
  { time: '06:00', npiErrors: 8, codeUnbundling: 14, duplicateClaims: 6, timelyFiling: 2, modifierIssues: 6, total: 36 },
  { time: '08:00', npiErrors: 12, codeUnbundling: 26, duplicateClaims: 11, timelyFiling: 4, modifierIssues: 12, total: 65 },
  { time: '10:00', npiErrors: 18, codeUnbundling: 34, duplicateClaims: 16, timelyFiling: 6, modifierIssues: 18, total: 92 },
  { time: '12:00', npiErrors: 15, codeUnbundling: 28, duplicateClaims: 14, timelyFiling: 5, modifierIssues: 15, total: 77 },
  { time: '14:00', npiErrors: 14, codeUnbundling: 25, duplicateClaims: 12, timelyFiling: 4, modifierIssues: 13, total: 68 },
  { time: '16:00', npiErrors: 11, codeUnbundling: 20, duplicateClaims: 9, timelyFiling: 3, modifierIssues: 10, total: 53 },
  { time: '18:00', npiErrors: 7, codeUnbundling: 15, duplicateClaims: 6, timelyFiling: 2, modifierIssues: 7, total: 37 },
  { time: '20:00', npiErrors: 5, codeUnbundling: 10, duplicateClaims: 4, timelyFiling: 1, modifierIssues: 5, total: 25 },
  { time: '22:00', npiErrors: 3, codeUnbundling: 5, duplicateClaims: 2, timelyFiling: 1, modifierIssues: 1, total: 12 },
];

export const mockAnomalyTrend7d: AnomalyTrendPoint[] = [
  { time: 'Mon', npiErrors: 52, codeUnbundling: 124, duplicateClaims: 68, timelyFiling: 18, modifierIssues: 56, total: 318 },
  { time: 'Tue', npiErrors: 48, codeUnbundling: 118, duplicateClaims: 62, timelyFiling: 16, modifierIssues: 51, total: 295 },
  { time: 'Wed', npiErrors: 55, codeUnbundling: 135, duplicateClaims: 74, timelyFiling: 22, modifierIssues: 60, total: 346 },
  { time: 'Thu', npiErrors: 44, codeUnbundling: 108, duplicateClaims: 58, timelyFiling: 14, modifierIssues: 46, total: 270 },
  { time: 'Fri', npiErrors: 38, codeUnbundling: 94, duplicateClaims: 49, timelyFiling: 12, modifierIssues: 39, total: 232 },
  { time: 'Sat', npiErrors: 18, codeUnbundling: 42, duplicateClaims: 21, timelyFiling: 5, modifierIssues: 18, total: 104 },
  { time: 'Sun', npiErrors: 12, codeUnbundling: 28, duplicateClaims: 14, timelyFiling: 3, modifierIssues: 11, total: 68 },
];

// D. SLA Risk Trend
export const mockSLARiskTrend24h: SLARiskTrendPoint[] = [
  { time: '00:00', riskScore: 12, atRiskCount: 2, breachedCount: 0, avgTurnaroundMins: 14.2 },
  { time: '02:00', riskScore: 10, atRiskCount: 1, breachedCount: 0, avgTurnaroundMins: 13.8 },
  { time: '04:00', riskScore: 14, atRiskCount: 2, breachedCount: 0, avgTurnaroundMins: 15.1 },
  { time: '06:00', riskScore: 19, atRiskCount: 3, breachedCount: 0, avgTurnaroundMins: 17.4 },
  { time: '08:00', riskScore: 26, atRiskCount: 5, breachedCount: 1, avgTurnaroundMins: 22.0 },
  { time: '10:00', riskScore: 32, atRiskCount: 8, breachedCount: 1, avgTurnaroundMins: 26.5 },
  { time: '12:00', riskScore: 28, atRiskCount: 6, breachedCount: 1, avgTurnaroundMins: 24.1 },
  { time: '14:00', riskScore: 24, atRiskCount: 5, breachedCount: 1, avgTurnaroundMins: 21.3 },
  { time: '16:00', riskScore: 21, atRiskCount: 4, breachedCount: 1, avgTurnaroundMins: 19.5 },
  { time: '18:00', riskScore: 18, atRiskCount: 3, breachedCount: 1, avgTurnaroundMins: 18.2 },
  { time: '20:00', riskScore: 16, atRiskCount: 2, breachedCount: 1, avgTurnaroundMins: 16.0 },
  { time: '22:00', riskScore: 18, atRiskCount: 2, breachedCount: 1, avgTurnaroundMins: 15.4 },
];

export const mockSLARiskTrend7d: SLARiskTrendPoint[] = [
  { time: 'Mon', riskScore: 24, atRiskCount: 6, breachedCount: 2, avgTurnaroundMins: 22.4 },
  { time: 'Tue', riskScore: 22, atRiskCount: 5, breachedCount: 1, avgTurnaroundMins: 20.8 },
  { time: 'Wed', riskScore: 25, atRiskCount: 7, breachedCount: 2, avgTurnaroundMins: 23.5 },
  { time: 'Thu', riskScore: 20, atRiskCount: 4, breachedCount: 1, avgTurnaroundMins: 19.2 },
  { time: 'Fri', riskScore: 18, atRiskCount: 3, breachedCount: 1, avgTurnaroundMins: 18.2 },
  { time: 'Sat', riskScore: 11, atRiskCount: 1, breachedCount: 0, avgTurnaroundMins: 14.1 },
  { time: 'Sun', riskScore: 9, atRiskCount: 1, breachedCount: 0, avgTurnaroundMins: 12.8 },
];

// 3. Distributions

// A. Claim Amount Distribution
export const mockClaimAmountBrackets: ClaimAmountBracket[] = [
  { range: '< $500', count: 42100, percentage: 33.6, totalAmount: 9840000, anomalyRate: 0.8, color: 'from-cyan-500 to-blue-500' },
  { range: '$500 - $1.5k', count: 38450, percentage: 30.7, totalAmount: 34200000, anomalyRate: 1.4, color: 'from-blue-500 to-indigo-500' },
  { range: '$1.5k - $5k', count: 24180, percentage: 19.3, totalAmount: 68500000, anomalyRate: 3.2, color: 'from-indigo-500 to-purple-500' },
  { range: '$5k - $15k', count: 14200, percentage: 11.3, totalAmount: 112400000, anomalyRate: 5.1, color: 'from-purple-500 to-amber-500' },
  { range: '$15k - $50k', count: 5200, percentage: 4.1, totalAmount: 138600000, anomalyRate: 8.4, color: 'from-amber-500 to-rose-500' },
  { range: '> $50k', count: 1300, percentage: 1.0, totalAmount: 96500000, anomalyRate: 14.8, color: 'from-rose-500 to-red-600' },
];

// B. Incident Severity Distribution
export const mockIncidentSeverityDistribution: SeverityDistributionItem[] = [
  {
    severity: 'CRITICAL',
    count: 3,
    percentage: 25.0,
    affectedClaims: 208,
    valueAtRisk: 56920,
    avgResolutionTime: '< 30m required',
    color: 'bg-rose-500',
    badgeVariant: 'danger',
  },
  {
    severity: 'HIGH',
    count: 4,
    percentage: 33.3,
    affectedClaims: 932,
    valueAtRisk: 38450,
    avgResolutionTime: '< 4h target',
    color: 'bg-amber-500',
    badgeVariant: 'warning',
  },
  {
    severity: 'MEDIUM',
    count: 3,
    percentage: 25.0,
    affectedClaims: 1380,
    valueAtRisk: 14230,
    avgResolutionTime: '< 24h target',
    color: 'bg-cyan-500',
    badgeVariant: 'info',
  },
  {
    severity: 'LOW',
    count: 2,
    percentage: 16.7,
    affectedClaims: 321,
    valueAtRisk: 3140,
    avgResolutionTime: '< 48h target',
    color: 'bg-slate-500',
    badgeVariant: 'neutral',
  },
];

// 4. Recent Incidents Table Data (Realistic healthcare claims data)
export const mockRecentIncidents: DashboardIncidentItem[] = [
  {
    id: 'INC-8921',
    type: 'Billing NPI Checksum Failure & NCCI Lumbar MRI Conflict',
    affectedClaims: 142,
    severity: 'CRITICAL',
    slaRisk: '88% (24m left)',
    slaRiskPercent: 88,
    status: 'Investigating',
    time: '8m ago',
    payer: 'Medicare CMS',
    financialImpact: 4850.00,
    summary: 'Unregistered billing NPI 9999999999 with unbundled CPT 72148 + 72149.'
  },
  {
    id: 'INC-7734',
    type: 'Inpatient 24h SLA Breached & Revenue Code 0270 Outlier',
    affectedClaims: 18,
    severity: 'CRITICAL',
    slaRisk: '100% (Breached)',
    slaRiskPercent: 100,
    status: 'Investigating',
    time: '24m ago',
    payer: 'UnitedHealthcare',
    financialImpact: 48920.00,
    summary: 'High-dollar surgical supply charge verification hold exceeded 24h statutory window.'
  },
  {
    id: 'INC-4419',
    type: 'Statutory Timely Filing Limit Exceeded (465 Days Old)',
    affectedClaims: 48,
    severity: 'CRITICAL',
    slaRisk: '72% (At Risk)',
    slaRiskPercent: 72,
    status: 'Detected',
    time: '45m ago',
    payer: 'Humana',
    financialImpact: 3150.00,
    summary: 'Cataract surgery encounter date of service exceeds 365-day timely filing deadline.'
  },
  {
    id: 'INC-6641',
    type: 'Duplicate Lesion Destruction CPT 17000 on Encounter',
    affectedClaims: 312,
    severity: 'HIGH',
    slaRisk: '45% (Moderate)',
    slaRiskPercent: 45,
    status: 'Awaiting Review',
    time: '1h ago',
    payer: 'Aetna Health',
    financialImpact: 940.00,
    summary: 'Multiple primary lesion codes submitted instead of required add-on code 17003.'
  },
  {
    id: 'INC-5512',
    type: 'Modifier 25 Inconsistency with Problem-Oriented E&M',
    affectedClaims: 620,
    severity: 'HIGH',
    slaRisk: '38% (Moderate)',
    slaRiskPercent: 38,
    status: 'Investigating',
    time: '2h ago',
    payer: 'Anthem BlueCross',
    financialImpact: 12450.00,
    summary: 'Separate identifiable evaluation service missing clinical documentation link.'
  },
  {
    id: 'INC-3890',
    type: 'NCCI Column 1 / Column 2 Endoscopy Edit Conflict',
    affectedClaims: 840,
    severity: 'MEDIUM',
    slaRisk: '22% (Low Risk)',
    slaRiskPercent: 22,
    status: 'Detected',
    time: '3h ago',
    payer: 'Cigna Healthcare',
    financialImpact: 8760.00,
    summary: 'Colonoscopy biopsy code billed concurrently with hot biopsy forceps excision.'
  },
  {
    id: 'INC-2104',
    type: 'ICD-10 Laterality Code Mismatch on Joint Replacement',
    affectedClaims: 540,
    severity: 'MEDIUM',
    slaRisk: '15% (Low Risk)',
    slaRiskPercent: 15,
    status: 'Awaiting Review',
    time: '4h ago',
    payer: 'Medicare CMS',
    financialImpact: 5480.00,
    summary: 'Left knee surgical modifier submitted with right knee primary diagnosis code.'
  },
  {
    id: 'INC-1940',
    type: 'Provider Taxonomy Crosswalk Discrepancy (EDI 2000A)',
    affectedClaims: 320,
    severity: 'LOW',
    slaRisk: '5% (Normal)',
    slaRiskPercent: 5,
    status: 'Resolved',
    time: '6h ago',
    payer: 'UnitedHealthcare',
    financialImpact: 3140.00,
    summary: 'Primary care taxonomy mapped to specialist billing category during clearinghouse ingestion.'
  }
];

// 5. System Status Section Data
export const mockSystemStatus: SystemStatusItem[] = [
  {
    name: 'Claims Pipeline',
    status: 'Healthy',
    state: 'healthy',
    metricLabel: 'Throughput',
    metricValue: '18,900 / hr',
    secondaryInfo: 'Latency: 142ms · 99.98% Uptime',
    iconName: 'Activity',
  },
  {
    name: 'Data Quality Engine',
    status: 'Active',
    state: 'active',
    metricLabel: 'Rule Set',
    metricValue: 'v2026.3.4 (48 Rules)',
    secondaryInfo: '0 Syntax Errors · 100% Parsing',
    iconName: 'ShieldCheck',
  },
  {
    name: 'Anomaly Engine',
    status: 'Active',
    state: 'active',
    metricLabel: 'Model State',
    metricValue: 'Isolation Forest + Heuristics',
    secondaryInfo: '99.4% Precision · 0 False Positives',
    iconName: 'Cpu',
  },
  {
    name: 'Risk Engine',
    status: 'Active',
    state: 'active',
    metricLabel: 'SLA Watchdog',
    metricValue: '1 Breached · 2 At Risk',
    secondaryInfo: 'Statutory Prompt-Pay Rules Enforced',
    iconName: 'Clock',
  },
  {
    name: 'AI Investigation',
    status: 'Ready',
    state: 'ready',
    metricLabel: 'Copilot Agent',
    metricValue: 'PayerGuard AI Core',
    secondaryInfo: 'Avg Root Cause Triage: 3.2s',
    iconName: 'Sparkles',
  },
];
