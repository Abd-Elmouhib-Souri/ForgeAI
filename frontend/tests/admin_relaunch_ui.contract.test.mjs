/*
 * Sprint 7.6 analysis relaunch, console side.
 *
 *   G1  one shared relaunch action (list + detail): POST
 *       /admin/analyses/{id}/relaunch with a 2FA confirmation describing the
 *       project; a cancelled dialog is not an error;
 *   G2  stuck runs are visible ("Bloquée") from the backend flag, never
 *       recomputed from dates in the browser;
 *   G3  the detail page shows the post-analysis pipeline stages in French.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
const relaunch = read("app/admin/_components/relaunch.ts");
const list = read("app/admin/analyses/page.tsx");
const detail = read("app/admin/analyses/[id]/page.tsx");
const labels = read("app/admin/_components/labels.ts");

test("G1: one relaunch action, confirmed by 2FA, used by list and detail", () => {
  assert.match(relaunch, /adminFetch\(`\/admin\/analyses\/\$\{projectId\}\/relaunch`/);
  assert.match(relaunch, /method: "POST"/);
  assert.match(relaunch, /confirm: `Relancer l'analyse du projet « \$\{title\} »/);
  assert.match(relaunch, /export function canRelaunch/);
  for (const [name, source] of [["list", list], ["detail", detail]]) {
    assert.match(source, /relaunchAnalysis\(/, name);
    assert.match(source, /canRelaunch\(/, name);
    assert.match(source, /isAdminActionCancelled\(err\)/, name);
  }
});

test("G2: stuck runs come from the backend flag", () => {
  assert.match(list, /analysis\.analysis_stalled/);
  assert.match(list, /Bloquée/);
  assert.match(detail, /analysis_stalled/);
  for (const source of [list, detail, relaunch]) {
    assert.doesNotMatch(source, /analysis_heartbeat_at/);
    assert.doesNotMatch(source, /Date\.now\(\)/);
  }
});

test("G3: the pipeline stages are shown with French labels", () => {
  assert.match(detail, /detail\.pipeline/);
  assert.match(labels, /project_manager: "Plan projet"/);
  assert.match(labels, /solution_architecture: "Architecture de la solution"/);
  assert.match(labels, /waiting_retry: "Nouvel essai programmé"/);
  assert.match(detail, /pipelineStageLabel\(/);
  assert.match(detail, /pipelineStatusLabel\(/);
});

test("row actions never overlap (RED 28 Sept 2026, user's screenshot)", () => {
  // Buttons wrap inside a flex container with a gap instead of piling up.
  const cell = list.slice(list.indexOf("canRelaunch(analysis.analysis_status") - 400, list.indexOf("Diagnostic"));
  assert.match(cell, /className="flex flex-wrap items-center justify-end gap-2"/);
  assert.doesNotMatch(cell, /className="mr-2 /);
});

test("status badges stay on one line (\"En file d'attente\" broke out of its pill)", () => {
  for (const source of [list, read("app/admin/projects/page.tsx")]) {
    assert.match(source, /whitespace-nowrap rounded-full border px-3 py-1 text-xs \$\{className\}/);
  }
});
