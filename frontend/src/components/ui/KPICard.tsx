import React from 'react';
import { cn } from '../../utils/cn';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

export interface KPICardProps {
  title: string;
  value: string | number;
  unit?: string;
  changePercent?: number;
  isPositiveGood?: boolean; // If true, + is green, - is red (e.g. clean claim rate). If false, + is red (e.g. error rate)
  trendLabel?: string;
  subtext?: string;
  icon?: React.ReactNode;
  status?: 'good' | 'warning' | 'critical' | 'neutral' | 'info';
  className?: string;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  unit,
  changePercent,
  isPositiveGood = true,
  trendLabel = 'vs last 24h',
  subtext,
  icon,
  status = 'neutral',
  className,
}) => {
  const statusBorder = {
    good: 'border-l-4 border-l-emerald-500',
    warning: 'border-l-4 border-l-amber-500',
    critical: 'border-l-4 border-l-rose-500',
    info: 'border-l-4 border-l-cyan-500',
    neutral: 'border-l-4 border-l-slate-600',
  };

  const isPositive = changePercent !== undefined ? changePercent > 0 : null;
  const isZero = changePercent === 0;

  // Determine trend color
  let trendColor = 'text-slate-400 bg-slate-800/60 border-slate-700';
  if (changePercent !== undefined && !isZero) {
    if ((isPositive && isPositiveGood) || (!isPositive && !isPositiveGood)) {
      trendColor = 'text-emerald-400 bg-emerald-950/50 border-emerald-800/40';
    } else {
      trendColor = 'text-rose-400 bg-rose-950/50 border-rose-800/40';
    }
  }

  return (
    <div
      className={cn(
        'bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm transition-all duration-150 hover:border-slate-700',
        statusBorder[status],
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        {icon && (
          <div className="p-2 rounded-lg bg-slate-800/80 text-slate-300 border border-slate-750">
            {icon}
          </div>
        )}
      </div>

      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="text-2xl font-bold tracking-tight text-white font-mono">
          {value}
        </span>
        {unit && <span className="text-xs text-slate-400 font-medium">{unit}</span>}
      </div>

      <div className="mt-3 flex items-center justify-between text-xs pt-2 border-t border-slate-800/60">
        {changePercent !== undefined ? (
          <div className="flex items-center gap-1.5">
            <span
              className={cn(
                'inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[11px] font-medium border font-mono',
                trendColor
              )}
            >
              {isZero ? (
                <Minus className="w-3 h-3" />
              ) : isPositive ? (
                <ArrowUpRight className="w-3 h-3" />
              ) : (
                <ArrowDownRight className="w-3 h-3" />
              )}
              {isPositive ? `+${changePercent}%` : `${changePercent}%`}
            </span>
            <span className="text-slate-400 text-[11px]">{trendLabel}</span>
          </div>
        ) : (
          <span className="text-slate-400 text-[11px]">{subtext}</span>
        )}

        {subtext && changePercent !== undefined && (
          <span className="text-slate-400 text-[11px] truncate max-w-[120px]" title={subtext}>
            {subtext}
          </span>
        )}
      </div>
    </div>
  );
};
