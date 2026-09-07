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


const detailPath =
  path.join(
    frontend,
    "app",
    "projects",
    "[id]",
    "_components",
    "ProjectDetailClient.tsx",
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


const detail =
  fs.readFileSync(
    detailPath,
    "utf8",
  );


const navigation =
  fs.readFileSync(
    navigationPath,
    "utf8",
  );


// -----------------------------------------------------------------------------
// CONTROLS
// -----------------------------------------------------------------------------

test(
  "control_report_and_product_plan_share_one_workspace",
  () => {
    assert.match(
      detail,
      /grid gap-8 lg:grid-cols-\[15rem_minmax\(0,1fr\)\] lg:items-start/u,
    );


    const nav =
      detail.indexOf(
        "<ReportNavigation",
      );

    const report =
      detail.indexOf(
        "<FinalReportSection",
      );

    const product =
      detail.indexOf(
        "<ProjectManagerSection",
      );


    assert.ok(
      nav >= 0,
    );

    assert.ok(
      report > nav,
    );

    assert.ok(
      product > report,
    );
  },
);


test(
  "control_mobile_compact_navigation_is_preserved",
  () => {
    assert.match(
      navigation,
      /<details className="[^"]*lg:hidden[^"]*">/u,
    );

    assert.match(
      navigation,
      /max-h-\[60vh\][^"]*overflow-y-auto/u,
    );
  },
);


// -----------------------------------------------------------------------------
// EXPECTED PRODUCT REDS
// -----------------------------------------------------------------------------

test(
  "red_desktop_grid_item_owns_sticky_positioning",
  () => {
    assert.match(
      navigation,
      /<aside className="hidden lg:sticky lg:top-24 lg:block lg:self-start">/u,
      "The desktop grid item itself must own sticky positioning so its containing block is the complete report + product workspace.",
    );
  },
);


test(
  "red_internal_panel_scrolls_without_owning_page_sticky",
  () => {
    assert.doesNotMatch(
      navigation,
      /<div className="sticky top-24 max-h-\[calc\(100vh-7rem\)\] overflow-y-auto/u,
      "A sticky child inside a content-height aside has no full-workspace sticky runway.",
    );


    assert.match(
      navigation,
      /<div className="max-h-\[calc\(100vh-7rem\)\] overflow-y-auto rounded-3xl/u,
      "The viewport-bounded inner panel may scroll, but it must not own page-level sticky positioning.",
    );
  },
);
