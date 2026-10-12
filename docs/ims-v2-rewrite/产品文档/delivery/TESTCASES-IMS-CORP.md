# TESTCASES-IMS-CORP — 公司资产（P0）

---

## 平台账号

### TC-IMS-C-001-01 平台筛选

- **When** 打开 `/ims/corp/account/douyin` 并查询  
- **Then** 请求含 `platformType=DOUYIN`；列表仅抖音账号

### TC-IMS-C-001-02 采集 Tab 入口

- **Given** 平台账号 id  
- **When** 打开详情 · 采集 Tab  
- **Then** 可见 bind 状态与「导入 Collector」；**无** Channel-D 外部竞品配置字段

### TC-IMS-C-001-03 选择器校验

- **When** 手输 companyId 提交  
- **Then** 1500/1501/1502 拒绝

### TC-IMS-C-001-04 与 COLLECT 分工

- **When** 用户从 COLLECT P2a 找 Cookie  
- **Then** 规格/页内 Alert 指向账号详情采集 Tab（非 P2a）

---

## 资源

### TC-IMS-C-002-01 实名人列表

- **When** R1 打开实名人 L3  
- **Then** 分页列表非报错；脱敏列符合规格

---

## 设备（BLOCKED）

### TC-IMS-C-003-01 空态

- **Given** 设备 API BLOCKED  
- **When** 打开办公设备 L3  
- **Then** 空态或 BLOCKED 说明；无假数据 CRUD 成功 toast


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-CORP-A01 登记公众号平台账号

### TC-IMS-CORP-A01-01-01 P0 主路径

- **Given** CORP 菜单；强关联公司/实名人可选。
- **When** 用户按故事主路径操作（页面 `caWechatOfficial`）
- **Then** AccountSelect 可选；采集类平台 Cookie 仅详情采集 Tab。

## US-CORP-A02 登记视频号平台账号

### TC-IMS-CORP-A02-01-01 P0 主路径

- **Given** CORP 菜单；强关联公司/实名人可选。
- **When** 用户按故事主路径操作（页面 `caWechatChannels`）
- **Then** AccountSelect 可选；采集类平台 Cookie 仅详情采集 Tab。

## US-CORP-A03 登记抖音平台账号

### TC-IMS-CORP-A03-01-01 P0 主路径

- **Given** CORP 菜单；强关联公司/实名人可选。
- **When** 用户按故事主路径操作（页面 `caDouyin`）
- **Then** AccountSelect 可选；采集类平台 Cookie 仅详情采集 Tab。

## US-CORP-A04 登记快手平台账号

### TC-IMS-CORP-A04-01-01 P0 主路径

- **Given** CORP 菜单；强关联公司/实名人可选。
- **When** 用户按故事主路径操作（页面 `caKuaishou`）
- **Then** AccountSelect 可选；采集类平台 Cookie 仅详情采集 Tab。

## US-CORP-A05 登记小红书平台账号

### TC-IMS-CORP-A05-01-01 P0 主路径

- **Given** CORP 菜单；强关联公司/实名人可选。
- **When** 用户按故事主路径操作（页面 `caXhs`）
- **Then** AccountSelect 可选；采集类平台 Cookie 仅详情采集 Tab。

## US-CORP-R01 维护公司主体

### TC-IMS-CORP-R01-01-01 P0 主路径

- **Given** CORP 资源 L3。
- **When** 用户按故事主路径操作（页面 `crCompany`）
- **Then** 列表分页；脱敏列符合规格。

## US-CORP-R02 维护实名人

### TC-IMS-CORP-R02-01-01 P0 主路径

- **Given** CORP 资源 L3。
- **When** 用户按故事主路径操作（页面 `crRealname`）
- **Then** 列表分页；脱敏列符合规格。

## US-CORP-R03 维护手机卡

### TC-IMS-CORP-R03-01-01 P0 主路径

- **Given** CORP 资源 L3。
- **When** 用户按故事主路径操作（页面 `crSim`）
- **Then** 列表分页；脱敏列符合规格。

## US-CORP-R04 维护证件档案

### TC-IMS-CORP-R04-01-01 P0 主路径

- **Given** CORP 资源 L3。
- **When** 用户按故事主路径操作（页面 `crCert`）
- **Then** 列表分页；脱敏列符合规格。

## US-CORP-D01 登记办公设备

### TC-IMS-CORP-D01-01-01 P0 主路径

- **Given** 设备 API 部分 BLOCKED。
- **When** 用户按故事主路径操作（页面 `cdOffice`）
- **Then** 空态或 BLOCKED 说明；无假 CRUD 成功 toast。

## US-CORP-D02 登记直播/拍摄设备

### TC-IMS-CORP-D02-01-01 P0 主路径

- **Given** 设备 API 部分 BLOCKED。
- **When** 用户按故事主路径操作（页面 `cdLive`）
- **Then** 空态或 BLOCKED 说明；无假 CRUD 成功 toast。

## US-CORP-D03 登记手机设备

### TC-IMS-CORP-D03-01-01 P0 主路径

- **Given** 设备 API 部分 BLOCKED。
- **When** 用户按故事主路径操作（页面 `cdPhone`）
- **Then** 空态或 BLOCKED 说明；无假 CRUD 成功 toast。

