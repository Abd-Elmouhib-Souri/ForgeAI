/*
 * Sprint 7.2 admin audit log, console side.
 *
 * The page reads the separate admin API (never the public one), downloads
 * the CSV with the bearer token in a header (never in the URL, which ends
 * up in logs and history), and offers no way to edit or delete an entry.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const page = read("../app/admin/audit/page.tsx");
const client = read("../lib/admin-api.ts");
const dashboard = read("../app/admin/dashboard/page.tsx");

test("audit page reads the admin API list, actions and CSV export", () => {
  assert.match(page, /adminFetch\(\s*`\/admin\/audit\$\{buildQuery/);
  assert.match(page, /adminFetch\("\/admin\/audit\/actions"\)/);
  assert.match(page, /adminDownload\(`\/admin\/audit\/export\.csv\$\{buildQuery\(filters\)\}`/);
  assert.doesNotMatch(page, /from "@\/lib\/api"/);
});

test("audit page is read-only", () => {
  assert.doesNotMatch(page, /method:\s*"(PATCH|PUT|DELETE|POST)"/);
});

test("CSV download sends the token in a header, never in the URL", () => {
  const download = client.slice(client.indexOf("export async function adminDownload"));
  assert.match(download, /Authorization: `Bearer \$\{token\}`/);
  assert.doesNotMatch(client, /[?&](token|access_token)=/);
  assert.match(download, /URL\.revokeObjectURL/);
});

test("dashboard links to the audit log", () => {
  assert.match(dashboard, /href="\/admin\/audit"/);
});
