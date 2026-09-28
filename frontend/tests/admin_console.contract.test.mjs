/*
 * Sprint 7.3 unified admin console.
 *
 * Observed REDs (audit 27 Sept 2026):
 *   C1  every admin page re-implemented its own header and link bar, each
 *       with a different subset of links (no way to reach the audit log from
 *       most pages), in English ("Users", "Projects", "Health", "Errors");
 *   C2  sensitive actions asked the 2FA code with window.prompt and the
 *       deletions with window.confirm (unstyled, blockable, no retry);
 *   C3  the admin console mounted the PUBLIC AuthProvider, which calls the
 *       public /auth/refresh on every admin page load;
 *   C4  raw codes shown to the admin: roles ("student"), analysis statuses
 *       ("completed"), English labels ("Owner", "Completed", "Status").
 */

import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const read = (path) => readFileSync(join(root, path), "utf8");

function adminPages() {
  const out = [];
  const walk = (dir) => {
    for (const name of readdirSync(join(root, dir))) {
      const rel = `${dir}/${name}`;
      if (statSync(join(root, rel)).isDirectory()) walk(rel);
      else if (name === "page.tsx" && !rel.startsWith("app/admin/login")) out.push(rel);
    }
  };
  walk("app/admin");
  return out;
}

const pages = adminPages();
const shellPath = "app/admin/_components/AdminShell.tsx";

test("C1: one shared shell for every console page, login excluded", () => {
  assert.ok(pages.length >= 9, pages.join(", "));
  const layout = read("app/admin/layout.tsx");
  assert.match(layout, /AdminShell/);
  const shell = read(shellPath);
  assert.match(shell, /pathname === "\/admin\/login"/);
  for (const [href, label] of [
    ["/admin/dashboard", "Tableau de bord"],
    ["/admin/users", "Utilisateurs"],
    ["/admin/projects", "Projets"],
    ["/admin/analyses", "Analyses IA"],
    ["/admin/errors", "Erreurs"],
    ["/admin/health", "Santé du système"],
    ["/admin/audit", "Journal d'audit"],
  ]) {
    assert.ok(shell.includes(`href: "${href}"`) && shell.includes(label), `${href} / ${label}`);
  }
  for (const section of ["Pilotage", "Clients", "Intelligence", "Plateforme", "Mon compte"]) {
    assert.ok(shell.includes(section), section);
  }
});

test("C1: pages no longer carry their own navigation bar", () => {
  for (const page of pages) {
    const source = read(page);
    assert.doesNotMatch(source, /<nav[\s>]/, `${page} still has a <nav>`);
    assert.doesNotMatch(source, /<header[\s>]/, `${page} still has a <header>`);
    assert.match(source, /AdminPageHeader/, `${page} must use AdminPageHeader`);
  }
});

test("C2: no browser prompt / confirm anywhere in the console", () => {
  for (const file of [...pages, "app/admin/login/page.tsx", "lib/admin-api.ts", shellPath]) {
    assert.doesNotMatch(read(file), /window\.(prompt|confirm)\(/, file);
  }
});

test("C2: sensitive calls go through the console's confirmation dialog", () => {
  const client = read("lib/admin-api.ts");
  assert.match(client, /export function setConfirmationHandler/);
  assert.match(client, /export function isAdminActionCancelled/);
  // A wrong code re-opens the dialog with the backend's reason.
  assert.match(client, /confirmation_invalid/);

  const dialog = read("app/admin/_components/ConfirmDialog.tsx");
  assert.match(dialog, /setConfirmationHandler\(/);
  assert.match(dialog, /autoComplete="one-time-code"/);
  assert.match(dialog, /role="dialog"/);
  assert.match(dialog, /aria-modal="true"/);
  assert.match(read(shellPath), /ConfirmDialog/);

  // Deletions describe what is deleted inside the same dialog.
  assert.match(read("app/admin/users/page.tsx"), /confirm: `Supprimer définitivement le compte/);
  assert.match(read("app/admin/projects/page.tsx"), /confirm: `Supprimer définitivement le projet/);
  for (const page of ["app/admin/users/page.tsx", "app/admin/projects/page.tsx"]) {
    assert.match(read(page), /isAdminActionCancelled\(err\)/, page);
  }
});

test("C3: the public session provider is not mounted on /admin", () => {
  const layout = read("app/layout.tsx");
  assert.doesNotMatch(layout, /<AuthProvider>/);
  assert.match(layout, /<Providers>/);
  const providers = read("app/providers.tsx");
  assert.match(providers, /pathname\?\.startsWith\("\/admin"\)/);
  const adminBranch = providers.slice(providers.indexOf('startsWith("/admin")'));
  assert.ok(adminBranch.indexOf("return <>{children}</>") < adminBranch.indexOf("<AuthProvider>"));
  for (const file of [...pages, shellPath, "lib/admin-api.ts"]) {
    assert.doesNotMatch(read(file), /auth-context|from "@\/lib\/api"/, file);
  }
});

test("C3: the shell ends the session when the 15-minute admin token expires", () => {
  const shell = read(shellPath);
  assert.match(shell, /getAdminTokenExpiry\(\)/);
  assert.match(shell, /adminLogout\(/);
  assert.match(read("lib/admin-api.ts"), /export function getAdminTokenExpiry/);
});

test("C4: French labels, no raw codes or English words", () => {
  const forbidden = [
    ">Users<", ">Projects<", ">Health<", ">Errors<", ">Dashboard<",
    "Dashboard administrateur", "Health système", "Top secteurs", "Top régions",
    ">Owner<", "Status analyse", 'label="Completed"', 'label="Status"', 'title="Admins"',
  ];
  for (const page of pages) {
    const source = read(page);
    for (const word of forbidden) {
      assert.ok(!source.includes(word), `${page} still shows ${word}`);
    }
  }
  const labels = read("app/admin/_components/labels.ts");
  assert.match(labels, /student: "Étudiant"/);
  assert.match(labels, /completed: "Terminée"/);
  for (const page of [
    "app/admin/projects/page.tsx",
    "app/admin/analyses/page.tsx",
    "app/admin/analyses/[id]/page.tsx",
    "app/admin/users/[id]/page.tsx",
    "app/admin/errors/page.tsx",
  ]) {
    assert.match(read(page), /analysisStatusLabel\(/, page);
  }
  assert.match(read("app/admin/users/page.tsx"), /roleLabel\(/);
});

test("C4: audit reasons come from the backend label, not a frontend copy", () => {
  const audit = read("app/admin/audit/page.tsx");
  assert.match(audit, /detail_label/);
  assert.doesNotMatch(audit, /bad_credentials:/);
});

test("shell files exist", () => {
  for (const file of [shellPath, "app/admin/_components/ConfirmDialog.tsx",
    "app/admin/_components/AdminPageHeader.tsx", "app/admin/_components/labels.ts",
    "app/admin/layout.tsx", "app/providers.tsx"]) {
    assert.ok(existsSync(join(root, file)), file);
  }
});
