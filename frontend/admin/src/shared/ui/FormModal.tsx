import { type PropsWithChildren, type ReactNode, useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import { Button } from './Button';
import './FormModal.css';

export function FormModal({
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
  const [render, setRender] = useState(false);

  useEffect(() => {
    if (open) setRender(true);
  }, [open]);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  if (!render) return null;

  return (
    <div
      className={cn(
        'form-modal fixed inset-0 z-[110] flex items-center justify-center bg-surface-scrim/60 p-6',
        open ? 'form-modal--open' : 'form-modal--close',
      )}
      onAnimationEnd={() => {
        if (!open) setRender(false);
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          'flex max-h-[min(90vh,720px)] w-full max-w-2xl flex-col overflow-hidden rounded-[2px] border border-border bg-surface shadow-lg',
          widthClassName,
        )}
      >
        {/* Metro-style accent bar */}
        <div className="h-1 w-full bg-primary" />

        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-6 pt-5 pb-4">
          <div className="min-w-0 flex-1">
            <h3 className="text-xl font-semibold leading-tight text-text">{title}</h3>
            {description ? (
              <p className="mt-1.5 text-sm leading-6 text-text-secondary">{description}</p>
            ) : null}
          </div>
          <Button
            variant="ghost"
            onClick={onClose}
            className="!min-h-0 !p-1.5 text-text-muted hover:text-text"
            aria-label="关闭"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 pb-6">{children}</div>

        {/* Footer */}
        {footer ? (
          <div className="border-t border-border px-6 py-4">{footer}</div>
        ) : null}
      </div>
    </div>
  );
}
