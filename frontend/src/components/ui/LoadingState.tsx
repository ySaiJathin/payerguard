import React from 'react';
import { cn } from '../../utils/cn';
import { Loader2 } from 'lucide-react';

export interface LoadingStateProps {
  message?: string;
  submessage?: string;
  variant?: 'spinner' | 'skeleton' | 'table-skeleton';
  rows?: number;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading claims data...',
  submessage = 'Validating EDI segments against HIPAA & CMS rules',
  variant = 'spinner',
  rows = 5,
  className,
}) => {
  if (variant === 'skeleton') {
    return (
      <div className={cn('w-full space-y-3 p-4', className)}>
        <div className="h-6 w-1/3 bg-slate-800 rounded animate-pulse" />
        <div className="h-4 w-1/2 bg-slate-800/60 rounded animate-pulse" />
        <div className="h-24 w-full bg-slate-800/40 rounded-lg animate-pulse mt-4" />
      </div>
    );
  }

  if (variant === 'table-skeleton') {
    return (
      <div className={cn('w-full space-y-2 p-2', className)}>
        <div className="h-9 w-full bg-slate-800/80 rounded animate-pulse mb-3" />
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-12 w-full bg-slate-800/40 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col items-center justify-center p-12 text-center', className)}>
      <div className="relative flex items-center justify-center mb-4">
        <div className="w-12 h-12 rounded-full border-2 border-cyan-500/20 border-t-cyan-500 animate-spin" />
        <Loader2 className="w-5 h-5 text-cyan-400 absolute" />
      </div>
      <h4 className="text-sm font-medium text-slate-200">{message}</h4>
      {submessage && <p className="text-xs text-slate-400 mt-1">{submessage}</p>}
    </div>
  );
};
