import type { ReactNode } from "react";

import AdminShell from "./_components/AdminShell";

// Sprint 7.3: every /admin page shares the console frame (login excluded
// inside AdminShell).
export default function AdminLayout({ children }: { children: ReactNode }) {
  return <AdminShell>{children}</AdminShell>;
}
