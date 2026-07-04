import { type PropsWithChildren, type ReactNode, useEffect, useState } from 'react';
import { cn } from '@/shared/lib/cn';
import { Button } from './Button';
import './Drawer.css';

export function Drawer({
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

  if (!render) return null;

  return (
    <div
      className={cn(
        'drawer fixed inset-0 z-[100] flex justify-end',
        open ? 'drawer--open' : 'drawer--close',
      )}
      onAnimationEnd={() => { if (!open) setRender(false); }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className={cn('flex h-full w-full max-w-2xl flex-col bg-surface', widthClassName)}>
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
