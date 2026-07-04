/**
 * Error code filter options for the errors page.
 *
 * Two sources write to model_request_logs.ErrorCode:
 *   - .NET LlmAdapt runtime  (UPPER_CASE)
 *   - Python ai_gateway      (lower_case)
 *
 * The primary source is now the backend /errors/distinct-error-codes endpoint
 * (which returns codes actually present in the DB).  We ship a small local
 * fallback so the dropdown is never empty while the API is loading.
 */
import { useMemo } from 'react';
import type { TFunction } from 'i18next';
import { useDistinctErrorCodes } from './hooks';

export type ErrorCodeOption = { value: string; label: string };

/** Keep for backwards compatibility with existing test/consumer imports. */
export type KnownErrorCode =
  | 'UPSTREAM_FAILURE'
  | 'upstream_error'
  | 'provider_timeout'
  | 'provider_rate_limited'
  | 'provider_auth_failed'
  | 'unsupported_capability'
  | 'validation_error'
  | 'session_closed';

/** Local fallback — the most common error codes with human-readable labels. */
const LOCAL_KNOWN_LABELS: Record<string, string> = {
  UPSTREAM_FAILURE: 'UPSTREAM_FAILURE',
  upstream_error: 'upstream_error',
  provider_timeout: 'provider_timeout',
  provider_rate_limited: 'provider_rate_limited',
  provider_auth_failed: 'provider_auth_failed',
  unsupported_capability: 'unsupported_capability',
  validation_error: 'validation_error',
  session_closed: 'session_closed',
};

/** Static getter – used in tests and as fallback for the hook. */
export function getErrorCodeOptions(t: TFunction<'common'>): ErrorCodeOption[] {
  return Object.keys(LOCAL_KNOWN_LABELS).map((code) => ({
    value: code,
    label: `${code} — ${t(`modules.modelMonitoring.errors.errorCodeLabels.${code}`, code)}`,
  }));
}

function buildErrorCodeOptions(
  errorCodes: string[] | undefined,
  t: TFunction<'common'>,
): ErrorCodeOption[] {
  const codes = errorCodes?.length ? errorCodes : Object.keys(LOCAL_KNOWN_LABELS);
  return codes.map((code) => {
    const translated = t(`modules.modelMonitoring.errors.errorCodeLabels.${code}`, '');
    const label = translated ? `${code} — ${translated}` : code;
    return { value: code, label };
  });
}

/**
 * Hook: returns error code filter options, preferring codes that actually
 * exist in the DB (via API), falling back to the local known list.
 */
export function useErrorCodeOptions(t: TFunction<'common'>): ErrorCodeOption[] {
  const { data } = useDistinctErrorCodes();
  return useMemo(() => buildErrorCodeOptions(data?.errorCodes, t), [data?.errorCodes, t]);
}
