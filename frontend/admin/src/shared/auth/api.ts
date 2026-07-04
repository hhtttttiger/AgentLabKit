import { apiRequest } from '@/shared/api/client';
import type { LoginRequest, LoginResponse } from './types';

export function login(request: LoginRequest): Promise<LoginResponse> {
  return apiRequest<LoginResponse>('/api/auth/token', {
    method: 'POST',
    body: request,
    skipAuth: true,
  });
}
