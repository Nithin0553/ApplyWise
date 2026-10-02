// F01: public contract of the auth feature. Other features should import
// only from here, not from this folder's internal files directly.

export { AuthProvider, useAuth } from "./AuthContext";
export { LoginForm } from "./LoginForm";
export { RegisterForm } from "./RegisterForm";
export { RequireRole } from "./RequireRole";
export type { AuthResponse, LoginInput, RegisterInput, User, UserRole } from "./types";
