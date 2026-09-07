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


const globalsPath =
  path.join(
    frontend,
    "app",
    "globals.css",
  );


const navigationPath =
  path.join(
    frontend,
    "app",
    "projects",
    "[id]",
    "_components",
    "ReportNavigation.tsx",
  );


const productManagerPath =
  path.join(
    frontend,
    "app",
    "projects",
    "[id]",
    "_sections",
    "ProjectManagerSection.tsx",
  );


const globals =
  fs.readFileSync(
    globalsPath,
    "utf8",
  );


const navigation =
  fs.readFileSync(
    navigationPath,
    "utf8",
  );


const productManager =
  fs.readFileSync(
    productManagerPath,
    "utf8",
  );


function forgePageBody() {
  const match =
    globals.match(
      /\.forge-page\s*\{([\s\S]*?)\}/u,
    );


  assert.ok(
    match,
    ".forge-page must remain a canonical page-shell CSS authority.",
  );


  return match[1];
}


// =============================================================================
// CONTROLS
// =============================================================================

test(
  "control_desktop_navigation_grid_item_owns_sticky",
  () => {
    assert.match(
      navigation,
      /<aside className="hidden lg:sticky lg:top-24 lg:block lg:self-start">/u,
    );


    assert.doesNotMatch(
      navigation,
      /<div className="sticky top-24/u,
    );
  },
);


test(
  "control_velocity_and_burndown_visual_regions_exist",
  () => {
    assert.match(
      productManager,
      /id="product-plan-velocity-chart"/u,
    );


    assert.match(
      productManager,
      /id="product-plan-burndown-chart"/u,
    );


    assert.ok(
      (
        productManager.match(
          /role="img"/gu,
        )
        ??
        []
      ).length
      >=
      2,
    );
  },
);


// =============================================================================
// EXPECTED PRODUCT REDS
// =============================================================================

test(
  "red_forge_page_clips_horizontal_decoration_without_becoming_scroll_container",
  () => {
    const body =
      forgePageBody();


    assert.doesNotMatch(
      body,
      /overflow-x\s*:\s*hidden\s*;/u,
      "overflow-x:hidden causes the page shell to participate in scroll-container semantics and breaks viewport sticky behavior.",
    );


    assert.match(
      body,
      /overflow-x\s*:\s*clip\s*;/u,
      "Decorative horizontal overflow must be clipped without creating a scroll container.",
    );
  },
);


test(
  "red_planning_charts_remain_full_width_inside_metrics_panel",
  () => {
    assert.doesNotMatch(
      productManager,
      /className="mt-5 grid gap-5 2xl:grid-cols-2"/u,
      "Velocity and Burndown must not become two narrow nested columns on large desktop screens.",
    );


    assert.match(
      productManager,
      /className="mt-5 grid gap-5"/u,
      "Planning charts should remain vertically stacked and use the full available metrics-panel width.",
    );
  },
);
