import { DQRuleConfig, SLAPolicyConfig } from '../types';

export const mockDQRules: DQRuleConfig[] = [
  {
    id: 'RUL-001',
    code: 'DQ_ERR_INVALID_BILLING_NPI',
    name: 'NPPES Billing NPI Registry Check',
    category: 'npi_validation',
    severity: 'critical',
    enabled: true,
    description: 'Validates that billing NPI satisfies the Luhn check formula and is currently active in the NPPES national provider index.',
    executionCount: 142850,
    failureCount: 42,
  },
  {
    id: 'RUL-002',
    code: 'DQ_ERR_NCCI_MUTUALLY_EXCLUSIVE',
    name: 'CMS NCCI Mutually Exclusive Edits',
    category: 'icd_cpt_accuracy',
    severity: 'high',
    enabled: true,
    description: 'Enforces CMS National Correct Coding Initiative (NCCI) PTP edits to prevent improper unbundling of comprehensive code pairs.',
    executionCount: 142850,
    failureCount: 186,
  },
  {
    id: 'RUL-003',
    code: 'DQ_ERR_SAME_DAY_DUPLICATE_CPT',
    name: 'Same-Day Duplicate Service Line Detection',
    category: 'duplicate_detection',
    severity: 'high',
    enabled: true,
    description: 'Scans for identical CPT/HCPCS codes submitted on the same patient, provider, and DOS within a 72-hour sliding window.',
    executionCount: 142850,
    failureCount: 94,
  },
  {
    id: 'RUL-004',
    code: 'DQ_ERR_TIMELY_FILING_LIMIT_EXCEEDED',
    name: 'Payer Timely Filing Statutory Threshold',
    category: 'timely_filing',
    severity: 'critical',
    enabled: true,
    description: 'Validates that service date is within statutory timely filing window (Commercial 90-180 days, Medicare/Medicaid 365 days).',
    executionCount: 142850,
    failureCount: 28,
  },
  {
    id: 'RUL-005',
    code: 'DQ_ERR_HIGH_DOLLAR_CHARGE_OUTLIER',
    name: 'Statistical Charge Outlier & Anomaly Detection',
    category: 'high_dollar_anomaly',
    severity: 'medium',
    enabled: true,
    threshold: 3.0,
    description: 'Applies statistical anomaly scoring on submitted charge against regional 90th percentile historical benchmark for given taxonomy.',
    executionCount: 142850,
    failureCount: 65,
  },
  {
    id: 'RUL-006',
    code: 'DQ_ERR_MODIFIER_25_COMPATIBILITY',
    name: 'Significant E/M Modifier 25 Validation',
    category: 'modifier_compatibility',
    severity: 'medium',
    enabled: true,
    description: 'Ensures Modifier 25 billed on E/M service has accompanying distinct procedural code and supporting secondary clinical diagnosis.',
    executionCount: 142850,
    failureCount: 112,
  }
];

export const mockSLAPolicies: SLAPolicyConfig[] = [
  {
    id: 'SLA-POL-001',
    name: 'Commercial Clean Claim 24h Fast Track',
    claimType: '837P',
    targetMaxMinutes: 1440, // 24 hours
    warningThresholdMinutes: 60,
    escalationRole: 'Lead Claims Auditor',
    autoMitigate: false,
  },
  {
    id: 'SLA-POL-002',
    name: 'Medicare Institutional UB-04 Statutory Adjudication',
    claimType: '837I',
    targetMaxMinutes: 2880, // 48 hours
    warningThresholdMinutes: 120,
    escalationRole: 'Senior Compliance Director',
    autoMitigate: true,
  },
  {
    id: 'SLA-POL-003',
    name: 'Dental Electronic 837D Stream Adjudication',
    claimType: '837D',
    targetMaxMinutes: 720, // 12 hours
    warningThresholdMinutes: 30,
    escalationRole: 'Dental Claims Specialist',
    autoMitigate: true,
  }
];
