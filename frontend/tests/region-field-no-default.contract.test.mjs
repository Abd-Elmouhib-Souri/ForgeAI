import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const newPagePath = new URL(
  "../app/projects/new/page.tsx",
  import.meta.url
);

const editPagePath = new URL(
  "../app/projects/[id]/edit/page.tsx",
  import.meta.url
);

async function read(url) {
  return readFile(url, "utf8");
}

test("new project region starts empty", async () => {
  const source = await read(newPagePath);

  assert.match(
    source,
    /const \[marketRegion, setMarketRegion\] = useState\(""\)/
  );

  assert.doesNotMatch(
    source,
    /useState\("Tunisie"\)/
  );

  assert.match(
    source,
    /market_region:\s*marketRegion \|\| null/
  );
});

test(
  "new project select contains a neutral option",
  async () => {
    const source = await read(newPagePath);

    assert.match(
      source,
      /<option value="">\{t\.regionPlaceholder\}<\/option>/
    );
  }
);

test(
  "edit project does not invent a missing region",
  async () => {
    const source = await read(editPagePath);

    assert.match(
      source,
      /const \[marketRegion, setMarketRegion\] = useState\(""\)/
    );

    assert.match(
      source,
      /setMarketRegion\(res\.data\.market_region \|\| ""\)/
    );

    assert.doesNotMatch(
      source,
      /res\.data\.market_region \|\| "Tunisie"/
    );
  }
);

test(
  "edit project can persist an empty region",
  async () => {
    const source = await read(editPagePath);

    assert.match(
      source,
      /market_region:\s*marketRegion \|\| null/
    );

    assert.match(
      source,
      /<option value="">\{t\.regionPlaceholder\}<\/option>/
    );
  }
);
