import { FlatCompat } from "@eslint/eslintrc";
import js from "@eslint/js";
import eslintPluginArrayFunc from "eslint-plugin-array-func";
import eslintPluginJsonc from "eslint-plugin-jsonc";
import eslintPluginMarkdown from "eslint-plugin-markdown";
import eslintPluginNoSecrets from "eslint-plugin-no-secrets";
import eslintPluginPrettier from "eslint-plugin-prettier";
import eslintPluginPrettierRecommended from "eslint-plugin-prettier/recommended";
import eslintPluginSecurity from "eslint-plugin-security";
import eslintPluginSimpleImportSort from "eslint-plugin-simple-import-sort";
import eslintPluginSonarjs from "eslint-plugin-sonarjs";
import eslintPluginToml from "eslint-plugin-toml";
import eslintPluginUnicorn from "eslint-plugin-unicorn";
import eslintPluginYml from "eslint-plugin-yml";
import globals from "globals";

const compat = new FlatCompat();

const ignores = [
  "!.circleci",
  "**/__pycache__",
  "*~",
  ".git",
  ".mypy_cache",
  ".ruff_cache",
  ".pytest_cache",
  ".venv",
  "dist",
  "node_modules",
  "package-lock.json",
  "poetry.lock",
  "test-results",
  "typings",
];

export default [
  {
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
    linterOptions: {
      reportUnusedDisableDirectives: "warn",
    },
    plugins: {
      arrayFunc: eslintPluginArrayFunc,
      jsonc: eslintPluginJsonc,
      markdown: eslintPluginMarkdown,
      "no-secrets": eslintPluginNoSecrets,
      prettier: eslintPluginPrettier,
      security: eslintPluginSecurity,
      "simple-import-sort": eslintPluginSimpleImportSort,
      // sonarjs: eslintPluginSonarjs,
      toml: eslintPluginToml,
      unicorn: eslintPluginUnicorn,
      yml: eslintPluginYml,
    },
    rules: {
      "array-func/prefer-array-from": "off", // for modern browsers the spread operator, as preferred by unicorn, works fine.
      "max-params": ["warn", 4],
      "no-console": "warn",
      "no-debugger": "warn",
      "no-constructor-bind/no-constructor-bind": "error",
      "no-constructor-bind/no-constructor-state": "error",
      "no-secrets/no-secrets": "error",
      "prettier/prettier": "warn",
      "security/detect-object-injection": "off",
      "simple-import-sort/exports": "warn",
      "simple-import-sort/imports": "warn",
      "space-before-function-paren": "off",
      "unicorn/switch-case-braces": ["warn", "avoid"],
      "unicorn/prefer-node-protocol": 0,
      "unicorn/prevent-abbreviations": "off",
      "unicorn/filename-case": [
        "error",
        { case: "kebabCase", ignore: [".*.md"] },
      ],
      /*
     ...importPlugin.configs["recommended"].rules,
     "import/no-unresolved": [
       "error",
       {
         ignore: ["^[@]"],
       },
     ],
     */
    },
    /*
    settings: {
      "import/parsers": {
        espree: [".js", ".cjs", ".mjs", ".jsx"],
        "@typescript-eslint/parser": [".ts"],
      },
      "import/resolver": {
        typescript: true, 
        node: true,
      },
    },
     */
    ignores,
  },
  js.configs.recommended,
  eslintPluginArrayFunc.configs.all,
  ...eslintPluginJsonc.configs["flat/recommended-with-jsonc"],
  ...eslintPluginMarkdown.configs.recommended,
  eslintPluginPrettierRecommended,
  eslintPluginSecurity.configs.recommended,
  eslintPluginSonarjs.configs.recommended,
  ...eslintPluginToml.configs["flat/recommended"],
  ...eslintPluginYml.configs["flat/standard"],
  ...eslintPluginYml.configs["flat/prettier"],
  {
    files: ["**/*.md"],
    processor: "markdown/markdown",
    rules: {
      "prettier/prettier": ["warn", { parser: "markdown" }],
    },
  },
  {
    files: ["**/*.md/*.js"], // Will match js code inside *.md files
    rules: {
      "no-unused-vars": "off",
      "no-undef": "off",
    },
  },
  {
    files: ["**/*.md/*.sh"],
    rules: {
      "prettier/prettier": ["error", { parser: "sh" }],
    },
  },
  {
    files: ["docker-compose*.yaml"],
    rules: {
      "yml/no-empty-mapping-value": "off",
    },
  },
  ...compat.config({
    root: true,
    env: {
      browser: true,
      es2024: true,
      node: true,
    },
    extends: [
      // PRACTICES
      "plugin:eslint-comments/recommended",
      // "plugin:import/recommended",
      "plugin:no-use-extend-native/recommended",
      "plugin:optimize-regex/all",
      // "plugin:promise/recommended",
      "plugin:switch-case/recommended",
      // SECURITY
      // "plugin:no-unsanitized/DOM",
    ],
    parserOptions: {
      ecmaFeatures: {
        impliedStrict: true,
      },
      ecmaVersion: "latest",
    },
    plugins: [
      "eslint-comments",
      // "import",
      "no-constructor-bind",
      "no-secrets",
      "no-use-extend-native",
      "optimize-regex",
      "switch-case",
    ],
    rules: {
      "no-constructor-bind/no-constructor-bind": "error",
      "no-constructor-bind/no-constructor-state": "error",
      "eslint-comments/no-unused-disable": 1,
      "switch-case/newline-between-switch-case": "off", // Malfunctioning
    },
    ignorePatterns: ignores,
  }),
];
