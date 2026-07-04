import { useState, useCallback, useRef, createContext, useContext, useEffect, type ReactNode } from 'react';
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { cn } from '@/shared/lib/cn';

type ToastTone = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
  removing?: boolean;
}

interface ToastContextValue {
  toast: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} });
export const useToast = () => useContext(ToastContext);

const MAX_VISIBLE = 5;
const DISMISS_MS = 2500;
const EXIT_MS = 250;

/** Global notify function — set by ToastProvider on mount. */
let globalNotify: ((message: string, tone?: ToastTone) => void) | null = null;

/**
 * Fire a toast from outside React (e.g. window.onerror).
 * Returns false if ToastProvider is not mounted.
 */
export function notify(message: string, tone: ToastTone = 'info'): boolean {
  if (!globalNotify) return false;
  globalNotify(message, tone);
  return true;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(0);
  const timers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  const remove = useCallback((id: number) => {
    timers.current.delete(id);
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const startRemoval = useCallback((id: number) => {
    setItems((prev) =>
      prev.map((t) => (t.id === id ? { ...t, removing: true } : t)),
    );
    const exitTimer = setTimeout(() => remove(id), EXIT_MS);
    timers.current.set(id, exitTimer);
  }, [remove]);

  const toast = useCallback((message: string, tone: ToastTone = 'success') => {
    const id = nextId.current++;
    setItems((prev) => {
      const next = [...prev, { id, message, tone }];
      // If over limit, mark the oldest for removal
      if (next.length > MAX_VISIBLE) {
        const oldest = next.find((t) => !t.removing);
        if (oldest) {
          startRemoval(oldest.id);
        }
      }
      return next;
    });
    const dismissTimer = setTimeout(() => startRemoval(id), DISMISS_MS);
    timers.current.set(id, dismissTimer);
  }, [startRemoval]);

  // Expose global notify on mount
  useEffect(() => {
    globalNotify = toast;
    (window as unknown as Record<string, unknown>).__toastNotify = (msg: string, tone?: ToastTone) => toast(msg, tone);
    return () => {
      globalNotify = null;
      delete (window as unknown as Record<string, unknown>).__toastNotify;
    };
  }, [toast]);

  // Cleanup all timers on unmount
  useEffect(() => {
    const currentTimers = timers.current;
    return () => {
      currentTimers.forEach((t) => clearTimeout(t));
    };
  }, []);

  return (
    <ToastContext value={{ toast }}>
      {children}
      <div className="fixed top-16 left-1/2 -translate-x-1/2 z-[200] flex flex-col items-center gap-2">
        {items.map((t) => (
          <div
            key={t.id}
            data-removing={t.removing || undefined}
            className={cn(
              'flex items-center gap-2 rounded-[2px] border px-4 py-3 text-sm',
              'animate-[toast-in_0.25s_ease-out]',
              'data-[removing]:animate-[toast-out_0.25s_ease-in_forwards]',
              t.tone === 'success' && 'border-success/20 bg-success-subtle text-success-text',
              t.tone === 'error' && 'border-error/20 bg-error-subtle text-error-text',
              t.tone === 'info' && 'border-border bg-surface text-text',
            )}
          >
            {t.tone === 'success' && <CheckCircle size={16} />}
            {t.tone === 'error' && <XCircle size={16} />}
            {t.tone === 'info' && <AlertCircle size={16} />}
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext>
  );
}
