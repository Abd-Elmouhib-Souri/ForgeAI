/*
 * Sprint 7.7 real health checks, console side.
 *
 *   I1  the page reads /admin/health through the shared loader, and
 *       "Tester maintenant" asks the API to test again (refresh=true);
 *   I2  statuses are shown in French, never as raw codes ("healthy",
 *       "Model:" were displayed before);
 *   I3  latency, missing models and migration revisions are visible.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
const page = read("app/admin/health/page.tsx");
const labels = read("app/admin/_components/labels.ts");

test("I1: shared loader + refresh on demand", () => {
  assert.match(page, /useAdminResource<HealthReport>\(/);
  assert.match(page, /refresh=true/);
  assert.match(page, /Tester maintenant/);
  assert.doesNotMatch(page, /useEffect\(/);
});

test("I2: French statuses, no raw code", () => {
  for (const pair of ['healthy: "Opérationnel"', 'degraded: "Dégradé"', 'down: "Hors service"', 'not_configured: "Non configuré"']) {
    assert.ok(labels.includes(pair), pair);
  }
  assert.match(page, /healthStatusLabel\(/);
  assert.doesNotMatch(page, /\{service\.status\}|\{report\.overall_status\}/);
  assert.doesNotMatch(page, /Model:/);
});

test("I3: latency and details are visible", () => {
  assert.match(page, /latency_ms/);
  assert.match(page, /missing_models/);
  assert.match(page, /details\.database/);
});
