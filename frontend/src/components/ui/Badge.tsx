import React from 'react';
import { cn } from '../../utils/cn';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'purple';
  size?: 'sm' | 'md';
  dot?: boolean;
  pulse?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'neutral',
  size = 'md',
  dot = false,
  pulse = false,
  children,
  ...props
}) => {
  const variantStyles = {
    success: 'bg-emerald-950/70 text-emerald-300 border-emerald-800/60',
    warning: 'bg-amber-950/70 text-amber-300 border-amber-800/60',
    danger: 'bg-rose-950/70 text-rose-300 border-rose-800/60',
    info: 'bg-cyan-950/70 text-cyan-300 border-cyan-800/60',
    purple: 'bg-indigo-950/70 text-indigo-300 border-indigo-800/60',
    neutral: 'bg-slate-800/80 text-slate-300 border-slate-700',
  };

  const dotColors = {
    success: 'bg-emerald-400',
    warning: 'bg-amber-400',
    danger: 'bg-rose-400',
    info: 'bg-cyan-400',
    purple: 'bg-indigo-400',
    neutral: 'bg-slate-400',
  };

  const sizeStyles = {
    sm: 'text-[11px] px-2 py-0.5 font-medium gap-1.5',
    md: 'text-xs px-2.5 py-1 font-medium gap-1.5',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md border tracking-wide select-none',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    >
      {dot && (
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full shrink-0',
            dotColors[variant],
            pulse && (variant === 'success' ? 'animate-pulse-ring' : variant === 'warning' ? 'animate-pulse-amber' : 'animate-pulse-rose')
          )}
        />
      )}
      {children}
    </span>
  );
};
