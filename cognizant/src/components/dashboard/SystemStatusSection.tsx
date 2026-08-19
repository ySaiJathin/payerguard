import React from 'react';
import {
  Activity,
  ShieldCheck,
  Cpu,
  Clock,
  Sparkles,
  CheckCircle2,
  Zap,
  Server
} from 'lucide-react';
import { SystemStatusItem } from '../../data/mockDashboardData';

interface SystemStatusSectionProps {
  systems: SystemStatusItem[];
}

export const SystemStatusSection: React.FC<SystemStatusSectionProps> = ({ systems }) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'Activity':
        return <Activity className="w-4 h-4 text-emerald-400" />;
      case 'ShieldCheck':
        return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
      case 'Cpu':
        return <Cpu className="w-4 h-4 text-cyan-400" />;
      case 'Clock':
        return <Clock className="w-4 h-4 text-amber-400" />;
      case 'Sparkles':
        return <Sparkles className="w-4 h-4 text-indigo-400" />;
      default:
        return <Server className="w-4 h-4 text-slate-400" />;
    }
  };

  const getStatusBadge = (status: string, state: string) => {
    if (status === 'Healthy') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Healthy
        </span>
      );
    }
    if (status === 'Active') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          Active
        </span>
      );
    }
    if (status === 'Ready') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
          Ready
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-950/80 text-amber-300 border border-amber-800/60 font-mono">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
        {status}
      </span>
    );
  };

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 sm:p-5 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 mb-3 border-b border-slate-800/70">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200 font-heading">
            System & Engine Operational Status
          </h2>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-ping opacity-75" />
            <span className="text-slate-300 font-medium">All Core Engines Operational</span>
          </span>
          <span className="text-slate-600 hidden sm:inline">|</span>
          <span className="hidden sm:inline text-slate-400">Sync: Realtime (100ms)</span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {systems.map((sys) => (
          <div
            key={sys.name}
            className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/80 transition-all duration-200 group"
          >
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2 truncate">
                <div className="p-1.5 rounded-md bg-slate-900 border border-slate-800 shrink-0">
                  {getIcon(sys.iconName)}
                </div>
                <span className="text-xs font-semibold text-slate-200 truncate group-hover:text-white">
                  {sys.name}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between mt-1">
              <span className="text-[11px] text-slate-400">{sys.metricLabel}:</span>
              {getStatusBadge(sys.status, sys.state)}
            </div>

            <div className="mt-2 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px]">
              <span className="font-mono text-slate-300 font-medium truncate" title={sys.metricValue}>
                {sys.metricValue}
              </span>
            </div>
            <div className="text-[10px] text-slate-400 truncate mt-0.5" title={sys.secondaryInfo}>
              {sys.secondaryInfo}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
