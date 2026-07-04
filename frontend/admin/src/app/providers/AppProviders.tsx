import type { ReactNode } from 'react';
import type { ErrorInfo } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/shared/api/queryClient';
import { ErrorBoundary } from '@/shared/error/ErrorBoundary';
import { DocumentLanguageSync } from '@/shared/i18n/DocumentLanguageSync';
import { ThemeProvider } from '@/shared/theme';
import { ToastProvider } from '@/shared/ui/Toast';

function handleRootError(error: Error, _info: ErrorInfo) {
  // Reserved for error reporting integration (e.g. Sentry.captureException)
  console.error('[RootErrorBoundary]', error);
}

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary onError={handleRootError}>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <DocumentLanguageSync />
            {children}
          </ToastProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
