/*
 * Admin console navigation and buttons (RED from the user's screenshots,
 * 30 Sept 2026: "améliorer plus les boutons de navigation").
 *
 * Observed REDs:
 *   N1  ~25 hand-written button styles, no keyboard focus ring, no loading state;
 *   N2  the sidebar was plain text links (no icon, weak active state);
 *   N3  the "← Analyses IA" back link was 12px grey text;
 *   N4  the pager had only Précédent/Suivant, the audit page its own copy;
 *   N5  filters were plain buttons without aria-pressed, duplicated per page;
 *   N6  the analyses table forced min-width 1250px inside a ~1230px card:
 *       it always scrolled sideways, the date wrapped on 3 lines and the
 *       row actions stacked.
 */

import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const root = fileURLToPath(new URL("../", import.meta.url));
const read = (path) => readFileSync(join(root, path), "utf8").replace(/\r\n/g, "\n");

function tsxFiles(dir) {
  return readdirSync(join(root, dir)).flatMap((name) => {
    const path = join(dir, name);
    return statSync(join(root, path)).isDirectory() ? tsxFiles(path) : path.endsWith(".tsx") ? [path] : [];
  });
}

const adminFiles = tsxFiles("app/admin");
const button = read("app/admin/_components/Button.tsx");
const shell = read("app/admin/_components/AdminShell.tsx");
const header = read("app/admin/_components/AdminPageHeader.tsx");
const pager = read("app/admin/_components/Pagination.tsx");
const tabs = read("app/admin/_components/FilterTabs.tsx");
const analyses = read("app/admin/analyses/page.tsx");

test("N1: one shared button with variants, focus ring and loading state", () => {
  for (const name of ["export function Button", "export function ButtonLink", "export function buttonClass"]) {
    assert.ok(button.includes(name), name);
  }
  for (const variant of ["primary", "secondary", "warning", "info", "danger", "success", "ghost"]) {
    assert.match(button, new RegExp(`\\b${variant}: "`), variant);
  }
  assert.match(button, /focus-visible:ring-2/);
  assert.match(button, /disabled:cursor-not-allowed/);
  assert.match(button, /aria-busy=\{loading/);
  assert.match(button, /LoaderCircle/);
});

test("N1: no page hand-writes a button or a button-looking link any more", () => {
  const allowed = new Set(["app/admin/_components/Button.tsx", "app/admin/_components/FilterTabs.tsx"]);
  for (const file of adminFiles) {
    const rel = relative(root, join(root, file)).replaceAll("\\", "/");
    if (allowed.has(rel)) continue;
    const source = read(file);
    assert.doesNotMatch(source, /<button[\s>]/, `${rel}: use <Button>`);
    if (rel !== "app/admin/_components/AdminShell.tsx") {
      assert.doesNotMatch(source, /<Link[^>]*className="[^"]*rounded-lg/, `${rel}: use <ButtonLink>`);
    }
  }
});

test("N2: sidebar items carry an icon, a clear active state and a focus ring", () => {
  const items = shell.match(/\{ href: "\/admin\/[a-z]+", label: "[^"]+", icon: [A-Za-z]+ \}/g) ?? [];
  assert.equal(items.length, 7, "7 entries with an icon");
  assert.match(shell, /aria-current=\{active \? "page" : undefined\}/);
  assert.match(shell, /focus-visible:ring-2/);
  assert.match(shell, /aria-controls="admin-mobile-menu"/);
  assert.match(shell, /icon=\{LogOut\}/);
});

test("N3: the back link is a real button with an arrow", () => {
  assert.match(header, /<ButtonLink/);
  assert.match(header, /icon=\{ArrowLeft\}/);
  assert.doesNotMatch(header, /← \{backLabel\}/);
});

test("N4: full pager, reused by the audit page", () => {
  for (const label of ["Première page", "Page précédente", "Page suivante", "Dernière page"]) {
    assert.ok(pager.includes(`aria-label="${label}"`), label);
  }
  assert.match(read("app/admin/audit/page.tsx"), /<Pagination/);
});

test("N5: filters are one accessible toggle group", () => {
  assert.match(tabs, /role="group"/);
  assert.match(tabs, /aria-pressed=\{active\}/);
  for (const file of ["app/admin/analyses/page.tsx", "app/admin/users/page.tsx"]) {
    const source = read(file);
    assert.match(source, /<FilterTabs/, file);
    assert.doesNotMatch(source, /function FilterButton/, file);
  }
});

test("N6: list tables fit their card (~1180px), actions stay on one line", () => {
  // Users (1250px) and projects (1200px) had the same forced width as analyses.
  for (const file of ["app/admin/analyses/page.tsx", "app/admin/users/page.tsx", "app/admin/projects/page.tsx"]) {
    const widths = [...read(file).matchAll(/min-w-\[(\d+)px\]/g)].map((match) => Number(match[1]));
    assert.ok(widths.every((width) => width <= 1000), `${file}: ${widths}`);
  }
  assert.match(analyses, /icon=\{RotateCcw\}/);
  assert.match(analyses, /icon=\{Stethoscope\}/);
  assert.match(analyses, /whitespace-nowrap px-3 py-4 text-white\/60/); // the end date never wraps
});
