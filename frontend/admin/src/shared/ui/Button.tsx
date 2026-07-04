import type { ButtonHTMLAttributes, PropsWithChildren } from 'react';
import { cn } from '@/shared/lib/cn';

type ButtonProps = PropsWithChildren<
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  }
>;

export function Button({ className, variant = 'primary', type = 'button', ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex min-h-control items-center justify-center gap-2 rounded-[2px] px-4 py-2.5 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-state-focus/30 disabled:cursor-not-allowed disabled:opacity-50',
        variant === 'primary' && 'bg-primary text-text-inverse hover:bg-primary-hover active:bg-primary-active',
        variant === 'secondary' && 'border border-border-strong bg-surface text-text hover:bg-background-subtle',
        variant === 'danger' && 'bg-error text-text-inverse hover:bg-error/90',
        variant === 'ghost' && 'text-text-secondary hover:bg-state-hover hover:text-text',
        className,
      )}
      {...props}
    />
  );
}
