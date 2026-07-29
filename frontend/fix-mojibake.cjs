const fs = require("fs");
const path = require("path");

const roots = ["app", "components", "lib"];
const extensions = new Set([".ts", ".tsx"]);

const pairs = [
  ["\u00C3\u00A9", "\u00E9"],
  ["\u00C3\u00A8", "\u00E8"],
  ["\u00C3\u00AA", "\u00EA"],
  ["\u00C3\u00AB", "\u00EB"],
  ["\u00C3\u00A0", "\u00E0"],
  ["\u00C3\u00A1", "\u00E1"],
  ["\u00C3\u00A2", "\u00E2"],
  ["\u00C3\u00A4", "\u00E4"],
  ["\u00C3\u00AE", "\u00EE"],
  ["\u00C3\u00AF", "\u00EF"],
  ["\u00C3\u00B4", "\u00F4"],
  ["\u00C3\u00B6", "\u00F6"],
  ["\u00C3\u00B9", "\u00F9"],
  ["\u00C3\u00BB", "\u00FB"],
  ["\u00C3\u00BC", "\u00FC"],
  ["\u00C3\u00A7", "\u00E7"],
  ["\u00C3\u0089", "\u00C9"],
  ["\u00C3\u2030", "\u00C9"],
  ["\u00C3\u0080", "\u00C0"],
  ["\u00C3\u0087", "\u00C7"],

  ["\u00C2\u00AB", "\u00AB"],
  ["\u00C2\u00BB", "\u00BB"],
  ["\u00C2\u00B0", "\u00B0"],
  ["\u00C2", ""],

  ["\u00E2\u20AC\u2122", "\u2019"],
  ["\u00E2\u20AC\u02DC", "\u2018"],
  ["\u00E2\u20AC\u0153", "\u201C"],
  ["\u00E2\u20AC\u009D", "\u201D"],
  ["\u00E2\u20AC\uFFFD", "\u201D"],
  ["\u00E2\u20AC\u201D", "\u2014"],
  ["\u00E2\u20AC\u201C", "\u2013"],
  ["\u00E2\u20AC\u00A6", "\u2026"],

  ["\u00E2\u0153\u201C", "\\u20AC\u00A6", "\u2026"],

  ["\u00E2\u0153\u201C", "\u2713"],
  ["\u00E2\u0153\u201D", "\u2713"],
  ["\u00E2\u0153\u2026", "\u2705"],
  ["\u00E2\u0153\u00A8", "\u2728"],

  ["\u00F0\u0178\u2019\u00A1", "\u{1F4A1}"],
  ["\u00F0\u0178\u0161\u20AC", "\u{1F680}"],
  ["\u00F0\u0178\u201C\u0160", "\u{1F4CA}"],
  ["\u00F0\u0178\u00A7\u00A0", "\u{1F9E0}"],
];

function walk(dir) {
  if (!fs.existsSync(dir)) return [];

  const entries = fs.readdirSync(dir, { withFileTypes: true });

  return entries.flatMap((entry) => {
    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      return walk(fullPath);
    }

    if (entry.isFile() && extensions.has(path.extname(entry.name))) {
      return [fullPath];
    }

    return [];
  });
}

const files = roots.flatMap(walk);
let changedCount = 0;

for (const file of files) {
  let text = fs.readFileSync(file, "utf8");
  let next = text;

  for (const [bad, good] of pairs) {
    next = next.split(bad).join(good);
  }

  if (next !== text) {
    fs.writeFileSync(file, next, "utf8");
    changedCount += 1;
    console.log("fixed:", file);
  }
}

console.log("changed files:", changedCount);
