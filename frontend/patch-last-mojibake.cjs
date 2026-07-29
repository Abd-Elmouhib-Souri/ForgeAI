const fs = require("fs");

function replaceInFile(file, replacers) {
  let text = fs.readFileSync(file, "utf8");
  let next = text;

  for (const [pattern, replacement] of replacers) {
    next = next.replace(pattern, replacement);
  }

  fs.writeFileSync(file, next, "utf8");
  console.log("patched:", file);
}

replaceInFile("app/login/page.tsx", [
  [
    /passwordPlaceholder:\s*"[^"]*"/g,
    'passwordPlaceholder: "\\u2022\\u2022\\u2022\\u2022\\u2022\\u2022\\u2022\\u2022"',
  ],
]);

replaceInFile("app/projects/page.tsx", [
  [
    /<span className="forge-eyebrow">.*?\{t\.eyebrow\}<\/span>/,
    '<span className="forge-eyebrow">{"\\u2728"} {t.eyebrow}</span>',
  ],
]);

replaceInFile("app/projects/[id]/edit/page.tsx", [
  [
    /<span className="forge-eyebrow">.*?\{t\.eyebrow\}<\/span>/,
    '<span className="forge-eyebrow">{"\\u270F\\uFE0F"} {t.eyebrow}</span>',
  ],
]);
