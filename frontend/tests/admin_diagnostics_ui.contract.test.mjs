/*
 * Sprint 7.8 readable analysis diagnostic, console side.
 *
 *   U1  the page displays what the backend decided (summary, steps with
 *       French status, notes, errors): no step name or status is mapped
 *       or recomputed in the browser;
 *   U2  a degraded step ("Réussie avec repli") is visually distinct;
 *   U3  what the analysis does not record is said on the page;
 *   U4  the raw analysis_data stays available, collapsed, and is only
 *       serialised when opened (it can weigh more than 1 MB);
 *   U5  the old raw panels (English step keys, blind error dump) are gone.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
const page = read("app/admin/analyses/[id]/page.tsx");

test("U1: summary and steps come from the backend", () => {
  assert.match(page, /diagnostics\.summary\.headline/);
  assert.match(page, /diagnostics\.steps\.map\(/);
  assert.match(page, /step\.status_label/);
  assert.match(page, /step\.notes/);
  assert.match(page, /step\.error/);
  for (const key of ["idea_readiness_check", "fallback_used", "error_handled", "completed_steps"]) {
    assert.doesNotMatch(page, new RegExp(key), key);
  }
});

test("U2: each status has its own look, degraded included", () => {
  for (const status of ["completed", "degraded", "failed", "running", "not_run"]) {
    assert.match(page, new RegExp(`\\b${status}: "`), status);
  }
  for (const level of ["ok", "warning", "error", "running", "not_started"]) {
    assert.match(page, new RegExp(`\\b${level}: "`), level);
  }
});

test("U3: sources, evidence and what is not recorded", () => {
  assert.match(page, /diagnostics\.sources\.confidence_label/);
  assert.match(page, /diagnostics\.evidence\.verdict_label/);
  assert.match(page, /diagnostics\.not_recorded/);
  assert.match(page, /diagnostics\.queries\.unique/);
  assert.match(page, /formatDuration\(/);
});

test("U4: raw JSON collapsed and serialised only when opened", () => {
  assert.match(page, /<details/);
  assert.match(page, /onToggle=/);
  assert.match(page, /Données brutes \(JSON\)/);
  assert.match(page, /showRaw \? <JsonBlock/);
});

test("U5: the old raw panels are gone", () => {
  assert.doesNotMatch(page, /diagnostics\.technical/);
  assert.doesNotMatch(page, /diagnostics\.startup_evaluator/);
  assert.doesNotMatch(page, /analysis_error brut/);
});
