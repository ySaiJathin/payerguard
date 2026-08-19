import { ClaimRecord } from '../types';

export const mockClaims: ClaimRecord[] = [
  {
    id: 'CLM-2026-9812',
    claimNumber: '9812-4401-BCBS',
    payer: 'Anthem BlueCross',
    payerId: 'BCBS-IL-001',
    ediStandard: '837P',
    patientId: 'PT-904128',
    patientName: 'Eleanor Vance',
    providerNpi: '1487692019',
    providerName: 'Apex Cardiology Associates',
    providerTaxonomy: '207RC0000X (Cardiovascular Disease)',
    renderingNpi: '1487692019',
    renderingProviderName: 'Dr. Michael Chen, MD',
    facilityName: 'Northwestern Memorial Hospital',
    serviceDate: '2026-08-16',
    receivedAt: '2026-08-18T03:15:20Z',
    slaDeadline: '2026-08-19T03:15:20Z',
    slaRemainingMinutes: 1080,
    slaStatus: 'on_track',
    status: 'clean',
    billedAmount: 1850.00,
    expectedAllowedAmount: 1420.50,
    primaryDiagnosis: 'I25.10 (Atherosclerotic heart disease)',
    secondaryDiagnoses: ['I10 (Essential hypertension)', 'E11.9 (Type 2 diabetes)'],
    lineItems: [
      {
        lineNumber: 1,
        cptCode: '93306',
        cptDescription: 'Echocardiography, transthoracic, real-time with image documentation',
        modifiers: ['26'],
        units: 1,
        charge: 1250.00,
        serviceDate: '2026-08-16',
        posCode: '11 (Office)',
        status: 'valid',
      },
      {
        lineNumber: 2,
        cptCode: '93000',
        cptDescription: 'Electrocardiogram, routine ECG with at least 12 leads',
        units: 1,
        charge: 600.00,
        serviceDate: '2026-08-16',
        posCode: '11 (Office)',
        status: 'valid',
      }
    ],
    anomalyScore: 0.04,
    violations: [],
    rawEdiSnippet: `ISA*00*          *00*          *ZZ*APEXCARDIO     *ZZ*BCBSIL         *260818*0315*^*00501*000009812*0*P*:~
GS*HC*APEXCARDIO*BCBSIL*20260818*0315*9812*X*005010X222A1~
ST*837*0001*005010X222A1~
BHT*0019*00*98124401BCBS*20260818*0315*CH~
NM1*41*2*APEX CARDIOLOGY*****46*1487692019~
CLM*9812-4401-BCBS*1850.00***11:B:1*Y*A*Y*Y~
HI*BK:I2510*BF:I10*BF:E119~
LX*1~
SV1*HC:93306:26*1250.00*UN*1***1~
DTP*472*D8*20260816~
LX*2~
SV1*HC:93000*600.00*UN*1***1~
DTP*472*D8*20260816~
SE*15*0001~
GE*1*9812~
IEA*1*000009812~`,
    ediSegments: [
      { segmentId: 'ISA', element: 'Interchange Control Header', content: 'ISA*00*...*00501*000009812*0*P*:~', hasError: false },
      { segmentId: 'NM1*41', element: 'Billing Provider', content: 'NM1*41*2*APEX CARDIOLOGY*****46*1487692019~', hasError: false },
      { segmentId: 'CLM', element: 'Claim Information', content: 'CLM*9812-4401-BCBS*1850.00***11:B:1*Y*A*Y*Y~', hasError: false },
      { segmentId: 'HI', element: 'Diagnosis Codes', content: 'HI*BK:I2510*BF:I10*BF:E119~', hasError: false },
      { segmentId: 'SV1', element: 'Service Line 1 (93306-26)', content: 'SV1*HC:93306:26*1250.00*UN*1***1~', hasError: false }
    ]
  },
  {
    id: 'CLM-2026-8921',
    claimNumber: '8921-7729-CMS',
    payer: 'Medicare CMS',
    payerId: 'CMS-MEDICARE-PART-B',
    ediStandard: '837P',
    patientId: 'PT-881903',
    patientName: 'Harold Jenkins',
    providerNpi: '9999999999', // Invalid test NPI
    providerName: 'Metropolitan Imaging Partners',
    providerTaxonomy: '2085R0202X (Diagnostic Radiology)',
    renderingNpi: '1093827101',
    renderingProviderName: 'Dr. Raymond Holt, MD',
    facilityName: 'Metropolitan Imaging Center',
    serviceDate: '2026-08-14',
    receivedAt: '2026-08-18T01:40:10Z',
    slaDeadline: '2026-08-18T05:40:10Z',
    slaRemainingMinutes: 24, // At Risk!
    slaStatus: 'at_risk',
    status: 'flagged',
    billedAmount: 4850.00,
    expectedAllowedAmount: 3100.00,
    primaryDiagnosis: 'M54.50 (Low back pain, unspecified)',
    secondaryDiagnoses: ['M51.26 (Intervertebral disc displacement, lumbar region)'],
    lineItems: [
      {
        lineNumber: 1,
        cptCode: '72148',
        cptDescription: 'Magnetic resonance imaging (MRI), lumbar spine; without contrast',
        units: 1,
        charge: 3200.00,
        serviceDate: '2026-08-14',
        posCode: '11 (Office)',
        status: 'valid',
      },
      {
        lineNumber: 2,
        cptCode: '72149',
        cptDescription: 'Magnetic resonance imaging (MRI), lumbar spine; with contrast',
        modifiers: ['59'],
        units: 1,
        charge: 1650.00,
        serviceDate: '2026-08-14',
        posCode: '11 (Office)',
        status: 'invalid',
        notes: 'Mutually exclusive billing under CMS NCCI edits without documented distinct anatomical site.'
      }
    ],
    anomalyScore: 0.94,
    violations: [
      {
        ruleId: 'RUL-NPI-001',
        ruleCode: 'DQ_ERR_INVALID_BILLING_NPI',
        ruleName: 'Billing Provider NPI Validation Failure',
        category: 'npi_validation',
        severity: 'critical',
        message: 'Billing Provider NPI 9999999999 failed Luhn checksum and is not registered in the NPPES Registry.',
        expectedValue: 'Active 10-digit NPI matching NPPES database',
        actualValue: '9999999999',
        segmentTarget: 'Loop 2010AA, NM1*85 (Billing Provider)',
        remediationSuggestion: 'Verify clinic NPI registration or re-submit with Organization NPI 1942857102.'
      },
      {
        ruleId: 'RUL-CCI-004',
        ruleCode: 'DQ_ERR_NCCI_MUTUALLY_EXCLUSIVE',
        ruleName: 'NCCI Procedure Code Conflict',
        category: 'icd_cpt_accuracy',
        severity: 'high',
        message: 'CPT 72149 billed concurrently with 72148 for same encounter violates CMS Column 1 / Column 2 edit.',
        expectedValue: '72148 OR 72158 (with and without contrast)',
        actualValue: '72148 + 72149',
        segmentTarget: 'Loop 2400, SV1*HC:72149',
        remediationSuggestion: 'Convert paired line items to comprehensive code CPT 72158.'
      }
    ],
    rawEdiSnippet: `ISA*00*          *00*          *ZZ*METROIMAGE     *ZZ*CMSMEDICARE    *260818*0140*^*00501*000008921*0*P*:~
GS*HC*METROIMAGE*CMSMEDICARE*20260818*0140*8921*X*005010X222A1~
ST*837*0001*005010X222A1~
BHT*0019*00*89217729CMS*20260818*0140*CH~
NM1*85*2*METROPOLITAN IMAGING*****XX*9999999999~  <<-- [ERROR: INVALID NPI]
CLM*8921-7729-CMS*4850.00***11:B:1*Y*A*Y*Y~
HI*BK:M5450*BF:M5126~
LX*1~
SV1*HC:72148*3200.00*UN*1***1~
LX*2~
SV1*HC:72149:59*1650.00*UN*1***1~  <<-- [ERROR: NCCI CONFLICT]
SE*14*0001~`,
    ediSegments: [
      { segmentId: 'NM1*85', element: 'Billing Provider', content: 'NM1*85*2*METROPOLITAN IMAGING*****XX*9999999999~', hasError: true, explanation: 'Invalid NPI 9999999999 (Checksum failure)' },
      { segmentId: 'CLM', element: 'Claim Header', content: 'CLM*8921-7729-CMS*4850.00***11:B:1*Y*A*Y*Y~', hasError: false },
      { segmentId: 'SV1*1', element: 'Line 1 (72148)', content: 'SV1*HC:72148*3200.00*UN*1***1~', hasError: false },
      { segmentId: 'SV1*2', element: 'Line 2 (72149)', content: 'SV1*HC:72149:59*1650.00*UN*1***1~', hasError: true, explanation: 'CMS NCCI unbundling edit violation' }
    ]
  },
  {
    id: 'CLM-2026-7734',
    claimNumber: '7734-1102-UHC',
    payer: 'UnitedHealthcare',
    payerId: 'UHC-COMM-87726',
    ediStandard: '837I',
    patientId: 'PT-449102',
    patientName: 'Gregory House',
    providerNpi: '1396847291',
    providerName: 'St. Jude Regional Medical Center',
    providerTaxonomy: '282N00000X (General Acute Care Hospital)',
    facilityName: 'St. Jude Hospital Inpatient Unit',
    serviceDate: '2026-08-01',
    receivedAt: '2026-08-18T00:10:00Z',
    slaDeadline: '2026-08-18T02:10:00Z',
    slaRemainingMinutes: -120, // Breached
    slaStatus: 'breached',
    status: 'sla_breached',
    billedAmount: 48920.00,
    expectedAllowedAmount: 36500.00,
    primaryDiagnosis: 'J18.9 (Pneumonia, unspecified organism)',
    secondaryDiagnoses: ['J96.01 (Acute respiratory failure with hypoxia)', 'I50.9 (Heart failure, unspecified)'],
    lineItems: [
      {
        lineNumber: 1,
        cptCode: '0120',
        cptDescription: 'Room & Board - Semi-Private (4 days)',
        units: 4,
        charge: 18000.00,
        serviceDate: '2026-08-01',
        posCode: '21 (Inpatient Hospital)',
        status: 'valid',
      },
      {
        lineNumber: 2,
        cptCode: '0250',
        cptDescription: 'Pharmacy - General Classification',
        units: 1,
        charge: 14500.00,
        serviceDate: '2026-08-02',
        posCode: '21 (Inpatient Hospital)',
        status: 'valid',
      },
      {
        lineNumber: 3,
        cptCode: '0270',
        cptDescription: 'Medical/Surgical Supplies - General',
        units: 1,
        charge: 16420.00,
        serviceDate: '2026-08-03',
        posCode: '21 (Inpatient Hospital)',
        status: 'warning',
        notes: 'High-dollar outlier supply charge exceeds standard DRG 193 historical ceiling by 142%.'
      }
    ],
    anomalyScore: 0.88,
    violations: [
      {
        ruleId: 'RUL-SLA-001',
        ruleCode: 'SLA_ERR_INPATIENT_TIMEOUT',
        ruleName: '24-Hour Clean Claim Processing SLA Exceeded',
        category: 'timely_filing',
        severity: 'critical',
        message: 'Claim ingestion exceeded 24-hour statutory adjudication window due to complex clinical chart review hold.',
        expectedValue: '< 1440 minutes turnaround',
        actualValue: '1560 minutes elapsed',
        segmentTarget: 'Pipeline SLA Timer',
        remediationSuggestion: 'Expedite immediate automated adjudication override or flag for emergency senior auditor signoff.'
      },
      {
        ruleId: 'RUL-OUTLIER-009',
        ruleCode: 'DQ_ERR_HIGH_DOLLAR_CHARGE_OUTLIER',
        ruleName: 'Hospital Supply Charge Outlier Detection',
        category: 'high_dollar_anomaly',
        severity: 'medium',
        message: 'Revenue code 0270 charge of $16,420 deviates >3 standard deviations from peer regional hospitals.',
        expectedValue: '< $6,800.00',
        actualValue: '$16,420.00',
        segmentTarget: 'Loop 2400, SV2 (Institutional Service Line 3)',
        remediationSuggestion: 'Request itemized supply breakdown ledger from hospital billing department.'
      }
    ],
    rawEdiSnippet: `ISA*00*          *00*          *ZZ*STJUDEHOSP     *ZZ*UHC            *260818*0010*^*00501*000007734*0*P*:~
GS*HC*STJUDEHOSP*UHC*20260818*0010*7734*X*005010X223A2~
ST*837*0001*005010X223A2~
CLM*7734-1102-UHC*48920.00***11:A:1*Y*A*Y*Y~
HI*BK:J189*BF:J9601*BF:I509~
SV2*0120*18000.00*UN*4~
SV2*0250*14500.00*UN*1~
SV2*0270*16420.00*UN*1~`,
    ediSegments: [
      { segmentId: 'CLM', element: 'UB-04 Claim Header', content: 'CLM*7734-1102-UHC*48920.00***11:A:1*Y*A*Y*Y~', hasError: false },
      { segmentId: 'SV2*3', element: 'Supplies Rev Code 0270', content: 'SV2*0270*16420.00*UN*1~', hasError: true, explanation: 'High-dollar outlier charge' }
    ]
  },
  {
    id: 'CLM-2026-6641',
    claimNumber: '6641-9930-AET',
    payer: 'Aetna Health',
    payerId: 'AETNA-COMM-60054',
    ediStandard: '837P',
    patientId: 'PT-103948',
    patientName: 'Clarissa Montgomery',
    providerNpi: '1831209485',
    providerName: 'Summit Dermatology Clinic',
    providerTaxonomy: '207N00000X (Dermatology)',
    renderingNpi: '1831209485',
    renderingProviderName: 'Dr. Sarah Lin, MD',
    facilityName: 'Summit Dermatology Suite 400',
    serviceDate: '2026-08-17',
    receivedAt: '2026-08-18T04:20:00Z',
    slaDeadline: '2026-08-19T04:20:00Z',
    slaRemainingMinutes: 1140,
    slaStatus: 'on_track',
    status: 'flagged',
    billedAmount: 940.00,
    expectedAllowedAmount: 710.00,
    primaryDiagnosis: 'L82.1 (Other seborrheic keratosis)',
    lineItems: [
      {
        lineNumber: 1,
        cptCode: '17000',
        cptDescription: 'Destruction (eg, laser, cryosurgery) of premalignant lesion; first lesion',
        units: 1,
        charge: 420.00,
        serviceDate: '2026-08-17',
        posCode: '11 (Office)',
        status: 'valid',
      },
      {
        lineNumber: 2,
        cptCode: '17000',
        cptDescription: 'Destruction of premalignant lesion; first lesion [DUPLICATE]',
        units: 1,
        charge: 420.00,
        serviceDate: '2026-08-17',
        posCode: '11 (Office)',
        status: 'invalid',
        notes: 'Exact duplicate code and charge submitted within same encounter instead of add-on code 17003.'
      },
      {
        lineNumber: 3,
        cptCode: '99213',
        cptDescription: 'Office/outpatient visit for evaluation and management of established patient',
        modifiers: ['25'],
        units: 1,
        charge: 100.00,
        serviceDate: '2026-08-17',
        posCode: '11 (Office)',
        status: 'valid',
      }
    ],
    anomalyScore: 0.79,
    violations: [
      {
        ruleId: 'RUL-DUP-002',
        ruleCode: 'DQ_ERR_SAME_DAY_DUPLICATE_CPT',
        ruleName: 'Same-Day Duplicate Service Line Violation',
        category: 'duplicate_detection',
        severity: 'high',
        message: 'Duplicate billing of primary lesion code CPT 17000 on line 2. Additional lesions require add-on CPT 17003.',
        expectedValue: 'CPT 17003 (Add-on code for 2nd-14th lesion)',
        actualValue: 'CPT 17000 repeated',
        segmentTarget: 'Loop 2400, SV1*HC:17000 (Line 2)',
        remediationSuggestion: 'Auto-convert Line 2 CPT 17000 to CPT 17003 or bundle into primary code.'
      }
    ],
    rawEdiSnippet: `ISA*00*          *00*          *ZZ*SUMMITDERM     *ZZ*AETNA          *260818*0420*^*00501*000006641*0*P*:~
GS*HC*SUMMITDERM*AETNA*20260818*0420*6641*X*005010X222A1~
CLM*6641-9930-AET*940.00***11:B:1*Y*A*Y*Y~
HI*BK:L821~
LX*1~
SV1*HC:17000*420.00*UN*1***1~
LX*2~
SV1*HC:17000*420.00*UN*1***1~  <<-- [DUPLICATE LINE ITEM]
LX*3~
SV1*HC:99213:25*100.00*UN*1***1~`,
    ediSegments: [
      { segmentId: 'SV1*1', element: 'Service Line 1 (17000)', content: 'SV1*HC:17000*420.00*UN*1***1~', hasError: false },
      { segmentId: 'SV1*2', element: 'Service Line 2 (17000)', content: 'SV1*HC:17000*420.00*UN*1***1~', hasError: true, explanation: 'Duplicate primary procedure code' },
      { segmentId: 'SV1*3', element: 'Service Line 3 (99213-25)', content: 'SV1*HC:99213:25*100.00*UN*1***1~', hasError: false }
    ]
  },
  {
    id: 'CLM-2026-5520',
    claimNumber: '5520-3381-CIG',
    payer: 'Cigna Healthcare',
    payerId: 'CIGNA-COMM-62308',
    ediStandard: '837P',
    patientId: 'PT-662910',
    patientName: 'Marcus Sterling',
    providerNpi: '1720194820',
    providerName: 'Orthopedic Spine Center',
    providerTaxonomy: '207X00000X (Orthopaedic Surgery)',
    renderingNpi: '1720194820',
    renderingProviderName: 'Dr. David Vance, MD',
    facilityName: 'Surgical Specialty Pavilion',
    serviceDate: '2026-08-15',
    receivedAt: '2026-08-18T02:00:00Z',
    slaDeadline: '2026-08-19T02:00:00Z',
    slaRemainingMinutes: 980,
    slaStatus: 'on_track',
    status: 'clean',
    billedAmount: 14200.00,
    expectedAllowedAmount: 11100.00,
    primaryDiagnosis: 'M48.061 (Spinal stenosis, lumbar region with neurogenic claudication)',
    lineItems: [
      {
        lineNumber: 1,
        cptCode: '22612',
        cptDescription: 'Arthrodesis, posterior or posterolateral technique, single level; lumbar',
        modifiers: ['51'],
        units: 1,
        charge: 9800.00,
        serviceDate: '2026-08-15',
        posCode: '22 (On Campus Outpatient)',
        status: 'valid',
      },
      {
        lineNumber: 2,
        cptCode: '22842',
        cptDescription: 'Posterior segmental instrumentation; 3 to 6 vertebral segments',
        units: 1,
        charge: 4400.00,
        serviceDate: '2026-08-15',
        posCode: '22 (On Campus Outpatient)',
        status: 'valid',
      }
    ],
    anomalyScore: 0.08,
    violations: [],
    rawEdiSnippet: `ISA*00*          *00*          *ZZ*ORTHOSPINE     *ZZ*CIGNA          *260818*0200*^*00501*000005520*0*P*:~
GS*HC*ORTHOSPINE*CIGNA*20260818*0200*5520*X*005010X222A1~
CLM*5520-3381-CIG*14200.00***22:B:1*Y*A*Y*Y~
HI*BK:M48061~
LX*1~
SV1*HC:22612:51*9800.00*UN*1***1~
LX*2~
SV1*HC:22842*4400.00*UN*1***1~`,
    ediSegments: [
      { segmentId: 'CLM', element: 'Claim Header', content: 'CLM*5520-3381-CIG*14200.00***22:B:1*Y*A*Y*Y~', hasError: false },
      { segmentId: 'SV1*1', element: 'Line 1 (22612-51)', content: 'SV1*HC:22612:51*9800.00*UN*1***1~', hasError: false },
      { segmentId: 'SV1*2', element: 'Line 2 (22842)', content: 'SV1*HC:22842*4400.00*UN*1***1~', hasError: false }
    ]
  },
  {
    id: 'CLM-2026-4419',
    claimNumber: '4419-8821-HUM',
    payer: 'Humana',
    payerId: 'HUMANA-MED-ADV-47003',
    ediStandard: '837P',
    patientId: 'PT-994012',
    patientName: 'Beatrice Lawson',
    providerNpi: '1948201749',
    providerName: 'Valley Eye Institute',
    providerTaxonomy: '207W00000X (Ophthalmology)',
    facilityName: 'Valley Ambulatory Surgery Center',
    serviceDate: '2025-05-10', // Old service date: Timely filing breach
    receivedAt: '2026-08-18T05:00:00Z',
    slaDeadline: '2026-08-19T05:00:00Z',
    slaRemainingMinutes: 1200,
    slaStatus: 'on_track',
    status: 'rejected',
    billedAmount: 3150.00,
    expectedAllowedAmount: 0.00,
    primaryDiagnosis: 'H25.13 (Age-related nuclear cataract, bilateral)',
    lineItems: [
      {
        lineNumber: 1,
        cptCode: '66984',
        cptDescription: 'Extracapsular cataract removal with insertion of intraocular lens prosthesis',
        modifiers: ['RT'],
        units: 1,
        charge: 3150.00,
        serviceDate: '2025-05-10',
        posCode: '24 (Ambulatory Surgical Center)',
        status: 'invalid',
        notes: 'Date of service exceeds payer 365-day statutory timely filing limit.'
      }
    ],
    anomalyScore: 0.96,
    violations: [
      {
        ruleId: 'RUL-TIME-001',
        ruleCode: 'DQ_ERR_TIMELY_FILING_LIMIT_EXCEEDED',
        ruleName: 'Timely Filing Deadline Exceeded (>365 Days)',
        category: 'timely_filing',
        severity: 'critical',
        message: 'Encounter service date 2025-05-10 is 465 days prior to received date 2026-08-18 (Limit: 365 days).',
        expectedValue: 'DOS within past 365 calendar days',
        actualValue: '465 calendar days elapsed',
        segmentTarget: 'Loop 2400, DTP*472 (Date of Service)',
        remediationSuggestion: 'Issue hard rejection code PR-27 to provider unless documented proof of payer appeal is attached.'
      }
    ],
    rawEdiSnippet: `ISA*00*          *00*          *ZZ*VALLEYEYE      *ZZ*HUMANA         *260818*0500*^*00501*000004419*0*P*:~
GS*HC*VALLEYEYE*HUMANA*20260818*0500*4419*X*005010X222A1~
CLM*4419-8821-HUM*3150.00***24:B:1*Y*A*Y*Y~
HI*BK:H2513~
LX*1~
SV1*HC:66984:RT*3150.00*UN*1***1~
DTP*472*D8*20250510~  <<-- [TIMELY FILING BREACH]`,
    ediSegments: [
      { segmentId: 'CLM', element: 'Claim Header', content: 'CLM*4419-8821-HUM*3150.00***24:B:1*Y*A*Y*Y~', hasError: false },
      { segmentId: 'DTP*472', element: 'Service Date', content: 'DTP*472*D8*20250510~', hasError: true, explanation: 'DOS older than 365 days timely filing statutory window' }
    ]
  }
];
