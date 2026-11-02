import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({ baseDirectory: __dirname });

/**
 * Configuración de ESLint (NN-113.2).
 *
 * Antes `npm run lint` **no era ejecutable**: el paquete no estaba en las
 * dependencias, así que el comando fallaba sin comprobar nada. Ahora el lint
 * forma parte de la puerta de calidad y se ejecuta en la CI.
 */
const eslintConfig = [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "out/**",
      "playwright-report/**",
      "test-results/**",
      "next-env.d.ts",
    ],
  },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      // El proyecto usa `<a>` para navegación interna en algunos sitios: se
      // avisa, pero no se rompe la compilación por ello.
      "@next/next/no-html-link-for-pages": "off",
    },
  },
];

export default eslintConfig;
