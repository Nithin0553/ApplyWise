# F01 Authentication UI

Feature-owned UI for registration, login, role-aware access, and session flows.

## Public contract

Other features should only import from `./index.ts`:

- `AuthProvider` / `useAuth()` — current user, bearer token, and
  login/register/logout actions.
- `RequireRole` — conditionally render UI by role. This is a display
  convenience only, not a security boundary; the server-side
  `require_role` dependency in `apps/api/app/modules/auth/dependencies.py`
  is what actually enforces access.
- `LoginForm` / `RegisterForm` — ready-to-use forms wired to `useAuth()`.

Internal files (`api.ts`, `AuthContext.tsx`, etc.) may change without
notice; do not import them directly from another feature.
