import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  AlertOctagon,
  ShieldCheck,
  Clock,
  CheckCircle2,
  FileText,
  Layers,
  Activity,
  AlertTriangle,
  RefreshCw,
  Send,
  XCircle,
  FileCode,
  UserCheck,
  Check,
  TrendingDown,
  Info
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import { Modal } from '../components/ui/Modal';
import { mockIncidents } from '../data/mockIncidents';
import { incidentService } from '../services/incidentService';
import { formatCurrency, formatDate, getSeverityColor, getSLAStatusBadge } from '../utils/formatters';

type TabType = 'violations' | 'edi_segments' | 'line_items' | 'root_cause' | 'audit_trail';

export const Investigation: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Find incident by ID (or default to INC-8921)
  const [incident, setIncident] = useState(() => {
    const found = mockIncidents.find((i) => i.id === id || i.claimId === id);
    return found || mockIncidents[0];
  });

  const [activeTab, setActiveTab] = useState<TabType>('violations');
  const [actionModal, setActionModal] = useState<{
    isOpen: boolean;
    type: 'resolve' | 'reprocess' | 'escalate' | 'dismiss';
  }>({ isOpen: false, type: 'resolve' });

  const [resolutionNotes, setResolutionNotes] = useState('');
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const claim = incident.claimDetails;
  const sevColor = getSeverityColor(incident.severity);
  const slaBadge = getSLAStatusBadge(incident.slaStatus);
  const isBreached = incident.slaStatus === 'breached';

  const handleActionConfirm = () => {
    const actionType = actionModal.type;
    let newStatus: 'resolved' | 'reprocessed' | 'escalated' | 'false_positive' = 'resolved';
    let message = '';

    if (actionType === 'resolve') {
      newStatus = 'resolved';
      message = 'Incident marked as Resolved and clean claim authorized for adjudication.';
    } else if (actionType === 'reprocess') {
      newStatus = 'resolved';
      message = 'Claim auto-corrected and queued for immediate re-adjudication.';
    } else if (actionType === 'escalate') {
      newStatus = 'escalated';
      message = 'Ticket escalated to Provider Clearinghouse Relations.';
    } else {
      newStatus = 'false_positive';
      message = 'Flag dismissed as False Positive.';
    }

    const updated = incidentService.updateIncidentStatus(
      incident.id,
      newStatus,
      resolutionNotes || `Action ${actionType.toUpperCase()} triggered by Dr. Sarah Jenkins`
    );

    if (updated) {
      setIncident({ ...updated });
    }

    setActionModal({ isOpen: false, type: 'resolve' });
    setResolutionNotes('');
    setSuccessToast(message);
    setTimeout(() => setSuccessToast(null), 4000);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Back Button & Top Action Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="xs"
            onClick={() => navigate('/incidents')}
            leftIcon={<ArrowLeft className="w-3.5 h-3.5" />}
          >
            Back to Incidents
          </Button>

          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-bold text-cyan-400">{incident.id}</span>
            <span className="text-slate-500">/</span>
            <span className="text-xs font-mono text-slate-300">{incident.claimNumber}</span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {incident.status !== 'resolved' ? (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setActionModal({ isOpen: true, type: 'dismiss' })}
              >
                Dismiss Flag
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setActionModal({ isOpen: true, type: 'escalate' })}
                leftIcon={<Send className="w-3.5 h-3.5 text-amber-400" />}
              >
                Escalate to Provider
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => setActionModal({ isOpen: true, type: 'reprocess' })}
                leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              >
                Auto-Correct & Reprocess
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => setActionModal({ isOpen: true, type: 'resolve' })}
                leftIcon={<Check className="w-3.5 h-3.5" />}
              >
                Mark Resolved
              </Button>
            </>
          ) : (
            <Badge variant="success" size="md" dot>
              Ticket Resolved & Reprocessed
            </Badge>
          )}
        </div>
      </div>

      {/* Success Notification Toast */}
      {successToast && (
        <div className="p-3.5 rounded-xl bg-emerald-950/80 border border-emerald-700 text-emerald-200 text-xs font-medium flex items-center justify-between shadow-lg animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successToast}</span>
          </div>
          <button onClick={() => setSuccessToast(null)} className="text-emerald-400 hover:text-emerald-200 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Incident Header Card */}
      <Card className="border-slate-800 bg-slate-900/90">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1.5 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={sevColor.badge} size="md">
                {incident.severity.toUpperCase()} PRIORITY
              </Badge>
              <Badge variant="neutral" size="md">
                {incident.category.replace('_', ' ').toUpperCase()}
              </Badge>
              <Badge variant={slaBadge.variant} size="md" dot pulse={isBreached || incident.slaStatus === 'at_risk'}>
                {isBreached ? 'SLA BREACHED (-120m)' : `SLA Target: ${incident.slaRemainingMinutes}m left`}
              </Badge>
            </div>
            <h2 className="text-lg font-bold text-white font-heading mt-1">
              {incident.title}
            </h2>
            <p className="text-xs text-slate-300 leading-relaxed max-w-3xl">
              {incident.description}
            </p>
          </div>

          {/* Anomaly Gauge & Financial Impact */}
          <div className="flex items-center gap-4 p-3 rounded-xl bg-slate-950/70 border border-slate-800 self-start lg:self-center">
            <div className="text-center px-2">
              <span className="text-[10px] uppercase font-semibold text-slate-400 block">Anomaly Confidence</span>
              <span className="text-xl font-bold font-mono text-rose-400 mt-0.5 block">
                {(incident.anomalyConfidence * 100).toFixed(0)}%
              </span>
            </div>
            <div className="h-8 w-px bg-slate-800" />
            <div className="text-center px-2">
              <span className="text-[10px] uppercase font-semibold text-slate-400 block">Billed Exposure</span>
              <span className="text-xl font-bold font-mono text-cyan-400 mt-0.5 block">
                {formatCurrency(incident.billedAmount)}
              </span>
            </div>
          </div>
        </div>

        {/* Claim Meta Strip */}
        <div className="mt-4 pt-3.5 border-t border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <span className="text-slate-400 text-[10px] block uppercase">Payer / Plan</span>
            <span className="font-semibold text-slate-200">{incident.payer}</span>
          </div>
          <div>
            <span className="text-slate-400 text-[10px] block uppercase">Patient Name</span>
            <span className="font-semibold text-slate-200">{claim.patientName}</span>
          </div>
          <div>
            <span className="text-slate-400 text-[10px] block uppercase">Provider & NPI</span>
            <span className="font-mono text-slate-200">{claim.providerNpi} ({claim.providerName})</span>
          </div>
          <div>
            <span className="text-slate-400 text-[10px] block uppercase">Date of Service</span>
            <span className="font-mono text-slate-200">{claim.serviceDate}</span>
          </div>
        </div>
      </Card>

      {/* Forensic Navigation Tabs */}
      <div className="border-b border-slate-800 flex items-center gap-2 overflow-x-auto text-xs font-medium">
        <button
          onClick={() => setActiveTab('violations')}
          className={`pb-3 px-3 flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'violations'
              ? 'border-cyan-500 text-cyan-300 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <AlertTriangle className="w-3.5 h-3.5" />
          Rule Violations ({claim.violations.length})
        </button>

        <button
          onClick={() => setActiveTab('edi_segments')}
          className={`pb-3 px-3 flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'edi_segments'
              ? 'border-cyan-500 text-cyan-300 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileCode className="w-3.5 h-3.5" />
          EDI 837 Segment Inspector
        </button>

        <button
          onClick={() => setActiveTab('line_items')}
          className={`pb-3 px-3 flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'line_items'
              ? 'border-cyan-500 text-cyan-300 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          Service Line Items ({claim.lineItems.length})
        </button>

        <button
          onClick={() => setActiveTab('root_cause')}
          className={`pb-3 px-3 flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'root_cause'
              ? 'border-cyan-500 text-cyan-300 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          Root Cause & Impact
        </button>

        <button
          onClick={() => setActiveTab('audit_trail')}
          className={`pb-3 px-3 flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'audit_trail'
              ? 'border-cyan-500 text-cyan-300 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          Audit Trail ({incident.auditTrail.length})
        </button>
      </div>

      {/* Tab Content 1: Rule Violations */}
      {activeTab === 'violations' && (
        <div className="space-y-4">
          {claim.violations.length === 0 ? (
            <Card className="p-8 text-center text-xs text-slate-400">
              No active rule violations recorded on this claim transaction.
            </Card>
          ) : (
            claim.violations.map((violation, idx) => (
              <Card key={idx} className="border-rose-900/50 bg-slate-900/80">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-rose-950 text-rose-400 border border-rose-800/60">
                      <AlertOctagon className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-white">
                        {violation.ruleName}
                      </h4>
                      <span className="font-mono text-xs text-cyan-400 font-medium">
                        {violation.ruleCode}
                      </span>
                    </div>
                  </div>
                  <Badge variant="danger" size="sm">
                    {violation.severity.toUpperCase()}
                  </Badge>
                </div>

                <div className="mt-4 space-y-3 text-xs">
                  <p className="text-slate-200 leading-relaxed font-medium">
                    {violation.message}
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-lg bg-slate-950/60 border border-slate-800 font-mono text-[11px]">
                    <div>
                      <span className="text-slate-400 block text-[10px]">Segment Target</span>
                      <span className="text-cyan-300">{violation.segmentTarget || 'Loop 2000'}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Actual Value Received</span>
                      <span className="text-rose-300">{violation.actualValue || 'Invalid format'}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Expected Compliant Value</span>
                      <span className="text-emerald-300">{violation.expectedValue || 'Standard format'}</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-cyan-950/30 border border-cyan-800/40 text-cyan-200">
                    <span className="font-semibold text-cyan-300 block mb-0.5">Automated Remediation Suggestion:</span>
                    <p className="text-xs">{violation.remediationSuggestion}</p>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Tab Content 2: EDI 837 Segment Inspector */}
      {activeTab === 'edi_segments' && (
        <Card className="bg-slate-950 border-slate-800">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="font-mono text-xs uppercase text-slate-300">
                ANSI ASC X12N 837 Professional / Institutional Segment Stream
              </CardTitle>
              <CardDescription>
                Raw transaction stream with highlighted delimiter syntax and rule failure loops
              </CardDescription>
            </div>
            <span className="text-xs font-mono text-cyan-400">EDI 5010A1</span>
          </CardHeader>
          <CardContent>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 font-mono text-xs text-slate-300 leading-relaxed overflow-x-auto whitespace-pre">
              {claim.rawEdiSnippet || `ISA*00*          *00*          *ZZ*SUBMITTER      *ZZ*RECEIVER       *260818*0140*^*00501*000008921*0*P*:~
GS*HC*SUBMITTER*RECEIVER*20260818*0140*8921*X*005010X222A1~
ST*837*0001*005010X222A1~
BHT*0019*00*${claim.claimNumber}*20260818*0140*CH~
NM1*85*2*METROPOLITAN IMAGING*****XX*${claim.providerNpi}~
CLM*${claim.claimNumber}*${claim.billedAmount.toFixed(2)}***11:B:1*Y*A*Y*Y~
HI*BK:${claim.primaryDiagnosis.split(' ')[0]}~
LX*1~
SV1*HC:99214*185.00*UN*1***1~
SE*12*0001~
GE*1*8921~
IEA*1*000008921~`}
            </div>

            {claim.ediSegments && (
              <div className="mt-4 space-y-2">
                <span className="text-xs font-semibold text-slate-300 block">Parsed Segment Explanations:</span>
                {claim.ediSegments.map((seg, i) => (
                  <div
                    key={i}
                    className={`p-2.5 rounded-lg border text-xs font-mono flex items-center justify-between ${
                      seg.hasError
                        ? 'bg-rose-950/40 border-rose-800/60 text-rose-200'
                        : 'bg-slate-900/50 border-slate-800 text-slate-300'
                    }`}
                  >
                    <div>
                      <span className="font-bold text-white mr-2">[{seg.segmentId}]</span>
                      <span className="text-slate-400 mr-2">{seg.element}:</span>
                      <span>{seg.content}</span>
                    </div>
                    {seg.hasError && (
                      <Badge variant="danger" size="sm">
                        {seg.explanation || 'Rule Violation'}
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tab Content 3: Service Line Items */}
      {activeTab === 'line_items' && (
        <Card>
          <CardHeader>
            <CardTitle>Encounter Service Line Breakdown (Loop 2400)</CardTitle>
            <CardDescription>Individual procedure codes, units, modifiers, and line validation status</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Line #</TableHead>
                  <TableHead>CPT / HCPCS</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Modifiers</TableHead>
                  <TableHead>Units</TableHead>
                  <TableHead>Charge</TableHead>
                  <TableHead>Line Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {claim.lineItems.map((item) => (
                  <TableRow key={item.lineNumber}>
                    <TableCell className="font-mono font-bold text-slate-400">
                      #{item.lineNumber}
                    </TableCell>
                    <TableCell className="font-mono font-bold text-cyan-400">
                      {item.cptCode}
                    </TableCell>
                    <TableCell className="text-xs text-slate-200">
                      {item.cptDescription}
                      {item.notes && (
                        <span className="text-rose-400 text-[11px] block mt-0.5 font-sans">
                          ⚠ {item.notes}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {item.modifiers ? item.modifiers.map((m) => (
                        <span key={m} className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 mr-1 border border-slate-700">
                          {m}
                        </span>
                      )) : '-'}
                    </TableCell>
                    <TableCell className="font-mono text-slate-300">
                      {item.units}
                    </TableCell>
                    <TableCell className="font-mono font-semibold text-white">
                      {formatCurrency(item.charge)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={item.status === 'valid' ? 'success' : item.status === 'warning' ? 'warning' : 'danger'} size="sm">
                        {item.status.toUpperCase()}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Tab Content 4: Root Cause & Impact */}
      {activeTab === 'root_cause' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="border-amber-900/40 bg-slate-900/80">
            <CardHeader>
              <CardTitle className="text-amber-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Root Cause Forensic Diagnosis
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs leading-relaxed text-slate-200">
              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <span className="font-semibold text-slate-400 uppercase text-[10px] block mb-1">Primary Failure Mode</span>
                <p>{incident.rootCauseAnalysis.primaryFailure}</p>
              </div>

              <div>
                <span className="font-semibold text-slate-400 uppercase text-[10px] block mb-1.5">Affected Clearinghouse Subsystems</span>
                <div className="flex flex-wrap gap-1.5">
                  {incident.rootCauseAnalysis.affectedSubsystems.map((sub, i) => (
                    <span key={i} className="px-2 py-1 rounded bg-slate-800 text-cyan-300 font-mono text-[11px] border border-slate-700">
                      {sub}
                    </span>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-rose-900/40 bg-slate-900/80">
            <CardHeader>
              <CardTitle className="text-rose-300 flex items-center gap-2">
                <TrendingDown className="w-4 h-4 text-rose-400" />
                Financial & Statutory Liability Impact
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs leading-relaxed text-slate-200">
              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <span className="font-semibold text-slate-400 uppercase text-[10px] block mb-1">Financial & Regulatory Risk</span>
                <p>{incident.rootCauseAnalysis.impactDescription}</p>
              </div>

              <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/50">
                <span className="font-semibold text-emerald-300 uppercase text-[10px] block mb-1">Recommended Auditor Action</span>
                <p className="text-emerald-200">{incident.rootCauseAnalysis.recommendedFix}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab Content 5: Audit Trail */}
      {activeTab === 'audit_trail' && (
        <Card>
          <CardHeader>
            <CardTitle>Forensic Audit Trail & Event Timeline</CardTitle>
            <CardDescription>Immutable log of automated pipeline evaluations and auditor state transitions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 relative before:absolute before:inset-0 before:left-3 before:w-0.5 before:bg-slate-800">
              {incident.auditTrail.map((log) => (
                <div key={log.id} className="relative flex items-start gap-4 pl-8 text-xs">
                  <div className="absolute left-1.5 top-1.5 w-3.5 h-3.5 rounded-full bg-cyan-500 border-2 border-slate-900 ring-2 ring-cyan-500/20" />
                  <div className="flex-1 p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-white">{log.action}</span>
                      <span className="font-mono text-[10px] text-slate-400">{formatDate(log.timestamp)}</span>
                    </div>
                    <span className="text-[11px] text-cyan-400 font-mono block mt-0.5">Actor: {log.actor}</span>
                    <p className="text-slate-300 mt-1">{log.details}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Action Dialog Modal */}
      <Modal
        isOpen={actionModal.isOpen}
        onClose={() => setActionModal({ isOpen: false, type: 'resolve' })}
        title={
          actionModal.type === 'resolve'
            ? 'Mark Incident as Resolved'
            : actionModal.type === 'reprocess'
            ? 'Auto-Correct EDI & Reprocess Claim'
            : actionModal.type === 'escalate'
            ? 'Escalate to Provider Clearinghouse'
            : 'Dismiss as False Positive'
        }
        description={`Target Incident: ${incident.id} | Claim: ${incident.claimNumber}`}
        footer={
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setActionModal({ isOpen: false, type: 'resolve' })}
            >
              Cancel
            </Button>
            <Button
              variant={actionModal.type === 'resolve' || actionModal.type === 'reprocess' ? 'primary' : 'danger'}
              size="sm"
              onClick={handleActionConfirm}
            >
              Confirm Action
            </Button>
          </>
        }
      >
        <div className="space-y-3 text-xs">
          <p className="text-slate-300">
            {actionModal.type === 'resolve' &&
              'This action will certify that the data quality defect has been mitigated and release the claim to the downstream adjudication gateway.'}
            {actionModal.type === 'reprocess' &&
              'This action will automatically apply recommended segment crosswalk corrections (e.g. CPT combination, NPI lookup) and re-inject into the live adjudication pipeline.'}
            {actionModal.type === 'escalate' &&
              'This action will dispatch an urgent clearinghouse alert to the billing provider relations department.'}
            {actionModal.type === 'dismiss' &&
              'This action will mark the rule violation as a verified false positive with auditor signoff.'}
          </p>

          <div className="space-y-1">
            <label className="font-semibold text-slate-200 block">Auditor Resolution Notes / Signoff:</label>
            <textarea
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder="Enter specific remediation details, clearinghouse reference numbers, or authorization codes..."
              rows={3}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 font-sans"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};
