"use client";

import { ReactNode, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function ProtectedPage({ children }: { children: ReactNode }) {
  const { user, isLoading, forceLocalLogout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const checkLogoutFlag = () => {
      const forcedLogout = localStorage.getItem("forgeai_force_logged_out") === "1";

      if (forcedLogout) {
        forceLocalLogout();
        router.replace("/login");
      }
    };

    checkLogoutFlag();

    window.addEventListener("pageshow", checkLogoutFlag);
    window.addEventListener("focus", checkLogoutFlag);

    return () => {
      window.removeEventListener("pageshow", checkLogoutFlag);
      window.removeEventListener("focus", checkLogoutFlag);
    };
  }, [forceLocalLogout, router]);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, user, router, pathname]);

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <div className="text-center">
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-white/20 border-t-white" />
          <p className="text-sm text-white/70">Chargement de ForgeAI...</p>
        </div>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <p className="animate-pulse text-sm text-white/70">
          Redirection vers la connexion...
        </p>
      </main>
    );
  }

  return <>{children}</>;
}