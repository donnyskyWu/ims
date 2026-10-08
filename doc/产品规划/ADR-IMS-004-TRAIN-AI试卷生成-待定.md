# ADR-IMS-004：TRAIN AI 培训试卷生成（已批准设计）

> **状态**：**已批准**（2026-10-01 用户拍板 · 本期完整实现）  
> **关联**：《TRAIN-培训管理-API契约.md》§2.4 · 《TRAIN-培训管理-页面规格.md》P2 AI 向导 · AIR 连接器

---

## 1. 背景

TRAIN-004：学习任务在勾选 **已发布** 资料后，经 AIR 生成 **单选 + 判断** 题草稿，人工审阅后写入任务 `quiz`（与手工编辑器并存）。OPS / football-front **无** 现网 LMS API。

---

## 2. 决策

| # | 项 | 决定 |
|---|-----|------|
| D1 | 能力归属 | IMS `/admin-api/ims/train/*`；模型调用 **仅** 经 AIR 连接器（收编 OPS 模型/提示词） |
| D2 | 执行形态 | **同步 HTTP v1**（请求阻塞 ≤90s；超长资料截断/OSS 分片读）；Job 异步 **Out of v1**（OPS 无统一 Job 框架可复用） |
| D3 | 题型 | **单选（SINGLE）+ 判断（TRUE_FALSE）**；无简答自动判分 |
| D4 | 资料输入 | 请求传 `materialIds[]`；服务端读 `ims_train_material` OSS Key / linkUrl；**不**新建 digest 表于 v1 |
| D5 | 采纳路径 | 生成结果 **不落库** 为独立试卷表；**采纳**后合并进 `POST/PUT …/train/task` 的 `quiz[]` + `passScore` |
| D6 | 审计 | 日志字段：`materialIds`、`promptCode`、`modelCode`、`operatorUserId`（`system_users.id` · ADR-056） |

---

## 3. API（IMS 设计 SSOT · 2026-10-01）

### 3.1 POST `/admin-api/ims/train/quiz/ai-generate`

**权限**：R1/R2（培训主责）

**请求**：

```typescript
interface TrainQuizAiGenerateReq {
  materialIds: number[];       // 必填 ≥1，均须 PUBLISHED
  questionCount: number;       // 5~30，默认 10
  /** 题型权重；v1 仅 SINGLE | TRUE_FALSE */
  mix?: { single?: number; trueFalse?: number };  // 默认 7:3
  difficulty?: 'EASY' | 'MEDIUM' | 'HARD';       // 默认 MEDIUM
}
```

**响应 `data`**：

```typescript
interface TrainQuizAiGenerateResp {
  draftId: string;             // 服务端内存/Redis 15min，供采纳幂等
  questions: Array<{
    type: 'SINGLE' | 'TRUE_FALSE';
    stem: string;
    options?: string[];        // SINGLE 必填 2~6 项
    answerIndex?: number;      // SINGLE
    answerBoolean?: boolean;   // TRUE_FALSE
    materialId: number;        // 溯源
    source: 'AI_DRAFT';
  }>;
  meta: { modelCode: string; promptCode: string; generatedAt: string };
}
```

**错误码**：1111（资料未发布/不存在）、1112（AIR 调用失败）、1113（生成超时）、1114（题量为 0）、1504。

### 3.2 POST `/admin-api/ims/train/quiz/ai-adopt`（可选 · 与直接写 task 二选一）

**请求**：`{ draftId: string; taskId?: number }` → 返回 `{ quiz: TrainTaskCreateReq['quiz']; passScore: number }` 供表单填充。**v1 允许**前端跳过本接口，直接将 `questions` 填入任务保存请求。

---

## 4. 交互 SSOT

P2 学习任务：**AI 生成试卷** 向导步骤 = 选资料（已选 materialIds 可预填）→ 参数（题量/难度）→ **同步**生成中 → 预览 → **采纳到问卷编辑器** / 丢弃。与《TRAIN-培训管理-页面规格》P2 一致。

---

## 5. 与 PERF-003

TRAIN `quiz` 为 **任务内嵌快照**；PERF-003 在线考试 **不**共用表；题型枚举可对齐命名，**禁止**共享写入。

---

## 6. 批准门槛（已满足）

- [x] 产品确认 O1 同步 v1、O3 单选+判断（2026-10-01）  
- [x] API 写入契约 §2.4  
- [ ] AIR SLA 与 111x 段登记全局规范（实现 Slice 前补一行映射表）
