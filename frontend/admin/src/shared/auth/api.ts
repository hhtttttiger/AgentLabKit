import { apiRequest } from '@/shared/api/client';
import type {
  ChangePasswordRequest,
  CreateUserRequest,
  LoginRequest,
  LoginResponse,
  UpdateProfileRequest,
  UpdateUserRequest,
  UserListItem,
} from './types';

// ── Auth ─────────────────────────────────────────────────────────────

export function login(request: LoginRequest): Promise<LoginResponse> {
  return apiRequest<LoginResponse>('/api/auth/token', {
    method: 'POST',
    body: request,
    skipAuth: true,
  });
}

// ── Current user ─────────────────────────────────────────────────────

export function getMe(): Promise<UserListItem> {
  return apiRequest<UserListItem>('/api/auth/me');
}

export function changePassword(data: ChangePasswordRequest): Promise<void> {
  return apiRequest('/api/auth/password', {
    method: 'PUT',
    body: data,
  });
}

export function updateProfile(data: UpdateProfileRequest): Promise<UserListItem> {
  return apiRequest<UserListItem>('/api/auth/profile', {
    method: 'PUT',
    body: data,
  });
}

// ── User management (admin) ──────────────────────────────────────────

export type PagedResult<T> = {
  items: T[];
  totalCount: number;
  page: number;
  pageSize: number;
};

export function listUsers(params?: { page?: number; pageSize?: number }): Promise<PagedResult<UserListItem>> {
  return apiRequest<PagedResult<UserListItem>>('/api/auth/users', {
    query: params,
  });
}

export function getUser(id: string): Promise<UserListItem> {
  return apiRequest<UserListItem>(`/api/auth/users/${id}`);
}

export function createUser(data: CreateUserRequest): Promise<UserListItem> {
  return apiRequest<UserListItem>('/api/auth/register', {
    method: 'POST',
    body: data,
  });
}

export function updateUser(id: string, data: UpdateUserRequest): Promise<UserListItem> {
  return apiRequest<UserListItem>(`/api/auth/users/${id}`, {
    method: 'PUT',
    body: data,
  });
}

export function deleteUser(id: string): Promise<UserListItem> {
  return apiRequest<UserListItem>(`/api/auth/users/${id}`, {
    method: 'DELETE',
  });
}
