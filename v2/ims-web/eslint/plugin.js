/** IMS 前端约束：路径、角色判断、模板英文枚举码。 */

function isAdminApi(value) {
  return typeof value === "string" && value.includes("/admin-api");
}

const noAdminApi = {
  meta: { type: "problem", docs: { description: "业务代码不得手写接口前缀" } },
  create(context) {
    return {
      Literal(node) {
        if (isAdminApi(node.value)) {
          context.report({ node, message: "不得手写接口前缀，请调用生成的请求函数" });
        }
      },
      TemplateElement(node) {
        if (isAdminApi(node.value.raw) || isAdminApi(node.value.cooked)) {
          context.report({ node, message: "不得手写接口前缀，请调用生成的请求函数" });
        }
      },
    };
  },
};

const noRoleCheck = {
  meta: { type: "problem", docs: { description: "禁止按角色名判断权限" } },
  create(context) {
    return {
      Identifier(node) {
        if (node.name === "role_key" || node.name === "roleKey") {
          context.report({ node, message: "禁止按角色标识判断权限，请使用权限码" });
        }
      },
      CallExpression(node) {
        const callee = node.callee;
        if (
          callee.type === "MemberExpression" &&
          callee.property.type === "Identifier" &&
          callee.property.name === "includes" &&
          callee.object.type === "Identifier" &&
          callee.object.name === "roles"
        ) {
          context.report({ node, message: "禁止按角色集合判断权限，请使用权限码" });
        }
      },
    };
  },
};

const noEnumText = {
  meta: { type: "problem", docs: { description: "模板不得出现纯英文枚举码" } },
  create(context) {
    return {
      VText(node) {
        const text = String(node.value || "").trim();
        if (/^[A-Z_]{4,}$/.test(text)) {
          context.report({ node, message: "页面不能展示英文枚举码，请改用字典中文" });
        }
      },
    };
  },
};

const plugin = {
  meta: { name: "ims" },
  rules: {
    "no-admin-api": noAdminApi,
    "no-role-check": noRoleCheck,
    "no-enum-text": noEnumText,
  },
};

export default plugin;
