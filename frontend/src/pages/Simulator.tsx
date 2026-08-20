import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Play,
  UploadCloud,
  Layers,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  FileWarning,
  Activity,
  Sparkles,
  Info,
} from 'lucide-react';

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { demoApi } from '../services/api';
import { injectionTypeLabel, bandForScore, scoreBandVariant } from '../utils/incidentDisplay';
import { formatNumber } from '../utils/formatters';
import type {
  BatchManifestEntry,
  PipelineRunResult,
  SimulationStatus,
} from '../types/api';

/**
 * The Simulator drives the whole demo: it picks one of the three synthetic
 * batches, streams it in at a fixed interval, optionally injects fresh
 * anomalies on the way in, and fires the real pipeline when the last chunk
 * lands. The upload control lives here too rather than on a page of its own,
 * because an uploaded file is just another way to feed the same pipeline.
 *
 * Nothing on this page fabricates a number: the progress readout is the
 * backend's own run state, and the results panel is the pipeline's real
 * output (`PipelineRunResult`).
 */

const POLL_INTERVAL_MS = 1500;
const TERMINAL_STATES = new Set(['complete', 'failed']);

const STATE_LABEL: Record<string, string> = {
  queued: 'Queued',
  ingesting: 'Ingesting',
  analyzing: 'Analyzing',
  complete: 'Complete',
  failed: 'Failed',
};

export const Simulator: React.FC = () => {
  const navigate = useNavigate();

  const [batches, setBatches] = React.useState<BatchManifestEntry[] | null>(null);
  const [batchesError, setBatchesError] = React.useState<string | null>(null);
  const [selectedBatch, setSelectedBatch] = React.useState<string>('');
  const [injectAnomalies, setInjectAnomalies] = React.useState(false);

  const [status, setStatus] = React.useState<SimulationStatus | null>(null);
  const [startError, setStartError] = React.useState<string | null>(null);

  const [uploadBusy, setUploadBusy] = React.useState(false);
  const [uploadError, setUploadError] = React.useState<string | null>(null);
  const [uploadResult, setUploadResult] = React.useState<PipelineRunResult | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    demoApi
      .batches()
      .then((entries) => {
        setBatches(entries);
        setSelectedBatch((current) => current || entries[0]?.batch_id || '');
      })
      .catch((error: Error) => setBatchesError(error.message));
  }, []);

  /* Poll the run until it reaches a terminal state.
   *
   * A poll failure (most commonly "Unknown simulation run" -- the backend's
   * run state is in-process and doesn't survive a restart) used to only set
   * `startError` and leave `status.state` untouched. Since that state was
   * never one of TERMINAL_STATES, this effect's dependency on `status`
   * never changed and the same interval kept firing indefinitely, re-polling
   * a run that will never come back. A failed poll is now folded into
   * `status` itself as a terminal `failed` state, which both stops the
   * interval (this effect re-runs, sees TERMINAL_STATES, returns early) and
   * shows the failure in the run card instead of silently repeating. */
  React.useEffect(() => {
    if (!status || TERMINAL_STATES.has(status.state)) return;
    const timer = window.setInterval(() => {
      demoApi
        .simulationStatus(status.run_id)
        .then(setStatus)
        .catch((error: Error) => {
          setStartError(error.message);
          setStatus((current) =>
            current
              ? {
                  ...current,
                  state: 'failed',
                  error: error.message,
                  message: 'Lost track of this run — see the error below.',
                  updated_at: new Date().toISOString(),
                }
              : current
          );
        });
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [status]);

  const running = status !== null && !TERMINAL_STATES.has(status.state);

  const startRun = async () => {
    setStartError(null);
    setUploadResult(null);
    try {
      setStatus(await demoApi.startSimulation(selectedBatch, injectAnomalies));
    } catch (error) {
      setStartError((error as Error).message);
    }
  };

  const onFileChosen = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploadBusy(true);
    setUploadError(null);
    setUploadResult(null);
    setStatus(null);
    try {
      setUploadResult(await demoApi.upload(file));
    } catch (error) {
      setUploadError((error as Error).message);
    } finally {
      setUploadBusy(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const activeBatch = batches?.find((batch) => batch.batch_id === selectedBatch) ?? null;
  const result = status?.result ?? uploadResult;
  const progressPct =
    status && status.claims_total > 0
      ? Math.min(100, (status.claims_ingested / status.claims_total) * 100)
      : 0;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* ---------------- header ---------------- */}
      <div className="flex flex-col gap-4 pb-2 border-b border-slate-800/80 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white font-heading sm:text-2xl">
            Ingestion Simulator
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Stream a synthetic batch in at a fixed interval, or upload a claims file. Either way the
            full pipeline runs on completion and the results land on the dashboard.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => navigate('/history')}>
          View incident history
        </Button>
      </div>

      {/* ---------------- controls ---------------- */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-cyan-950/80 border border-cyan-800/50 text-cyan-400">
                <Layers className="w-4 h-4" />
              </div>
              <CardTitle>Synthetic batch</CardTitle>
            </div>
            <CardDescription className="mt-1">
              Three generated batches with different volumes, amount distributions and injected
              issue profiles.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {batchesError && (
              <p className="text-xs text-rose-300 bg-rose-950/40 border border-rose-900/60 rounded-lg p-3">
                {batchesError}
              </p>
            )}

            {!batches && !batchesError && (
              <p className="text-xs text-slate-400 flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading batches (generating them on
                first run)...
              </p>
            )}

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {(batches ?? []).map((batch) => {
                const isActive = batch.batch_id === selectedBatch;
                return (
                  <button
                    key={batch.batch_id}
                    disabled={running}
                    onClick={() => setSelectedBatch(batch.batch_id)}
                    className={`text-left p-3 rounded-xl border transition-colors disabled:opacity-60 ${
                      isActive
                        ? 'bg-cyan-600/10 border-cyan-500/40'
                        : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-slate-100">{batch.label}</span>
                      <span className="text-[10px] font-mono text-slate-400">{batch.batch_id}</span>
                    </div>
                    <p className="mt-1 text-[11px] text-slate-400 leading-relaxed">
                      {batch.description}
                    </p>
                    <div className="mt-2 grid grid-cols-2 gap-1 text-[10px] text-slate-400 font-mono">
                      <span>{formatNumber(batch.rows)} rows</span>
                      <span>{formatNumber(batch.injected_rows)} injected</span>
                      <span>{batch.missing_cell_pct.toFixed(1)}% null cells</span>
                      <span>{formatNumber(batch.duplicate_rows)} dup rows</span>
                    </div>
                  </button>
                );
              })}
            </div>

            {activeBatch && (
              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                  Injected ground truth in {activeBatch.batch_id}
                </span>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {Object.entries(activeBatch.injected_counts).map(([type, count]) => (
                    <span
                      key={type}
                      className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300"
                    >
                      {injectionTypeLabel(type)} &times;{count}
                    </span>
                  ))}
                </div>
                <p className="mt-2 text-[10px] text-slate-500">
                  {activeBatch.date_from} to {activeBatch.date_to} &middot; median paid amount{' '}
                  {activeBatch.clm_pmt_amt_median.toFixed(2)}
                </p>
              </div>
            )}

            <label className="flex items-start gap-3 p-3 rounded-lg bg-slate-950/60 border border-slate-800 cursor-pointer">
              <input
                type="checkbox"
                checked={injectAnomalies}
                disabled={running}
                onChange={(event) => setInjectAnomalies(event.target.checked)}
                className="mt-0.5 accent-cyan-500"
              />
              <span>
                <span className="text-xs font-semibold text-slate-100 flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  Inject anomalies at simulation time
                </span>
                <span className="block mt-1 text-[11px] text-slate-400 leading-relaxed">
                  Off: detection runs on the batch exactly as generated. On: the generator injects a
                  fresh cluster (missing-value, duplicate and amount spikes) plus a thin background
                  of volume drops and distribution shifts, live, on top of what is already there.
                </span>
              </span>
            </label>

            <div className="flex items-center gap-3">
              <Button
                variant="primary"
                size="sm"
                onClick={startRun}
                isLoading={running}
                disabled={running || !selectedBatch || uploadBusy}
                leftIcon={<Play className="w-3.5 h-3.5" />}
              >
                Run Simulation
              </Button>
              <span className="text-[11px] text-slate-500">
                Streams in {status?.chunk_total ?? 8} chunks, one every{' '}
                {status?.chunk_interval_seconds ?? 4}s.
              </span>
            </div>

            {startError && (
              <p className="text-xs text-rose-300 bg-rose-950/40 border border-rose-900/60 rounded-lg p-3">
                {startError}
              </p>
            )}
          </CardContent>
        </Card>

        {/* ---------------- upload ---------------- */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-emerald-950/80 border border-emerald-800/50 text-emerald-400">
                <UploadCloud className="w-4 h-4" />
              </div>
              <CardTitle>Upload a claims file</CardTitle>
            </div>
            <CardDescription className="mt-1">
              Validated against the claims schema, then run through the identical pipeline.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.txt"
              onChange={onFileChosen}
              disabled={uploadBusy || running}
              className="block w-full text-[11px] text-slate-400 file:mr-3 file:rounded-lg file:border file:border-slate-700 file:bg-slate-900 file:px-3 file:py-1.5 file:text-xs file:text-slate-200 hover:file:border-slate-600 disabled:opacity-60"
            />
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Comma- or pipe-delimited, one row per claim, carrying all 197 columns of the cleaned
              claims schema. A mismatch is rejected with the specific columns that are wrong.
            </p>

            {uploadBusy && (
              <p className="text-xs text-slate-300 flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Validating and running the
                pipeline...
              </p>
            )}

            {uploadError && (
              <div className="text-xs text-rose-300 bg-rose-950/40 border border-rose-900/60 rounded-lg p-3 flex gap-2">
                <FileWarning className="w-4 h-4 shrink-0 mt-0.5" />
                <span className="leading-relaxed">{uploadError}</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ---------------- live progress ---------------- */}
      {status && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-md bg-slate-900 border border-slate-800 text-cyan-400">
                  <Activity className="w-4 h-4" />
                </div>
                <CardTitle>
                  Run {status.batch_label} &middot; {status.batch_id}
                </CardTitle>
              </div>
              <Badge
                variant={
                  status.state === 'complete'
                    ? 'success'
                    : status.state === 'failed'
                    ? 'danger'
                    : 'info'
                }
                size="sm"
              >
                {STATE_LABEL[status.state] ?? status.state}
              </Badge>
            </div>
            <CardDescription className="mt-1">
              Anomaly injection {status.inject_anomalies ? 'on' : 'off'} &middot; run id{' '}
              <span className="font-mono">{status.run_id.slice(0, 8)}</span>
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-3">
            <div className="h-2.5 w-full rounded-full overflow-hidden bg-slate-800/60">
              <div
                className="h-full bg-linear-to-r from-cyan-600 to-cyan-400 transition-all duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-center">
              <Metric label="Chunk" value={`${status.chunk_index} / ${status.chunk_total}`} />
              <Metric
                label="Claims ingested"
                value={`${formatNumber(status.claims_ingested)} / ${formatNumber(status.claims_total)}`}
              />
              <Metric label="Current window" value={status.current_window ?? '--'} />
              <Metric label="Interval" value={`${status.chunk_interval_seconds}s`} />
            </div>
            <p className="text-xs text-slate-300 flex items-start gap-2">
              {status.state === 'complete' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              ) : status.state === 'failed' ? (
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              ) : (
                <Loader2 className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5 animate-spin" />
              )}
              <span className="leading-relaxed">{status.message}</span>
            </p>
            {status.error && (
              <p className="text-xs text-rose-300 bg-rose-950/40 border border-rose-900/60 rounded-lg p-3 font-mono">
                {status.error}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* ---------------- results ---------------- */}
      {result && <RunResult result={result} onOpenHistory={() => navigate('/history')} />}
    </div>
  );
};

const Metric: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800/80">
    <span className="text-[10px] text-slate-400 uppercase tracking-wider block">{label}</span>
    <span className="text-sm font-bold text-white font-mono">{value}</span>
  </div>
);

const RunResult: React.FC<{ result: PipelineRunResult; onOpenHistory: () => void }> = ({
  result,
  onOpenHistory,
}) => {
  const perType = Object.entries(result.anomaly.per_injection_type);
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle>Pipeline result &mdash; {result.batch_label}</CardTitle>
            <CardDescription className="mt-1">
              {formatNumber(result.rows)} rows, {formatNumber(result.claims)} distinct claims
              &middot; source <span className="font-mono">{result.source}</span>
              {result.injection_applied ? ' · live injection applied' : ''}
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={onOpenHistory}>
            See incidents
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric label="Quality score" value={result.quality_composite_score.toFixed(1)} />
          <Metric label="Detection F1" value={result.anomaly.f1.toFixed(3)} />
          <Metric label="False-positive rate" value={result.anomaly.fpr.toFixed(3)} />
          <Metric label="Incidents created" value={String(result.incident_ids.length)} />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
              Isolation Forest, per injection type
            </span>
            <div className="mt-2 space-y-1.5">
              {perType.length === 0 && (
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  No per-type breakdown: this run had no injected ground truth to measure recall
                  against (uploaded files carry no injection labels).
                </p>
              )}
              {perType.map(([type, metrics]) => (
                <div key={type} className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-300">{injectionTypeLabel(type)}</span>
                  <span className="font-mono text-amber-300">
                    R {metrics.recall.toFixed(2)} &middot; P {metrics.precision.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-2 text-[10px] text-slate-500">
              Trained on {formatNumber(result.anomaly.train_rows)} clean claims; evaluated on{' '}
              {formatNumber(result.anomaly.eval_rows)} held-out claims of which{' '}
              {formatNumber(result.anomaly.injected_eval_rows)} were injected.
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
              XGBoost risk score by window
            </span>
            <div className="mt-2 space-y-1.5 max-h-52 overflow-y-auto pr-1">
              {result.windows.map((window) => {
                const band = bandForScore(window.risk_score);
                return (
                  <div key={window.window_id} className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-300 font-mono">{window.window_id}</span>
                    <span className="flex items-center gap-2">
                      <span className="text-slate-500">
                        {window.anomaly_claim_count}/{window.claim_count} flagged
                      </span>
                      <Badge variant={scoreBandVariant(band)} size="sm">
                        {window.risk_score.toFixed(0)} {band}
                      </Badge>
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {result.investigations.length > 0 && (
          <div className="pt-1">
            <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-950/30 border border-amber-800/50 text-[11px] text-amber-200 mb-3">
              <Info className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-400" />
              <span>
                These are generated by <span className="font-mono">{result.investigations[0].model_version}</span> —
                a deterministic per-anomaly-type template filled in with this run's real numbers, not a
                live Mistral call. The wording is fixed; every number inside it is real.
              </span>
            </div>

            <div className="space-y-3">
              {result.investigations.map((inv) => (
                <div
                  key={inv.investigation_id}
                  className="p-3 rounded-lg bg-slate-950/60 border border-slate-800"
                >
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <span className="text-[11px] font-mono text-cyan-400 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" />
                      window {inv.evidence_snapshot_id}
                    </span>
                    {inv.insufficient_evidence && (
                      <Badge variant="warning" size="sm">
                        insufficient evidence
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-slate-200 leading-relaxed mb-1.5">{inv.summary}</p>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    <span className="text-slate-300 font-semibold">Root cause: </span>
                    {inv.likely_root_cause}
                  </p>
                  <p className="text-[11px] text-slate-400 leading-relaxed mt-1">
                    <span className="text-slate-300 font-semibold">Recommended fix: </span>
                    {inv.recommended_fix}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default Simulator;
