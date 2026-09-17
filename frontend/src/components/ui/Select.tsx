import { forwardRef, useId, type SelectHTMLAttributes } from 'react';

import { cn } from '@/lib/cn';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: SelectOption[];
}

/** A labelled native select: keyboard and screen-reader behaviour for free. */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, label, error, options, id, ...props },
  ref,
) {
  const generatedId = useId();
  const selectId = id ?? generatedId;

  return (
    <div className="flex w-full flex-col gap-1.5">
      {label != null && (
        <label htmlFor={selectId} className="text-sm font-medium text-content-secondary">
          {label}
        </label>
      )}
      <select
        ref={ref}
        id={selectId}
        aria-invalid={error != null}
        className={cn(
          'h-10 w-full rounded-lg border bg-surface-950 px-3 text-sm text-content-primary',
          'transition-colors focus:ring-2 focus:ring-brand-500/40 focus:outline-none',
          error != null ? 'border-negative' : 'border-surface-700 focus:border-brand-500',
          className,
        )}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error != null && <p className="text-xs text-negative">{error}</p>}
    </div>
  );
});
