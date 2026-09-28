"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { AuthProvider } from "@/lib/auth-context";
import { LanguageProvider } from "@/lib/language-context";

// Sprint 7.3 (RED C3): the admin console has its own session (admin API,
// port 8002). The public providers must not run there: AuthProvider calls
// the public /auth/refresh on mount, which has nothing to do with an admin.
export default function Providers({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname?.startsWith("/admin")) {
    return <>{children}</>;
  }
  return (
    <LanguageProvider>
      <AuthProvider>{children}</AuthProvider>
    </LanguageProvider>
  );
}
