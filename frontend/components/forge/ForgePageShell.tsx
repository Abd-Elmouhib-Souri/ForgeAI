"use client";

import type { ReactNode } from "react";
import ForgeNavbar from "@/components/forge/ForgeNavbar";

type ForgePageShellProps = {
  children: ReactNode;
  active?: "dashboard" | "projects" | "new-project" | "none";
  showNavbar?: boolean;
};

export default function ForgePageShell({
  children,
  active = "none",
  showNavbar = true,
}: ForgePageShellProps) {
  return (
    <main className="forge-page min-h-screen">
      {showNavbar && <ForgeNavbar active={active} />}
      {children}
    </main>
  );
}