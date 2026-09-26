import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    // next-env.d.ts est régénéré automatiquement par Next.js (triple-slash
    // reference standard, présent dans tous les projets Next) — faux
    // positif connu de @typescript-eslint/triple-slash-reference avec la
    // config plate (flat config), sans rapport avec le code applicatif.
    ignores: ["next-env.d.ts"],
  },
];

export default eslintConfig;
