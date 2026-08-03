import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const paths = {
  types: "app/projects/[id]/_types/project-detail.types.ts",
  client: "app/projects/[id]/_components/ProjectDetailClient.tsx",
  journey: "app/projects/[id]/_sections/AnalysisJourneySection.tsx",
};

async function read(path) {
  return readFile(
    new URL(`../${path}`, import.meta.url),
    "utf8"
  );
}

test(
  "analysis status exposes needs_clarification",
  async () => {
    const source = await read(paths.types);

    assert.match(
      source,
      /\|\s*"needs_clarification"/
    );

    assert.match(
      source,
      /idea_readiness\?:\s*IdeaReadinessData/
    );

    assert.match(
      source,
      /context_confidence\?:\s*ContextConfidenceData/
    );

    assert.match(
      source,
      /project_context_packet\?:\s*ProjectContextPacketData/
    );
  }
);

test(
  "polling treats needs_clarification as terminal",
  async () => {
    const source = await read(paths.client);

    assert.match(
      source,
      /TERMINAL_ANALYSIS_STATUSES[\s\S]*"needs_clarification"/
    );

    assert.match(
      source,
      /isTerminalAnalysisStatus\(result\?\.analysis_status\)/
    );

    assert.match(
      source,
      /currentStatus === "needs_clarification"/
    );
  }
);

test(
  "clarification UI exposes score, fields, questions, and edit action",
  async () => {
    const source = await read(paths.client);

    assert.match(
      source,
      /ContextClarificationPanel/
    );

    assert.match(
      source,
      /readiness\.missingFields/
    );

    assert.match(
      source,
      /readiness\.ambiguousFields/
    );

    assert.match(
      source,
      /readiness\.blockers/
    );

    assert.match(
      source,
      /readiness\.questions/
    );

    assert.match(
      source,
      /editHref=\{`\/projects\/\$\{id\}\/edit`\}/
    );
  }
);

test(
  "frontend does not invent Tunisia as the detail fallback",
  async () => {
    const source = await read(paths.client);

    assert.doesNotMatch(
      source,
      /defaultRegion:\s*"Tunisie"/
    );

    assert.match(
      source,
      /defaultRegion:\s*"Non définie"/
    );
  }
);

test(
  "validation journey starts with the canonical context gate",
  async () => {
    const source = await read(paths.journey);

    assert.match(
      source,
      /contextReadinessState/
    );

    assert.match(
      source,
      /Project context validated/
    );

    assert.match(
      source,
      /Contexte projet validé/
    );

    assert.match(
      source,
      /Clarification required/
    );

    assert.match(
      source,
      /Clarification requise/
    );
  }
);