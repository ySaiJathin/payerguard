import React from 'react';
import { cn } from '../../utils/cn';
import { Button } from './Button';
import { ShieldCheck } from 'lucide-react';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-12 text-center rounded-xl border border-dashed border-slate-800 bg-slate-900/30',
        className
      )}
    >
      <div className="p-3.5 rounded-2xl bg-slate-800/80 text-cyan-400 border border-slate-700/60 mb-4">
        {icon || <ShieldCheck className="w-8 h-8 text-cyan-400" />}
      </div>
      <h4 className="text-base font-semibold text-slate-100">{title}</h4>
      <p className="text-xs text-slate-400 max-w-sm mt-1.5 leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <div className="mt-5">
          <Button size="sm" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  );
};
