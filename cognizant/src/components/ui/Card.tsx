import React from 'react';
import { cn } from '../../utils/cn';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'subtle' | 'bordered';
  hoverEffect?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', hoverEffect = false, children, ...props }, ref) => {
    const variants = {
      default: 'bg-slate-900/90 border border-slate-800 text-slate-100 shadow-sm',
      glass: 'bg-slate-900/60 backdrop-blur-md border border-slate-800/80 text-slate-100 shadow-md',
      subtle: 'bg-slate-950/60 border border-slate-800/50 text-slate-200',
      bordered: 'bg-transparent border-2 border-slate-800 text-slate-100',
    };

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-xl p-5 transition-all duration-150',
          variants[variant],
          hoverEffect && 'hover:border-slate-700 hover:shadow-lg',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);
Card.displayName = 'Card';

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div className={cn('flex flex-col space-y-1.5 pb-4 border-b border-slate-800/80 mb-4', className)} {...props}>
    {children}
  </div>
);

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  className,
  children,
  ...props
}) => (
  <h3 className={cn('text-base font-semibold text-slate-100 leading-tight flex items-center justify-between', className)} {...props}>
    {children}
  </h3>
);

export const CardDescription: React.FC<React.HTMLAttributes<HTMLParagraphElement>> = ({
  className,
  children,
  ...props
}) => (
  <p className={cn('text-xs text-slate-400', className)} {...props}>
    {children}
  </p>
);

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div className={cn('', className)} {...props}>
    {children}
  </div>
);

export const CardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div className={cn('flex items-center pt-4 border-t border-slate-800/80 mt-4', className)} {...props}>
    {children}
  </div>
);
