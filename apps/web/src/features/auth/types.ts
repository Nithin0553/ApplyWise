// F01: shared types for the auth feature. Keep in sync with the backend
// contracts in apps/api/app/modules/auth/schemas.py.

export type UserRole = "job_seeker" | "administrator";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface RegisterInput {
  email: string;
  password: string;
  fullName: string;
}

export interface LoginInput {
  email: string;
  password: string;
}
