import vue from "eslint-plugin-vue";
import tseslint from "typescript-eslint";
import ims from "./eslint/plugin.js";

export default tseslint.config(
  {
    ignores: ["dist/**", "node_modules/**", "coverage/**"],
  },
  ...vue.configs["flat/essential"],
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.{ts,vue}", "eslint/**/*.js"],
    plugins: { ims },
    rules: {
      "ims/no-admin-api": "error",
      "ims/no-role-check": "error",
      "ims/no-enum-text": "error",
      "vue/multi-word-component-names": "off",
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    },
  },
  {
    files: ["src/api/generated/**", "src/api/http.ts"],
    rules: { "ims/no-admin-api": "off" },
  },
);
