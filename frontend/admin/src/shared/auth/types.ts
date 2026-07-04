export type AuthUser = {
  userId: string;
  userName: string | null;
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
