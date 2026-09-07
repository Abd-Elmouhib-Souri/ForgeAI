import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";


const here =
  path.dirname(
    fileURLToPath(
      import.meta.url,
    ),
  );


const frontend =
  path.resolve(
    here,
    "..",
  );


const root =
  path.resolve(
    frontend,
    "..",
  );


const projectRoot =
  path.join(
    frontend,
    "app",
    "projects",
    "[id]",
  );


const pmPath =
  path.join(
    projectRoot,
    "_sections",
    "ProjectManagerSection.tsx",
  );


const backendSchemaPath =
  path.join(
    root,
    "backend",
    "app",
    "schemas",
    "project_management.py",
  );


const backendServicePath =
  path.join(
    root,
    "backend",
    "app",
    "services",
    "project_management_plan_service.py",
  );


const pm =
  fs.readFileSync(
    pmPath,
    "utf8",
  );


const backendSchema =
  fs.readFileSync(
    backendSchemaPath,
    "utf8",
  );


const backendService =
  fs.readFileSync(
    backendServicePath,
    "utf8",
  );


function sourceFiles(
  directory,
) {
  const results = [];


  for (
    const entry
    of fs.readdirSync(
      directory,
      {
        withFileTypes: true,
      },
    )
  ) {
    const absolute =
      path.join(
        directory,
        entry.name,
      );


    if (
      entry.isDirectory()
    ) {
      results.push(
        ...sourceFiles(
          absolute,
        ),
      );

      continue;
    }


    if (
      /\.(?:ts|tsx|js|jsx)$/u.test(
        entry.name,
      )
    ) {
      results.push(
        absolute,
      );
    }
  }


  return results;
}


const projectSources =
  sourceFiles(
    projectRoot,
  )
    .map(
      (file) =>
        fs.readFileSync(
          file,
          "utf8",
        ),
    )
    .join(
      "\n",
    );


function occurrences(
  source,
  token,
) {
  return (
    source.split(
      token,
    ).length
    -
    1
  );
}


// =============================================================================
// CONTROLS
//
// These prove the chart source-of-truth already exists server-side.
// =============================================================================

test(
  "control_backend_velocity_authority_is_certified",
  () => {
    assert.match(
      backendSchema,
      /planned_velocity:\s*float/u,
    );

    assert.match(
      backendSchema,
      /projected_velocity:\s*float/u,
    );

    assert.match(
      backendSchema,
      /actual_velocity:\s*Optional\[float\]\s*=\s*None/u,
    );
  },
);


test(
  "control_backend_burndown_authority_is_certified",
  () => {
    assert.match(
      backendSchema,
      /ideal_burndown:\s*list\[float\]/u,
    );

    assert.match(
      backendSchema,
      /planned_burndown:\s*list\[float\]/u,
    );

    assert.match(
      backendSchema,
      /actual_burndown:\s*Optional\[list\[float\]\]\s*=\s*None/u,
    );

    assert.match(
      backendService,
      /ideal_burndown\s*=\s*ideal/u,
    );

    assert.match(
      backendService,
      /planned_burndown\s*=\s*list\(ideal\)/u,
    );
  },
);


test(
  "control_actual_delivery_metrics_remain_nullable",
  () => {
    assert.match(
      backendSchema,
      /actual_velocity:\s*Optional\[float\]\s*=\s*None/u,
    );

    assert.match(
      backendSchema,
      /actual_burndown:\s*Optional\[list\[float\]\]\s*=\s*None/u,
    );
  },
);


// =============================================================================
// EXPECTED PRODUCT REDS
// =============================================================================

test(
  "red_frontend_projects_backend_burndown_series",
  () => {
    assert.match(
      pm,
      /ideal_burndown:\s*number\[\]/u,
      "Frontend Plan metrics must project backend ideal_burndown directly.",
    );

    assert.match(
      pm,
      /planned_burndown:\s*number\[\]/u,
      "Frontend Plan metrics must project backend planned_burndown directly.",
    );

    assert.match(
      pm,
      /actual_burndown:\s*number\[\]\s*\|\s*null/u,
      "Frontend Plan metrics must preserve nullable actual_burndown.",
    );
  },
);


test(
  "red_velocity_has_a_real_visual_chart_region",
  () => {
    assert.match(
      projectSources,
      /id=["']product-plan-velocity-chart["']/u,
      "Velocity requires a stable visual chart region.",
    );

    assert.match(
      projectSources,
      /planned_velocity/u,
    );

    assert.match(
      projectSources,
      /projected_velocity/u,
    );

    assert.match(
      projectSources,
      /actual_velocity/u,
    );

    assert.match(
      projectSources,
      /(?:<svg\b|LineChart\b|AreaChart\b|ResponsiveLine\b|ReactApexChart\b)/u,
      "A numeric card alone is not a Velocity chart.",
    );
  },
);


test(
  "red_burndown_has_a_real_visual_chart_region",
  () => {
    assert.match(
      projectSources,
      /id=["']product-plan-burndown-chart["']/u,
      "Burndown requires a stable visual chart region.",
    );

    assert.match(
      projectSources,
      /ideal_burndown/u,
    );

    assert.match(
      projectSources,
      /planned_burndown/u,
    );

    assert.match(
      projectSources,
      /actual_burndown/u,
    );

    assert.match(
      projectSources,
      /(?:<svg\b|LineChart\b|AreaChart\b|ResponsiveLine\b|ReactApexChart\b)/u,
      "Text or numeric values alone are not a Burndown chart.",
    );
  },
);


test(
  "red_charts_render_backend_truth_without_fabricating_actual_delivery",
  () => {
    assert.match(
      projectSources,
      /plan\.metrics\.(?:planned_velocity|projected_velocity)/u,
      "Velocity chart must consume backend metric authority.",
    );

    assert.match(
      projectSources,
      /plan\.metrics\.(?:ideal_burndown|planned_burndown)/u,
      "Burndown chart must consume backend metric authority.",
    );


    assert.doesNotMatch(
      projectSources,
      /actual_velocity\s*\?\?\s*(?:planned_velocity|projected_velocity)/u,
      "Unknown actual velocity must never be fabricated from planned/projected values.",
    );


    assert.doesNotMatch(
      projectSources,
      /actual_burndown\s*\?\?\s*(?:ideal_burndown|planned_burndown)/u,
      "Unknown actual burndown must never be fabricated from ideal/planned values.",
    );
  },
);


test(
  "red_planning_charts_are_accessible_and_responsive",
  () => {
    assert.ok(
      occurrences(
        projectSources,
        'role="img"',
      )
      >=
      2,
      "Both planning charts need accessible image semantics.",
    );


    assert.ok(
      occurrences(
        projectSources,
        "aria-label",
      )
      >=
      2,
      "Both planning charts need accessible labels.",
    );


    assert.ok(
      occurrences(
        projectSources,
        "viewBox",
      )
      >=
      2,
      "Responsive SVG charts must expose a viewBox.",
    );
  },
);
