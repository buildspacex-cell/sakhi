import { clsx } from 'clsx';

export type BadgeVariant = 'primary' | 'outline';

export function badge({ variant = 'primary' }: { variant?: BadgeVariant } = {}) {
  return clsx(
    'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium transition',
    variant === 'primary'
      ? 'bg-brand-600 text-white shadow hover:bg-brand-500'
      : 'border border-slate-300 text-slate-700 hover:border-brand-400'
  );
}

export const card = 'rounded-3xl border border-slate-200 bg-white p-6 shadow';

export const heading = 'text-3xl font-semibold tracking-tight text-slate-900';
