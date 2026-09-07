import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const cwd = process.cwd();

const frontendRoot = fs.existsSync(
  path.join(cwd, "app", "projects"),
)
  ? cwd
  : path.join(cwd, "frontend");

const pmPath = path.join(
  frontendRoot,
  "app",
  "projects",
  "[id]",
  "_sections",
  "ProjectManagerSection.tsx",
);

const parentPath = path.join(
  frontendRoot,
  "app",
  "projects",
  "[id]",
  "_components",
  "ProjectDetailClient.tsx",
);

const pmSource = fs.readFileSync(pmPath, "utf8");
const parentSource = fs.readFileSync(parentPath, "utf8");

test(
  "Project Manager reloads the existing backend plan when analysis completion changes",
  () => {
    /*
     * Universal invariant:
     *
     * The backend owns ProjectManagementPlan truth.
     *
     * ProjectManagerSection may mount before analysis completes.
     * When analysis later completes and the backend automatically
     * persists a Project Management plan, the frontend must reload
     * that existing plan.
     *
     * It must not require the user to POST /generate merely to
     * discover a plan that already exists.
     */

    const callStart = parentSource.indexOf("<ProjectManagerSection");

    assert.notEqual(
      callStart,
      -1,
      "ProjectManagerSection call site must exist",
    );

    const callEnd = parentSource.indexOf("/>", callStart);

    assert.notEqual(
      callEnd,
      -1,
      "ProjectManagerSection call site must be complete",
    );

    const callSite = parentSource.slice(callStart, callEnd + 2);

    assert.match(
      callSite,
      /analysisCompletedAt\s*=/,
      "parent must pass the canonical analysis completion marker",
    );

    assert.match(
      pmSource,
      /analysisCompletedAt\??\s*:\s*string\s*\|\s*null/,
      "ProjectManagerSection must accept the analysis completion marker",
    );

    const effectMatch = pmSource.match(
      /useEffect\(\(\)\s*=>\s*\{[\s\S]*?void\s+load\(\)[\s\S]*?\},\s*\[([^\]]+)\]\s*\);/,
    );

    assert.ok(
      effectMatch,
      "autoload useEffect calling load() must exist",
    );

    assert.match(
      effectMatch[1],
      /\bload\b/,
      "autoload effect must depend on load",
    );

    assert.match(
      effectMatch[1],
      /\banalysisCompletedAt\b/,
      "autoload effect must reload when analysis completion changes",
    );

    /*
     * Loading an existing canonical plan must remain a GET.
     * Automatic lifecycle synchronization must never generate
     * a second plan.
     */
    const effectSource = effectMatch[0];

    assert.doesNotMatch(
      effectSource,
      /project-manager\/generate/,
      "analysis completion synchronization must not generate a new plan",
    );

    assert.doesNotMatch(
      effectSource,
      /api\.post/,
      "analysis completion synchronization must remain read-only",
    );
  },
);
