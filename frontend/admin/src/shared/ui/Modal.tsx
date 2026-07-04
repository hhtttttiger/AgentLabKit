import type { PropsWithChildren, ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';
import { Button } from './Button';

export function Modal({
  open,
  title,
  description,
  children,
  footer,
  onClose,
  widthClassName,
}: PropsWithChildren<{
  open: boolean;
  title: string;
  description?: string;
  footer?: ReactNode;
  onClose: () => void;
  widthClassName?: string;
}>) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center bg-surface-scrim/60 p-6">
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          'flex max-h-[min(90vh,720px)] w-full max-w-2xl flex-col overflow-hidden rounded-[2px] border border-border bg-surface',
          widthClassName,
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
          <div>
            <h3 className="text-xl font-semibold text-text">{title}</h3>
            {description ? <p className="mt-2 text-sm leading-6 text-text-secondary">{description}</p> : null}
          </div>
          <Button variant="ghost" onClick={onClose}>
            关闭
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {footer ? <div className="border-t border-border px-6 py-4">{footer}</div> : null}
      </div>
    </div>
  );
}
