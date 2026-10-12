import { describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import { defineComponent, h } from "vue";
import MoneyText from "./MoneyText.vue";
import EmptyState from "./EmptyState.vue";
import PageHeader from "./PageHeader.vue";
import StatusTag from "./StatusTag.vue";
import { useAuthStore } from "@/stores/auth";
import { useDictStore } from "@/stores/dict";

const RouterLinkStub = defineComponent({
  props: { to: { type: String, default: "" } },
  setup(_, { slots }) {
    return () => h("a", slots.default?.());
  },
});

describe("component smoke", () => {
  it("renders money, empty state and page scope", () => {
    setActivePinia(createPinia());
    const auth = useAuthStore();
    auth.dataScopeText = "本部门（市场一组）";
    const money = mount(MoneyText, { props: { value: "-20" } });
    expect(money.text()).toContain("¥-20.00");
    expect(money.classes()).toContain("neg");
    const empty = mount(EmptyState, { props: { type: "noPermission" } });
    expect(empty.text()).toContain("暂无权限查看此内容");
    const header = mount(PageHeader, {
      props: { title: "人员" },
      global: { plugins: [], stubs: { RouterLink: RouterLinkStub } },
    });
    expect(header.text()).toContain("统计范围：本部门（市场一组）");
  });

  it("renders a status from the dictionary", () => {
    setActivePinia(createPinia());
    const dict = useDictStore();
    dict.seed("dict_user_status", [{ dictValue: "FROZEN", dictLabel: "已冻结", colorType: "warning", status: "ENABLED", sort: 0 }]);
    const tag = mount(StatusTag, { props: { dictType: "dict_user_status", value: "FROZEN" } });
    expect(tag.text()).toContain("已冻结");
  });
});
