import { ClaimRecord, EDIStandard, PayerName, RuleViolation } from '../types';

const SAMPLE_PAYERS: PayerName[] = [
  'Medicare CMS',
  'UnitedHealthcare',
  'Anthem BlueCross',
  'Aetna Health',
  'Cigna Healthcare',
  'Humana',
];

const SAMPLE_PROVIDERS = [
  { name: 'Mayo Clinic Healthcare', npi: '1948271049', taxonomy: '208D00000X (General Practice)' },
  { name: 'Cleveland Clinic Foundation', npi: '1093847291', taxonomy: '207RC0000X (Cardiovascular Disease)' },
  { name: 'Cedars-Sinai Medical Center', npi: '1487692019', taxonomy: '2085R0202X (Diagnostic Radiology)' },
  { name: 'Johns Hopkins Medicine', npi: '1720194820', taxonomy: '207X00000X (Orthopaedic Surgery)' },
  { name: 'Kaiser Permanente Medical Group', npi: '1831209485', taxonomy: '207Q00000X (Family Medicine)' },
];

const SAMPLE_PROCEDURES = [
  { cpt: '99214', desc: 'Office visit, established patient, moderate MDM (30-39 min)', charge: 185.00 },
  { cpt: '99213', desc: 'Office visit, established patient, low MDM (20-29 min)', charge: 120.00 },
  { cpt: '93000', desc: 'Electrocardiogram, routine ECG with at least 12 leads', charge: 450.00 },
  { cpt: '80053', desc: 'Comprehensive metabolic panel (14 tests)', charge: 85.00 },
  { cpt: '71046', desc: 'Radiologic examination, chest; 2 views', charge: 320.00 },
  { cpt: '99284', desc: 'Emergency department visit, high severity MDM', charge: 950.00 },
  { cpt: '29881', desc: 'Arthroscopy, knee, surgical; with meniscectomy', charge: 4200.00 },
  { cpt: '45380', desc: 'Colonoscopy, flexible; with biopsy, single or multiple', charge: 2100.00 },
];

const SAMPLE_PATIENTS = [
  'Alexander Mitchell', 'Sophia Chen', 'James Thornton', 'Emma Rodriguez',
  'Liam Washington', 'Olivia Vance', 'Noah Patel', 'Ava Campbell',
  'Lucas Wright', 'Mia Kowalski', 'Benjamin Hayes', 'Charlotte Bennett'
];

export function generateRandomClaim(forceAnomalyType?: string): ClaimRecord {
  const payer = SAMPLE_PAYERS[Math.floor(Math.random() * SAMPLE_PAYERS.length)];
  const provider = SAMPLE_PROVIDERS[Math.floor(Math.random() * SAMPLE_PROVIDERS.length)];
  const patient = SAMPLE_PATIENTS[Math.floor(Math.random() * SAMPLE_PATIENTS.length)];
  const randomNum = Math.floor(1000 + Math.random() * 9000);
  const claimId = `CLM-2026-${randomNum}`;
  const claimNumber = `${randomNum}-${Math.floor(1000 + Math.random() * 9000)}-${payer.substring(0, 3).toUpperCase()}`;
  const standards: EDIStandard[] = ['837P', '837P', '837P', '837I', 'CMS-1500'];
  const ediStandard = standards[Math.floor(Math.random() * standards.length)];

  // Determine if this is an anomaly
  const isAnomaly = forceAnomalyType ? true : Math.random() < 0.20; // 20% chance of anomaly in live stream
  const anomalyType = forceAnomalyType || (isAnomaly ? ['missing_npi', 'ncci_unbundling', 'duplicate_cpt', 'high_dollar', 'timely_filing'][Math.floor(Math.random() * 5)] : 'none');

  let violations: RuleViolation[] = [];
  let status: ClaimRecord['status'] = 'clean';
  let anomalyScore = Math.round((Math.random() * 0.12) * 100) / 100;
  let billedAmount = 0;
  const lineItems = [];

  const proc1 = SAMPLE_PROCEDURES[Math.floor(Math.random() * SAMPLE_PROCEDURES.length)];
  lineItems.push({
    lineNumber: 1,
    cptCode: proc1.cpt,
    cptDescription: proc1.desc,
    units: 1,
    charge: proc1.charge,
    serviceDate: new Date().toISOString().split('T')[0],
    posCode: '11 (Office)',
    status: 'valid' as const,
  });
  billedAmount += proc1.charge;

  if (anomalyType === 'missing_npi') {
    status = 'flagged';
    anomalyScore = 0.95;
    violations.push({
      ruleId: 'RUL-NPI-001',
      ruleCode: 'DQ_ERR_INVALID_BILLING_NPI',
      ruleName: 'Billing Provider NPI Validation Failure',
      category: 'npi_validation',
      severity: 'critical',
      message: 'Billing Provider NPI contains invalid Luhn format: 0000000000.',
      remediationSuggestion: 'Verify billing NPI with credentialing database.'
    });
  } else if (anomalyType === 'ncci_unbundling') {
    status = 'flagged';
    anomalyScore = 0.88;
    lineItems.push({
      lineNumber: 2,
      cptCode: '93010',
      cptDescription: 'Electrocardiogram report only [Mutually exclusive with 93000]',
      units: 1,
      charge: 150.00,
      serviceDate: new Date().toISOString().split('T')[0],
      posCode: '11 (Office)',
      status: 'invalid' as const,
      notes: 'NCCI PTP edit conflict with comprehensive code.'
    });
    billedAmount += 150.00;
    violations.push({
      ruleId: 'RUL-CCI-004',
      ruleCode: 'DQ_ERR_NCCI_MUTUALLY_EXCLUSIVE',
      ruleName: 'NCCI Procedure Code Conflict',
      category: 'icd_cpt_accuracy',
      severity: 'high',
      message: 'Unbundled component code billed alongside primary global procedure.',
      remediationSuggestion: 'Consolidate into single primary procedural line item.'
    });
  } else if (anomalyType === 'duplicate_cpt') {
    status = 'flagged';
    anomalyScore = 0.82;
    lineItems.push({
      lineNumber: 2,
      cptCode: proc1.cpt,
      cptDescription: `${proc1.desc} [Duplicate Line]`,
      units: 1,
      charge: proc1.charge,
      serviceDate: new Date().toISOString().split('T')[0],
      posCode: '11 (Office)',
      status: 'invalid' as const,
      notes: 'Exact duplicate line item without modifier.'
    });
    billedAmount += proc1.charge;
    violations.push({
      ruleId: 'RUL-DUP-002',
      ruleCode: 'DQ_ERR_SAME_DAY_DUPLICATE_CPT',
      ruleName: 'Same-Day Duplicate Service Line Violation',
      category: 'duplicate_detection',
      severity: 'high',
      message: `Duplicate billing of code CPT ${proc1.cpt} without appropriate repeat modifier.`,
      remediationSuggestion: 'Remove redundant service line or apply modifier 76/77.'
    });
  } else if (anomalyType === 'high_dollar') {
    billedAmount = 145800.00;
    status = 'pending_review';
    anomalyScore = 0.91;
    violations.push({
      ruleId: 'RUL-OUTLIER-009',
      ruleCode: 'DQ_ERR_HIGH_DOLLAR_CHARGE_OUTLIER',
      ruleName: 'High-Dollar Statistical Outlier',
      category: 'high_dollar_anomaly',
      severity: 'medium',
      message: 'Billed amount ($145,800.00) exceeds 99th percentile threshold for specialty.',
      remediationSuggestion: 'Trigger manual clinical review of high-dollar surgical implant ledger.'
    });
  } else if (anomalyType === 'timely_filing') {
    status = 'rejected';
    anomalyScore = 0.97;
    violations.push({
      ruleId: 'RUL-TIME-001',
      ruleCode: 'DQ_ERR_TIMELY_FILING_LIMIT_EXCEEDED',
      ruleName: 'Timely Filing Deadline Exceeded',
      category: 'timely_filing',
      severity: 'critical',
      message: 'Claim service date is older than payer statutory 365-day filing limit.',
      remediationSuggestion: 'Reject claim with denial code PR-27.'
    });
  }

  const now = new Date();
  const slaRemainingMinutes = status === 'clean' ? Math.floor(600 + Math.random() * 800) : (anomalyType === 'missing_npi' ? 18 : 120);
  const slaStatus = slaRemainingMinutes <= 0 ? 'breached' : (slaRemainingMinutes <= 30 ? 'at_risk' : 'on_track');

  return {
    id: claimId,
    claimNumber,
    payer,
    payerId: `${payer.substring(0, 4).toUpperCase()}-EDI-001`,
    ediStandard,
    patientId: `PT-${Math.floor(100000 + Math.random() * 900000)}`,
    patientName: patient,
    providerNpi: anomalyType === 'missing_npi' ? '0000000000' : provider.npi,
    providerName: provider.name,
    providerTaxonomy: provider.taxonomy,
    facilityName: `${provider.name} Main Pavilion`,
    serviceDate: new Date(Date.now() - 2 * 86400000).toISOString().split('T')[0],
    receivedAt: now.toISOString(),
    slaDeadline: new Date(Date.now() + slaRemainingMinutes * 60000).toISOString(),
    slaRemainingMinutes,
    slaStatus,
    status,
    billedAmount,
    expectedAllowedAmount: billedAmount * 0.78,
    primaryDiagnosis: 'Z00.00 (General adult medical exam)',
    lineItems,
    anomalyScore,
    violations,
  };
}
