import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Clock,
  RefreshCw,
  Check,
  XCircle,
  Info,
  Sparkles,
  ShieldAlert,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { DataState, DataCaveat } from '../components/ui/DataState';
import { useAsync } from '../hooks/useAsync';
import { auditApi, hitlApi, incidentsApi, llmApi } from '../services/api';
import { formatCurrency, formatDate } from '../utils/formatters';
import {
  REASON_CATEGORY_LABELS,
  bandForScore,
  pipelineStageLabel,
  scoreBandVariant,
  statusDisplay,
} from '../utils/incidentDisplay';
import type { Incident, ReasonCategory } from '../types/api';

/**
 * Incident forensic view.
 *
 * Four tabs, each backed by a real endpoint:
 *  - Evidence          -> the incident's own `evidence_snapshot`
 *  - Scoring Breakdown -> severity / business-impact / priority components
 *  - Root Cause        -> GET /llm/investigations/{incident_id}
 *  - Audit Trail       -> GET /history/incident/{incident_id} (paginated fetch)
 *
 * The EDI 837 Segment Inspector tab is gone -- the backend reads a CMS RIF
 * file and never sees an EDI transaction, so there was nothing to reshape it
 * into. The old "Rule Violations" and "Service Line Items" tabs are replaced
 * by the two evidence tabs above: the backend models incidents at *window*
 * grain and exposes no per-claim detail endpoint, so a per-line breakdown had
 * no source.
 */
type TabType = 'evidence' | 'scoring' | 'root_cause' | 'audit_trail';

const AUDIT_PAGE_SIZE = 25;

export const Investigation: React.FC = () => {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<TabType>('evidence');
  const [auditPage, setAuditPage] = useState(1);
  const [toast, setToast] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const incident = useAsync(() => incidentsApi.get(id), [id]);
  const investigations = useAsync(() => llmApi.investigations(id), [id]);
  const history = useAsync(
    () => auditApi.history('incident', id, { page: auditPage, page_size: AUDIT_PAGE_SIZE }),
    [id, auditPage]
  );

  // Reject requires all three fields; the modal enforces that before sending.
  const [rejectOpen, setRejectOpen] = useState(false);
  const [acceptOpen, setAcceptOpen] = useState(false);
  const [reviewerId, setReviewerId] = useState('');
  const [reasonCategory, setReasonCategory] = useState<ReasonCategory>('incorrect_root_cause');
  const [feedbackText, setFeedbackText] = useState('');

  const showToast = (message: string) => {
    setToast(message);
    setTimeout(() => setToast(null), 5000);
  };

  const refreshAfterAction = () => {
    incident.reload();
    investigations.reload();
    history.reload();
  };

  const runAction = async (fn: () => Promise<unknown>, successMessage: string) => {
    setBusy(true);
    setActionError(null);
    try {
      await fn();
      showToast(successMessage);
      refreshAfterAction();
      return true;
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const handleAccept = async () => {
    const ok = await runAction(
      () => hitlApi.accept(id, { reviewer_id: reviewerId.trim() }),
      'Incident accepted. Remediation may now proceed.'
    );
    if (ok) {
      setAcceptOpen(false);
      setReviewerId('');
    }
  };

  const handleReject = async () => {
    const ok = await runAction(
      () =>
        hitlApi.reject(id, {
          reviewer_id: reviewerId.trim(),
          reason_category: reasonCategory,
          feedback_text: feedbackText.trim(),
        }),
      'Incident rejected and feedback recorded.'
    );
    if (ok) {
      setRejectOpen(false);
      setReviewerId('');
      setFeedbackText('');
    }
  };

  const handleRecalculate = () =>
    runAction(() => hitlApi.recalculate(id), 'Recalculation complete.');

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div className="flex items-center gap-3 flex-wrap">
          <Button
            variant="outline"
            size="xs"
            onClick={() => navigate('/history')}
            leftIcon={<ArrowLeft className="w-3.5 h-3.5" />}
          >
            Back to History
          </Button>
          <span className="font-mono text-sm font-bold text-cyan-400">{id.slice(0, 8)}</span>
          {incident.data && (
            <span className="text-xs font-mono text-slate-400">
              window {incident.data.window_id}
            </span>
          )}
        </div>

        {incident.data && (
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRecalculate}
              isLoading={busy}
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Recalculate
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => setRejectOpen(true)}
              leftIcon={<XCircle className="w-3.5 h-3.5" />}
            >
              Reject
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setAcceptOpen(true)}
              leftIcon={<Check className="w-3.5 h-3.5" />}
            >
              Accept
            </Button>
          </div>
        )}
      </div>

      {toast && (
        <div className="p-3.5 rounded-xl bg-emerald-950/80 border border-emerald-700 text-emerald-200 text-xs font-medium flex items-center justify-between shadow-lg">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{toast}</span>
          </div>
          <button onClick={() => setToast(null)} className="text-emerald-400 hover:text-emerald-200">
            Dismiss
          </button>
        </div>
      )}

      {actionError && (
        <div className="p-3.5 rounded-xl bg-rose-950/70 border border-rose-700 text-rose-200 text-xs flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <span className="font-mono break-words">{actionError}</span>
        </div>
      )}

      <DataState
        loading={incident.loading}
        error={incident.error}
        notComputed={incident.notComputed}
        label={`Incident ${id.slice(0, 8)}`}
        producedBy="POST /incidents"
      >
        {incident.data && (
          <>
            <IncidentHeaderCard incident={incident.data} />

            {/* Tabs */}
            <div className="border-b border-slate-800 flex items-center gap-2 overflow-x-auto text-xs font-medium">
              {(
                [
                  ['evidence', 'Evidence', <ShieldAlert key="a" className="w-3.5 h-3.5" />],
                  ['scoring', 'Scoring Breakdown', <Activity key="b" className="w-3.5 h-3.5" />],
                  ['root_cause', 'Root Cause (Mistral)', <Sparkles key="c" className="w-3.5 h-3.5" />],
                  ['audit_trail', 'Audit Trail', <Clock key="d" className="w-3.5 h-3.5" />],
                ] as const
              ).map(([key, label, icon]) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key as TabType)}
                  className={`pb-3 px-3 flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                    activeTab === key
                      ? 'border-cyan-500 text-cyan-300 font-semibold'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {icon}
                  {label}
                  {key === 'audit_trail' && history.data?.found && ` (${history.data.total_count})`}
                </button>
              ))}
            </div>

            {activeTab === 'evidence' && <EvidenceTab incident={incident.data} />}
            {activeTab === 'scoring' && <ScoringTab incident={incident.data} />}

            {activeTab === 'root_cause' && (
              <DataState
                loading={investigations.loading}
                error={investigations.error}
                notComputed={investigations.notComputed}
                label="LLM investigation"
                producedBy="POST /llm/investigate"
              >
                {investigations.data && <RootCauseTab data={investigations.data} />}
              </DataState>
            )}

            {activeTab === 'audit_trail' && (
              <DataState
                loading={history.loading}
                error={history.error}
                notComputed={history.notComputed}
                label="Audit trail"
                producedBy="Written at each pipeline stage"
              >
                {history.data && (
                  <AuditTrailTab
                    data={history.data}
                    page={auditPage}
                    onPageChange={setAuditPage}
                  />
                )}
              </DataState>
            )}
          </>
        )}
      </DataState>

      {/* Accept modal */}
      <Modal
        isOpen={acceptOpen}
        onClose={() => setAcceptOpen(false)}
        title="Accept Recommendation"
        description={`Incident ${id.slice(0, 8)}`}
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setAcceptOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleAccept}
              isLoading={busy}
              disabled={!reviewerId.trim()}
            >
              Confirm Accept
            </Button>
          </>
        }
      >
        <div className="space-y-3 text-xs">
          <p className="text-slate-300">
            Accepting records a human decision and allows the constrained remediation engine to run
            against the affected claims. The LLM never executes a fix itself.
          </p>
          <LabelledInput
            label="Reviewer ID"
            required
            value={reviewerId}
            onChange={setReviewerId}
            placeholder="e.g. reviewer-01"
          />
        </div>
      </Modal>

      {/* Reject modal -- all three fields are required by the backend */}
      <Modal
        isOpen={rejectOpen}
        onClose={() => setRejectOpen(false)}
        title="Reject Recommendation"
        description={`Incident ${id.slice(0, 8)}`}
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setRejectOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleReject}
              isLoading={busy}
              disabled={!reviewerId.trim() || !feedbackText.trim()}
            >
              Confirm Reject
            </Button>
          </>
        }
      >
        <div className="space-y-3 text-xs">
          <p className="text-slate-300">
            Rejecting captures feedback for future retraining. The backend requires a reviewer, a
            reason category, and non-empty feedback text.
          </p>

          <LabelledInput
            label="Reviewer ID"
            required
            value={reviewerId}
            onChange={setReviewerId}
            placeholder="e.g. reviewer-01"
          />

          <div className="space-y-1">
            <label className="font-semibold text-slate-200 block">
              Reason category <span className="text-rose-400">*</span>
            </label>
            <select
              value={reasonCategory}
              onChange={(e) => setReasonCategory(e.target.value as ReasonCategory)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-100 focus:outline-none focus:border-cyan-500"
            >
              {Object.entries(REASON_CATEGORY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="font-semibold text-slate-200 block">
              Feedback <span className="text-rose-400">*</span>
            </label>
            <textarea
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              placeholder="Why is the recommendation wrong? This is stored for future retraining."
              rows={4}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

// --- pieces ---

const LabelledInput: React.FC<{
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
}> = ({ label, value, onChange, placeholder, required }) => (
  <div className="space-y-1">
    <label className="font-semibold text-slate-200 block">
      {label} {required && <span className="text-rose-400">*</span>}
    </label>
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
    />
  </div>
);

const IncidentHeaderCard: React.FC<{ incident: Incident }> = ({ incident }) => {
  const priority = incident.priority_result?.priority ?? 0;
  const status = statusDisplay(incident.status);
  const exposure = (incident.evidence_snapshot?.affected_claims_amounts ?? []).reduce(
    (a, b) => a + b,
    0
  );

  return (
    <Card className="border-slate-800 bg-slate-900/90">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="space-y-1.5 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={scoreBandVariant(bandForScore(priority))} size="md">
              PRIORITY {priority.toFixed(1)}
            </Badge>
            <Badge variant={status.variant} size="md" dot>
              {status.label}
            </Badge>
          </div>
          <h2 className="text-lg font-bold text-white font-heading mt-1">
            Window {incident.window_id}
          </h2>
          <p className="text-xs text-slate-300 leading-relaxed max-w-3xl">{status.meaning}</p>
        </div>

        <div className="flex items-center gap-4 p-3 rounded-xl bg-slate-950/70 border border-slate-800 self-start lg:self-center">
          <ScoreStat label="Severity" value={incident.severity_result?.severity ?? 0} tone="text-rose-400" />
          <div className="h-8 w-px bg-slate-800" />
          <ScoreStat label="Risk" value={incident.risk_score} tone="text-amber-400" />
          <div className="h-8 w-px bg-slate-800" />
          <ScoreStat label="Quality" value={incident.quality_score} tone="text-emerald-400" />
        </div>
      </div>

      <div className="mt-4 pt-3.5 border-t border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <Meta label="Anomaly Score" value={incident.anomaly_score.toFixed(2)} />
        <Meta
          label="Affected Claims"
          value={`${((incident.evidence_snapshot?.affected_claim_pct ?? 0) * 100).toFixed(1)}%`}
        />
        <Meta label="Dollar Exposure" value={exposure > 0 ? formatCurrency(exposure) : 'n/a'} />
        <Meta label="Created" value={formatDate(incident.created_at)} />
      </div>
    </Card>
  );
};

const ScoreStat: React.FC<{ label: string; value: number; tone: string }> = ({
  label,
  value,
  tone,
}) => (
  <div className="text-center px-2">
    <span className="text-[10px] uppercase font-semibold text-slate-400 block">{label}</span>
    <span className={`text-xl font-bold font-mono mt-0.5 block ${tone}`}>{value.toFixed(1)}</span>
  </div>
);

const Meta: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div>
    <span className="text-slate-400 text-[10px] block uppercase">{label}</span>
    <span className="font-mono text-slate-200">{value}</span>
  </div>
);

/** Window/incident-level evidence -- the real replacement for "Rule Violations". */
const EvidenceTab: React.FC<{ incident: Incident }> = ({ incident }) => {
  const ev = incident.evidence_snapshot ?? {};
  const bands = ev.quality_check_bands ?? [];
  const counts = bands.reduce<Record<string, number>>((acc, b) => {
    acc[b] = (acc[b] ?? 0) + 1;
    return acc;
  }, {});
  const amounts = ev.affected_claims_amounts ?? [];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            Quality Check Evidence
          </CardTitle>
          <CardDescription>
            Great Expectations bands recorded on this window at incident creation
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          {bands.length === 0 ? (
            <p className="text-slate-400">
              No quality check bands were captured in this incident's evidence snapshot.
            </p>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              {(['CRITICAL', 'WARNING', 'PASS'] as const).map((band) => (
                <div
                  key={band}
                  className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-center"
                >
                  <span className="text-[10px] uppercase text-slate-400 block">{band}</span>
                  <span
                    className={`text-lg font-bold font-mono ${
                      band === 'CRITICAL'
                        ? 'text-rose-400'
                        : band === 'WARNING'
                        ? 'text-amber-400'
                        : 'text-emerald-400'
                    }`}
                  >
                    {counts[band] ?? 0}
                  </span>
                </div>
              ))}
            </div>
          )}

          <DataCaveat>
            The evidence snapshot stores the band of each contributing check, not the individual
            check records. There is no per-claim detail endpoint in the backend, so this is the
            finest grain available here.
          </DataCaveat>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            Anomaly &amp; Exposure Evidence
          </CardTitle>
          <CardDescription>Window-grain anomaly signal and affected-claim amounts</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          <div className="grid grid-cols-2 gap-2">
            <Stat
              label="Anomaly percentile"
              value={(ev.anomaly_score_percentile ?? 0).toFixed(2)}
            />
            <Stat
              label="Affected claims"
              value={`${((ev.affected_claim_pct ?? 0) * 100).toFixed(1)}%`}
            />
            <Stat label="Claims with amounts" value={String(amounts.length)} />
            <Stat
              label="Total exposure"
              value={amounts.length ? formatCurrency(amounts.reduce((a, b) => a + b, 0)) : 'n/a'}
            />
          </div>

          {ev.baseline_amount_percentiles && (
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-[10px] uppercase text-slate-400 block mb-1.5">
                Baseline amount percentiles used
              </span>
              <div className="grid grid-cols-5 gap-2 font-mono text-[11px]">
                {(['p25', 'p50', 'p75', 'p95', 'p99'] as const).map((k) => (
                  <div key={k}>
                    <span className="text-slate-500 block text-[10px]">{k}</span>
                    <span className="text-slate-200">
                      {formatCurrency(ev.baseline_amount_percentiles![k])}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

const Stat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
    <span className="text-[10px] uppercase text-slate-400 block">{label}</span>
    <span className="text-sm font-bold font-mono text-slate-100">{value}</span>
  </div>
);

/** Severity / business impact / priority components, all real computed values. */
const ScoringTab: React.FC<{ incident: Incident }> = ({ incident }) => {
  const sev = incident.severity_result;
  const impact = incident.business_impact_result;
  const priority = incident.priority_result;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Severity Components</CardTitle>
            <CardDescription>
              Weighted quality-failure, anomaly-magnitude, and materiality scores
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2.5 text-xs">
            <ComponentBar label="Quality failure severity" value={sev?.quality_failure_severity ?? 0} />
            <ComponentBar label="Anomaly magnitude" value={sev?.anomaly_magnitude_score ?? 0} />
            <ComponentBar label="Materiality" value={sev?.materiality_score ?? 0} />
            <WeightsRow weights={sev?.weights_used} />
            <div className="pt-2 mt-2 border-t border-slate-800 flex items-center justify-between">
              <span className="text-slate-300 font-semibold">Severity</span>
              <span className="font-mono font-bold text-rose-400 text-base">
                {(sev?.severity ?? 0).toFixed(2)}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Business Impact</CardTitle>
            <CardDescription>
              Computed only from measurable claim-amount fields
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2.5 text-xs">
            {(impact?.components ?? []).map((c) => (
              <div
                key={c.name}
                className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-start justify-between gap-3"
              >
                <div className="min-w-0">
                  <span className="text-slate-200 font-medium block">
                    {c.name.replace(/_/g, ' ')}
                  </span>
                  {c.status === 'unavailable' && c.reason && (
                    <span className="text-[11px] text-amber-300/90 block mt-0.5 leading-snug">
                      {c.reason}
                    </span>
                  )}
                </div>
                {c.status === 'computed' ? (
                  <span className="font-mono text-slate-100 shrink-0">
                    {(c.value ?? 0).toFixed(2)}
                  </span>
                ) : (
                  <Badge variant="warning" size="sm">
                    unavailable
                  </Badge>
                )}
              </div>
            ))}

            <div className="pt-2 mt-2 border-t border-slate-800 flex items-center justify-between">
              <span className="text-slate-300 font-semibold">Business Impact</span>
              <span className="font-mono font-bold text-cyan-400 text-base">
                {(impact?.business_impact ?? 0).toFixed(2)}
              </span>
            </div>

            {impact?.has_unavailable_components && (
              <DataCaveat>
                Some impact components cannot be computed from this dataset and are marked
                unavailable rather than defaulted to zero.
              </DataCaveat>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Priority Composition</CardTitle>
          <CardDescription>
            Four non-overlapping signals combined with configurable weights
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2.5 text-xs">
          <ComponentBar label="Severity" value={priority?.severity ?? 0} />
          <ComponentBar label="Risk" value={priority?.risk ?? 0} />
          <ComponentBar label="Business impact" value={priority?.business_impact ?? 0} />
          <ComponentBar label="Affected claims score" value={priority?.affected_claims_score ?? 0} />
          <WeightsRow weights={priority?.weights_used} />
          <div className="pt-2 mt-2 border-t border-slate-800 flex items-center justify-between">
            <span className="text-slate-300 font-semibold">Final Priority</span>
            <span className="font-mono font-bold text-white text-lg">
              {(priority?.priority ?? 0).toFixed(2)}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const ComponentBar: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div className="space-y-1">
    <div className="flex items-center justify-between">
      <span className="text-slate-300">{label}</span>
      <span className="font-mono text-slate-100">{value.toFixed(2)}</span>
    </div>
    <div className="h-2.5 w-full rounded-full overflow-hidden bg-slate-800/60">
      <div
        className="h-full bg-linear-to-r from-cyan-600 to-cyan-400"
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  </div>
);

const WeightsRow: React.FC<{ weights?: Record<string, number> }> = ({ weights }) =>
  weights && Object.keys(weights).length > 0 ? (
    <div className="flex flex-wrap gap-1.5 pt-1">
      {Object.entries(weights).map(([k, v]) => (
        <span
          key={k}
          className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px] border border-slate-700"
        >
          {k}={v}
        </span>
      ))}
    </div>
  ) : null;

/** Full Mistral output -- every field the backend returns, not a 4-field subset. */
const RootCauseTab: React.FC<{
  data: import('../types/api').InvestigationHistoryResponse;
}> = ({ data }) => {
  const latest = data.investigations[data.investigations.length - 1];

  if (!latest) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-xs text-slate-400 space-y-2">
          <p>No LLM investigation has been generated for this incident yet.</p>
          {data.failures.length > 0 && (
            <div className="mt-4 text-left space-y-2">
              <span className="text-slate-300 font-semibold">Recorded failures:</span>
              {data.failures.map((f) => (
                <div
                  key={f.failure_id}
                  className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-200"
                >
                  <span className="font-mono text-[11px]">{f.failure_type}</span> — {f.error_detail}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {latest.insufficient_evidence && (
        <div className="p-3.5 rounded-xl bg-amber-950/50 border border-amber-700/60 text-amber-200 text-xs flex items-start gap-2">
          <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <span>
            The model reported <strong>insufficient evidence</strong> to determine a root cause. It
            is required to say so rather than guess — treat the sections below as partial.
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Section title="Summary" body={latest.summary} tone="cyan" />
        <Section title="Likely Root Cause" body={latest.likely_root_cause} tone="amber" />
        <Section title="Evidence" body={latest.evidence} tone="slate" />
        <Section title="Business Impact" body={latest.business_impact_narrative} tone="rose" />
        <Section title="Recommended Fix" body={latest.recommended_fix} tone="emerald" />
        <Section
          title="Prevention Recommendation"
          body={latest.prevention_recommendation}
          tone="purple"
        />
      </div>

      <Card>
        <CardContent className="text-[11px] font-mono text-slate-400 flex flex-wrap gap-x-6 gap-y-1 pt-4">
          <span>
            investigation <span className="text-slate-200">{latest.investigation_id.slice(0, 8)}</span>
          </span>
          <span>
            model <span className="text-slate-200">{latest.model_version}</span>
          </span>
          <span>
            generated <span className="text-slate-200">{formatDate(latest.generated_at)}</span>
          </span>
          <span>
            revision{' '}
            <span className="text-slate-200">
              {data.investigations.length} of {data.investigations.length}
            </span>
          </span>
        </CardContent>
      </Card>

      {data.failures.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-rose-300">Investigation Failures</CardTitle>
            <CardDescription>Recorded attempts that did not produce output</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            {data.failures.map((f) => (
              <div
                key={f.failure_id}
                className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-200"
              >
                <span className="font-mono text-[11px]">{f.failure_type}</span> — {f.error_detail}
                <span className="text-[10px] text-rose-300/70 block mt-0.5">
                  {formatDate(f.occurred_at)}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

const TONES: Record<string, string> = {
  cyan: 'border-cyan-900/50 text-cyan-300',
  amber: 'border-amber-900/50 text-amber-300',
  rose: 'border-rose-900/50 text-rose-300',
  emerald: 'border-emerald-900/50 text-emerald-300',
  purple: 'border-purple-900/50 text-purple-300',
  slate: 'border-slate-800 text-slate-300',
};

const Section: React.FC<{ title: string; body: string; tone: string }> = ({ title, body, tone }) => (
  <Card className={`bg-slate-900/80 ${TONES[tone].split(' ')[0]}`}>
    <CardHeader>
      <CardTitle className={TONES[tone].split(' ')[1]}>{title}</CardTitle>
    </CardHeader>
    <CardContent>
      <p className="text-xs leading-relaxed text-slate-200 whitespace-pre-wrap">
        {body || <span className="text-slate-500 italic">Not provided.</span>}
      </p>
    </CardContent>
  </Card>
);

/** Real paginated fetch against /history/incident/{id}. */
const AuditTrailTab: React.FC<{
  data: import('../types/api').HistoryQueryResult;
  page: number;
  onPageChange: (p: number) => void;
}> = ({ data, page, onPageChange }) => {
  const totalPages = Math.max(1, Math.ceil(data.total_count / Math.max(1, data.page_size)));

  if (!data.found) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-xs text-slate-400">
          This incident has no audit history yet. Entries are written by each pipeline stage at the
          moment it acts, so a trail appears once the incident has been investigated or actioned.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Audit Trail</CardTitle>
          <CardDescription>
            {data.total_count} entr{data.total_count === 1 ? 'y' : 'ies'} across every pipeline stage
          </CardDescription>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <Button
            variant="outline"
            size="xs"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
          >
            Prev
          </Button>
          <span className="font-mono text-slate-400">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="xs"
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
          >
            Next
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-4 relative before:absolute before:inset-0 before:left-3 before:w-0.5 before:bg-slate-800">
          {data.entries.map((entry) => (
            <div key={entry.entry_id} className="relative flex items-start gap-4 pl-8 text-xs">
              <div className="absolute left-1.5 top-1.5 w-3.5 h-3.5 rounded-full bg-cyan-500 border-2 border-slate-900 ring-2 ring-cyan-500/20" />
              <div className="flex-1 p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <span className="font-semibold text-white">
                    {pipelineStageLabel(entry.pipeline_stage)}
                  </span>
                  <span className="font-mono text-[10px] text-slate-400">
                    #{entry.sequence_number} · {formatDate(entry.occurred_at)}
                  </span>
                </div>
                <span className="text-[11px] text-cyan-400 font-mono block mt-0.5">
                  {entry.source_module} → {entry.source_record_id.slice(0, 12)}
                </span>
                {entry.baseline_snapshot_id_used && (
                  <span className="text-[10px] text-slate-400 font-mono block mt-0.5">
                    baseline {entry.baseline_snapshot_id_used.slice(0, 8)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        <DataCaveat>
          Entries reference the owning module's own record rather than copying its content, so this
          trail cannot drift from the source of truth.
        </DataCaveat>
      </CardContent>
    </Card>
  );
};

export default Investigation;
