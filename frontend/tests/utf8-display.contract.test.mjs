import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const files = {
  client: new URL(
    "../app/projects/[id]/_components/ProjectDetailClient.tsx",
    import.meta.url
  ),
  journey: new URL(
    "../app/projects/[id]/_sections/AnalysisJourneySection.tsx",
    import.meta.url
  ),
};

async function read(url) {
  return readFile(url, "utf8");
}

const mojibakePattern = /Ã.|â€™|â€”|â€“|Â|ï¿½/;

test("project detail labels use valid UTF-8", async () => {
  const source = await read(files.client);

  assert.doesNotMatch(source, mojibakePattern);
  assert.match(source, /step:\s*"Étape"/);
  assert.match(source, /start:\s*"Début"/);
  assert.match(source, /targetRegion:\s*"Pays\/Région cible"/);
  assert.match(source, /launch:\s*"Lancer l’analyse"/);
});

test("analysis journey labels use valid UTF-8", async () => {
  const source = await read(files.journey);

  assert.doesNotMatch(source, mojibakePattern);
  assert.match(source, /Progression stratégique du projet/);
  assert.match(source, /Complétion/);
  assert.match(source, /étape par étape/);
});

// S4.33 universal production source encoding contract
test(
  "all frontend production sources avoid encoding corruption artifacts",
  async () => {
    const {
      readdir,
      readFile: readProductionFile,
    } = await import("node:fs/promises");

    const {
      join,
      relative,
    } = await import("node:path");

    const {
      fileURLToPath,
    } = await import("node:url");

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

    const corruptionPattern =
      /(?:\uFFFD|[\u0080-\u009F]|\u00E2\u20AC|\u00C3[\u00A0-\u00BF])/u;

    const checked = [];

    async function walk(directory) {
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
          await walk(fullPath);
          continue;
        }

        const extensionIndex =
          entry.name.lastIndexOf(".");

        const extension =
          extensionIndex >= 0
            ? entry.name.slice(extensionIndex)
            : "";

        if (!extensions.has(extension)) {
          continue;
        }

        const currentSource =
          await readProductionFile(
            fullPath,
            "utf8"
          );

        checked.push(
          relative(
            frontendRoot,
            fullPath
          )
        );

        assert.doesNotMatch(
          currentSource,
          corruptionPattern,
          (
            "Encoding corruption artifact in " +
            relative(frontendRoot, fullPath)
          )
        );
      }
    }

    for (const root of productionRoots) {
      await walk(
        join(
          frontendRoot,
          root
        )
      );
    }

    assert.ok(
      checked.length > 0,
      "No frontend production source was inspected"
    );
  }
);
