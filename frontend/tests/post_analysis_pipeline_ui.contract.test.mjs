/*
 * Post-analysis pipeline UI contracts.
 *
 * Observed product REDs (project 31, 23 Sept 2026):
 *   U1  "Générer le plan / l'architecture / Exporter" buttons were visible
 *       while the analysis was still running.
 *   U2  At 100 % nothing appeared until each button was clicked.
 *   U3  Every Solution Architect failure read "service temporairement
 *       indisponible" even for a decommissioned model.
 *
 * Source-level contracts, same style as the existing frontend suite.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");

const detail = read("../app/projects/[id]/_components/ProjectDetailClient.tsx");
const panel = read("../app/projects/[id]/_components/PostAnalysisPipelinePanel.tsx");
const pipelineLib = read("../app/projects/[id]/_lib/pipeline.ts");
const architecture = read("../app/projects/[id]/_sections/SolutionArchitectSection.tsx");
const classifier = read("../../backend/app/services/llm_failure_classifier.py");
const backendPipeline = read("../../backend/app/services/post_analysis_pipeline.py");

// U1 ------------------------------------------------------------------------

test("sections are gated behind a completed analysis and a displayable stage", () => {
  assert.match(detail, /const analysisIsCompleted = currentStatus === "completed";/);
  assert.match(detail, /\{showPlan && \(\s*<ProjectManagerSection/);
  assert.match(detail, /\{showArchitecture && \(\s*<SolutionArchitectSection/);
  assert.match(detail, /\{showExport && \(\s*<ExportSection/);
  assert.match(detail, /const showPlan = analysisIsCompleted && isStageDisplayable\(planStage\);/);
});

test("pipeline panel only mounts once the analysis is completed", () => {
  assert.match(detail, /\{analysisIsCompleted && \(\s*<PostAnalysisPipelinePanel/);
});

// U2 ------------------------------------------------------------------------

test("panel polls the backend pipeline state and never generates by itself", () => {
  assert.match(panel, /api\.get<PipelineState>\(`\/projects\/\$\{projectId\}\/pipeline`\)/);
  assert.match(panel, /api\.post\(`\/projects\/\$\{projectId\}\/pipeline\/run`\)/);
  assert.doesNotMatch(panel, /project-manager\/generate|solution-architecture\/generate/);
  assert.match(panel, /window\.setTimeout/);
  assert.match(panel, /window\.clearTimeout/);
});

test("sections reload when their stage finishes (provisional plan upgrade)", () => {
  assert.match(detail, /planStage\?\.finished_at \?\? analysisCompletedAt/);
  assert.match(detail, /architectureStage\?\.finished_at \?\? analysisCompletedAt/);
});

test("a previous run's pipeline state is never shown after a relaunch", () => {
  assert.match(detail, /pipelineSnapshot\.marker === analysisCompletedAt/);
});

// U3 ------------------------------------------------------------------------

test("every backend failure code has a human message", () => {
  const codes = [...classifier.matchAll(/^[A-Z_]+ = "([a-z_]+)"$/gm)].map((m) => m[1]);
  assert.ok(codes.length >= 5, "classifier codes must be discoverable");
  for (const code of [...codes, "ai_fallback_used"]) {
    assert.match(pipelineLib, new RegExp(`\\b${code}:`), `missing UI message for ${code}`);
  }
});

test("every backend stage status has a label", () => {
  const statuses = [
    ...backendPipeline.matchAll(/^(PENDING|RUNNING|COMPLETED|DEGRADED|WAITING_RETRY|FAILED|NOT_STARTED) = "([a-z_]+)"$/gm),
  ].map((m) => m[2]);
  assert.equal(statuses.length, 7);
  for (const status of statuses) {
    assert.match(pipelineLib, new RegExp(`\\b${status}: "`), `missing label for ${status}`);
  }
});

test("architecture errors use the backend reason instead of a generic message", () => {
  assert.match(architecture, /const reason = \(detail as \{ reason\?: unknown \}\)\.reason;/);
  assert.match(architecture, /failureReasonMessage\(reason, language\)/);
  assert.doesNotMatch(architecture, /générée à la demande/);
});

test("project-specific stack layers are displayed, not silently dropped", () => {
  assert.match(architecture, /Object\.entries\(architecture\.stack\.additional_layers \?\? \{\}\)/);
});

test("diagrams are re-rendered after every regeneration, even with an unchanged context", () => {
  // Real run 25 Sept 2026: "Régénérer l'architecture" cleared the SVGs but the
  // render effect was keyed on context_fingerprint, which does not change.
  assert.match(architecture, /\}, \[architecture, loadRender\]\);/);
  assert.doesNotMatch(architecture, /\[architecture\?\.context_fingerprint, loadRender\]/);
});
