const fs = require("fs");
const path = require("path");

const roots = ["app", "components", "lib"];
const extensions = new Set([".ts", ".tsx"]);

const markers = [
  "\u00C3",
  "\u00C2",
  "\u00E2\u20AC",
  "\u00E2\u0153",
  "\u00F0\u0178",
];

function walk(dir) {
  if (!fs.existsSync(dir)) return [];

  const entries = fs.readdirSync(dir, { withFileTypes: true });

  return entries.flatMap((entry) => {
    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) return walk(fullPath);

    if (entry.isFile() && extensions.has(path.extname(entry.name))) {
      return [fullPath];
    }

    return [];
  });
}

let hits = 0;

for (const file of roots.flatMap(walk)) {
  const text = fs.readFileSync(file, "utf8");

  if (markers.some((marker) => text.includes(marker))) {
    console.log("still has mojibake marker:", file);
    hits += 1;
  }
}

console.log("remaining files:", hits);
