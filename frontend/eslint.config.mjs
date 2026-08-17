import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const nextVitalsWithCompatibilityPolicy = nextVitals.map(
  (config, index) => {
    if (index !== 0) {
      return config;
    }

    return {
      ...config,
      rules: {
        ...config.rules,
        "react-hooks/set-state-in-effect": "warn",
      },
    };
  },
);

const typescriptPlugin =
  nextTs[0]?.plugins?.["@typescript-eslint"];

if (!typescriptPlugin) {
  throw new Error(
    "eslint-config-next/typescript did not expose @typescript-eslint plugin",
  );
}

const eslintConfig = defineConfig([
  ...nextVitalsWithCompatibilityPolicy,
  ...nextTs,
  {
    files: ["**/*.cjs"],
    plugins: {
      "@typescript-eslint": typescriptPlugin,
    },
    rules: {
      "@typescript-eslint/no-require-imports": "off",
    },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
