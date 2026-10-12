/** 颜色只允许出现在 Token 文件。 */
export default {
  ignoreFiles: ["dist/**", "node_modules/**", "src/styles/tokens.css"],
  rules: {
    "color-no-hex": true,
    "function-disallowed-list": ["rgb", "rgba", "hsl", "hsla"],
  },
  overrides: [
    {
      files: ["**/*.{vue,html}"],
      customSyntax: "postcss-html",
    },
  ],
};
