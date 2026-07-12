export type AuthUser = {
  userId: string;
  userName: string | null;
  role: string;
};

export type LoginRequest = {
  username: string;
  password: string;
  provider?: string;
};

export type LoginResponse = {
  accessToken: string;
  expiresInMinutes: number;
};

// ── User management types ────────────────────────────────────────────

export type UserListItem = {
  id: string;
  username: string;
  displayName: string | null;
  email: string | null;
  role: string;
  isActive: boolean;
  lastLoginAtUtc: string | null;
  createdAtUtc: string;
  updatedAtUtc: string;
};

export type CreateUserRequest = {
  username: string;
  password: string;
  displayName?: string;
  email?: string;
  role?: string;
};

export type UpdateUserRequest = {
  displayName?: string;
  email?: string;
  role?: string;
  isActive?: boolean;
};

export type ChangePasswordRequest = {
  oldPassword: string;
  newPassword: string;
};

export type UpdateProfileRequest = {
  displayName?: string;
  email?: string;
};
