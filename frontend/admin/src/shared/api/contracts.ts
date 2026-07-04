export type ApiEnvelope<T> = {
  success: boolean;
  msg: string;
  data: T;
};

export type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  query?: Record<string, string | number | boolean | null | undefined>;
  body?: unknown;
  /** Send as FormData (multipart/form-data) — browser sets Content-Type with boundary. */
  formBody?: FormData;
  signal?: AbortSignal;
  /** Skip Authorization header (e.g. login endpoint). */
  skipAuth?: boolean;
};
