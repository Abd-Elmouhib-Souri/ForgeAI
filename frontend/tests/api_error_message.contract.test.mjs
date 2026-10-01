/*
 * RED 30 Sept 2026 (clone test, user's screenshot): creating a project showed
 * "Request failed with status code 422". A FastAPI validation error carries
 * a LIST in `detail`, which the helper skipped, falling back to axios's
 * English technical message. The person must read the page's own message.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const helper = readFileSync(new URL("../lib/api-error.ts", import.meta.url), "utf8");

test("an HTTP error never shows axios's technical message", () => {
  // A backend string detail is still shown (French messages written by the API).
  assert.match(helper, /typeof detail === "string"/);
  // Any HTTP response without a readable detail (422 list, 500...) -> the page's message.
  assert.match(helper, /return fallback; \/\/ HTTP error without a readable detail/);
  assert.doesNotMatch(helper, /Request failed with status code/);
});
