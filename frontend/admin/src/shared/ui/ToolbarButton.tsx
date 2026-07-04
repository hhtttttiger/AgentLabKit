import { type ButtonHTMLAttributes, type PropsWithChildren } from 'react';
import { cn } from '@/shared/lib/cn';
import { Button } from './Button';

type Variant = 'primary' | 'secondary' | 'ghost';

/**
 * Compact button sized for use inside FilterToolbar action slots.
 * Renders smaller than the default Button (h-control-sm vs min-h-control).
 *
 * - `variant="primary"` (default): blue CTA — use for create/submit actions
 * - `variant="secondary"`: bordered — use for refresh, reset, export
 * - `variant="ghost"`: no border — use for low-emphasis actions
 */
export function ToolbarButton({
  variant = 'secondary',
  className,
  children,
  ...props
}: PropsWithChildren<
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }
>) {
  const px = variant === 'primary' ? 'px-3' : 'px-2.5';
  return (
    <Button
      variant={variant}
      className={cn('h-control-sm min-h-0 rounded-[2px] py-1.5 text-xs', px, className)}
      {...props}
    >
      {children}
    </Button>
  );
}
