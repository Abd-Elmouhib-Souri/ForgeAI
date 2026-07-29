const fs = require("fs");

const files = [
  "app/projects/new/page.tsx",
  "app/projects/page.tsx",
  "app/dashboard/page.tsx",
  "app/projects/[id]/edit/page.tsx",
];

for (const file of files) {
  if (!fs.existsSync(file)) continue;

  let text = fs.readFileSync(file, "utf8");

  text = text
    .replaceAll("\\u20AC¦", "✓")
    .replaceAll("\\u20AC", "✓")
    .replaceAll("âœ…", "✓")
    .replaceAll("âœ“", "✓")
    .replaceAll("âœï¸", "✏️")
    .replaceAll("ðŸš€", "🚀")
    .replaceAll("ðŸ’¡", "💡")
    .replaceAll("ðŸ“Š", "📊");

  fs.writeFileSync(file, text, "utf8");
  console.log("patched:", file);
}
