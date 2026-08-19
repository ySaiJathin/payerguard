import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  AlertTriangle,
  AlertOctagon,
  Clock,
  Activity,
  Layers,
  RefreshCw,
  UploadCloud,
  Play,
  FileText,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  Sparkles,
} from 'lucide-react';
import { KPICard } from '../components/ui/KPICard';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { SystemStatusSection } from '../components/dashboard/SystemStatusSection';
import { ClaimsVolumeChart } from '../components/dashboard/ClaimsVolumeChart';
import { DataQualityTrendChart } from '../components/dashboard/DataQualityTrendChart';
import { AnomalyTrendChart } from '../components/dashboard/AnomalyTrendChart';
import { SLARiskTrendChart } from '../components/dashboard/SLARiskTrendChart';
import { ClaimAmountDistribution } from '../components/dashboard/ClaimAmountDistribution';
import { IncidentSeverityDistribution } from '../components/dashboard/IncidentSeverityDistribution';
import { RecentIncidentsTable } from '../components/dashboard/RecentIncidentsTable';
import {
  mockDashboardKPIs,
  mockVolumeTrend24h,
  mockVolumeTrend7d,
  mockDataQualityTrend24h,
  mockDataQualityTrend7d,
  mockAnomalyTrend24h,
  mockAnomalyTrend7d,
  mockSLARiskTrend24h,
  mockSLARiskTrend7d,
  mockClaimAmountBrackets,
  mockIncidentSeverityDistribution,
  mockRecentIncidents,
  mockSystemStatus,
} from '../data/mockDashboardData';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('24h');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshedTime, setLastRefreshedTime] = useState('Just now');

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setIsRefreshing(false);
      setLastRefreshedTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    }, 500);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Title & Command Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-heading">
              PayerGuard Operations Dashboard
            </h1>
            <Badge variant="info" size="sm" dot pulse>
              Live Telemetry
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time EDI 837 claim ingestion, automated data quality scoring, and statutory prompt-pay SLA risk watchdog.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Time range selector */}
          <div className="bg-slate-900 p-1 rounded-lg border border-slate-800 flex items-center text-xs">
            {(['24h', '7d', '30d'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  timeRange === range
                    ? 'bg-slate-800 text-cyan-300 shadow-xs'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {range.toUpperCase()}
              </button>
            ))}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            isLoading={isRefreshing}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate('/upload')}
            leftIcon={<UploadCloud className="w-3.5 h-3.5" />}
          >
            Upload Claims
          </Button>
        </div>
      </div>

      {/* 1. System Status Section */}
      <SystemStatusSection systems={mockSystemStatus} />

      {/* 2. 6 Required KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {/* KPI 1: Data Quality Score */}
        <KPICard
          title={mockDashboardKPIs.dataQualityScore.title}
          value={mockDashboardKPIs.dataQualityScore.value}
          changePercent={mockDashboardKPIs.dataQualityScore.changePercent}
          isPositiveGood={mockDashboardKPIs.dataQualityScore.isPositiveGood}
          trendLabel={mockDashboardKPIs.dataQualityScore.trendLabel}
          subtext={mockDashboardKPIs.dataQualityScore.subtext}
          status={mockDashboardKPIs.dataQualityScore.status}
          icon={<ShieldCheck className="w-5 h-5 text-emerald-400" />}
        />

        {/* KPI 2: Active Anomalies */}
        <KPICard
          title={mockDashboardKPIs.activeAnomalies.title}
          value={mockDashboardKPIs.activeAnomalies.value}
          unit={mockDashboardKPIs.activeAnomalies.unit}
          changePercent={mockDashboardKPIs.activeAnomalies.changePercent}
          isPositiveGood={mockDashboardKPIs.activeAnomalies.isPositiveGood}
          trendLabel={mockDashboardKPIs.activeAnomalies.trendLabel}
          subtext={mockDashboardKPIs.activeAnomalies.subtext}
          status={mockDashboardKPIs.activeAnomalies.status}
          icon={<AlertTriangle className="w-5 h-5 text-amber-400" />}
        />

        {/* KPI 3: Critical Incidents */}
        <KPICard
          title={mockDashboardKPIs.criticalIncidents.title}
          value={mockDashboardKPIs.criticalIncidents.value}
          unit={mockDashboardKPIs.criticalIncidents.unit}
          changePercent={mockDashboardKPIs.criticalIncidents.changePercent}
          isPositiveGood={mockDashboardKPIs.criticalIncidents.isPositiveGood}
          trendLabel={mockDashboardKPIs.criticalIncidents.trendLabel}
          subtext={mockDashboardKPIs.criticalIncidents.subtext}
          status={mockDashboardKPIs.criticalIncidents.status}
          icon={<AlertOctagon className="w-5 h-5 text-rose-400" />}
        />

        {/* KPI 4: SLA Risk */}
        <KPICard
          title={mockDashboardKPIs.slaRisk.title}
          value={mockDashboardKPIs.slaRisk.value}
          changePercent={mockDashboardKPIs.slaRisk.changePercent}
          isPositiveGood={mockDashboardKPIs.slaRisk.isPositiveGood}
          trendLabel={mockDashboardKPIs.slaRisk.trendLabel}
          subtext={mockDashboardKPIs.slaRisk.subtext}
          status={mockDashboardKPIs.slaRisk.status}
          icon={<Clock className="w-5 h-5 text-amber-400" />}
        />

        {/* KPI 5: Claims Processed */}
        <KPICard
          title={mockDashboardKPIs.claimsProcessed.title}
          value={mockDashboardKPIs.claimsProcessed.value}
          unit={mockDashboardKPIs.claimsProcessed.unit}
          changePercent={mockDashboardKPIs.claimsProcessed.changePercent}
          isPositiveGood={mockDashboardKPIs.claimsProcessed.isPositiveGood}
          trendLabel={mockDashboardKPIs.claimsProcessed.trendLabel}
          subtext={mockDashboardKPIs.claimsProcessed.subtext}
          status={mockDashboardKPIs.claimsProcessed.status}
          icon={<Activity className="w-5 h-5 text-cyan-400" />}
        />

        {/* KPI 6: Claims Affected */}
        <KPICard
          title={mockDashboardKPIs.claimsAffected.title}
          value={mockDashboardKPIs.claimsAffected.value}
          unit={mockDashboardKPIs.claimsAffected.unit}
          changePercent={mockDashboardKPIs.claimsAffected.changePercent}
          isPositiveGood={mockDashboardKPIs.claimsAffected.isPositiveGood}
          trendLabel={mockDashboardKPIs.claimsAffected.trendLabel}
          subtext={mockDashboardKPIs.claimsAffected.subtext}
          status={mockDashboardKPIs.claimsAffected.status}
          icon={<Layers className="w-5 h-5 text-rose-400" />}
        />
      </div>

      {/* 3. 4 Required Trend Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Claims Volume Trend */}
        <ClaimsVolumeChart
          data24h={mockVolumeTrend24h}
          data7d={mockVolumeTrend7d}
          activeRange={timeRange}
        />

        {/* Chart 2: Data Quality Trend */}
        <DataQualityTrendChart
          data24h={mockDataQualityTrend24h}
          data7d={mockDataQualityTrend7d}
          activeRange={timeRange}
        />

        {/* Chart 3: Anomaly Trend */}
        <AnomalyTrendChart
          data24h={mockAnomalyTrend24h}
          data7d={mockAnomalyTrend7d}
          activeRange={timeRange}
        />

        {/* Chart 4: SLA Risk Trend */}
        <SLARiskTrendChart
          data24h={mockSLARiskTrend24h}
          data7d={mockSLARiskTrend7d}
          activeRange={timeRange}
        />
      </div>

      {/* 4. 2 Required Distributions Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Distribution 1: Claim Amount Distribution */}
        <ClaimAmountDistribution brackets={mockClaimAmountBrackets} />

        {/* Distribution 2: Incident Severity Distribution */}
        <IncidentSeverityDistribution distribution={mockIncidentSeverityDistribution} />
      </div>

      {/* 5. Recent Incidents Table */}
      <RecentIncidentsTable incidents={mockRecentIncidents} />
    </div>
  );
};

export default Dashboard;
