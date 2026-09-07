import assert from "node:assert/strict";
import {
  readdir,
  readFile,
} from "node:fs/promises";
import {
  extname,
  join,
  relative,
} from "node:path";
import {
  fileURLToPath,
} from "node:url";
import test from "node:test";


const frontendRoot = fileURLToPath(
  new URL("../", import.meta.url)
);

const productionRoots = [
  "app",
  "components",
  "lib",
];

const extensions = new Set([
  ".ts",
  ".tsx",
  ".js",
  ".jsx",
  ".mjs",
  ".cjs",
]);


async function walk(directory) {
  const result = [];

  const entries = await readdir(
    directory,
    {
      withFileTypes: true,
    }
  );

  for (const entry of entries) {
    const fullPath = join(
      directory,
      entry.name
    );

    if (entry.isDirectory()) {
      result.push(
        ...(await walk(fullPath))
      );
      continue;
    }

    if (
      extensions.has(
        extname(entry.name)
      )
    ) {
      result.push(fullPath);
    }
  }

  return result;
}


test(
  "frontend never consumes bearer access tokens from URL parameters",
  async () => {
    const offenders = [];

    for (const root of productionRoots) {
      const directory = join(
        frontendRoot,
        root
      );

      for (const path of await walk(directory)) {
        const source = await readFile(
          path,
          "utf8"
        );

        const consumesBearerFromUrl =
          /(?:searchParams|URLSearchParams)[\s\S]{0,160}access_token/u
            .test(source);

        const embedsBearerInQuery =
          /[?&]access_token=/u
            .test(source);

        if (
          consumesBearerFromUrl
          || embedsBearerInQuery
        ) {
          offenders.push(
            relative(
              frontendRoot,
              path
            )
          );
        }
      }
    }

    assert.deepEqual(
      offenders,
      [],
      (
        "Bearer access tokens must not " +
        "cross the browser URL boundary"
      )
    );
  }
);
