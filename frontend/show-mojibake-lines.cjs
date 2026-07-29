const fs = require("fs");

const files = [
  "app/login/page.tsx",
  "app/projects/page.tsx",
  "app/projects/[id]/edit/page.tsx",
];

const markers = [
  "\u00C3",
  "\u00C2",
  "\u00E2\u20AC",
  "\u00E2\u0153",
  "\u00F0\u0178",
];

for (const file of files) {
  const text = fs.readFileSync(file, "utf8");
  const lines = text.split(/\r?\n/);

  lines.forEach((line, index) => {
    if (markers.some((marker) => line.includes(marker))) {
      console.log("");
      console.log(file + ":" + (index + 1));
      console.log(line);
    }
  });
}
