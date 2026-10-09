<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>模型与提示词</h1>
        <div class="sub">OPS M8 收编 · 禁止两套 Key · /ims/air/cfg</div>
      </div>
    </div>

    <div class="rowline" style="gap: 8px; margin-bottom: 12px; flex-wrap: wrap">
      <button class="btn btn-sm" :class="tab === 'model' ? 'btn-pri' : 'btn-sec'" type="button" @click="switchTab('model')">
        模型连接
      </button>
      <button class="btn btn-sm" :class="tab === 'prompt' ? 'btn-pri' : 'btn-sec'" type="button" @click="switchTab('prompt')">
        提示词
      </button>
      <button class="btn btn-sm" :class="tab === 'key' ? 'btn-pri' : 'btn-sec'" type="button" @click="switchTab('key')">
        Key 管理
      </button>
      <button class="btn btn-sm" :class="tab === 'audit' ? 'btn-pri' : 'btn-sec'" type="button" @click="switchTab('audit')">
        审计监控
      </button>
      <span class="sp"></span>
      <button v-if="tab === 'model'" class="btn btn-pri btn-sm" type="button" @click="openModelForm()">新增模型</button>
      <button v-else-if="tab === 'prompt'" class="btn btn-pri btn-sm" type="button" @click="openPromptForm()">新增提示词</button>
      <button v-else-if="tab === 'key'" class="btn btn-pri btn-sm" type="button" data-testid="air-key-generate" @click="openGenerate">
        生成 Key
      </button>
    </div>

    <div v-if="tab === 'key'" class="tbl-block">
      <form class="qbar" data-testid="air-key-query" @submit.prevent="loadKeys">
        <input
          v-model="keyQuery.userName"
          placeholder="归属人员"
          style="width: 140px"
          data-testid="air-key-user-filter"
        />
        <select v-model="keyQuery.status" style="width: 120px" data-testid="air-key-status">
          <option value="">全部状态</option>
          <option value="ACTIVE">启用</option>
          <option value="FROZEN">冻结</option>
          <option value="REVOKED">已吊销</option>
        </select>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="air-key-search">查询</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="air-key-reset" @click="resetKeys">重置</button>
      </form>
      <p v-if="keyListError" class="hint" style="color: var(--red)" data-testid="air-key-list-error">{{ keyListError }}</p>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>持有人</th>
              <th>掩码</th>
              <th>QPM 限额</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="6"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-else-if="!keys.length">
              <td colspan="6">
                <div class="empty" data-testid="air-key-empty"><div class="et">暂无 Key</div></div>
              </td>
            </tr>
            <tr v-for="row in keys" v-else :key="row.id" :data-status="row.status">
              <td class="mono">{{ row.keyCode }}</td>
              <td>{{ row.ownerUsername || row.ownerName || row.ownerUserId }}</td>
              <td class="mono" data-testid="air-key-mask">{{ row.keyMask || row.keyPrefix }}</td>
              <td class="num" data-testid="air-qpm-cell">{{ row.qpmLimit }}</td>
              <td data-testid="air-key-status-cell">{{ keyStatusLabel(row) }}</td>
              <td>
                <button
                  v-if="row.status === 'ACTIVE'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="air-key-renew"
                  @click="openRenew(row)"
                >
                  换新
                </button>
                <button
                  v-if="row.status === 'ACTIVE'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="air-key-freeze"
                  @click="askKeyAction(row, 'freeze')"
                >
                  停用
                </button>
                <button
                  v-if="row.status === 'FROZEN'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="air-key-unfreeze"
                  @click="askKeyAction(row, 'unfreeze')"
                >
                  启用
                </button>
                <button
                  v-if="row.status === 'ACTIVE'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="air-key-revoke"
                  @click="revokeKey(row)"
                >
                  吊销
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'audit'">
      <div class="tbl-block" data-testid="air-mcp-audit">
        <div class="rowline" style="margin-bottom: 8px">
          <b>MCP 调用审计</b>
          <span class="hint">数据来自 ims_mcp_log · 网关不执行模型，Token 记 0</span>
          <span class="sp"></span>
          <button class="btn btn-sec btn-sm" type="button" data-testid="air-mcp-export" @click="exportMcpPage">
            导出当前页
          </button>
        </div>
        <form class="qbar" data-testid="air-mcp-query" @submit.prevent="searchMcpLogs">
          <input
            v-model="mcpKeyword"
            placeholder="工具名 / 人员"
            style="width: 140px"
            data-testid="air-mcp-keyword"
          />
          <select v-model="mcpTool" style="width: 180px" data-testid="air-mcp-tool">
            <option value="">全部工具</option>
            <option value="skills.list">skills.list</option>
            <option value="skills.get">skills.get</option>
            <option value="experts.list">experts.list</option>
            <option value="experts.assemble">experts.assemble</option>
          </select>
          <select v-model="mcpResult" style="width: 120px" data-testid="air-mcp-result">
            <option value="">全部结果</option>
            <option value="SUCCESS">成功</option>
            <option value="FAIL">失败</option>
          </select>
          <input v-model="mcpKeyCode" placeholder="Key 编号" style="width: 120px" data-testid="air-mcp-key" />
          <input v-model="mcpFrom" type="date" aria-label="开始日期" data-testid="air-mcp-from" />
          <input v-model="mcpTo" type="date" aria-label="结束日期" data-testid="air-mcp-to" />
          <button class="btn btn-pri btn-sm" type="submit" data-testid="air-mcp-search">查询</button>
          <button class="btn btn-sec btn-sm" type="button" data-testid="air-mcp-reset" @click="resetMcpLogs">重置</button>
        </form>
        <p v-if="mcpFilterError" class="hint" style="color: var(--red)" data-testid="air-mcp-filter-error">{{ mcpFilterError }}</p>
        <p class="hint" data-testid="air-mcp-hint">
          过滤命中只计组装时被剔除的未发布技能。本期无检索，不返回 knowledgeContext。
        </p>
        <p class="hint" data-testid="air-mcp-retain">仅导出当前页。审计日志保留 180 天，超期记录已清理。</p>
        <p v-if="exportMsg" class="hint" data-testid="air-mcp-export-msg">{{ exportMsg }}</p>
        <p v-if="drillLabel" class="hint" data-testid="air-mcp-drill">
          已从用量下钻：{{ drillLabel }}
          <button class="btn btn-sec btn-sm" type="button" data-testid="air-mcp-drill-clear" @click="clearDrill">
            清除下钻
          </button>
        </p>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th>工具</th>
                <th>调用人</th>
                <th>Key</th>
                <th>结果</th>
                <th>耗时</th>
                <th>Token</th>
                <th>过滤命中</th>
                <th>鉴权说明</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="mcpLoading">
                <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!mcpLogs.length">
                <td colspan="9"><div class="empty"><div class="et">暂无调用日志</div></div></td>
              </tr>
              <tr
                v-for="row in mcpLogs"
                v-else
                :key="row.id"
                data-testid="air-mcp-row"
                :data-tool="row.tool"
                :data-cost="row.costMs"
                :data-token="row.tokenCnt"
                :data-filter="row.filterHit"
                :data-digest="row.paramDigest"
                style="cursor: pointer"
                @click="openLog(row)"
              >
                <td class="mono">{{ row.createdAt }}</td>
                <td class="mono" data-testid="air-mcp-tool-cell">{{ row.tool }}</td>
                <td>{{ row.userName }}</td>
                <td class="mono">{{ row.keyCode || '—' }}</td>
                <td>{{ row.resultCode === 'SUCCESS' ? '成功' : `失败·${row.resultCode}` }}</td>
                <td class="num" data-testid="air-mcp-cost" :style="row.costMs > 1500 ? 'color:#b58105' : ''">{{ row.costMs }} ms</td>
                <td class="num" data-testid="air-mcp-token">{{ row.tokenCnt }}</td>
                <td class="num" data-testid="air-mcp-filter">{{ row.filterHit }}</td>
                <td>{{ row.authNote }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="tbl-block" style="margin-top: 16px" data-testid="air-usage-card">
        <div class="rowline" style="margin-bottom: 8px">
          <b>用量统计</b>
          <span class="hint" data-testid="air-usage-as-of">数据截至 {{ usageAsOf }}</span>
          <span class="hint" data-testid="air-usage-retain">近 7 天 · 审计日志保留 180 天</span>
        </div>
        <p class="hint" data-testid="air-usage-stub">
          连接器在线数、QPS 与慢调用告警接预警中心（本地桩，不外发）。
        </p>
        <form class="qbar" @submit.prevent="loadUsage">
          <input v-model="usageStart" type="date" data-testid="air-usage-start" />
          <input v-model="usageEnd" type="date" data-testid="air-usage-end" />
          <button
            class="btn btn-sm"
            :class="usageBy === 'DAY' ? 'btn-pri' : 'btn-sec'"
            type="button"
            data-testid="air-usage-by-day"
            @click="setUsageBy('DAY')"
          >
            按日
          </button>
          <button
            class="btn btn-sm"
            :class="usageBy === 'PERSON' ? 'btn-pri' : 'btn-sec'"
            type="button"
            data-testid="air-usage-by-person"
            @click="setUsageBy('PERSON')"
          >
            按人
          </button>
          <button
            class="btn btn-sm"
            :class="usageBy === 'TOOL' ? 'btn-pri' : 'btn-sec'"
            type="button"
            data-testid="air-usage-by-tool"
            @click="setUsageBy('TOOL')"
          >
            按工具
          </button>
          <button class="btn btn-pri btn-sm" type="submit" data-testid="air-usage-search">统计</button>
        </form>
        <p v-if="usageError" class="hint" style="color: var(--red)" data-testid="air-usage-error">{{ usageError }}</p>
        <p v-if="usageEmpty" class="hint" data-testid="air-usage-empty">该区间暂无调用</p>
        <div v-if="usageBy === 'DAY' && usageDays.length" class="air-usage-bars" data-testid="air-usage-days">
          <button
            v-for="row in usageDays"
            :key="row.statDate"
            class="air-usage-bar"
            type="button"
            data-testid="air-usage-day"
            :data-date="row.statDate"
            :data-count="row.callCnt"
            @click="drillDay(row.statDate)"
          >
            <span class="air-usage-fill" :style="{ height: barHeight(row.callCnt) }"></span>
            <b>{{ row.callCnt }}</b>
            <span class="mono">{{ row.statDate.slice(5) }}</span>
          </button>
        </div>
        <div v-else-if="usageBy === 'PERSON'" class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>调用人</th>
                <th>部门</th>
                <th>次数</th>
                <th>Token</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in usagePeople" :key="row.userId" data-testid="air-usage-person" :data-count="row.callCnt">
                <td>{{ row.userName || row.userId }}</td>
                <td>{{ row.deptName }}</td>
                <td class="num">{{ row.callCnt }}</td>
                <td class="num">{{ row.tokenCnt }}</td>
                <td>
                  <button class="btn btn-sec btn-sm" type="button" data-testid="air-usage-drill" @click="drillPerson(row)">
                    下钻
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="usageBy === 'TOOL'" class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>工具</th>
                <th>次数</th>
                <th>失败</th>
                <th>平均耗时</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in usageTools" :key="row.tool" data-testid="air-usage-tool" :data-tool="row.tool" :data-count="row.callCnt">
                <td class="mono">
                  {{ row.tool }}
                  <div v-if="row.tool === 'experts.assemble'" class="hint">组装包下发 · 网关不执行模型，Token 记 0</div>
                </td>
                <td class="num">{{ row.callCnt }}</td>
                <td class="num">{{ row.failCnt }}</td>
                <td class="num">{{ row.avgCostMs }} ms</td>
                <td>
                  <button class="btn btn-sec btn-sm" type="button" data-testid="air-usage-drill" @click="drillTool(row.tool)">
                    下钻
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="tbl-block" style="margin-top: 16px">
        <div class="rowline" style="margin-bottom: 8px"><b>模型调用留痕</b></div>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Trace</th>
                <th>场景</th>
                <th>模型</th>
                <th>Token</th>
                <th>耗时 ms</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading"><td colspan="6"><div class="empty"><div class="et">加载中</div></div></td></tr>
              <tr v-else-if="!audits.length">
                <td colspan="6"><div class="empty" data-testid="air-audit-empty"><div class="et">暂无模型调用留痕</div></div></td>
              </tr>
              <tr v-for="row in audits" v-else :key="row.id">
                <td class="mono">{{ row.traceId }}</td>
                <td>{{ row.scene }}</td>
                <td>{{ row.modelName }}</td>
                <td class="num">{{ row.tokenIn }}/{{ row.tokenOut }}</td>
                <td class="num">{{ row.latencyMs }}</td>
                <td>{{ row.status }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-else-if="tab === 'model'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>厂商</th>
              <th>模型</th>
              <th>场景</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="6"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-else-if="!models.length">
              <td colspan="6"><div class="empty" data-testid="air-model-empty"><div class="et">暂无模型连接</div></div></td>
            </tr>
            <tr v-for="row in models" v-else :key="row.id">
              <td class="mono">{{ row.configCode }}</td>
              <td>{{ row.vendor }}</td>
              <td>{{ row.modelName }}</td>
              <td>{{ row.useCase }}</td>
              <td>{{ row.status }}</td>
              <td><button class="btn btn-sec btn-sm" type="button" @click="openModelForm(row)">编辑</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'prompt'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>场景</th>
              <th>文档类型</th>
              <th>版本</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="6"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-else-if="!prompts.length">
              <td colspan="6"><div class="empty" data-testid="air-prompt-empty"><div class="et">暂无提示词</div></div></td>
            </tr>
            <tr v-for="row in prompts" v-else :key="row.id">
              <td class="mono">{{ row.promptCode }}</td>
              <td>{{ row.scene }}</td>
              <td>{{ row.docType || '—' }}</td>
              <td>{{ row.versionLabel }}</td>
              <td>{{ row.status }}</td>
              <td><button class="btn btn-sec btn-sm" type="button" @click="openPromptForm(row)">编辑</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="keyAction" class="modal-mask" data-testid="air-key-action">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">{{ keyAction.kind === 'freeze' ? '停用 Key' : '启用 Key' }}</h3>
        <p class="hint" data-testid="air-key-action-hint">
          {{
            keyAction.kind === 'freeze'
              ? '停用期间所有 MCP 调用返回 401，恢复后即刻生效。'
              : '解冻后清空认证失败计数，并按当前在职状态与授权实时鉴权。'
          }}
        </p>
        <p style="margin: 8px 0 0">{{ keyAction.keyCode }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" data-testid="air-key-action-cancel" @click="keyAction = null">
            取消
          </button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-key-action-ok" @click="confirmKeyAction">
            {{ keyAction.kind === 'freeze' ? '确认停用' : '确认启用' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="activeLog" class="modal-mask" @click.self="activeLog = null">
      <div class="card" style="width: 560px; padding: 20px" data-testid="air-mcp-detail">
        <h3 style="margin: 0 0 12px">调用详情</h3>
        <div class="kv">
          <div><div class="k">时间</div><div class="v mono">{{ activeLog.createdAt }}</div></div>
          <div><div class="k">调用人</div><div class="v">{{ activeLog.userName || '—' }}</div></div>
          <div><div class="k">Key</div><div class="v mono">{{ activeLog.keyCode || '—' }}</div></div>
          <div><div class="k">工具</div><div class="v mono" data-testid="air-mcp-detail-tool">{{ activeLog.tool }}</div></div>
          <div><div class="k">结果</div><div class="v">{{ activeLog.resultCode === 'SUCCESS' ? '成功' : `失败·${activeLog.resultCode}` }}</div></div>
          <div><div class="k">耗时</div><div class="v">{{ activeLog.costMs }} ms</div></div>
          <div><div class="k">Token</div><div class="v">{{ activeLog.tokenCnt }}</div></div>
          <div><div class="k">过滤命中</div><div class="v">{{ activeLog.filterHit }}</div></div>
        </div>
        <p class="hint">鉴权说明：{{ activeLog.authNote || '—' }}</p>
        <p class="hint">参数摘要：<span class="mono" data-testid="air-mcp-digest">{{ activeLog.paramDigest || '—' }}</span></p>
        <p v-if="activeLog.tool === 'experts.assemble'" class="hint" data-testid="air-mcp-pack-note">
          组装包下发。网关不执行模型，不返回 knowledgeContext。
        </p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-mcp-detail-close" @click="activeLog = null">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="showKeyForm" class="modal-mask" @click.self="showKeyForm = false">
      <div class="card" style="width: 440px; padding: 20px" data-testid="air-key-form">
        <h3 style="margin: 0 0 12px">{{ keyForm.mode === 'renew' ? '换新并调整 QPM' : '生成 Key' }}</h3>
        <p class="hint">明文只在成功时展示一次。换新后新 Key 的 QPM 立即按新限额计数，旧 Key 宽限 24 小时。</p>
        <template v-if="keyForm.mode === 'generate'">
          <label class="fld">归属人员</label>
          <div style="display: flex; gap: 8px; margin-bottom: 8px">
            <input v-model="userKeyword" class="fld-in" data-testid="air-key-user-search" placeholder="用户名，如 e2e_author" />
            <button class="btn btn-sec btn-sm" type="button" @click="searchUsers">查找</button>
          </div>
          <select v-model="keyForm.userId" class="fld-in" data-testid="air-key-user">
            <option value="">请选择</option>
            <option v-for="user in userOptions" :key="user.id" :value="String(user.id)">
              {{ user.username }}{{ user.nickname ? ` · ${user.nickname}` : '' }}
            </option>
          </select>
        </template>
        <label class="fld">设备用途</label>
        <input v-model="keyForm.deviceName" class="fld-in" data-testid="air-key-device" />
        <label class="fld">QPM 限额（次/分钟）</label>
        <input v-model.number="keyForm.qpmLimit" class="fld-in" type="number" min="1" data-testid="air-qpm-limit" />
        <label class="fld">有效期至</label>
        <input v-model="keyForm.expireAt" class="fld-in" type="date" data-testid="air-key-expire" />
        <p v-if="keyError" class="hint" style="color: var(--red)" data-testid="air-key-error">{{ keyError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showKeyForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-key-save" @click="submitKey">
            {{ keyForm.mode === 'renew' ? '换新' : '生成' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="issued" class="modal-mask">
      <div class="card" style="width: 520px; padding: 20px" data-testid="air-key-plain-modal">
        <h3 style="margin: 0 0 12px">Key 明文（仅此一次）</h3>
        <p class="hint">关闭后不可再次查看。列表只保留掩码。</p>
        <p class="mono" data-testid="air-key-code">{{ issued.keyCode }}</p>
        <p class="mono" data-testid="air-key-plain" style="word-break: break-all">{{ issued.plainKey }}</p>
        <p data-testid="air-key-issued-qpm">QPM {{ issued.qpmLimit }} 次/分钟</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-key-plain-close" @click="issued = null">
            关闭（明文不再显示）
          </button>
        </div>
      </div>
    </div>

    <div v-if="showModel" class="modal-mask" @click.self="showModel = false">
      <div class="card" style="width: 440px; padding: 20px">
        <h3 style="margin: 0 0 12px">{{ modelForm.id ? '编辑模型' : '新增模型' }}</h3>
        <label class="fld">厂商</label>
        <input v-model="modelForm.vendor" class="fld-in" placeholder="QWEN / GPT …" />
        <label class="fld">模型名</label>
        <input v-model="modelForm.modelName" class="fld-in" />
        <label class="fld">Endpoint</label>
        <input v-model="modelForm.endpointUrl" class="fld-in" />
        <label class="fld">状态</label>
        <select v-model="modelForm.status" class="fld-in">
          <option value="CONNECTED">CONNECTED</option>
          <option value="DISCONNECTED">DISCONNECTED</option>
        </select>
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showModel = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="saveModel">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showPrompt" class="modal-mask" @click.self="showPrompt = false">
      <div class="card" style="width: 480px; padding: 20px">
        <h3 style="margin: 0 0 12px">{{ promptForm.id ? '编辑提示词' : '新增提示词' }}</h3>
        <label class="fld">场景</label>
        <input v-model="promptForm.scene" class="fld-in" />
        <label class="fld">文档类型</label>
        <input v-model="promptForm.docType" class="fld-in" />
        <label class="fld">正文</label>
        <textarea v-model="promptForm.content" class="fld-in" rows="5" />
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showPrompt = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="savePrompt">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'

type ModelRow = {
  id: number
  configCode: string
  vendor: string
  modelName: string
  useCase: string
  endpointUrl: string
  status: string
}

type PromptRow = {
  id: number
  promptCode: string
  scene: string
  docType: string
  versionLabel: string
  content: string
  status: string
}

type TabId = 'model' | 'prompt' | 'key' | 'audit'

const route = useRoute()
const router = useRouter()
const tab = ref<TabId>('model')
const loading = ref(false)
const models = ref<ModelRow[]>([])
const prompts = ref<PromptRow[]>([])
type KeyRow = {
  id: number
  keyCode: string
  ownerUserId: number
  ownerName: string
  ownerUsername: string
  keyPrefix: string
  keyMask: string
  qpmLimit: number
  status: string
  freezeReason?: string
  graceUntil: string
}

type IssuedKey = {
  keyId: number
  keyCode: string
  plainKey: string
  qpmLimit: number
  keyMask: string
}

const keys = ref<KeyRow[]>([])
const showKeyForm = ref(false)
const keyError = ref('')
const keyListError = ref('')
const keyQuery = reactive({ userName: '', status: '' })
const keyAction = ref<null | { id: number; keyCode: string; kind: 'freeze' | 'unfreeze' }>(null)
const userKeyword = ref('')
const userOptions = ref<{ id: string; username: string; nickname: string }[]>([])
const issued = ref<IssuedKey | null>(null)
const keyForm = reactive({
  mode: 'generate' as 'generate' | 'renew',
  keyId: 0,
  userId: '',
  deviceName: '个人通用',
  qpmLimit: 60,
  expireAt: '',
})
type McpLog = {
  id: number
  createdAt: string
  tool: string
  userName: string
  keyCode: string
  resultCode: string
  costMs: number
  tokenCnt: number
  filterHit: number
  authNote: string
  paramDigest: string
}

type UsageDay = { statDate: string; callCnt: number; tokenCnt: number }
type UsagePerson = { userId: number; userName: string; deptName: string; callCnt: number; tokenCnt: number }
type UsageTool = { tool: string; callCnt: number; failCnt: number; avgCostMs: number }

const mcpLogs = ref<McpLog[]>([])
const mcpLoading = ref(false)
const mcpTool = ref('')
const mcpResult = ref('')
const mcpKeyword = ref('')
const mcpKeyCode = ref('')
const mcpFrom = ref('')
const mcpTo = ref('')
const mcpFilterError = ref('')
const exportMsg = ref('')
const drillLabel = ref('')
const drillDate = ref('')
const drillKeyword = ref('')
const activeLog = ref<McpLog | null>(null)
const usageAsOf = ref('—')
const usageBy = ref<'DAY' | 'PERSON' | 'TOOL'>('DAY')
const usageStart = ref('')
const usageEnd = ref('')
const usageError = ref('')
const usageDays = ref<UsageDay[]>([])
const usagePeople = ref<UsagePerson[]>([])
const usageTools = ref<UsageTool[]>([])
const usageEmpty = computed(() => {
  if (usageError.value) return false
  if (usageBy.value === 'DAY') return usageDays.value.length > 0 && usageDays.value.every((row) => row.callCnt === 0)
  if (usageBy.value === 'PERSON') return usagePeople.value.length === 0
  return usageTools.value.length > 0 && usageTools.value.every((row) => row.callCnt === 0)
})
const audits = ref<
  {
    id: number
    traceId: string
    scene: string
    modelName: string
    tokenIn: number
    tokenOut: number
    latencyMs: number
    status: string
  }[]
>([])
const showModel = ref(false)
const showPrompt = ref(false)
const formError = ref('')

const modelForm = reactive({
  id: 0,
  vendor: '',
  modelName: '',
  endpointUrl: '',
  status: 'CONNECTED',
})

const promptForm = reactive({
  id: 0,
  scene: '',
  docType: '',
  content: '',
  status: 'ENABLED',
})

function tabFromRoute(): TabId {
  const q = String(route.query.tab || '')
  if (q === 'key' || q === 'audit' || q === 'prompt') return q
  return 'model'
}

function switchTab(name: TabId) {
  tab.value = name
  router.replace({ path: '/ims/air/cfg', query: name === 'model' ? {} : { tab: name } })
  loadTabData(name)
}

function defaultExpire(): string {
  const day = new Date()
  day.setFullYear(day.getFullYear() + 1)
  const month = String(day.getMonth() + 1).padStart(2, '0')
  const date = String(day.getDate()).padStart(2, '0')
  return `${day.getFullYear()}-${month}-${date}`
}

function keyStatusLabel(row: KeyRow): string {
  if (row.status === 'REVOKED') return '已吊销'
  if (row.status === 'FROZEN') return row.freezeReason ? `冻结·${row.freezeReason}` : '冻结'
  if (row.graceUntil) return '启用（宽限）'
  return '启用'
}

function openGenerate() {
  keyError.value = ''
  issued.value = null
  keyForm.mode = 'generate'
  keyForm.keyId = 0
  keyForm.userId = ''
  keyForm.deviceName = '个人通用'
  keyForm.qpmLimit = 60
  keyForm.expireAt = defaultExpire()
  userKeyword.value = ''
  userOptions.value = []
  showKeyForm.value = true
}

function openRenew(row: KeyRow) {
  keyError.value = ''
  issued.value = null
  keyForm.mode = 'renew'
  keyForm.keyId = row.id
  keyForm.userId = String(row.ownerUserId)
  keyForm.deviceName = '个人通用'
  keyForm.qpmLimit = row.qpmLimit || 60
  keyForm.expireAt = defaultExpire()
  showKeyForm.value = true
}

async function searchUsers() {
  keyError.value = ''
  try {
    const res = await http.get('/system/user/page', {
      params: { pageNo: 1, pageSize: 20, username: userKeyword.value.trim() },
    })
    userOptions.value = res.data.data.list || []
    if (userOptions.value.length === 1) keyForm.userId = String(userOptions.value[0].id)
  } catch (error) {
    keyError.value = errorMessage(error)
  }
}

async function submitKey() {
  keyError.value = ''
  const qpm = Number(keyForm.qpmLimit)
  if (!Number.isInteger(qpm) || qpm < 1) {
    keyError.value = 'QPM 限额须为正整数'
    return
  }
  if (!keyForm.expireAt) {
    keyError.value = '请填写有效期'
    return
  }
  if (keyForm.mode === 'generate' && !keyForm.userId) {
    keyError.value = '请选择归属人员'
    return
  }
  try {
    const res =
      keyForm.mode === 'renew'
        ? await http.post(`/air/key/${keyForm.keyId}/renew`, {
            deviceName: keyForm.deviceName.trim() || '个人通用',
            qpmLimit: qpm,
            expireAt: keyForm.expireAt,
          })
        : await http.post('/air/key/generate', {
            userId: Number(keyForm.userId),
            deviceName: keyForm.deviceName.trim() || '个人通用',
            qpmLimit: qpm,
            expireAt: keyForm.expireAt,
            clientToken: `ui-${Date.now()}-${Math.random().toString(16).slice(2)}`,
          })
    issued.value = res.data.data
    showKeyForm.value = false
    await loadKeys()
  } catch (error) {
    keyError.value = errorMessage(error)
  }
}

async function revokeKey(row: KeyRow) {
  if (!window.confirm(`吊销 ${row.keyCode} 后不可恢复，调用立即失败。`)) return
  try {
    await http.post(`/air/key/${row.id}/revoke`, { reason: '页面吊销' })
    await loadKeys()
  } catch (error) {
    keyListError.value = errorMessage(error)
  }
}

function askKeyAction(row: KeyRow, kind: 'freeze' | 'unfreeze') {
  keyListError.value = ''
  keyAction.value = { id: row.id, keyCode: row.keyCode, kind }
}

async function confirmKeyAction() {
  const action = keyAction.value
  if (!action) return
  keyAction.value = null
  try {
    if (action.kind === 'freeze') {
      await http.post(`/air/key/${action.id}/freeze`, { reason: '管理员停用' })
    } else {
      await http.post(`/air/key/${action.id}/unfreeze`)
    }
    await loadKeys()
  } catch (error) {
    keyListError.value = errorMessage(error)
  }
}

function resetKeys() {
  keyQuery.userName = ''
  keyQuery.status = ''
  loadKeys()
}

async function loadKeys() {
  loading.value = true
  keyListError.value = ''
  try {
    const res = await http.get('/air/cfg/key/page', {
      params: {
        pageNo: 1,
        pageSize: 100,
        userName: keyQuery.userName.trim() || undefined,
        status: keyQuery.status || undefined,
      },
    })
    if (res.data.code === 0) keys.value = res.data.data.list || []
  } catch (error) {
    keys.value = []
    keyListError.value = errorMessage(error)
  } finally {
    loading.value = false
  }
}

async function loadAudits() {
  loading.value = true
  try {
    const res = await http.get('/air/cfg/audit/page', { params: { pageNo: 1, pageSize: 50 } })
    if (res.data.code === 0) audits.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

function resetMcpLogs() {
  mcpKeyword.value = ''
  mcpTool.value = ''
  mcpResult.value = ''
  mcpKeyCode.value = ''
  mcpFrom.value = ''
  mcpTo.value = ''
  mcpFilterError.value = ''
  drillDate.value = ''
  drillKeyword.value = ''
  drillLabel.value = ''
  loadMcpLogs()
}

function searchMcpLogs() {
  drillDate.value = ''
  drillKeyword.value = ''
  drillLabel.value = ''
  loadMcpLogs()
}

function openLog(row: McpLog) {
  activeLog.value = row
}

function clearDrill() {
  drillDate.value = ''
  drillKeyword.value = ''
  drillLabel.value = ''
  mcpTool.value = ''
  mcpResult.value = ''
  loadMcpLogs()
}

function drillDay(day: string) {
  mcpTool.value = ''
  mcpResult.value = ''
  drillKeyword.value = ''
  drillDate.value = day
  drillLabel.value = day
  loadMcpLogs()
}

function drillTool(tool: string) {
  mcpTool.value = tool
  drillDate.value = ''
  drillKeyword.value = ''
  drillLabel.value = `工具 ${tool}`
  loadMcpLogs()
}

function drillPerson(row: UsagePerson) {
  mcpTool.value = ''
  mcpResult.value = ''
  drillDate.value = ''
  drillKeyword.value = row.userName || String(row.userId)
  drillLabel.value = `调用人 ${drillKeyword.value}`
  loadMcpLogs()
}

function barHeight(count: number): string {
  const max = Math.max(...usageDays.value.map((row) => row.callCnt), 1)
  if (!count) return '0%'
  return `${Math.max(8, Math.round((count / max) * 100))}%`
}

function xmlEscape(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function exportMcpPage() {
  exportMsg.value = ''
  if (!mcpLogs.value.length) {
    exportMsg.value = '暂无调用日志可导出'
    return
  }
  const header = ['时间', '工具', '调用人', 'Key', '结果', '耗时ms', 'Token', '过滤命中', '鉴权说明', '参数摘要']
  const body = mcpLogs.value.map((row) => [
    row.createdAt,
    row.tool,
    row.userName,
    row.keyCode,
    row.resultCode,
    String(row.costMs),
    String(row.tokenCnt),
    String(row.filterHit),
    row.authNote,
    row.paramDigest,
  ])
  const xmlRows = [header, ...body]
    .map(
      (cols) =>
        `<Row>${cols.map((col) => `<Cell><Data ss:Type="String">${xmlEscape(String(col ?? ''))}</Data></Cell>`).join('')}</Row>`,
    )
    .join('')
  const xml = `<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
<Worksheet ss:Name="MCP审计"><Table>${xmlRows}</Table></Worksheet>
</Workbook>`
  const blob = new Blob([xml], { type: 'application/vnd.ms-excel' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = 'air_mcp_audit_page.xls'
  document.body.appendChild(link)
  link.click()
  link.remove()
  exportMsg.value = '已导出当前页'
}

async function loadMcpLogs() {
  mcpFilterError.value = ''
  const from = mcpFrom.value.trim()
  const to = mcpTo.value.trim()
  if ((from && !to) || (!from && to)) {
    mcpFilterError.value = '日期区间须同时填写开始日和结束日'
    return
  }
  if (from && to && to < from) {
    mcpFilterError.value = '结束日不能早于开始日'
    return
  }
  mcpLoading.value = true
  exportMsg.value = ''
  try {
    const res = await http.get('/air/mcp/audit-log', {
      params: {
        pageNo: 1,
        pageSize: 20,
        keyword: (drillKeyword.value || mcpKeyword.value).trim() || undefined,
        tool: mcpTool.value || undefined,
        result: mcpResult.value || undefined,
        keyCode: mcpKeyCode.value.trim() || undefined,
        dateRange: drillDate.value
          ? `${drillDate.value},${drillDate.value}`
          : from && to
            ? `${from},${to}`
            : undefined,
      },
    })
    if (res.data.code === 0) {
      mcpLogs.value = res.data.data.list || []
      if (!drillLabel.value) {
        usageAsOf.value = mcpLogs.value[0]?.createdAt || '—'
      }
    }
  } catch (error) {
    mcpLogs.value = []
    mcpFilterError.value = errorMessage(error)
  } finally {
    mcpLoading.value = false
  }
}

async function loadUsage() {
  usageError.value = ''
  if ((usageStart.value && !usageEnd.value) || (!usageStart.value && usageEnd.value)) {
    usageError.value = '请同时选择开始和结束日期'
    return
  }
  try {
    const res = await http.get('/air/usage/stat', {
      params: {
        by: usageBy.value,
        dateRange: usageStart.value && usageEnd.value ? `${usageStart.value},${usageEnd.value}` : undefined,
      },
    })
    const rows = res.data.data || []
    usageDays.value = usageBy.value === 'DAY' ? rows : []
    usagePeople.value = usageBy.value === 'PERSON' ? rows : []
    usageTools.value = usageBy.value === 'TOOL' ? rows : []
  } catch (error) {
    usageDays.value = []
    usagePeople.value = []
    usageTools.value = []
    usageError.value = errorMessage(error)
  }
}

function setUsageBy(next: 'DAY' | 'PERSON' | 'TOOL') {
  usageBy.value = next
  loadUsage()
}

function loadTabData(name: TabId) {
  if (name === 'model') loadModels()
  else if (name === 'prompt') loadPrompts()
  else if (name === 'key') loadKeys()
  else {
    loadAudits()
    loadMcpLogs()
    loadUsage()
  }
}

async function loadModels() {
  loading.value = true
  try {
    const res = await http.get('/air/cfg/model/page', { params: { pageNo: 1, pageSize: 50 } })
    if (res.data.code === 0) models.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

async function loadPrompts() {
  loading.value = true
  try {
    const res = await http.get('/air/cfg/prompt/page', { params: { pageNo: 1, pageSize: 50 } })
    if (res.data.code === 0) prompts.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

function openModelForm(row?: ModelRow) {
  formError.value = ''
  modelForm.id = row?.id || 0
  modelForm.vendor = row?.vendor || ''
  modelForm.modelName = row?.modelName || ''
  modelForm.endpointUrl = row?.endpointUrl || ''
  modelForm.status = row?.status || 'CONNECTED'
  showModel.value = true
}

function openPromptForm(row?: PromptRow) {
  formError.value = ''
  promptForm.id = row?.id || 0
  promptForm.scene = row?.scene || ''
  promptForm.docType = row?.docType || ''
  promptForm.content = row?.content || ''
  promptForm.status = row?.status || 'ENABLED'
  showPrompt.value = true
}

async function saveModel() {
  formError.value = ''
  const body = {
    vendor: modelForm.vendor,
    modelName: modelForm.modelName,
    endpointUrl: modelForm.endpointUrl,
    status: modelForm.status,
  }
  const res = modelForm.id
    ? await http.put(`/air/cfg/model/${modelForm.id}`, body)
    : await http.post('/air/cfg/model', body)
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showModel.value = false
  await loadModels()
}

async function savePrompt() {
  formError.value = ''
  const body = {
    scene: promptForm.scene,
    docType: promptForm.docType,
    content: promptForm.content,
    status: promptForm.status,
  }
  const res = promptForm.id
    ? await http.put(`/air/cfg/prompt/${promptForm.id}`, body)
    : await http.post('/air/cfg/prompt', body)
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showPrompt.value = false
  await loadPrompts()
}

watch(
  () => route.fullPath,
  () => {
    tab.value = tabFromRoute()
  },
  { immediate: true }
)

onMounted(() => {
  tab.value = tabFromRoute()
  loadTabData(tab.value)
})
</script>

<style>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.air-usage-bars {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  min-height: 120px;
  margin-top: 12px;
}
.air-usage-bar {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  height: 120px;
  border: 0;
  background: transparent;
  cursor: pointer;
  color: inherit;
  font: inherit;
}
.air-usage-fill {
  width: 70%;
  background: var(--blue);
  border-radius: 4px 4px 0 0;
  min-height: 0;
}
</style>
