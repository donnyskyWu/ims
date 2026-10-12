import { describe, expect, it } from "vitest";
import { ESLint } from "eslint";
import stylelint from "stylelint";

describe("lint rules", () => {
  it("rejects an interface prefix, a role check and an enum text node", async () => {
    const eslint = new ESLint({ cwd: process.cwd(), overrideConfigFile: "eslint.config.js" });
    const api = await eslint.lintText("const path = '/admin-api/ims/demo'\n", { filePath: "src/demo/bad.ts" });
    const role = await eslint.lintText("if (roles.includes('x')) {}\n", { filePath: "src/demo/role.ts" });
    const view = await eslint.lintText("<template><span>ACTIVE</span></template>\n", { filePath: "src/demo/Bad.vue" });
    expect(api[0].errorCount).toBeGreaterThan(0);
    expect(role[0].errorCount).toBeGreaterThan(0);
    expect(view[0].messages.some((item) => item.message.includes("枚举"))).toBe(true);
  });

  it("rejects a hex color outside the token file", async () => {
    const result = await stylelint.lint({
      code: ".a{color:#123456}",
      codeFilename: "src/demo/bad.css",
      configFile: "stylelint.config.js",
    });
    expect(result.errored).toBe(true);
  });
});
