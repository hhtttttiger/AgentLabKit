import { useLayoutEffect, useRef, useState, type PropsWithChildren, type ReactNode } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

export type ModuleLayoutSection = {
  key: string;
  label: string;
  path: string;
  end?: boolean;
};

export function ModuleLayoutShell({
  eyebrow,
  title,
  sections,
  leading,
  actions,
  children,
}: PropsWithChildren<{
  eyebrow: string;
  title: string;
  sections: ModuleLayoutSection[];
  leading?: ReactNode;
  actions?: ReactNode;
}>) {
  const location = useLocation();
  const itemRefs = useRef<(HTMLAnchorElement | null)[]>([]);
  const [indicator, setIndicator] = useState<{ left: number; width: number } | null>(null);

  useLayoutEffect(() => {
    const activeIdx = sections.findIndex((s) => {
      const isEnd = s.end ?? s.key === 'overview';
      return isEnd ? location.pathname === s.path : location.pathname.startsWith(s.path);
    });
    const el = itemRefs.current[activeIdx];
    if (el) setIndicator({ left: el.offsetLeft, width: el.offsetWidth });
    else setIndicator(null);
  }, [location.pathname, sections]);

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-border bg-surface px-8 py-3">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <div className="flex flex-wrap items-center gap-3">
            {leading}
            <div className="flex items-baseline gap-1.5">
              <span className="text-xs font-medium text-text-muted">{eyebrow}</span>
              <span className="text-xs text-border">/</span>
              <h1 className="text-base font-semibold text-text">{title}</h1>
            </div>
            <div className="h-4 w-px bg-border" />
            <nav className="relative flex">
              {indicator && (
                <div
                  className="absolute bottom-0 h-[3px] bg-primary"
                  style={{
                    left: indicator.left,
                    width: indicator.width,
                    transition: 'left 0.25s ease, width 0.2s ease',
                  }}
                />
              )}
              {sections.map((section, i) => (
                <NavLink
                  key={section.key}
                  ref={(el) => { itemRefs.current[i] = el; }}
                  to={section.path}
                  end={section.end ?? section.key === 'overview'}
                  className={({ isActive }) =>
                    `relative z-10 px-3.5 py-2 text-sm font-medium transition-colors ${
                      isActive ? 'text-text' : 'text-text-secondary hover:text-text'
                    }`
                  }
                >
                  {section.label}
                </NavLink>
              ))}
            </nav>
          </div>
          {actions}
        </div>
      </header>
      <div className="flex min-h-0 flex-1 flex-col px-8 pt-5 pb-3">{children ?? <Outlet />}</div>
    </div>
  );
}
