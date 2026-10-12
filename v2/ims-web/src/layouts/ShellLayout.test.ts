import { beforeEach, describe, expect, it } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { defineComponent, h } from "vue";
import ShellLayout from "./ShellLayout.vue";
import { visibleNav } from "./nav";
import { useAuthStore, type MenuNode } from "@/stores/auth";

const menus: MenuNode[] = [
  {
    id: "1",
    name: "公司资产",
    permCode: null,
    type: "DIR",
    path: "/ims/corp",
    icon: null,
    children: [
      {
        id: "2",
        name: "资源管理",
        permCode: null,
        type: "DIR",
        path: null,
        icon: "id",
        children: [
          {
            id: "3",
            name: "公司管理",
            permCode: "ims:corp:company:query",
            type: "MENU",
            path: "/ims/corp/resource/company",
            icon: "db",
            children: [],
          },
          {
            id: "4",
            name: "证件管理",
            permCode: "ims:cert:expire:query",
            type: "MENU",
            path: "/ims/corp/resource/certificate",
            icon: "shield",
            children: [],
          },
        ],
      },
    ],
  },
  {
    id: "5",
    name: "系统管理",
    permCode: null,
    type: "DIR",
    path: "/ims/system",
    icon: null,
    children: [
      {
        id: "6",
        name: "角色",
        permCode: "ims:system:role:query",
        type: "MENU",
        path: "/ims/system/role",
        icon: "shield",
        children: [],
      },
      {
        id: "7",
        name: "删除角色",
        permCode: "ims:system:role:delete",
        type: "BUTTON",
        path: null,
        icon: null,
        children: [],
      },
    ],
  },
];

function fillAuth() {
  const auth = useAuthStore();
  auth.user = {
    id: "1",
    username: "qa",
    nickname: "测试员",
    avatar: "",
    mainDeptName: "",
    deptNames: [],
    positionLabel: "",
    pwdResetRequired: false,
  };
  auth.permCodes = ["ims:corp:company:query"];
  auth.menus = menus;
  auth.ready = true;
  return auth;
}

async function mountShell(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/:pathMatch(.*)*", component: defineComponent({ setup: () => () => h("div") }) }],
  });
  await router.push(path);
  await router.isReady();
  const wrapper = mount(ShellLayout, {
    global: {
      plugins: [router],
      stubs: { MessageBell: true, DownloadBar: true },
    },
  });
  await flushPromises();
  return wrapper;
}

describe("visible nav", () => {
  it("drops buttons, unauthorized menus and empty groups", () => {
    const shown = visibleNav(menus, ["ims:corp:company:query"]);
    const names = JSON.stringify(shown);
    expect(names).toContain("公司管理");
    expect(names).not.toContain("证件管理");
    expect(names).not.toContain("角色");
    expect(names).not.toContain("删除角色");
    expect(names).not.toContain("系统管理");
  });
});

describe("shell sidebar", () => {
  beforeEach(() => {
    window.innerWidth = 1440;
    setActivePinia(createPinia());
  });

  it("renders the prototype sidebar and hides menus without permission", async () => {
    fillAuth();
    const wrapper = await mountShell("/ims/corp/resource/company");
    expect(wrapper.text()).toContain("IMS 一体化管理系统");
    expect(wrapper.text()).toContain("神鱼体育");
    expect(wrapper.text()).toContain("测试员");
    expect(wrapper.text()).toContain("qa");
    expect(wrapper.text()).not.toContain("收起");
    expect(wrapper.text()).toContain("公司管理");
    expect(wrapper.text()).not.toContain("角色");
    expect(wrapper.text()).not.toContain("证件管理");
    const company = wrapper.findAll("button.nav-item").find((item) => item.text().includes("公司管理"));
    const parent = wrapper.find("button.nav-parent");
    expect(company?.classes()).toContain("active");
    expect(parent.classes()).toContain("active");
    expect(company?.find("svg").exists()).toBe(true);
    await wrapper.get("button.nav-g-h").trigger("click");
    expect(wrapper.get(".nav-g").classes()).toContain("closed");
    expect(wrapper.get("button.nav-g-h").attributes("aria-expanded")).toBe("false");
    wrapper.unmount();
  });

  it("keeps the logo and user card when no menu is assigned", async () => {
    const auth = fillAuth();
    auth.menus = [];
    auth.permCodes = [];
    const wrapper = await mountShell("/");
    expect(wrapper.text()).toContain("IMS 一体化管理系统");
    expect(wrapper.text()).toContain("尚未分配权限");
    expect(wrapper.find(".nav-item").exists()).toBe(false);
    wrapper.unmount();
  });

  it("uses a drawer below 1024px", async () => {
    fillAuth();
    window.innerWidth = 900;
    const wrapper = await mountShell("/ims/corp/resource/company");
    window.dispatchEvent(new Event("resize"));
    await flushPromises();
    expect(wrapper.find(".menu-btn").exists()).toBe(true);
    expect(wrapper.get(".sider").classes()).toContain("is-drawer");
    await wrapper.get(".menu-btn").trigger("click");
    expect(wrapper.get(".sider").classes()).toContain("on");
    await wrapper.get(".nav-mask").trigger("click");
    expect(wrapper.get(".sider").classes()).not.toContain("on");
    wrapper.unmount();
  });
});
