import i18n from '@/shared/i18n';

export class ApiError extends Error {
  status: number;
  code?: string;
  detail?: string;

  constructor(message: string, status: number, detail?: string, code?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.code = code;
  }
}

export function getErrorMessage(error: unknown, fallback?: string) {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback ?? i18n.t('api.requestFailed');
}
