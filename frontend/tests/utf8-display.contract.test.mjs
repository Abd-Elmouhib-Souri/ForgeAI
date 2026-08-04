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
