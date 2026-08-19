import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileCheck,
  AlertTriangle,
  FileText,
  CheckCircle2,
  XCircle,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  Download,
  Eye
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import { formatCurrency } from '../utils/formatters';

interface UploadStep {
  name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  message?: string;
}

export const Upload: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [validationCompleted, setValidationCompleted] = useState(false);

  const [steps, setSteps] = useState<UploadStep[]>([
    { name: 'EDI Envelope Unpacking (ISA / GS / ST)', status: 'pending' },
    { name: 'HIPAA 5010 Structural & Schema Syntax Check', status: 'pending' },
    { name: 'NPPES NPI & Taxonomy Registry Validation', status: 'pending' },
    { name: 'CMS NCCI Procedure Mutually Exclusive Edits', status: 'pending' },
    { name: 'Timely Filing & SLA Clock Assignment', status: 'pending' },
    { name: 'Statistical Anomaly & High-Dollar Outlier Scoring', status: 'pending' },
  ]);

  const [batchResults, setBatchResults] = useState<{
    batchId: string;
    filename: string;
    totalClaims: number;
    cleanCount: number;
    flaggedCount: number;
    rejectedCount: number;
    totalBilled: number;
    claims: Array<{
      id: string;
      claimNumber: string;
      payer: string;
      patient: string;
      providerNpi: string;
      billed: number;
      status: 'clean' | 'flagged' | 'rejected';
      issue?: string;
    }>;
  } | null>(null);

  const runValidationSimulation = (filename: string, presetType: string) => {
    setIsProcessing(true);
    setProgress(10);
    setValidationCompleted(false);

    setSteps((prev) => prev.map((s) => ({ ...s, status: 'pending', message: undefined })));

    // Step 1
    setTimeout(() => {
      setSteps((prev) => [
        { ...prev[0], status: 'completed', message: 'ISA*00 control header validated (00501 standard)' },
        { ...prev[1], status: 'in_progress' },
        ...prev.slice(2),
      ]);
      setProgress(25);
    }, 400);

    // Step 2
    setTimeout(() => {
      setSteps((prev) => [
        prev[0],
        { ...prev[1], status: 'completed', message: 'All loops (2000A/B, 2300, 2400) conform to HIPAA 5010' },
        { ...prev[2], status: 'in_progress' },
        ...prev.slice(3),
      ]);
      setProgress(50);
    }, 900);

    // Step 3
    setTimeout(() => {
      const isMedicareAnomalous = presetType === 'medicare_anomalies';
      setSteps((prev) => [
        prev[0],
        prev[1],
        {
          ...prev[2],
          status: isMedicareAnomalous ? 'error' : 'completed',
          message: isMedicareAnomalous
            ? '1 Billing NPI failed checksum and is missing in NPPES'
            : 'All Billing & Rendering NPIs verified active in NPPES',
        },
        { ...prev[3], status: 'in_progress' },
        ...prev.slice(4),
      ]);
      setProgress(75);
    }, 1400);

    // Step 4 & 5
    setTimeout(() => {
      setSteps((prev) => [
        prev[0],
        prev[1],
        prev[2],
        { ...prev[3], status: 'completed', message: 'CMS NCCI PTP edits evaluated against v2026.3' },
        { ...prev[4], status: 'completed', message: 'SLA priority: Standard 24h turn-around active' },
        { ...prev[5], status: 'in_progress' },
      ]);
      setProgress(90);
    }, 1800);

    // Final Completion
    setTimeout(() => {
      setSteps((prev) => prev.map((s) => ({ ...s, status: s.status === 'error' ? 'error' : 'completed' })));
      setProgress(100);
      setIsProcessing(false);
      setValidationCompleted(true);

      if (presetType === 'medicare_anomalies') {
        setBatchResults({
          batchId: `BATCH-${Math.floor(100000 + Math.random() * 900000)}`,
          filename,
          totalClaims: 12,
          cleanCount: 9,
          flaggedCount: 2,
          rejectedCount: 1,
          totalBilled: 28450.00,
          claims: [
            {
              id: 'CLM-2026-8921',
              claimNumber: '8921-7729-CMS',
              payer: 'Medicare CMS',
              patient: 'Harold Jenkins',
              providerNpi: '9999999999',
              billed: 4850.00,
              status: 'flagged',
              issue: 'Billing NPI Checksum Failure (Loop 2010AA NM1*85) & NCCI MRI conflict',
            },
            {
              id: 'CLM-2026-6641',
              claimNumber: '6641-9930-AET',
              payer: 'Aetna Health',
              patient: 'Clarissa Montgomery',
              providerNpi: '1831209485',
              billed: 940.00,
              status: 'flagged',
              issue: 'Duplicate lesion destruction CPT 17000 on same date of service',
            },
            {
              id: 'CLM-2026-4419',
              claimNumber: '4419-8821-HUM',
              payer: 'Humana',
              patient: 'Beatrice Lawson',
              providerNpi: '1948201749',
              billed: 3150.00,
              status: 'rejected',
              issue: 'Service Date is 465 days old (Timely Filing exceeded > 365d)',
            },
            {
              id: 'CLM-2026-9812',
              claimNumber: '9812-4401-BCBS',
              payer: 'Anthem BlueCross',
              patient: 'Eleanor Vance',
              providerNpi: '1487692019',
              billed: 1850.00,
              status: 'clean',
            },
            {
              id: 'CLM-2026-5520',
              claimNumber: '5520-3381-CIG',
              payer: 'Cigna Healthcare',
              patient: 'Marcus Sterling',
              providerNpi: '1720194820',
              billed: 14200.00,
              status: 'clean',
            },
          ],
        });
      } else {
        setBatchResults({
          batchId: `BATCH-${Math.floor(100000 + Math.random() * 900000)}`,
          filename,
          totalClaims: 25,
          cleanCount: 25,
          flaggedCount: 0,
          rejectedCount: 0,
          totalBilled: 42100.00,
          claims: [
            {
              id: 'CLM-2026-9812',
              claimNumber: '9812-4401-BCBS',
              payer: 'Anthem BlueCross',
              patient: 'Eleanor Vance',
              providerNpi: '1487692019',
              billed: 1850.00,
              status: 'clean',
            },
            {
              id: 'CLM-2026-5520',
              claimNumber: '5520-3381-CIG',
              payer: 'Cigna Healthcare',
              patient: 'Marcus Sterling',
              providerNpi: '1720194820',
              billed: 14200.00,
              status: 'clean',
            },
            {
              id: 'CLM-2026-1102',
              claimNumber: '1102-8841-UHC',
              payer: 'UnitedHealthcare',
              patient: 'Patricia Hayes',
              providerNpi: '1093847291',
              billed: 3400.00,
              status: 'clean',
            },
          ],
        });
      }
    }, 2400);
  };

  const handlePresetSelect = (preset: string) => {
    setSelectedPreset(preset);
    if (preset === 'medicare_anomalies') {
      runValidationSimulation('medicare_part_b_anomalous_batch_20260818.837', preset);
    } else if (preset === 'inpatient_sample') {
      runValidationSimulation('uhc_inpatient_institutional_batch_20260818.837', preset);
    } else {
      runValidationSimulation('commercial_ortho_clean_batch_20260818.edi', preset);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      runValidationSimulation(file.name, 'custom_file');
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-heading">
            Upload & Batch EDI Ingestion
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Ingest and inspect EDI 837P/837I, CMS-1500, UB-04, CSV, or JSON batches with automated pre-flight quality checks.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="purple" size="sm">
            Supported: 837P / 837I / EDI 5010 / JSON
          </Badge>
        </div>
      </div>

      {/* Preset Test Scenarios */}
      <div className="space-y-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Instant Sample EDI Batches
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <button
            onClick={() => handlePresetSelect('medicare_anomalies')}
            disabled={isProcessing}
            className={`p-3 rounded-lg border text-left transition-all ${
              selectedPreset === 'medicare_anomalies'
                ? 'bg-cyan-950/40 border-cyan-500/60 ring-1 ring-cyan-500/50'
                : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-100">Medicare Part B (Anomalies)</span>
              <Badge variant="danger" size="sm">Contains Errors</Badge>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Includes NPI Checksum failure, NCCI conflict & Timely Filing breach.
            </p>
          </button>

          <button
            onClick={() => handlePresetSelect('inpatient_sample')}
            disabled={isProcessing}
            className={`p-3 rounded-lg border text-left transition-all ${
              selectedPreset === 'inpatient_sample'
                ? 'bg-cyan-950/40 border-cyan-500/60 ring-1 ring-cyan-500/50'
                : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-100">UHC Inpatient 837I</span>
              <Badge variant="warning" size="sm">High-Dollar</Badge>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Institutional claim batch with hospital DRG outlier supply charge.
            </p>
          </button>

          <button
            onClick={() => handlePresetSelect('clean_sample')}
            disabled={isProcessing}
            className={`p-3 rounded-lg border text-left transition-all ${
              selectedPreset === 'clean_sample'
                ? 'bg-cyan-950/40 border-cyan-500/60 ring-1 ring-cyan-500/50'
                : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-100">Commercial Clean 837P</span>
              <Badge variant="success" size="sm">100% Clean</Badge>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              25 clean outpatient claims ready for automated first-pass approval.
            </p>
          </button>
        </div>
      </div>

      {/* Drag and Drop Zone */}
      <Card>
        <div
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-slate-750 hover:border-cyan-500/60 rounded-xl p-8 sm:p-12 text-center bg-slate-950/40 hover:bg-slate-900/50 transition-all cursor-pointer group"
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".edi,.837,.txt,.json,.csv,.xml"
            className="hidden"
          />
          <div className="w-14 h-14 rounded-2xl bg-slate-800/80 text-cyan-400 border border-slate-700 flex items-center justify-center mx-auto mb-4 group-hover:scale-105 group-hover:border-cyan-500/40 transition-all">
            <UploadCloud className="w-7 h-7" />
          </div>
          <h3 className="text-base font-semibold text-slate-100">
            {selectedFile ? selectedFile.name : 'Click to select or drag & drop EDI claim file'}
          </h3>
          <p className="text-xs text-slate-400 mt-1.5 max-w-md mx-auto">
            Supports standard ANSI ASC X12N 837P / 837I / 837D, CMS-1500 JSON payloads, and clearinghouse flat CSV formats.
          </p>
          <div className="mt-4 flex items-center justify-center gap-2">
            <span className="text-[11px] font-mono text-slate-400 bg-slate-900 px-2.5 py-1 rounded border border-slate-800">
              Max file size: 50 MB
            </span>
            <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/60 px-2.5 py-1 rounded border border-cyan-800/40">
              Automated HIPAA Validation
            </span>
          </div>
        </div>
      </Card>

      {/* Live Processing Pipeline Status */}
      {(isProcessing || validationCompleted) && (
        <Card className="border-cyan-900/40">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="flex items-center gap-2 text-cyan-300">
                <ShieldCheck className="w-5 h-5 text-cyan-400" />
                EDI Ingestion & Rule Pipeline Engine
              </CardTitle>
              <CardDescription>
                Progressive schema, NPI registry, and CMS coding validation checks
              </CardDescription>
            </div>
            <span className="text-xs font-mono font-bold text-cyan-400">
              {progress}%
            </span>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Progress bar */}
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div
                className="h-full bg-linear-to-r from-cyan-500 to-blue-500 transition-all duration-300 rounded-full"
                style={{ width: `${progress}%` }}
              />
            </div>

            {/* Checklist */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
              {steps.map((step, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-start gap-2.5"
                >
                  {step.status === 'completed' && (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  )}
                  {step.status === 'in_progress' && (
                    <RefreshCw className="w-4 h-4 text-cyan-400 shrink-0 animate-spin mt-0.5" />
                  )}
                  {step.status === 'error' && (
                    <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  )}
                  {step.status === 'pending' && (
                    <div className="w-4 h-4 rounded-full border border-slate-600 shrink-0 mt-0.5" />
                  )}

                  <div className="flex-1 min-w-0">
                    <span className="text-xs font-medium text-slate-200 block">
                      {step.name}
                    </span>
                    {step.message && (
                      <span className={`text-[11px] mt-0.5 block ${step.status === 'error' ? 'text-rose-400 font-semibold' : 'text-slate-400'}`}>
                        {step.message}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Batch Validation Summary & Extracted Claims */}
      {batchResults && (
        <div className="space-y-6">
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-[11px] text-slate-400 uppercase font-semibold">Total Claims</span>
              <span className="text-xl font-bold font-mono text-white block mt-1">
                {batchResults.totalClaims}
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-800/50">
              <span className="text-[11px] text-emerald-300 uppercase font-semibold">Clean Pass</span>
              <span className="text-xl font-bold font-mono text-emerald-400 block mt-1">
                {batchResults.cleanCount}
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-800/50">
              <span className="text-[11px] text-amber-300 uppercase font-semibold">DQ Warnings</span>
              <span className="text-xl font-bold font-mono text-amber-400 block mt-1">
                {batchResults.flaggedCount}
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/50">
              <span className="text-[11px] text-rose-300 uppercase font-semibold">Hard Rejections</span>
              <span className="text-xl font-bold font-mono text-rose-400 block mt-1">
                {batchResults.rejectedCount}
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 col-span-2 sm:col-span-1">
              <span className="text-[11px] text-slate-400 uppercase font-semibold">Total Billed</span>
              <span className="text-xl font-bold font-mono text-cyan-400 block mt-1">
                {formatCurrency(batchResults.totalBilled)}
              </span>
            </div>
          </div>

          {/* Extracted Claim Records Table */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Batch Extraction & Audit Manifest ({batchResults.filename})</CardTitle>
                <CardDescription>
                  Evaluated claim units ready for ingestion into active adjudication pipeline
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="xs"
                  leftIcon={<Download className="w-3.5 h-3.5" />}
                >
                  Export Manifest
                </Button>
                {batchResults.flaggedCount > 0 && (
                  <Button
                    variant="danger"
                    size="xs"
                    onClick={() => navigate('/incidents')}
                    rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                  >
                    View Incidents ({batchResults.flaggedCount + batchResults.rejectedCount})
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Claim ID</TableHead>
                    <TableHead>Payer & Patient</TableHead>
                    <TableHead>Provider NPI</TableHead>
                    <TableHead>Billed Amount</TableHead>
                    <TableHead>Validation Status</TableHead>
                    <TableHead>Primary DQ Issue / Rule</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {batchResults.claims.map((claim) => (
                    <TableRow key={claim.id}>
                      <TableCell className="font-mono font-bold text-slate-100">
                        {claim.id}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col">
                          <span className="text-slate-200 font-medium">{claim.patient}</span>
                          <span className="text-[11px] text-slate-400">{claim.payer}</span>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-slate-300">
                        {claim.providerNpi}
                      </TableCell>
                      <TableCell className="font-mono font-semibold text-slate-200">
                        {formatCurrency(claim.billed)}
                      </TableCell>
                      <TableCell>
                        {claim.status === 'clean' && (
                          <Badge variant="success" size="sm" dot>Clean Pass</Badge>
                        )}
                        {claim.status === 'flagged' && (
                          <Badge variant="warning" size="sm" dot>DQ Flagged</Badge>
                        )}
                        {claim.status === 'rejected' && (
                          <Badge variant="danger" size="sm" dot>Rejected</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-slate-300 max-w-xs truncate">
                        {claim.issue || <span className="text-slate-400">Validated against all active rules</span>}
                      </TableCell>
                      <TableCell className="text-right">
                        {claim.status !== 'clean' ? (
                          <Button
                            variant="danger"
                            size="xs"
                            onClick={() => navigate(`/investigation/INC-${claim.id.replace('CLM-2026-', '')}`)}
                          >
                            Investigate
                          </Button>
                        ) : (
                          <Button
                            variant="outline"
                            size="xs"
                            onClick={() => navigate('/stream')}
                          >
                            Track Stream
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};
