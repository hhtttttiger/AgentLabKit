import { Suspense, lazy, type ComponentType, type JSX, type ReactElement } from 'react';
import { ErrorBoundary } from '@/shared/error/ErrorBoundary';

// React.lazy is typed against ComponentType<any>; keep the unsafeness scoped to this helper.
type ComponentModule = Record<string, ComponentType<any>>;

function RouteLoadingFallback() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-text-muted">加载中...</div>
    </div>
  );
}

export function lazyRoute<TModule extends ComponentModule, TKey extends keyof TModule & string>(
  loader: () => Promise<TModule>,
  exportName: TKey,
) {
  return lazy(async () => {
    const module = await loader();
    return { default: module[exportName] };
  });
}

export function routeElement<TProps extends object = Record<string, never>>(
  Component: ComponentType<TProps>,
  props?: TProps,
): ReactElement<JSX.Element> {
  return (
    <ErrorBoundary>
      <Suspense fallback={<RouteLoadingFallback />}>
        <Component {...(props as TProps)} />
      </Suspense>
    </ErrorBoundary>
  );
}
