import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { MoreHorizontal } from 'lucide-react';

export type RowAction = {
  label: string;
  onClick: () => void | Promise<void>;
  variant?: 'default' | 'danger';
  disabled?: boolean;
};

export function RowActions({ actions }: { actions: RowAction[] }) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });

  const updateMenuPosition = useCallback(() => {
    const trigger = triggerRef.current;
    if (!trigger) {
      return;
    }

    const rect = trigger.getBoundingClientRect();
    setMenuPosition({
      top: rect.bottom + 4,
      left: rect.right,
    });
  }, []);

  useEffect(() => {
    if (!open) return;

    updateMenuPosition();

    function handleOutsideClick(e: MouseEvent) {
      const target = e.target as Node;
      const clickedTrigger = containerRef.current?.contains(target) ?? false;
      const clickedMenu = menuRef.current?.contains(target) ?? false;
      if (!clickedTrigger && !clickedMenu) {
        setOpen(false);
      }
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    function handleViewportChange() {
      updateMenuPosition();
    }

    document.addEventListener('mousedown', handleOutsideClick);
    document.addEventListener('keydown', handleEscape);
    window.addEventListener('resize', handleViewportChange);
    window.addEventListener('scroll', handleViewportChange, true);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('keydown', handleEscape);
      window.removeEventListener('resize', handleViewportChange);
      window.removeEventListener('scroll', handleViewportChange, true);
    };
  }, [open, updateMenuPosition]);

  return (
    <div ref={containerRef} className="relative inline-block">
      <button
        ref={triggerRef}
        type="button"
        aria-label="更多操作"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => {
          if (!open) {
            updateMenuPosition();
          }
          setOpen((v) => !v);
        }}
        className="flex h-8 w-8 items-center justify-center rounded-lg border border-transparent text-text-secondary transition hover:border-border hover:bg-state-hover hover:text-text"
      >
        <MoreHorizontal size={16} />
      </button>

      {open && createPortal(
        <div
          ref={menuRef}
          role="menu"
          className="fixed z-50 min-w-[140px] overflow-hidden rounded-[2px] border border-border bg-surface py-1"
          style={{
            top: `${menuPosition.top}px`,
            left: `${menuPosition.left}px`,
            transform: 'translateX(-100%)',
          }}
        >
          {actions.map((action) => (
            <button
              key={action.label}
              role="menuitem"
              type="button"
              disabled={action.disabled}
              onClick={() => {
                setOpen(false);
                action.onClick();
              }}
              className={`w-full px-4 py-2 text-left text-sm transition ${action.disabled ? 'cursor-not-allowed opacity-40' : 'hover:bg-state-hover'} ${
                action.variant === 'danger' ? 'text-red-600' : 'text-text'
              }`}
            >
              {action.label}
            </button>
          ))}
        </div>,
        document.body,
      )}
    </div>
  );
}
