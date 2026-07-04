import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './app/App';
import { notify } from '@/shared/ui/Toast';
import i18n from '@/shared/i18n';
import './shared/i18n';
import './index.css';
import 'highlight.js/styles/github-dark.css';

// Last-resort catchers for errors that escape React's ErrorBoundary.
// Logs to console and shows a toast notification.
window.onerror = (_msg, _source, _lineno, _colno, error) => {
  console.error('[window.onerror]', error);
  notify(i18n.t('toast.operationFailed'), 'error');
};

window.addEventListener('unhandledrejection', (event) => {
  console.error('[unhandledrejection]', event.reason);
  notify(i18n.t('toast.operationFailed'), 'error');
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
