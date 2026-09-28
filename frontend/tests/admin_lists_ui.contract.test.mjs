/*
 * Sprint 7.4 admin lists, console side.
 *
 * The admin API now pages, searches, filters and sorts in SQL. The console
 * must stop downloading whole tables and computing in the browser:
 *   E1  every list page reads ONE page from the API and shows a pager;
 *   E2  no list is filtered / searched / counted in the browser; the
 *       counters come from /admin/stats (computed by the database);
 *   E3  the CSV export uses exactly the filters of the screen;
 *   E4  loading never calls setState synchronously in an effect (the
 *       shared hook derives "loading" from the requested URL).
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");

const pages = {
  users: read("app/admin/users/page.tsx"),
  projects: read("app/admin/projects/page.tsx"),
  analyses: read("app/admin/analyses/page.tsx"),
  errors: read("app/admin/errors/page.tsx"),
};
const hook = read("app/admin/_components/useAdminResource.ts");
const pager = read("app/admin/_components/Pagination.tsx");

test("E1: each list page reads one page from the admin API and shows a pager", () => {
  for (const [name, source] of Object.entries(pages)) {
    assert.match(source, new RegExp(`useAdminResource<Page<[A-Za-z]+>>\\(\\s*\`/admin/${name}\\$\\{`), name);
    assert.match(source, /<Pagination/, name);
    assert.match(source, /buildListQuery\(/, name);
  }
  assert.match(pager, /Précédent/);
  assert.match(pager, /Suivant/);
  assert.match(pager, /sur \{total\}/);
});

test("E2: no whole-list filtering, searching or counting in the browser", () => {
  for (const [name, source] of Object.entries(pages)) {
    assert.doesNotMatch(source, /(users|projects|analyses|errors)\.filter\(/, name);
    assert.doesNotMatch(source, /(users|projects|analyses|errors)\.length/, name);
    assert.doesNotMatch(source, /useMemo\(/, name);
  }
  for (const name of ["users", "projects", "analyses"]) {
    assert.match(pages[name], /useAdminResource<AdminStats>\("\/admin\/stats"/, name);
  }
});

test("E3: the CSV export sends the same filters as the list", () => {
  assert.match(pages.users, /adminDownload\(`\/admin\/users\/export\.csv\$\{buildListQuery\(filters\)\}`/);
  assert.match(pages.projects, /adminDownload\(`\/admin\/projects\/export\.csv\$\{buildListQuery\(filters\)\}`/);
});

test("E4: the shared hook never sets state synchronously inside its effect", () => {
  const effect = hook.slice(hook.indexOf("useEffect("), hook.indexOf("}, [url, version]"));
  // Only inside promise callbacks (.then / .catch), guarded against stale answers.
  const direct = effect.split("\n").filter((line) => /^\s{4}set[A-Z]\w*\(/.test(line));
  assert.deepEqual(direct, []);
  assert.match(effect, /\.then\(/);
  assert.match(effect, /cancelled/);
  assert.match(hook, /isLoading: loadedKey !== key/);
  assert.match(read("app/admin/_components/listQuery.ts"), /export function buildListQuery/);
});
