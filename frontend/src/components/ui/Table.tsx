import React from 'react';
import { cn } from '../../utils/cn';

export interface TableProps extends React.HTMLAttributes<HTMLTableElement> {
  dense?: boolean;
}

export const Table = React.forwardRef<HTMLTableElement, TableProps>(
  ({ className, dense = false, ...props }, ref) => (
    <div className="relative w-full overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/60">
      <table
        ref={ref}
        className={cn('w-full caption-bottom text-left text-xs text-slate-300', dense ? 'text-[11px]' : 'text-xs', className)}
        {...props}
      />
    </div>
  )
);
Table.displayName = 'Table';

export const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <thead ref={ref} className={cn('bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold', className)} {...props} />
));
TableHeader.displayName = 'TableHeader';

export const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody ref={ref} className={cn('divide-y divide-slate-800/60 font-normal', className)} {...props} />
));
TableBody.displayName = 'TableBody';

export const TableRow = React.forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement> & { isSelected?: boolean }
>(({ className, isSelected, ...props }, ref) => (
  <tr
    ref={ref}
    className={cn(
      'transition-colors hover:bg-slate-800/40 data-[state=selected]:bg-slate-800/60',
      isSelected && 'bg-slate-800/60',
      className
    )}
    {...props}
  />
));
TableRow.displayName = 'TableRow';

export const TableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <th
    ref={ref}
    className={cn('h-10 px-4 py-2.5 text-left align-middle font-medium text-slate-400 tracking-wider', className)}
    {...props}
  />
));
TableHead.displayName = 'TableHead';

export const TableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <td
    ref={ref}
    className={cn('px-4 py-3 align-middle text-slate-200', className)}
    {...props}
  />
));
TableCell.displayName = 'TableCell';
