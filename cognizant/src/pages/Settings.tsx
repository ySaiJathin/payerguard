import React, { useState } from 'react';
import {
  Settings as SettingsIcon,
  Shield,
  Clock,
  Sliders,
  Bell,
  CheckCircle2,
  Save,
  Server,
  Layers,
  ToggleLeft,
  ToggleRight,
  Database
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { mockDQRules, mockSLAPolicies } from '../data/mockRules';
import { DQRuleConfig, SLAPolicyConfig } from '../types';

type SettingsTab = 'sla' | 'rules' | 'gateways' | 'notifications';

export const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('sla');
  const [slaPolicies, setSlaPolicies] = useState<SLAPolicyConfig[]>(mockSLAPolicies);
  const [rules, setRules] = useState<DQRuleConfig[]>(mockDQRules);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const toggleRule = (ruleId: string) => {
    setRules((prev) =>
      prev.map((r) => (r.id === ruleId ? { ...r, enabled: !r.enabled } : r))
    );
  };

  const handleSave = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-heading">
              Platform & Policy Configuration
            </h1>
            <Badge variant="purple" size="sm">
              Enterprise Admin
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Configure prompt-pay SLA statutory ceilings, Data Quality rule thresholds, clearinghouse connectors, and automated escalation webhooks.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={handleSave}
            leftIcon={<Save className="w-3.5 h-3.5" />}
          >
            Save Configuration
          </Button>
        </div>
      </div>

      {/* Save Toast */}
      {savedSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-950/80 border border-emerald-700 text-emerald-200 text-xs font-medium flex items-center gap-2 shadow-lg">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>Platform policies and rule thresholds successfully updated and applied to active ingestion workers.</span>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="border-b border-slate-800 flex items-center gap-2 overflow-x-auto text-xs font-medium">
        <button
          onClick={() => setActiveTab('sla')}
          className={`pb-3 px-3 flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'sla'
              ? 'border-cyan-500 text-cyan-300 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          SLA Statutory Policies ({slaPolicies.length})
        </button>

        <button
          onClick={() => setActiveTab('rules')}
          className={`pb-3 px-3 flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'rules'
              ? 'border-cyan-500 text-cyan-300 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          Data Quality Rule Engine ({rules.length})
        </button>

        <button
          onClick={() => setActiveTab('gateways')}
          className={`pb-3 px-3 flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'gateways'
              ? 'border-cyan-500 text-cyan-300 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Server className="w-3.5 h-3.5" />
          Clearinghouse EDI Gateways
        </button>

        <button
          onClick={() => setActiveTab('notifications')}
          className={`pb-3 px-3 flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'notifications'
              ? 'border-cyan-500 text-cyan-300 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Bell className="w-3.5 h-3.5" />
          Escalation Webhooks & Alerts
        </button>
      </div>

      {/* Tab 1: SLA Policies */}
      {activeTab === 'sla' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Prompt-Pay & Statutory SLA Turnaround Timelines</CardTitle>
              <CardDescription>
                Define max adjudication durations before automated breach escalations trigger
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {slaPolicies.map((pol) => (
                <div
                  key={pol.id}
                  className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white text-xs">{pol.name}</span>
                      <Badge variant="neutral" size="sm">{pol.claimType}</Badge>
                    </div>
                    <p className="text-xs text-slate-400">
                      Target Turnaround: <span className="font-mono text-cyan-400 font-bold">{pol.targetMaxMinutes / 60} hours</span> ({pol.targetMaxMinutes} min) | Warning trigger at &lt;{pol.warningThresholdMinutes}m
                    </p>
                    <span className="text-[11px] text-slate-400 font-mono">
                      Escalation Assignee: {pol.escalationRole}
                    </span>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right text-xs">
                      <span className="text-slate-400 block text-[10px] uppercase">Auto Mitigate</span>
                      <span className={`font-mono font-bold ${pol.autoMitigate ? 'text-emerald-400' : 'text-slate-400'}`}>
                        {pol.autoMitigate ? 'ENABLED' : 'MANUAL AUDIT'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 2: Rules Engine */}
      {activeTab === 'rules' && (
        <Card>
          <CardHeader>
            <CardTitle>Active Data Quality & Anomaly Heuristic Rules</CardTitle>
            <CardDescription>
              Toggle validation rules or adjust statistical anomaly sensitivity
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {rules.map((r) => (
              <div
                key={r.id}
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white text-xs">{r.name}</span>
                    <span className="font-mono text-[10px] text-cyan-400 bg-cyan-950 px-1.5 py-0.5 rounded border border-cyan-800/40">
                      {r.code}
                    </span>
                    <Badge variant={r.severity === 'critical' ? 'danger' : r.severity === 'high' ? 'warning' : 'info'} size="sm">
                      {r.severity.toUpperCase()}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
                    {r.description}
                  </p>
                  <div className="flex items-center gap-4 text-[11px] text-slate-400 font-mono pt-1">
                    <span>Evaluations: {r.executionCount.toLocaleString()}</span>
                    <span>Failures: {r.failureCount}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <button
                    onClick={() => toggleRule(r.id)}
                    className="flex items-center gap-2 p-1 text-xs cursor-pointer focus:outline-none"
                  >
                    {r.enabled ? (
                      <span className="flex items-center gap-1.5 text-emerald-400 font-medium font-mono">
                        <ToggleRight className="w-6 h-6 text-emerald-400" /> Active
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5 text-slate-400 font-medium font-mono">
                        <ToggleLeft className="w-6 h-6 text-slate-600" /> Disabled
                      </span>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Tab 3: Gateways */}
      {activeTab === 'gateways' && (
        <Card>
          <CardHeader>
            <CardTitle>Connected EDI 5010 Clearinghouses & SFTP Gateways</CardTitle>
            <CardDescription>Direct clearinghouse ingestion pipelines and automated polling endpoints</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { name: 'Change Healthcare / Optum AS2 Gateway', status: 'Operational', latency: '42ms', protocol: 'AS2 / HTTPS' },
              { name: 'Availity Real-Time EDI Stream', status: 'Operational', latency: '38ms', protocol: 'REST / WebSocket' },
              { name: 'Medicare CMS Core SFTP Dropzone', status: 'Operational', latency: '120ms', protocol: 'SFTP (Port 22)' },
              { name: 'Anthem BCBS Clearinghouse Ingestion', status: 'Operational', latency: '55ms', protocol: 'EDI Direct' },
            ].map((gw, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between"
              >
                <div>
                  <span className="font-semibold text-xs text-white block">{gw.name}</span>
                  <span className="text-[11px] text-slate-400 font-mono">{gw.protocol}</span>
                </div>
                <div className="flex items-center gap-3 font-mono text-xs">
                  <span className="text-slate-400">{gw.latency}</span>
                  <Badge variant="success" size="sm" dot>{gw.status}</Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Tab 4: Webhooks */}
      {activeTab === 'notifications' && (
        <Card>
          <CardHeader>
            <CardTitle>Automated SLA Breach Webhook Subscriptions</CardTitle>
            <CardDescription>Dispatch real-time incident payloads to incident response systems</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-xs text-white">PagerDuty SLA Critical Escalation</span>
                  <Badge variant="success" size="sm">Connected</Badge>
                </div>
                <p className="text-xs text-slate-400 font-mono truncate">
                  https://events.pagerduty.com/v2/enqueue/payerguard-sla-breach
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-xs text-white">Slack Claims Audit Channel (#payer-alerts)</span>
                  <Badge variant="success" size="sm">Active</Badge>
                </div>
                <p className="text-xs text-slate-400 font-mono truncate">
                  https://hooks.slack.com/services/T00/B00/payerguard-alerts
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
