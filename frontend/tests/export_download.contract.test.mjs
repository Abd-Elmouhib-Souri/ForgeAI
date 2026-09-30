/*
 * Sprint 6.1 export hardening, frontend side.
 *
 * The backend no longer serves /exports publicly: the file is streamed by
 * GET /projects/{id}/exports/{export_id}/download, which requires the
 * bearer token. That token lives in axios memory, so a plain <a href> can
 * never authenticate: the section must fetch a Blob through `api`.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const section = readFileSync(
  new URL("../app/projects/[id]/_sections/ExportSection.tsx", import.meta.url),
  "utf8",
);

test("export download goes through the authenticated api client as a blob", () => {
  assert.match(section, /api\.get<Blob>\(\s*\w+\.url,\s*\{\s*responseType: "blob"\s*\}/);
  assert.match(section, /URL\.createObjectURL\(/);
  assert.match(section, /URL\.revokeObjectURL\(/);
});

test("no public export URL is ever built", () => {
  assert.doesNotMatch(section, /NEXT_PUBLIC_API_URL/);
  assert.doesNotMatch(section, /file_path/);
  assert.match(section, /download_url: string;/);
  assert.match(section, /file_name: string;/);
});

test("export labels are properly accented French", () => {
  assert.match(section, /Télécharge le rapport complet/);
  assert.match(section, /Génération en cours/);
  assert.doesNotMatch(section, /Telecharge|Generation du|echoue|Reessayez/);
});
