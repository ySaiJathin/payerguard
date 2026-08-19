import { Incident } from '../types';
import { mockClaims } from './mockClaims';

export const mockIncidents: Incident[] = [
  {
    id: 'INC-8921',
    claimId: 'CLM-2026-8921',
    claimNumber: '8921-7729-CMS',
    title: 'Billing NPI Checksum Failure & NCCI Lumbar MRI Conflict',
    description: 'Claim contains an unregistered billing NPI 9999999999 along with concurrent unbundled lumbar MRI service lines (72148 + 72149). SLA timer has 24 minutes remaining.',
    category: 'npi_validation',
    severity: 'critical',
    status: 'investigating',
    slaStatus: 'at_risk',
    slaRemainingMinutes: 24,
    payer: 'Medicare CMS',
    billedAmount: 4850.00,
    detectedAt: '2026-08-18T01:40:10Z',
    updatedAt: '2026-08-18T03:55:00Z',
    assignee: {
      name: 'Dr. Sarah Jenkins',
      role: 'Lead Claims Auditor',
      avatar: 'SJ'
    },
    anomalyConfidence: 0.94,
    rootCauseAnalysis: {
      primaryFailure: 'Loop 2010AA NM1*85 Provider NPI was transposed during clearinghouse ingestion mapping. Line item 2 lacked required distinct procedure modifier justification.',
      impactDescription: 'High risk of Medicare Part B post-payment audit clawback ($4,850) and immediate statutory SLA breach if unaddressed within 24m.',
      affectedSubsystems: ['NPPES Registry Gateway', 'CMS NCCI Edit Engine v2026.3', 'EDI 837P Ingestion Parser'],
      recommendedFix: 'Re-map billing provider NPI to Metropolitan Imaging Org NPI 1942857102 and consolidate line items 1 & 2 into combined CPT 72158.'
    },
    claimDetails: mockClaims[1],
    auditTrail: [
      {
        id: 'LOG-101',
        timestamp: '2026-08-18T01:40:10Z',
        actor: 'PayerGuard Automated Ingestion Pipeline',
        action: 'Ingestion Anomaly Triggered',
        details: 'NPI Checksum failed in Loop 2010AA. Anomaly score computed at 0.94.'
      },
      {
        id: 'LOG-102',
        timestamp: '2026-08-18T01:41:00Z',
        actor: 'SLA Engine',
        action: 'Priority Escalated',
        details: 'Flagged as High Priority. SLA deadline assigned for 05:40:10 UTC.'
      },
      {
        id: 'LOG-103',
        timestamp: '2026-08-18T03:30:00Z',
        actor: 'Dr. Sarah Jenkins',
        action: 'Investigation Assigned',
        details: 'Audit assigned to Lead Auditor. Investigation underway.'
      }
    ]
  },
  {
    id: 'INC-7734',
    claimId: 'CLM-2026-7734',
    claimNumber: '7734-1102-UHC',
    title: 'Inpatient 24h SLA Breached & Revenue Code 0270 Outlier',
    description: 'High-dollar inpatient institutional claim ($48,920) has exceeded the 24-hour adjudication threshold due to complex surgical supply verification holds.',
    category: 'timely_filing',
    severity: 'critical',
    status: 'escalated',
    slaStatus: 'breached',
    slaRemainingMinutes: -120,
    payer: 'UnitedHealthcare',
    billedAmount: 48920.00,
    detectedAt: '2026-08-18T00:10:00Z',
    updatedAt: '2026-08-18T04:15:00Z',
    assignee: {
      name: 'Marcus Brody',
      role: 'Senior Compliance Director',
      avatar: 'MB'
    },
    anomalyConfidence: 0.88,
    rootCauseAnalysis: {
      primaryFailure: 'Supply charge ($16,420) flagged by outlier heuristics triggered manual review workflow that queued beyond 24h statutory window.',
      impactDescription: 'State insurance commissioner SLA fine liability ($500/day penalty) + prompt payment interest accumulation.',
      affectedSubsystems: ['Inpatient Adjudication Router', 'Institutional DRG Pricing Engine'],
      recommendedFix: 'Request itemized chargemaster bill from St. Jude Medical Center and grant temporary provisional SLA extension code EXT-99.'
    },
    claimDetails: mockClaims[2],
    auditTrail: [
      {
        id: 'LOG-201',
        timestamp: '2026-08-18T00:10:00Z',
        actor: 'EDI 837I Parser',
        action: 'Ingestion Complete',
        details: 'Institutional claim received with billed total $48,920.00.'
      },
      {
        id: 'LOG-202',
        timestamp: '2026-08-18T02:10:00Z',
        actor: 'SLA Watchdog',
        action: 'SLA Breached',
        details: '24-hour statutory prompt pay deadline exceeded.'
      },
      {
        id: 'LOG-203',
        timestamp: '2026-08-18T04:15:00Z',
        actor: 'Marcus Brody',
        action: 'Escalated to Hospital Relations',
        details: 'Contacted provider billing director for expedited chargemaster log.'
      }
    ]
  },
  {
    id: 'INC-6641',
    claimNumber: '6641-9930-AET',
    claimId: 'CLM-2026-6641',
    title: 'Duplicate Lesion Destruction CPT 17000 on Same Encounter',
    description: 'Summit Dermatology submitted multiple primary lesion destruction codes (17000) on the same date of service instead of required add-on code 17003.',
    category: 'duplicate_detection',
    severity: 'high',
    status: 'open',
    slaStatus: 'on_track',
    slaRemainingMinutes: 1140,
    payer: 'Aetna Health',
    billedAmount: 940.00,
    detectedAt: '2026-08-18T04:20:00Z',
    updatedAt: '2026-08-18T04:20:00Z',
    assignee: {
      name: 'Elena Rostova',
      role: 'Data Quality Specialist',
      avatar: 'ER'
    },
    anomalyConfidence: 0.79,
    rootCauseAnalysis: {
      primaryFailure: 'Provider EHR billing template auto-populated CPT 17000 for both primary and secondary lesion entries.',
      impactDescription: 'Potential overpayment of $320 if both billed as primary surgical procedures.',
      affectedSubsystems: ['Procedure Coding Crosswalk', 'AMA CPT Coding Rules Engine'],
      recommendedFix: 'Automatically adjust Line 2 from CPT 17000 ($420) to CPT 17003 ($100) and approve claim.'
    },
    claimDetails: mockClaims[3],
    auditTrail: [
      {
        id: 'LOG-301',
        timestamp: '2026-08-18T04:20:00Z',
        actor: 'Duplicate Service Detector',
        action: 'Rule Violation Detected',
        details: 'CPT 17000 duplicate detected within encounter 6641-9930-AET.'
      }
    ]
  },
  {
    id: 'INC-4419',
    claimNumber: '4419-8821-HUM',
    claimId: 'CLM-2026-4419',
    title: 'Statutory Timely Filing Limit Exceeded (465 Days Old)',
    description: 'Cataract surgery encounter date of service (2025-05-10) exceeds Humana Medicare Advantage 365-day timely filing window.',
    category: 'timely_filing',
    severity: 'critical',
    status: 'open',
    slaStatus: 'on_track',
    slaRemainingMinutes: 1200,
    payer: 'Humana',
    billedAmount: 3150.00,
    detectedAt: '2026-08-18T05:00:00Z',
    updatedAt: '2026-08-18T05:00:00Z',
    assignee: {
      name: 'Unassigned',
      role: 'Claims Triage Queue',
      avatar: 'TQ'
    },
    anomalyConfidence: 0.96,
    rootCauseAnalysis: {
      primaryFailure: 'Provider submitted claim beyond 365 calendar days without attached proof of good cause or prior payer delay.',
      impactDescription: 'Immediate hard claim denial with zero patient liability under Medicare Advantage guidelines.',
      affectedSubsystems: ['Timely Filing SLA Gatekeeper'],
      recommendedFix: 'Issue EDI 835 Remittance Advice with Claim Adjustment Reason Code 29 (Time limit for filing has expired).'
    },
    claimDetails: mockClaims[5] || mockClaims[0],
    auditTrail: [
      {
        id: 'LOG-401',
        timestamp: '2026-08-18T05:00:00Z',
        actor: 'Timely Filing Rule Checker',
        action: 'Hard Rejection Triggered',
        details: 'DOS 2025-05-10 is 465 days old. Limit is 365 days.'
      }
    ]
  },
  {
    id: 'INC-5512',
    claimNumber: '5512-4901-ANT',
    claimId: 'CLM-2026-5512',
    title: 'Modifier 25 Inconsistency on E&M Service with Minor Surgery',
    description: 'Separate identifiable evaluation and management service (CPT 99214) billed with minor procedure without required medical necessity documentation in encounter record.',
    category: 'modifier_compatibility',
    severity: 'high',
    status: 'investigating',
    slaStatus: 'at_risk',
    slaRemainingMinutes: 45,
    payer: 'Anthem BlueCross',
    billedAmount: 12450.00,
    detectedAt: '2026-08-18T03:10:00Z',
    updatedAt: '2026-08-18T04:25:00Z',
    assignee: {
      name: 'Elena Rostova',
      role: 'Data Quality Specialist',
      avatar: 'ER'
    },
    anomalyConfidence: 0.85,
    rootCauseAnalysis: {
      primaryFailure: 'Modifier 25 appended to CPT 99214 without distinct diagnosis code mapping or clinical narrative justifying separate evaluation.',
      impactDescription: 'High risk of payer post-payment review recoupment ($12,450).',
      affectedSubsystems: ['Modifier Compatibility Matrix', 'E&M Validation Engine'],
      recommendedFix: 'Request provider office clinical progress note verifying distinct problem-oriented evaluation.'
    },
    claimDetails: mockClaims[0],
    auditTrail: [
      {
        id: 'LOG-501',
        timestamp: '2026-08-18T03:10:00Z',
        actor: 'Modifier Validation Subsystem',
        action: 'Flagged for Clinical Review',
        details: 'Modifier 25 attached to CPT 99214 flagged for missing clinical nexus.'
      }
    ]
  },
  {
    id: 'INC-3890',
    claimNumber: '3890-8812-CIG',
    claimId: 'CLM-2026-3890',
    title: 'NCCI Column 1 / Column 2 Endoscopy Edit Conflict',
    description: 'Upper GI endoscopy biopsy billed concurrently with hot biopsy forceps excision without separate lesion anatomical markers.',
    category: 'icd_cpt_accuracy',
    severity: 'medium',
    status: 'open',
    slaStatus: 'on_track',
    slaRemainingMinutes: 720,
    payer: 'Cigna Healthcare',
    billedAmount: 8760.00,
    detectedAt: '2026-08-18T02:40:00Z',
    updatedAt: '2026-08-18T02:40:00Z',
    assignee: {
      name: 'Marcus Brody',
      role: 'Senior Compliance Director',
      avatar: 'MB'
    },
    anomalyConfidence: 0.76,
    rootCauseAnalysis: {
      primaryFailure: 'CPT 43239 and CPT 43238 billed on same date of service without anatomical modifier 59/XS.',
      impactDescription: 'NCCI edit denial by payer clearinghouse gateway.',
      affectedSubsystems: ['CMS NCCI Edit Engine v2026.3'],
      recommendedFix: 'Review endoscopy operative report and append modifier XS to line 2 if biopsy was performed at distinct site.'
    },
    claimDetails: mockClaims[4] || mockClaims[0],
    auditTrail: [
      {
        id: 'LOG-601',
        timestamp: '2026-08-18T02:40:00Z',
        actor: 'NCCI Rules Engine',
        action: 'Anomaly Flagged',
        details: 'Column 1 / Column 2 edit conflict detected.'
      }
    ]
  },
  {
    id: 'INC-2104',
    claimNumber: '2104-3329-CMS',
    claimId: 'CLM-2026-2104',
    title: 'ICD-10 Laterality Code Mismatch on Total Knee Arthroplasty',
    description: 'Surgical modifier RT (Right side) submitted with ICD-10 diagnosis M17.12 (Unilateral primary osteoarthritis, left knee).',
    category: 'icd_cpt_accuracy',
    severity: 'medium',
    status: 'open',
    slaStatus: 'on_track',
    slaRemainingMinutes: 840,
    payer: 'Medicare CMS',
    billedAmount: 5480.00,
    detectedAt: '2026-08-18T01:15:00Z',
    updatedAt: '2026-08-18T01:15:00Z',
    assignee: {
      name: 'Dr. Sarah Jenkins',
      role: 'Lead Claims Auditor',
      avatar: 'SJ'
    },
    anomalyConfidence: 0.92,
    rootCauseAnalysis: {
      primaryFailure: 'ICD-10 laterality digit (2 for left) conflicts with surgical modifier RT.',
      impactDescription: 'Instant Medicare Part B edit rejection.',
      affectedSubsystems: ['ICD-10 Laterality Verification Gate'],
      recommendedFix: 'Correct ICD-10 code to M17.11 (Right knee) based on operative report verification.'
    },
    claimDetails: mockClaims[0],
    auditTrail: [
      {
        id: 'LOG-701',
        timestamp: '2026-08-18T01:15:00Z',
        actor: 'Laterality Checker',
        action: 'Diagnosis / Procedure Inconsistency',
        details: 'Left knee diagnosis M17.12 with RT modifier detected.'
      }
    ]
  },
  {
    id: 'INC-1940',
    claimNumber: '1940-5521-UHC',
    claimId: 'CLM-2026-1940',
    title: 'Provider Taxonomy Crosswalk Discrepancy (EDI 2000A)',
    description: 'Primary care taxonomy mapped to specialist billing category during clearinghouse ingestion.',
    category: 'npi_validation',
    severity: 'low',
    status: 'resolved',
    slaStatus: 'met',
    slaRemainingMinutes: 0,
    payer: 'UnitedHealthcare',
    billedAmount: 3140.00,
    detectedAt: '2026-08-17T22:30:00Z',
    updatedAt: '2026-08-18T04:10:00Z',
    assignee: {
      name: 'Elena Rostova',
      role: 'Data Quality Specialist',
      avatar: 'ER'
    },
    anomalyConfidence: 0.65,
    rootCauseAnalysis: {
      primaryFailure: 'Ingestion crosswalk mapped taxonomy code 207Q00000X to invalid specialty table entry.',
      impactDescription: 'Prevented automated tier-1 adjudication.',
      affectedSubsystems: ['Taxonomy Crosswalk Engine'],
      recommendedFix: 'Taxonomy corrected in master provider directory and claim re-queued for adjudication.'
    },
    claimDetails: mockClaims[0],
    auditTrail: [
      {
        id: 'LOG-801',
        timestamp: '2026-08-17T22:30:00Z',
        actor: 'Taxonomy Validator',
        action: 'Warning Triggered',
        details: 'Taxonomy mismatch mapped.'
      },
      {
        id: 'LOG-802',
        timestamp: '2026-08-18T04:10:00Z',
        actor: 'Elena Rostova',
        action: 'Remediated & Resolved',
        details: 'Corrected taxonomy mapping in clearinghouse profile.'
      }
    ]
  }
];
