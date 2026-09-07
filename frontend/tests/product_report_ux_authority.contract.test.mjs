import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";


const FRONTEND = process.cwd();

const REPO = path.resolve(
  FRONTEND,
  "..",
);


function read(...parts) {
  return fs.readFileSync(
    path.join(
      FRONTEND,
      ...parts,
    ),
    "utf8",
  );
}


function readRepo(...parts) {
  return fs.readFileSync(
    path.join(
      REPO,
      ...parts,
    ),
    "utf8",
  );
}


function sourceFiles(root) {
  const output = [];

  for (
    const entry
    of fs.readdirSync(
      root,
      {
        withFileTypes: true,
      },
    )
  ) {

    const absolute = path.join(
      root,
      entry.name,
    );

    if (
      entry.name === "node_modules"
      ||
      entry.name === ".next"
    ) {
      continue;
    }

    if (entry.isDirectory()) {

      output.push(
        ...sourceFiles(
          absolute,
        ),
      );

      continue;
    }

    if (
      /\.(?:ts|tsx|js|jsx)$/.test(
        entry.name,
      )
    ) {
      output.push(
        absolute,
      );
    }
  }

  return output;
}


const detail = read(
  "app",
  "projects",
  "[id]",
  "_components",
  "ProjectDetailClient.tsx",
);


const navigation = read(
  "app",
  "projects",
  "[id]",
  "_components",
  "ReportNavigation.tsx",
);


const finalReport = read(
  "app",
  "projects",
  "[id]",
  "_sections",
  "FinalReportSection.tsx",
);


const projectManager = read(
  "app",
  "projects",
  "[id]",
  "_sections",
  "ProjectManagerSection.tsx",
);


const backendSchema = readRepo(
  "backend",
  "app",
  "schemas",
  "project_management.py",
);


// ============================================================================
// CONTROLS
//
// These contracts are already true.
// They prove B1 is testing the correct product layer.
// ============================================================================

test(
  "control_existing_report_navigation_component_is_reused",
  () => {

    assert.match(
      navigation,
      /export\s+default\s+function\s+ReportNavigation\b/,
    );
  },
);


test(
  "control_project_manager_exposes_stable_root_anchor",
  () => {

    assert.match(
      projectManager,
      /id=["']project-manager["']/,
    );
  },
);


test(
  "control_final_report_exposes_stable_section_anchors",
  () => {

    for (
      const id
      of [
        "executive-summary",
        "problem",
        "solution",
        "target-market",
        "market-opportunity",
        "startup-score",
        "verdict",
        "action-plan",
        "limitations",
      ]
    ) {

      assert.ok(
        finalReport.includes(
          `id="${id}"`,
        ),
        `Missing report anchor: ${id}`,
      );
    }
  },
);


test(
  "control_backend_release_planning_authority_is_certified",
  () => {

    assert.match(
      backendSchema,
      /class\s+ReleasePlanningMetadataV1\s*\(/,
    );

    assert.match(
      backendSchema,
      /release_planning:\s*Optional\[ReleasePlanningMetadataV1\]\s*=\s*None/,
    );

    for (
      const field
      of [
        "effective_sprint_count",
        "recommended_sprint_count",
        "effective_sprint_duration_days",
        "recommended_sprint_duration_days",
        "effective_sprint_capacity_story_points",
        "release_capacity_story_points",
        "capacity_utilization_ratio",
        "release_duration_days",
      ]
    ) {

      assert.ok(
        backendSchema.includes(
          field,
        ),
        `Backend release authority field missing: ${field}`,
      );
    }
  },
);


test(
  "control_frontend_does_not_recompute_release_metrics",
  () => {

    assert.doesNotMatch(
      projectManager,
      /planned_velocity\s*\*\s*(?:settings\.)?capacity_adjustment/,
    );

    assert.doesNotMatch(
      projectManager,
      /sprint_count\s*\*\s*(?:settings\.)?sprint_duration_days/,
    );

    assert.doesNotMatch(
      projectManager,
      /assigned_story_points\s*\/\s*release_capacity_story_points/,
    );
  },
);


// ============================================================================
// REAL RED 1
//
// Internal development milestones must never leak into user-facing UI.
// ============================================================================

test(
  "no_internal_development_milestone_is_exposed_in_user_facing_frontend",
  () => {

    const roots = [
      path.join(
        FRONTEND,
        "app",
      ),
      path.join(
        FRONTEND,
        "components",
      ),
    ].filter(
      (candidate) =>
        fs.existsSync(
          candidate,
        ),
    );


    const literalSprint4 =
      /(?:["'`][^"'`\n]*\bSprint\s*4\b[^"'`\n]*["'`])|(?:>\s*Sprint\s*4\s*<)/i;


    for (const root of roots) {

      for (
        const file
        of sourceFiles(
          root,
        )
      ) {

        const source = fs.readFileSync(
          file,
          "utf8",
        );

        assert.doesNotMatch(
          source,
          literalSprint4,
          `Internal development milestone leaked by ${path.relative(FRONTEND, file)}`,
        );
      }
    }
  },
);


// ============================================================================
// REAL RED 2
//
// Product feature naming is user-oriented, not engineering-oriented.
// ============================================================================

test(
  "product_manager_uses_product_oriented_plan_naming",
  () => {

    assert.match(
      projectManager,
      /title:\s*"Plan produit[^"]*"/,
    );

    assert.match(
      projectManager,
      /title:\s*"Product plan[^"]*"/i,
    );

    assert.doesNotMatch(
      projectManager,
      /Product Manager IA\s*·\s*Sprint\s*4/i,
    );

    assert.doesNotMatch(
      projectManager,
      /AI Product Manager\s*·\s*Sprint\s*4/i,
    );
  },
);


// ============================================================================
// REAL RED 3
//
// The whole report workspace owns one navigation authority.
// ReportNavigation must not remain trapped inside FinalReportSection.
// ============================================================================

test(
  "full_report_workspace_owns_single_report_navigation",
  () => {

    assert.match(
      detail,
      /import\s+ReportNavigation\s+from\s+["'][^"']+ReportNavigation["']/,
    );


    const detailRenders = [
      ...detail.matchAll(
        /<ReportNavigation\b/g,
      ),
    ].length;


    assert.equal(
      detailRenders,
      1,
      "ProjectDetailClient must render exactly one full-report navigation",
    );


    assert.doesNotMatch(
      finalReport,
      /<ReportNavigation\b/,
    );


    assert.doesNotMatch(
      finalReport,
      /import\s+ReportNavigation\b/,
    );
  },
);


// ============================================================================
// REAL RED 4
//
// Navigation must reach the Product Plan and useful long-form subsections.
// ============================================================================

test(
  "report_navigation_includes_product_plan_and_subsection_targets",
  () => {

    const requiredTargets = [
      "project-manager",
      "product-plan-overview",
      "product-plan-settings",
      "product-plan-backlog",
      "product-plan-sprints",
      "product-plan-dependencies",
      "product-plan-metrics",
      "product-plan-advice",
    ];


    for (
      const id
      of requiredTargets
    ) {

      assert.ok(
        navigation.includes(
          id,
        ),
        `Navigation target missing: ${id}`,
      );
    }
  },
);


// ============================================================================
// REAL RED 5
//
// Every navigation target corresponds to a stable rendered DOM anchor.
// ============================================================================

test(
  "product_plan_exposes_stable_subsection_anchors",
  () => {

    const requiredAnchors = [
      "product-plan-overview",
      "product-plan-settings",
      "product-plan-backlog",
      "product-plan-sprints",
      "product-plan-dependencies",
      "product-plan-metrics",
      "product-plan-advice",
    ];


    for (
      const id
      of requiredAnchors
    ) {

      assert.ok(
        projectManager.includes(
          `id="${id}"`,
        ),
        `Product Plan section anchor missing: ${id}`,
      );
    }
  },
);


// ============================================================================
// REAL RED 6
//
// Navigation indicates the section currently visible in the viewport.
// ============================================================================

test(
  "report_navigation_tracks_active_section",
  () => {

    assert.match(
      navigation,
      /IntersectionObserver/,
    );

    assert.match(
      navigation,
      /active(?:Section)?Id|activeId/,
    );

    assert.match(
      navigation,
      /aria-current/,
    );
  },
);


// ============================================================================
// REAL RED 7
//
// Desktop gets a true sticky sidebar.
// Mobile/tablet gets compact navigation.
// ============================================================================

test(
  "report_navigation_has_desktop_sidebar_and_mobile_compact_modes",
  () => {

    assert.match(
      navigation,
      /<aside\b/,
    );

    assert.match(
      navigation,
      /hidden\s+lg:block|lg:block/,
    );

    assert.match(
      navigation,
      /<details\b/,
    );

    assert.match(
      navigation,
      /lg:hidden/,
    );

    assert.match(
      navigation,
      /\bsticky\b/,
    );

    assert.match(
      detail,
      /lg:grid-cols-/,
    );
  },
);


// ============================================================================
// REAL RED 8
//
// Navigation may define potential sections but renders only DOM sections
// that actually exist.
// ============================================================================

test(
  "report_navigation_filters_to_rendered_sections",
  () => {

    assert.match(
      navigation,
      /document\.getElementById/,
    );

    assert.match(
      navigation,
      /\.filter\s*\(/,
    );
  },
);


// ============================================================================
// REAL RED 9
//
// Frontend plan contract must project the certified backend release metadata.
// release_planning remains nullable for legacy plans.
// ============================================================================

test(
  "frontend_plan_contract_projects_release_planning_metadata_and_modes",
  () => {

    for (
      const field
      of [
        "release_planning",
        "sprint_count_mode",
        "sprint_duration_mode",
        "effective_sprint_count",
        "recommended_sprint_count",
        "effective_sprint_duration_days",
        "recommended_sprint_duration_days",
        "cadence_band",
        "cadence_confidence",
        "cadence_reason_codes",
        "effective_sprint_capacity_story_points",
        "release_capacity_story_points",
        "capacity_utilization_ratio",
        "release_duration_days",
      ]
    ) {

      assert.ok(
        projectManager.includes(
          field,
        ),
        `Frontend release contract missing: ${field}`,
      );
    }


    assert.match(
      projectManager,
      /release_planning\??:\s*[A-Za-z0-9_]+\s*\|\s*null/,
    );


    assert.match(
      projectManager,
      /sprint_count_mode:\s*"auto"\s*\|\s*"manual"/,
    );


    assert.match(
      projectManager,
      /sprint_duration_mode:\s*"auto"\s*\|\s*"manual"/,
    );
  },
);


// ============================================================================
// REAL RED 10
//
// React displays backend release metadata directly.
// It must not become another planning engine.
// ============================================================================

test(
  "product_plan_displays_backend_release_metadata_directly",
  () => {

    assert.match(
      projectManager,
      /const\s+releasePlanning\s*=\s*plan\.release_planning/,
    );


    for (
      const field
      of [
        "effective_sprint_count",
        "effective_sprint_duration_days",
        "release_capacity_story_points",
        "capacity_utilization_ratio",
        "release_duration_days",
      ]
    ) {

      assert.match(
        projectManager,
        new RegExp(
          `releasePlanning(?:\\?|)\\.${field}`,
        ),
        `Release authority value not displayed directly: ${field}`,
      );
    }
  },
);