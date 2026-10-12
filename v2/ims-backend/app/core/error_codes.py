"""错误码注册表。1281～1286 为本批登录与组织权限扩展段。1296、1297 为个人工作台；1298 保留未启用。"""
from __future__ import annotations

from dataclasses import dataclass

# 号段：域 -> 允许的闭区间。COMMON 显式拥有跨域通用码。
# 1281～1295 与 SYS 共用，按序分配给后续批次。
DOMAIN_RANGES: dict[str, list[tuple[int, int]]] = {
    "COMMON": [(1001, 1001), (1008, 1008), (1500, 1504), (5001, 5007)],
    "AUTH": [(1002, 1007), (1009, 1010)],
    "SYS": [(1211, 1220), (1281, 1298)],
    "TRAIN": [(1101, 1110)],
    "FLOW": [(1131, 1140)],
    "FOOTBALL": [(1271, 1280)],
}


@dataclass(frozen=True)
class ErrorEntry:
    code: int
    domain: str
    msg: str
    front_strategy: str


def _e(code, domain, msg, strategy="toast") -> ErrorEntry:
    return ErrorEntry(code, domain, msg, strategy)


BASE_ENTRIES: list[ErrorEntry] = [
    _e(1001, "COMMON", "参数校验失败", "fieldError"),
    _e(1002, "AUTH", "登录已失效，请重新登录", "relogin"),
    _e(1003, "AUTH", "您的账号已在其他设备登录，本设备已下线", "relogin"),
    _e(1006, "AUTH", "钉钉同步失败", "toast"),
    _e(1008, "COMMON", "暂无权限", "noPermission"),
    _e(1101, "TRAIN", "资料未发布或不可用", "toast"),
    _e(1106, "TRAIN", "培训题目生成调用失败", "toast"),
    _e(1107, "TRAIN", "培训题目生成超时", "toast"),
    _e(1108, "TRAIN", "有效题目数量为 0", "toast"),
    _e(1109, "TRAIN", "培训题目生成未配置或未启用", "toast"),
    _e(1139, "FLOW", "当前流程不可撤销", "toast"),
    _e(1211, "SYS", "主键不可修改", "toast"),
    _e(1212, "SYS", "权限码不存在", "toast"),
    _e(1213, "SYS", "未知的参数项", "toast"),
    _e(1214, "SYS", "用户名或密码错误", "toast"),
    _e(1215, "SYS", "账号已锁定，请 {n} 分钟后再试", "toast"),
    _e(1216, "SYS", "账号已冻结或已离职，无法登录", "toast"),
    _e(1217, "SYS", "未找到与钉钉账号对应的用户，请联系管理员", "toast"),
    _e(1218, "SYS", "部门不能移动到自身或下级部门之下", "toast"),
    _e(1219, "SYS", "同一上级部门下已有同名部门", "toast"),
    _e(1220, "SYS", "系统部门或来自钉钉的部门不能这样调整", "toast"),
    _e(1281, "SYS", "该岗位已绑定启用中的规则「{name}」，确认替换后原规则将停用", "toast"),
    _e(1282, "SYS", "该规则还有 {n} 名在用人员，请先处理（调岗或按其他规则刷新）后再删除", "toast"),
    _e(1283, "SYS", "输入的规则名称不一致，未删除", "toast"),
    _e(1284, "SYS", "规则名称已存在", "toast"),
    _e(1285, "SYS", "规则已被他人修改（当前 v{n}），请刷新后重试", "toast"),
    _e(1286, "SYS", "事件状态已变化，请刷新后重试", "toast"),
    _e(1287, "SYS", "请先指定主部门", "fieldError"),
    _e(1289, "SYS", "套餐仍被租户使用，不可删除", "toast"),
    _e(1290, "SYS", "平台租户不可停用或删除", "toast"),
    _e(1291, "SYS", "非平台租户不可访问租户套餐管理", "noPermission"),
    _e(1292, "SYS", "手机号已被其他用户使用", "fieldError"),
    _e(1293, "SYS", "确认文字不一致，未执行危险操作", "toast"),
    _e(1296, "SYS", "待办已处理或已作废", "toast"),
    _e(1297, "SYS", "跳转目标单据不存在或已删除", "toast"),
    _e(1271, "FOOTBALL", "直播数据读取超时", "toast"),
    _e(1272, "FOOTBALL", "直播服务返回失败", "toast"),
    _e(1273, "FOOTBALL", "直播服务鉴权失败", "toast"),
    _e(1500, "COMMON", "关联的数据不存在", "toast"),
    _e(1501, "COMMON", "关联的数据已停用", "toast"),
    _e(1502, "COMMON", "存在关联数据，不能删除或停用", "toast"),
    _e(1503, "COMMON", "字典值不合法", "toast"),
    _e(1504, "COMMON", "资源不可用", "toast"),
    _e(5001, "COMMON", "数据库异常，请稍后再试", "toast"),
    _e(5002, "COMMON", "缓存服务异常，请稍后再试", "toast"),
    _e(5003, "COMMON", "钉钉服务超时，请稍后再试", "toast"),
    _e(5004, "COMMON", "绘图服务暂不可用", "toast"),
    _e(5005, "COMMON", "文件处理失败", "toast"),
    _e(5006, "COMMON", "定时任务执行失败", "toast"),
    _e(5007, "COMMON", "系统繁忙，请稍后再试", "toast"),
]

_REGISTRY: dict[int, ErrorEntry] = {}


def _in_range(domain: str, code: int) -> bool:
    return any(lo <= code <= hi for lo, hi in DOMAIN_RANGES.get(domain, []))


def build_registry(extra: list[ErrorEntry] | None = None) -> dict[int, ErrorEntry]:
    reg: dict[int, ErrorEntry] = {}
    for entry in list(BASE_ENTRIES) + list(extra or []):
        if entry.code in reg:
            raise ValueError(f"错误码重复登记: {entry.code}")
        if not _in_range(entry.domain, entry.code):
            raise ValueError(f"错误码 {entry.code} 不属于域 {entry.domain} 的号段")
        if not entry.front_strategy:
            raise ValueError(f"错误码 {entry.code} 缺少前端策略")
        reg[entry.code] = entry
    return reg


def install_registry(extra: list[ErrorEntry] | None = None) -> dict[int, ErrorEntry]:
    global _REGISTRY
    _REGISTRY = build_registry(extra)
    return _REGISTRY


def get_registry() -> dict[int, ErrorEntry]:
    if not _REGISTRY:
        install_registry()
    return _REGISTRY


def get_entry(code: int) -> ErrorEntry | None:
    return get_registry().get(code)


def check_messages(entries: list[ErrorEntry] | None = None) -> list[str]:
    """中文提示不得含连续大写编码或接口路径。"""
    import re

    bad = []
    items = entries if entries is not None else list(get_registry().values())
    pattern = re.compile(r"[A-Z_]{3,}|/admin-api")
    for entry in items:
        if pattern.search(entry.msg):
            bad.append(f"{entry.code}: {entry.msg}")
    return bad


install_registry()
