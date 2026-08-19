import React from 'react';
import { cn } from '../../utils/cn';

export interface StatusIndicatorProps {
  status: 'operational' | 'degraded' | 'breached' | 'processing' | 'inactive';
  label?: string;
  sublabel?: string;
  size?: 'sm' | 'md' | 'lg';
  pulse?: boolean;
  className?: string;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  label,
  sublabel,
  size = 'md',
  pulse = true,
  className,
}) => {
  const statusConfig = {
    operational: {
      dot: 'bg-emerald-400',
      ring: 'bg-emerald-500/30',
      text: 'text-emerald-400',
      defaultLabel: 'Operational',
      pulseClass: 'animate-pulse-ring',
    },
    degraded: {
      dot: 'bg-amber-400',
      ring: 'bg-amber-500/30',
      text: 'text-amber-400',
      defaultLabel: 'Degraded',
      pulseClass: 'animate-pulse-amber',
    },
    breached: {
      dot: 'bg-rose-400',
      ring: 'bg-rose-500/30',
      text: 'text-rose-400',
      defaultLabel: 'Breached',
      pulseClass: 'animate-pulse-rose',
    },
    processing: {
      dot: 'bg-cyan-400',
      ring: 'bg-cyan-500/30',
      text: 'text-cyan-400',
      defaultLabel: 'Processing',
      pulseClass: 'animate-pulse',
    },
    inactive: {
      dot: 'bg-slate-500',
      ring: 'bg-slate-700/30',
      text: 'text-slate-400',
      defaultLabel: 'Standby',
      pulseClass: '',
    },
  };

  const config = statusConfig[status];

  const dotSizes = {
    sm: 'w-2 h-2',
    md: 'w-2.5 h-2.5',
    lg: 'w-3 h-3',
  };

  return (
    <div className={cn('inline-flex items-center gap-2', className)}>
      <span className="relative flex items-center justify-center shrink-0">
        {pulse && status !== 'inactive' && (
          <span
            className={cn(
              'absolute inline-flex h-full w-full rounded-full opacity-75',
              config.pulseClass,
              config.dot
            )}
          />
        )}
        <span className={cn('relative inline-flex rounded-full', dotSizes[size], config.dot)} />
      </span>
      {(label || config.defaultLabel) && (
        <div className="flex flex-col">
          <span className={cn('text-xs font-medium tracking-tight', config.text)}>
            {label || config.defaultLabel}
          </span>
          {sublabel && (
            <span className="text-[10px] text-slate-400 font-mono">{sublabel}</span>
          )}
        </div>
      )}
    </div>
  );
};
