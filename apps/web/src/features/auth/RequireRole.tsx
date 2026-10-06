// F01: client-side RBAC gate for conditionally rendering UI by role.
//
// This only hides/shows UI; it is not a security boundary on its own. The
// corresponding server-side check (`require_role` in
// apps/api/app/modules/auth/dependencies.py) is what actually enforces
// access, per "authorization is enforced server-side" in
// docs/ARCHITECTURE.md.

import type { ReactNode } from "react";

import { useAuth } from "./AuthContext";
import type { UserRole } from "./types";

interface RequireRoleProps {
  allow: UserRole[];
  children: ReactNode;
  fallback?: ReactNode;
}

export function RequireRole({ allow, children, fallback = null }: RequireRoleProps) {
  const { user } = useAuth();

  if (!user || !allow.includes(user.role)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
