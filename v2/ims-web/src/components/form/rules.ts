import type { FormItemRule } from "element-plus";

export function requiredRule(label: string): FormItemRule {
  return { required: true, message: `请填写${label}`, trigger: "blur" };
}

export function lengthRule(min: number, max: number, label = "内容"): FormItemRule {
  return { min, max, message: `${label}长度须为 ${min} 到 ${max} 个字`, trigger: "blur" };
}

export const mobileRule: FormItemRule = {
  pattern: /^1\d{10}$/,
  message: "手机号格式不正确",
  trigger: "blur",
};

export const emailRule: FormItemRule = {
  type: "email",
  message: "邮箱格式不正确",
  trigger: "blur",
};

export const moneyRule: FormItemRule = {
  validator: (_rule, value, callback) => {
    if (value === "" || value === null || value === undefined) {
      callback();
      return;
    }
    if (!/^-?\d+(\.\d{1,2})?$/.test(String(value))) {
      callback(new Error("金额最多保留两位小数"));
      return;
    }
    callback();
  },
  trigger: "blur",
};

export const percentRule: FormItemRule = {
  validator: (_rule, value, callback) => {
    if (value === "" || value === null || value === undefined) {
      callback();
      return;
    }
    const number = Number(value);
    if (Number.isNaN(number) || number < 0 || number > 100) {
      callback(new Error("百分比须在 0 到 100 之间"));
      return;
    }
    callback();
  },
  trigger: "blur",
};

export const integerRule: FormItemRule = {
  validator: (_rule, value, callback) => {
    if (value === "" || value === null || value === undefined) {
      callback();
      return;
    }
    if (!/^-?\d+$/.test(String(value))) {
      callback(new Error("须为整数"));
      return;
    }
    callback();
  },
  trigger: "blur",
};

export const dictValueRule: FormItemRule = {
  pattern: /^[A-Z][A-Z0-9_]*$/,
  message: "字典值格式不正确",
  trigger: "blur",
};
