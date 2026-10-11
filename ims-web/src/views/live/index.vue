<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>{{ ledgerMode ? '直播台账' : '直播管理' }}</h1>
        <div class="sub">场次中心：列表→详情 Tab（数据/风控/下播） · 10 LIVE</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec" to="/ims/live/alarm" data-testid="live-alarm-link">风险告警</router-link>
        <button class="btn btn-pri" type="button" @click="openRegister">新建场次登记</button>
        <button class="btn btn-sec" type="button" data-testid="live-supplement-open" @click="openSupplement">历史补录</button>
        <button class="btn btn-sec" type="button" data-testid="live-ledger-export" :disabled="exporting" @click="exportLedger">导出</button>
      </div>
    </div>
    <p v-if="exportNote" class="hint" data-testid="live-export-note">{{ exportNote }}</p>
    <p v-if="exportReceipt" class="hint" data-testid="live-export-receipt">
      任务 {{ exportReceipt.exportTaskId }}
      <button class="btn btn-sec btn-sm" type="button" data-testid="live-export-claim" :disabled="exporting" @click="claimExport">领取文件</button>
    </p>
    <p v-if="exportError" class="hint bad" data-testid="live-export-error">{{ exportError }}</p>
    <p v-if="slowQueryHint" class="hint" data-testid="live-slow-query">{{ slowQueryHint }}</p>
    <p v-if="hint" class="hint" style="margin-bottom: 8px">{{ hint }}</p>
    <div v-if="view === 'sessions'" class="g4" data-testid="live-stat-cards">
      <div class="card stat"><span class="l">今日待开播</span><div class="n" data-testid="live-stat-today">{{ stats.todayPendingStart }}</div></div>
      <div class="card stat"><span class="l">直播中</span><div class="n" data-testid="live-stat-live">{{ stats.liveCount }}</div></div>
      <div class="card stat"><span class="l">待录入(24h)</span><div class="n" data-testid="live-stat-entry">{{ stats.entryDue24h }}</div></div>
      <div class="card stat"><span class="l">本月 GMV(已核准)</span><div class="n" data-testid="live-stat-gmv">{{ stats.monthConfirmedGmv }}</div></div>
    </div>
    <div class="tabs">
      <div class="tab" :class="{ on: view === 'sessions' }" data-testid="live-view-sessions" @click="view = 'sessions'">场次列表</div>
      <div class="tab" :class="{ on: view === 'pending' }" data-testid="live-view-pending" @click="openPending">
        待录入督办
        <span v-if="overdueCount" data-testid="live-pending-count" style="color: var(--red)">({{ overdueCount }})</span>
      </div>
    </div>
    <form v-if="view === 'sessions'" class="qbar" @submit.prevent="searchList">
      <input v-model="query.sessionCode" placeholder="场次 ID" style="width: 160px" />
      <select v-model="query.accountId" data-testid="live-filter-account" aria-label="直播账号" style="width: 160px">
        <option value="">全部账号</option>
        <option v-for="item in regOptions.accounts" :key="item.id" :value="String(item.id)">{{ item.accountName }}</option>
      </select>
      <select v-model="query.responsibleUserId" data-testid="live-filter-owner" aria-label="责任人" style="width: 140px">
        <option value="">全部责任人</option>
        <option v-for="item in regOptions.users" :key="item.id" :value="String(item.id)">{{ item.nickname || item.username }}</option>
      </select>
      <select v-model="query.sessionStatus" data-testid="live-filter-status" style="width: 100px">
        <option value="">全部状态</option>
        <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
      <select v-model="query.platform" data-testid="live-filter-platform" style="width: 110px">
        <option value="">全部平台</option>
        <option value="DOUYIN">抖音</option>
        <option value="KUAISHOU">快手</option>
        <option value="WECHAT_CHANNELS">视频号</option>
        <option value="OTHER">其他</option>
      </select>
      <select v-model="query.riskLevel" data-testid="live-filter-risk" style="width: 100px">
        <option value="">全部风险</option>
        <option value="GREEN">绿色</option>
        <option value="YELLOW">黄色</option>
        <option value="RED">红色</option>
      </select>
      <select v-model="query.isSupplement" data-testid="live-filter-supplement" style="width: 100px">
        <option value="">全部场次</option>
        <option value="false">正常</option>
        <option value="true">补录</option>
      </select>
      <input v-model="query.timeFrom" type="date" data-testid="live-filter-from" aria-label="开播起" />
      <input v-model="query.timeTo" type="date" data-testid="live-filter-to" aria-label="开播止" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetQuery">重置</button>
    </form>
    <p v-if="view === 'sessions' && dateRangeHint" class="hint" data-testid="live-filter-date-hint">{{ dateRangeHint }}</p>
    <div v-if="view === 'sessions'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>场次 ID</th>
              <th>账号</th>
              <th>主题</th>
              <th>平台</th>
              <th>计划开播</th>
              <th>风险级别</th>
              <th>场次状态</th>
              <th>同步状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="error">
              <td colspan="9">
                <div class="empty" data-testid="live-sessions-error">
                  <div class="et">{{ error }}</div>
                  <button class="btn btn-sec btn-sm" type="button" data-testid="live-sessions-retry" @click="loadList">重试</button>
                </div>
              </td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9">
                <div class="empty" data-testid="live-sessions-empty">
                  <div class="et">暂无场次</div>
                  <div class="es" data-testid="live-sessions-empty-hint">{{ sessionsEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.sessionCode">
              <td class="mono num" style="color: var(--blue); cursor: pointer" @click="openDetail(row)">
                {{ row.sessionCode }}
                <span v-if="row.isSupplement" data-testid="live-supplement-tag" style="margin-left: 6px; color: #8e8e93">补录</span>
                <span v-if="row.isSupplement && !row.approverUserId" data-testid="live-supplement-pending" style="margin-left: 4px; color: #8e8e93">待审批</span>
              </td>
              <td class="mono" style="font-size: 12px">{{ row.accountNo }}</td>
              <td>{{ row.topic }}</td>
              <td>{{ platformText(row.platform) }}</td>
              <td class="num" style="font-size: 12px">{{ minuteText(row.planStartTime) }}</td>
              <td>
                <span data-testid="live-risk-level" :data-level="row.riskLevel || ''" :style="{ color: riskColor(row.riskLevel), fontWeight: 600 }">{{ riskText(row.riskLevel) }}</span>
              </td>
              <td>{{ sessionStatusText(row) }}</td>
              <td>{{ syncLabel(row.footballSyncStatus) }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="openDetail(row)">详情</button>
                <button
                  v-if="ledgerMode"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="live-ledger-penetrate"
                  @click="openDetail(row)"
                >
                  穿透详情
                </button>
                <button
                  v-if="row.sessionStatus === 'APPROVED' && row.startAllowed"
                  class="btn btn-pri btn-sm"
                  type="button"
                  data-testid="live-row-start"
                  @click="startFromRow(row)"
                >
                  确认开播
                </button>
                <button
                  v-if="row.sessionStatus === 'LIVE' && row.endAllowed"
                  class="btn btn-pri btn-sm"
                  type="button"
                  data-testid="live-row-end"
                  @click="askEnd(row)"
                >
                  确认下播
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager" data-testid="live-session-pager">
        <span class="pg-total">共 {{ total }} 条</span>
        <span class="pg-size">20 条/页</span>
        <span class="pg-sp"></span>
        <span class="pg-n" :class="{ dis: pageNo <= 1 }" data-testid="live-page-prev" @click="gotoPage(pageNo - 1)">‹</span>
        <span class="pg-n on">{{ pageNo }}</span>
        <span class="pg-n" :class="{ dis: pageNo >= pageCount }" data-testid="live-page-next" @click="gotoPage(pageNo + 1)">›</span>
      </div>
    </div>
    <div v-else class="tbl-block" data-testid="live-pending-panel">
      <p v-if="pendingHint" class="hint bad" data-testid="live-overdue-hint">{{ pendingHint }}</p>
      <div data-testid="live-overdue-cards" style="display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 12px">
        <div v-if="!overdueCards.length" class="card" data-testid="live-overdue-card-empty" style="padding: 14px 16px">
          <div class="et">暂无超时督办</div>
          <div class="csub">超过 24 小时未录入的场次会在这里成卡。</div>
        </div>
        <div
          v-for="row in overdueCards"
          :key="row.sessionCode"
          class="card"
          data-testid="live-overdue-card"
          style="padding: 14px 16px; min-width: 240px"
        >
          <h3 class="mono" style="font-size: 14px">{{ row.sessionCode }}</h3>
          <div class="csub">{{ row.topic || '—' }} · 已超时 {{ row.overdueHours }} 小时</div>
          <p v-if="row.superviseChannel === 'IN_APP'" data-testid="live-overdue-stub" style="margin: 8px 0; color: var(--red)">
            外部钉钉未接通，已记入站内督办
          </p>
          <button class="btn btn-sec btn-sm" type="button" @click="openDetail(row)">去录入</button>
        </div>
      </div>
      <form class="qbar" @submit.prevent="loadPending">
        <input
          v-model="pendingOwner"
          inputmode="numeric"
          data-testid="live-pending-owner"
          placeholder="责任人 id"
          aria-label="待录入责任人"
          style="width: 120px"
        />
        <label class="hint">
          <input v-model="overdueOnly" type="checkbox" data-testid="live-overdue-only" />
          仅看超过 24 小时
        </label>
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="live-pending-query">查询</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="live-pending-reset" @click="resetPending">重置</button>
      </form>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>场次 ID</th>
              <th>主题</th>
              <th>实际起止</th>
              <th>下播时间</th>
              <th>责任人</th>
              <th>超时小时</th>
              <th>督办</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="pendingLoading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="pendingError">
              <td colspan="7">
                <div class="empty" data-testid="live-pending-error">
                  <div class="et">{{ pendingError }}</div>
                  <button class="btn btn-sec btn-sm" type="button" data-testid="live-pending-retry" @click="loadPending">重试</button>
                </div>
              </td>
            </tr>
            <tr v-else-if="!pendingRows.length">
              <td colspan="7">
                <div class="empty" data-testid="live-pending-empty">
                  <div class="et">{{ pendingEmptyTitle }}</div>
                  <div class="es">{{ pendingEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in pendingRows" v-else :key="row.sessionCode" data-testid="live-pending-row">
              <td class="mono num" style="color: var(--blue); cursor: pointer" @click="openDetail(row)">{{ row.sessionCode }}</td>
              <td>{{ row.topic }}</td>
              <td class="num" style="font-size: 12px" data-testid="live-pending-range">
                <span v-if="pendingRangeText(row)">{{ pendingRangeText(row) }}</span>
                <span v-else class="es" data-testid="live-pending-unrecorded">待录入</span>
              </td>
              <td class="num" style="font-size: 12px">{{ row.endedAt || '—' }}</td>
              <td>{{ row.responsibleUserName || '—' }}</td>
              <td class="num" data-testid="live-pending-hours">{{ row.overdueHours }}</td>
              <td>
                <span v-if="row.overdue" data-testid="live-pending-overdue" style="color: var(--red)">超 24h</span>
                <span v-else>未超时</span>
                <div v-if="row.overdue" class="es" data-testid="live-urge-stub">钉钉/短信本地桩，未外发</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <ProtoDrawer :open="registerOpen" :title="registerTitle" width="720px" :z-index="130" @close="closeRegister">
      <p class="hint">提交后执行风控。实名人证件过期或锁定会拦截新场次。</p>
      <div class="formrow one">
        <div v-if="editingCode" class="fld">
          <label>场次 ID（不可变更）</label>
          <input :value="editingCode" readonly data-testid="live-session-code-lock" />
        </div>
        <div class="fld">
          <label>直播账号 *</label>
          <select v-model="reg.accountId" data-testid="live-reg-account" :style="regGap('account') ? 'border-color: var(--red)' : ''" @change="onAccountPicked">
            <option value="">请选择使用中的账号</option>
            <option v-for="item in regOptions.accounts" :key="item.id" :value="String(item.id)">{{ item.accountName }}（{{ item.accountNo }}）</option>
          </select>
          <p v-if="regGap('account')" class="hint bad" data-testid="live-reg-gap-account">必填项，请填写</p>
        </div>
        <div class="fld">
          <label>实名人 *</label>
          <select v-model="reg.realnamePersonId" data-testid="live-reg-person" :style="regGap('person') ? 'border-color: var(--red)' : ''" @change="loadCertPreview">
            <option value="">请选择实名人</option>
            <option v-for="item in regOptions.realnames" :key="item.id" :value="String(item.id)">{{ item.realName }}{{ item.status === 'ENABLED' ? '' : '（停用）' }}</option>
          </select>
          <p v-if="regGap('person')" class="hint bad" data-testid="live-reg-gap-person">必填项，请填写</p>
          <p v-if="certPreview" class="hint" data-testid="live-reg-cert" :class="{ bad: certPreview.level !== 'PASS' }" :style="certPreview.level === 'FAIL' ? 'color: var(--red)' : certPreview.level === 'WARN' ? 'color: #b8860b' : ''">{{ certPreview.detail }}</p>
        </div>
        <div class="fld">
          <label>责任人 *</label>
          <select v-model="reg.responsibleUserId" data-testid="live-reg-owner" :style="regGap('owner') ? 'border-color: var(--red)' : ''">
            <option value="">请选择责任人</option>
            <option v-for="item in regOptions.users" :key="item.id" :value="String(item.id)">{{ item.nickname }}</option>
          </select>
          <p v-if="regGap('owner')" class="hint bad" data-testid="live-reg-gap-owner">必填项，请填写</p>
        </div>
        <div class="fld">
          <label>手机设备 *</label>
          <select v-model="reg.phoneId" data-testid="live-reg-phone" :style="regGap('phone') ? 'border-color: var(--red)' : ''">
            <option value="">请选择使用中的手机</option>
            <option v-for="item in regOptions.phones" :key="item.id" :value="String(item.id)">{{ item.label }}</option>
          </select>
          <p v-if="regGap('phone')" class="hint bad" data-testid="live-reg-gap-phone">必填项，请填写</p>
        </div>
        <div class="fld">
          <label>直播设备 *</label>
          <div data-testid="live-reg-devices" :style="regGap('devices') ? 'border: 1px solid var(--red); padding: 6px' : ''">
            <p v-if="!regOptions.devices.length" class="hint">暂无使用中的直播/拍摄设备</p>
            <label v-for="item in regOptions.devices" :key="item.id" style="display: block">
              <input type="checkbox" :checked="reg.deviceIds.includes(item.id)" @change="toggleDevice(item.id)" />
              {{ item.assetName }}（{{ item.assetCode }}）
            </label>
          </div>
          <p v-if="regGap('devices')" class="hint bad" data-testid="live-reg-gap-devices">必填项，请填写</p>
        </div>
        <div class="fld">
          <label>直播平台 *</label>
          <select v-model="reg.platform" data-testid="live-reg-platform" :style="regGap('platform') ? 'border-color: var(--red)' : ''">
            <option value="">请选择平台</option>
            <option value="DOUYIN">抖音</option>
            <option value="KUAISHOU">快手</option>
            <option value="WECHAT_CHANNELS">视频号</option>
            <option value="OTHER">其他</option>
          </select>
          <p v-if="regGap('platform')" class="hint bad" data-testid="live-reg-gap-platform">必填项，请填写</p>
        </div>
        <div class="fld">
          <label>主题 *</label>
          <input v-model="reg.topic" data-testid="live-reg-topic" maxlength="256" :style="regGap('topic') ? 'border-color: var(--red)' : ''" />
          <p v-if="regGap('topic')" class="hint bad" data-testid="live-reg-gap-topic">必填项，请填写</p>
        </div>
        <div class="fld">
          <label>计划开播 *</label>
          <input v-model="reg.planStartTime" type="datetime-local" data-testid="live-reg-plan" :style="regGap('plan') ? 'border-color: var(--red)' : ''" />
          <p v-if="regGap('plan')" class="hint bad" data-testid="live-reg-gap-plan">{{ planGapText }}</p>
        </div>
      </div>
      <div v-if="registerError" class="hint bad" data-testid="live-register-error">{{ registerError }}</div>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="closeRegister">取消</button>
        <button v-if="!editingCode" class="btn btn-pri" type="button" @click="submitRegister">提交登记</button>
        <button v-else class="btn btn-pri" type="button" data-testid="live-reregister-save" @click="submitRegister">保存整改</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="supplementOpen" title="历史补录" width="720px" @close="supplementOpen = false">
      <div v-if="supplementGaps.length" class="empty" data-testid="live-supplement-empty" style="padding: 12px 0 4px">
        <div class="et">历史补录还缺 {{ supplementGaps.length }} 项</div>
        <div class="es">账号、实名人、设备和补录说明都要填。说明为空返回 1049，审批通过后才入库。</div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>直播账号 *</label>
          <select v-model="sup.accountId" data-testid="live-supplement-account" :data-missing="supplementGap('account') ? '1' : '0'" :style="supplementGap('account') ? 'border-color: var(--red)' : ''">
            <option value="">请选择</option>
            <option v-for="item in regOptions.accounts" :key="item.id" :value="String(item.id)">{{ item.accountName }}</option>
          </select>
        </div>
        <div class="fld">
          <label>实名人 *</label>
          <select v-model="sup.realnamePersonId" data-testid="live-supplement-person" :data-missing="supplementGap('person') ? '1' : '0'" :style="supplementGap('person') ? 'border-color: var(--red)' : ''">
            <option value="">请选择</option>
            <option v-for="item in regOptions.realnames" :key="item.id" :value="String(item.id)">{{ item.realName }}</option>
          </select>
        </div>
        <div class="fld">
          <label>手机设备 *</label>
          <select v-model="sup.deviceId" data-testid="live-supplement-device" :data-missing="supplementGap('device') ? '1' : '0'" :style="supplementGap('device') ? 'border-color: var(--red)' : ''">
            <option value="">请选择</option>
            <option v-for="item in regOptions.phones" :key="item.id" :value="String(item.id)">{{ item.label }}</option>
          </select>
        </div>
        <div class="fld">
          <label>主题 *</label>
          <input v-model="sup.topic" data-testid="live-supplement-topic" :data-missing="supplementGap('topic') ? '1' : '0'" :style="supplementGap('topic') ? 'border-color: var(--red)' : ''" />
        </div>
        <div class="fld">
          <label>计划开播 *</label>
          <input v-model="sup.planStartTime" type="datetime-local" data-testid="live-supplement-plan" :data-missing="supplementGap('plan') ? '1' : '0'" :style="supplementGap('plan') ? 'border-color: var(--red)' : ''" />
        </div>
        <div class="fld">
          <label>补录说明 *</label>
          <input v-model="sup.supplementReason" data-testid="live-supplement-reason" maxlength="256" :data-missing="supplementGap('reason') ? '1' : '0'" :style="supplementGap('reason') ? 'border-color: var(--red)' : ''" />
        </div>
        <div class="fld">
          <label>GMV</label>
          <input v-model.number="sup.gmv" type="number" step="0.01" data-testid="live-supplement-gmv" />
        </div>
      </div>
      <div v-if="supplementError" class="hint bad" data-testid="live-supplement-error">{{ supplementError }}</div>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="supplementOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="live-supplement-submit" @click="submitSupplement">提交补录</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="detailOpen" :title="detailTitle" width="90%" @close="detailOpen = false">
      <div v-if="showEnd" class="acts" data-testid="live-detail-head" style="margin-bottom: 8px">
        <button class="btn btn-pri btn-sm" type="button" data-testid="live-end-btn" @click="askEnd()">确认下播</button>
      </div>
      <div v-if="detail" class="tabs" data-testid="live-ledger-detail">
        <div v-for="t in tabs" :key="t" class="tab" :class="{ on: tab === t }" @click="switchTab(t)">{{ t }}</div>
      </div>
      <div v-if="detail && tab === '基本信息'" class="tbl-block" style="margin-top: 12px">
        <table class="ipg-info-grid">
          <tbody>
            <tr v-for="line in basicLines" :key="line.k"><td class="lbl">{{ line.k }}</td><td>{{ line.v }}</td></tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="detail && tab === '直播数据'" class="tbl-block" style="margin-top: 12px">
        <p class="hint">GMV、峰值、涨粉由下播录入承载。此处只读 Football 直播间，结束时间仅作参考，不改变本场状态。</p>
        <div class="acts" style="margin: 8px 0">
          <input v-model="roomIdDraft" data-testid="live-room-id" placeholder="直播间 ID" style="width: 140px" />
          <button class="btn btn-sec btn-sm" type="button" data-testid="live-room-bind" @click="bindRoom">绑定</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="live-sync-btn" @click="doSync">从 Football 同步</button>
        </div>
        <p v-if="syncError" class="hint bad" data-testid="live-sync-error">{{ syncError }}</p>
        <div v-if="metrics && !metrics.footballRoomBasic" class="empty" data-testid="live-metrics-empty">
          <div class="et">未绑定 Football 直播间</div>
          <div class="es">绑定直播间后可看到观看、点赞和预约。GMV 仍走下播录入。</div>
        </div>
        <table v-if="metrics" class="ipg-info-grid" data-testid="live-room-basic">
          <tbody>
            <tr><td class="lbl">同步态</td><td>{{ syncLabel(metrics.syncStatus) }}</td></tr>
            <tr><td class="lbl">上次同步</td><td data-testid="live-room-synced-at">{{ minuteText(metrics.lastSyncAt) }}</td></tr>
            <tr><td class="lbl">直播间</td><td>{{ metrics.footballRoomId || '—' }}</td></tr>
            <template v-if="metrics.footballRoomBasic">
              <tr><td class="lbl">直播名称</td><td>{{ metrics.footballRoomBasic.liveName || '—' }}</td></tr>
              <tr><td class="lbl">作者</td><td>{{ metrics.footballRoomBasic.authorNickname || '—' }}</td></tr>
              <tr><td class="lbl">直播间状态</td><td data-testid="live-room-status">{{ roomStatusLabel(metrics.footballRoomBasic.status) }}</td></tr>
              <tr><td class="lbl">开始时间</td><td>{{ minuteText(metrics.footballRoomBasic.startTime) }}</td></tr>
              <tr><td class="lbl">结束时间</td><td data-testid="live-room-end">{{ minuteText(metrics.footballRoomBasic.endTime) }}</td></tr>
              <tr><td class="lbl">观看人数</td><td>{{ metrics.footballRoomBasic.viewerCount ?? '—' }}</td></tr>
              <tr><td class="lbl">点赞</td><td>{{ metrics.footballRoomBasic.likeCount ?? '—' }}</td></tr>
              <tr><td class="lbl">预约</td><td>{{ metrics.footballRoomBasic.reservationCount ?? '—' }}</td></tr>
            </template>
          </tbody>
        </table>
        <p v-if="metrics?.footballRoomBasic?.endTime" class="hint" data-testid="live-room-end-ref">直播间结束时间只作参考，不会因此改变本场状态。</p>
      </div>
      <div v-else-if="detail && tab === '风控登记'" class="tbl-block" style="margin-top: 12px">
        <div class="acts" style="margin-bottom: 8px">
          <button v-if="showRiskRun" class="btn btn-pri btn-sm" type="button" data-testid="live-risk-run" @click="doRisk">执行风控</button>
          <button v-if="showStart" class="btn btn-sec btn-sm" type="button" data-testid="live-start-btn" @click="doStart">确认开播</button>
          <button v-if="showReregister" class="btn btn-sec btn-sm" type="button" data-testid="live-reregister-open" @click="openEdit">重新登记整改</button>
          <button v-if="showEdit" class="btn btn-sec btn-sm" type="button" data-testid="live-edit-open" @click="openEdit">编辑</button>
          <button v-if="showCancel" class="btn btn-sec btn-sm" type="button" data-testid="live-cancel-open" @click="cancelForm = true">取消场次</button>
        </div>
        <div v-if="showCancel && cancelForm" class="formrow one" style="margin-bottom: 8px">
          <div class="fld">
            <label>取消原因 *</label>
            <input v-model="cancelReason" data-testid="live-cancel-reason" maxlength="256" />
          </div>
          <div class="acts">
            <button class="btn btn-pri btn-sm" type="button" data-testid="live-cancel-confirm" @click="doCancel">确认取消</button>
          </div>
        </div>
        <p v-if="actionError" class="hint bad" data-testid="live-action-error">{{ actionError }}</p>
        <p data-testid="live-session-status" :data-status="detail.sessionStatus" :data-level="detail.riskLevel || ''">风险分 {{ detail.riskScore ?? '—' }} · {{ riskText(detail.riskLevel) }} · 状态 {{ sessionStatusText(detail) }}</p>
        <p v-if="riskConclusion" data-testid="live-risk-conclusion" :style="{ color: riskColor(detail.riskLevel), fontWeight: 600 }">{{ riskConclusion }}</p>
        <p v-if="startBlockedHint" class="hint bad" data-testid="live-start-blocked">{{ startBlockedHint }}</p>
        <p v-if="detail.yellowNotice" data-testid="live-yellow-notice">{{ detail.yellowNotice }}</p>
        <p v-if="detail.approverName" data-testid="live-approver">审批人 {{ detail.approverName }}</p>
        <p v-if="detail.approveComment" data-testid="live-approve-comment-text">审批意见：{{ detail.approveComment }}</p>
        <p v-if="detail.cancelReason" data-testid="live-cancel-reason-text">取消原因：{{ detail.cancelReason }}</p>
        <div v-if="showYellowApprove" class="formrow one" style="margin-top: 8px">
          <div class="fld">
            <label>审批意见</label>
            <input v-model="approveComment" data-testid="live-approve-comment" maxlength="512" />
          </div>
          <div class="acts">
            <button class="btn btn-pri btn-sm" type="button" data-testid="live-approve-pass" @click="doApprove(true)">通过放行</button>
            <button class="btn btn-sec btn-sm" type="button" data-testid="live-approve-reject" @click="doApprove(false)">拒绝整改</button>
          </div>
        </div>
        <p v-if="detail.isSupplement" data-testid="live-supplement-reason-text">补录说明：{{ detail.supplementReason || '—' }}</p>
        <div v-if="showSupplementApprove" class="formrow one" style="margin-top: 8px">
          <div class="fld">
            <label>补录审批意见</label>
            <input v-model="supplementComment" data-testid="live-supplement-comment" maxlength="512" />
          </div>
          <div class="acts">
            <button class="btn btn-pri btn-sm" type="button" data-testid="live-supplement-pass" @click="doSupplementApprove(true)">通过补录</button>
            <button class="btn btn-sec btn-sm" type="button" data-testid="live-supplement-reject" @click="doSupplementApprove(false)">拒绝补录</button>
          </div>
        </div>
        <div v-if="!detail.riskCheckResults?.length" class="empty" data-testid="live-risk-empty">
          <div class="et">尚未执行风控</div>
          <div class="es">五项检查待落库：证件、账号、话费、违禁词、设备</div>
        </div>
        <table v-else>
          <thead><tr><th>检查项</th><th>结果</th><th>说明</th><th>权重分</th></tr></thead>
          <tbody>
            <tr v-for="c in detail.riskCheckResults" :key="c.checkItem" data-testid="live-risk-check" :data-result="c.checkResult">
              <td>{{ checkItemLabel(c.checkItem) }}</td>
              <td :style="{ color: checkColor(c.checkResult), fontWeight: 600 }">{{ checkResultLabel(c.checkResult) }}</td>
              <td data-testid="live-risk-detail">{{ c.detail || '—' }}</td>
              <td>{{ c.scoreWeight }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="detail && tab === '下播与 GMV'" class="tbl-block" style="margin-top: 12px">
        <div v-if="!reportLoaded" class="empty" data-testid="live-report-loading">
          <div class="et">加载中</div>
        </div>
        <template v-else>
        <p v-if="!entryOpen" class="hint bad" data-testid="live-report-locked">场次未下播，下播录入在状态为已下播后开放</p>
        <template v-if="entryOpen">
        <div v-if="!report" class="empty" data-testid="live-report-empty" style="padding: 12px 0">
          <div class="et">待录入</div>
          <div class="es">下播九项还没提交。缺字段返回 1046，提交后只能走更正单。</div>
        </div>
        <p v-if="financeView" class="hint" data-testid="live-report-finance-scope">财务字段：仅 GMV 与成本</p>
        <p v-if="report?.fieldScope === 'MASKED'" class="hint" data-testid="live-report-cost-masked">成本已脱敏</p>
        <div v-if="report" class="hint" data-testid="live-report-headline">
          录入状态 {{ entryText(report.entryStatus) }} · GMV ¥{{ displayMoney(report.gmv) }}
          · 客单价 <span data-testid="live-report-aov">{{ displayMoney(report.avgOrderValue) }}</span>
          · ROAS <span data-testid="live-report-roas">{{ displayMoney(report.roas) }}</span>
          · 时长 {{ reportDurationText }}
        </div>
        <p class="hint" data-testid="live-report-derived">
          UV价值 <span data-testid="live-report-uv">{{ reportUvText }}</span>
          · 时长 <span data-testid="live-report-duration">{{ reportDurationText }}</span>
        </p>
        <div :style="correcting ? 'display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start' : ''" data-testid="live-correction-compare">
          <div v-if="correcting" data-testid="live-correction-original">
            <b>原值</b>
            <div class="fld"><label>实际开始</label><div>{{ originalReport.actualStart || '—' }}</div></div>
            <div class="fld"><label>实际结束</label><div>{{ originalReport.actualEnd || '—' }}</div></div>
            <div class="fld"><label>GMV</label><div>{{ originalReport.gmv || '—' }}</div></div>
            <div class="fld"><label>订单数</label><div>{{ originalReport.orderCount || '—' }}</div></div>
            <div class="fld"><label>观看人数</label><div>{{ originalReport.viewerCount || '—' }}</div></div>
            <div class="fld"><label>峰值在线</label><div>{{ originalReport.peakOnline || '—' }}</div></div>
            <div class="fld"><label>涨粉</label><div>{{ originalReport.newFans || '—' }}</div></div>
            <div class="fld"><label>退款</label><div>{{ originalReport.refundAmount || '—' }}</div></div>
            <div class="fld"><label>投放成本</label><div>{{ originalReport.adCost || '—' }}</div></div>
          </div>
          <div>
            <b v-if="correcting">更正后</b>
        <div class="formrow one">
          <div v-if="showOpsFields" class="fld"><label>实际开始 *</label><input v-model="reportForm.actualStart" data-testid="live-report-start" :readonly="reportLocked && !correcting" :style="fieldMissing('actualStart') ? 'border-color: var(--red)' : ''" /></div>
          <div v-if="showOpsFields" class="fld"><label>实际结束 *</label><input v-model="reportForm.actualEnd" data-testid="live-report-end" :readonly="reportLocked && !correcting" :style="fieldMissing('actualEnd') ? 'border-color: var(--red)' : ''" /></div>
          <div class="fld"><label>GMV *</label><input v-model="reportForm.gmv" type="number" step="0.01" data-testid="live-report-gmv" :readonly="financeView || (reportLocked && !correcting)" :style="fieldMissing('gmv') ? 'border-color: var(--red)' : ''" /></div>
          <div v-if="showOpsFields" class="fld"><label>订单数 *</label><input v-model="reportForm.orderCount" type="number" data-testid="live-report-orders" :readonly="reportLocked && !correcting" :style="fieldMissing('orderCount') ? 'border-color: var(--red)' : ''" /></div>
          <div v-if="showOpsFields" class="fld">
            <label>客单价</label>
            <div data-testid="live-report-live-aov">{{ liveAov }}</div>
          </div>
          <div v-if="showOpsFields" class="fld"><label>观看人数 *</label><input v-model="reportForm.viewerCount" type="number" data-testid="live-report-viewers" :readonly="reportLocked && !correcting" :style="fieldMissing('viewerCount') ? 'border-color: var(--red)' : ''" /></div>
          <div v-if="showOpsFields" class="fld"><label>峰值在线 *</label><input v-model="reportForm.peakOnline" type="number" data-testid="live-report-peak" :readonly="reportLocked && !correcting" :style="fieldMissing('peakOnline') ? 'border-color: var(--red)' : ''" /></div>
          <div v-if="showOpsFields" class="fld"><label>涨粉 *</label><input v-model="reportForm.newFans" type="number" data-testid="live-report-fans" :readonly="reportLocked && !correcting" :style="fieldMissing('newFans') ? 'border-color: var(--red)' : ''" /></div>
          <div class="fld"><label>退款 *</label><input v-model="reportForm.refundAmount" type="number" step="0.01" data-testid="live-report-refund" :readonly="financeView || (reportLocked && !correcting)" :style="fieldMissing('refundAmount') ? 'border-color: var(--red)' : ''" /></div>
          <div class="fld">
            <label>投放成本 *</label>
            <input v-model="reportForm.adCost" data-testid="live-report-ad" :readonly="financeView || report?.fieldScope === 'MASKED' || (reportLocked && !correcting)" :style="fieldMissing('adCost') ? 'border-color: var(--red)' : ''" />
            <p class="hint" data-testid="live-ad-cost-hint">投放成本将关联冲话费记录核对。</p>
            <p class="hint">ROAS <span data-testid="live-report-live-roas">{{ liveRoas }}</span></p>
          </div>
          <div v-if="showCostEditor" class="fld">
            <label>成本明细</label>
            <select v-model="costDraft.costType" data-testid="live-cost-type">
              <option value="AD">投放</option>
              <option value="RECHARGE">冲话费</option>
              <option value="GIFT">打赏</option>
              <option value="SAMPLE">样品</option>
            </select>
            <input v-model="costDraft.amount" type="number" step="0.01" placeholder="金额" data-testid="live-cost-amount" :style="fieldMissing('amount') ? 'border-color: var(--red)' : ''" />
          </div>
          <div v-if="correcting" class="fld">
            <label>更正原因 *</label>
            <input
              v-model="correctionReason"
              maxlength="512"
              data-testid="live-report-correction-reason"
              :data-missing="correctionReasonBad ? '1' : '0'"
              :style="correctionReasonBad ? 'border-color: var(--red)' : ''"
            />
            <p class="hint" data-testid="live-correction-reason-hint">更正原因必填。留空不会生成更正单。</p>
          </div>
        </div>
          </div>
        </div>
        <ul v-if="costLines.length" data-testid="live-cost-details">
          <li v-for="(item, index) in costLines" :key="index">{{ costLabel(item.costType) }} {{ displayMoney(item.amount) }}</li>
        </ul>
        <p v-else-if="report" class="hint" data-testid="live-cost-empty">暂无成本明细</p>
        <p v-if="reportError" class="hint bad" data-testid="live-report-error">{{ reportError }}</p>
        <p v-if="correctionTrace" class="hint" data-testid="live-correction-trace">
          更正单 {{ correctionTrace.correctionId }}
          <span v-for="line in correctionTrace.changes || []" :key="line" data-testid="live-correction-change">{{ line }}</span>
        </p>
        <div data-testid="live-correction-slips" style="margin-top: 8px">
          <div v-if="!correctionSlips.length" class="empty" data-testid="live-correction-empty">
            <div class="et">暂无更正单</div>
            <div class="es">已提交或已核准的场次，修改请走更正单留痕。</div>
          </div>
          <ul v-else>
            <li v-for="slip in correctionSlips" :key="slip.id" data-testid="live-correction-slip">
              更正单 {{ slip.id }} · {{ slip.correctionReason || '—' }}
              <div v-for="line in slip.changes || []" :key="line" data-testid="live-correction-change">{{ line }}</div>
            </li>
          </ul>
        </div>
        <div v-if="!financeView" class="acts" style="margin-top: 8px">
          <button v-if="!reportLocked" class="btn btn-sec btn-sm" type="button" data-testid="live-report-draft" @click="saveDraft">保存草稿</button>
          <button v-if="!reportLocked" class="btn btn-pri btn-sm" type="button" data-testid="live-report-submit" @click="submitReport">提交下播</button>
          <button
            v-if="report && report.entryStatus === 'SUBMITTED'"
            class="btn btn-pri btn-sm"
            type="button"
            data-testid="live-report-confirm"
            @click="confirmReport"
          >
            核准下播
          </button>
          <button v-if="canCorrect && !correcting" class="btn btn-sec btn-sm" type="button" data-testid="live-report-correction-open" @click="openCorrection">更正</button>
          <button v-if="correcting" class="btn btn-pri btn-sm" type="button" data-testid="live-report-correction-submit" @click="submitCorrection">提交更正单</button>
        </div>
        </template>
        </template>
      </div>
      <div v-else-if="detail && tab === '关联'" class="tbl-block" style="margin-top: 12px">
        <h3 style="margin: 0 0 8px">绑定设备</h3>
        <ul v-if="detail.boundDevices?.length" data-testid="live-bound-devices">
          <li v-for="item in detail.boundDevices" :key="`${item.kind}-${item.id}`">
            <router-link :to="deviceLink(item)">{{ item.assetName }}<template v-if="item.assetCode && item.assetCode !== item.assetName">（{{ item.assetCode }}）</template></router-link>
          </li>
        </ul>
        <p v-else class="hint" data-testid="live-bound-empty">暂无绑定设备</p>
        <p class="hint" data-testid="live-related-alarm-title">告警摘要</p>
        <router-link
          class="btn btn-sec btn-sm"
          data-testid="live-view-alarms"
          :to="{ path: '/ims/live/alarm', query: { sessionCode: detail.sessionCode } }"
        >查看告警</router-link>
        <table v-if="alarms.length">
          <thead><tr><th>规则</th><th>级别</th><th>内容</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="a in alarms" :key="a.id">
              <td>{{ a.ruleName }}</td><td>{{ a.alarmLevel }}</td><td>{{ a.alarmContent }}<template v-if="a.mergeCount > 1"> ×{{ a.mergeCount }}</template></td><td>{{ a.handleStatus }}<template v-if="a.escalated"> · 已升级</template></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty" data-testid="live-related-alarm-empty">
          <div class="et">暂无告警记录</div>
          <div class="es">本场次还没有风险命中。处置在风险告警页完成。</div>
        </div>
      </div>
    </ProtoDrawer>
    <div
      v-if="endAsk"
      data-testid="live-end-dialog"
      style="position: fixed; inset: 0; z-index: 400; background: rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center"
    >
      <div class="card" style="padding: 16px; max-width: 440px">
        <p data-testid="live-end-copy">确认下播后开始 24 小时数据录入计时，确定下播？</p>
        <p v-if="actionError" class="hint bad">{{ actionError }}</p>
        <div class="acts" style="margin-top: 12px">
          <button class="btn btn-pri btn-sm" type="button" data-testid="live-end-confirm" @click="doEnd">确定下播</button>
          <button class="btn btn-sec btn-sm" type="button" data-testid="live-end-dismiss" @click="endAsk = false">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { errorMessage, http } from '../../api/http'

async function apiGet(url: string, params?: Record<string, unknown>) {
  const res = await http.get(url, { params })
  return res.data.data
}

async function apiPost(url: string, body?: unknown, config?: { headers?: Record<string, string> }) {
  const res = await http.post(url, body ?? {}, config)
  return res.data.data
}

async function apiPut(url: string, body?: unknown) {
  const res = await http.put(url, body ?? {})
  return res.data.data
}

const route = useRoute()
const ledgerMode = computed(() => route.path.includes('/live/ledger'))
const loading = ref(false)
const error = ref('')
const hint = ref('')
const exporting = ref(false)
const exportNote = ref('')
const exportError = ref('')
const exportReceipt = ref<{ exportTaskId: string; downloadUrl: string; fileName: string } | null>(null)
const rows = ref<any[]>([])
const total = ref(0)
const view = ref<'sessions' | 'pending'>('sessions')
const pendingRows = ref<any[]>([])
const pendingHint = ref('')
const pendingLoading = ref(false)
const pendingError = ref('')
const overdueCount = ref(0)
const overdueOnly = ref(false)
const reportError = ref('')
const syncError = ref('')
const roomIdDraft = ref('')
const reportMissing = ref<string[]>([])
const reportBadField = ref('')
const slowQueryHint = ref('')
const correcting = ref(false)
const correctionReason = ref('')
const originalReport = reactive({
  actualStart: '',
  actualEnd: '',
  gmv: '',
  orderCount: '',
  viewerCount: '',
  peakOnline: '',
  newFans: '',
  refundAmount: '',
  adCost: '',
})
const correctionTrace = ref<any>(null)
const correctionSlips = ref<any[]>([])
const query = reactive({
  sessionCode: '',
  accountId: '',
  responsibleUserId: '',
  sessionStatus: '',
  platform: '',
  riskLevel: '',
  isSupplement: '',
  timeFrom: '',
  timeTo: '',
})
const pendingOwner = ref('')
const pageNo = ref(1)
const pageSize = 20
const stats = reactive({
  todayPendingStart: 0,
  liveCount: 0,
  entryDue24h: 0,
  monthConfirmedGmv: 0,
})
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const statusOptions = [
  { value: 'PENDING_RISK_CHECK', label: '待风控' },
  { value: 'APPROVED', label: '已放行' },
  { value: 'LIVE', label: '直播中' },
  { value: 'ENDED', label: '已下播' },
  { value: 'CANCELLED', label: '已取消' },
]

const registerOpen = ref(false)
const registerError = ref('')
const editingCode = ref('')
const actionError = ref('')
const approveComment = ref('')
const cancelForm = ref(false)
const cancelReason = ref('')
const endAsk = ref(false)
const endCode = ref('')
const supplementOpen = ref(false)
const supplementError = ref('')
const supplementComment = ref('')
const sup = reactive({
  accountId: '',
  realnamePersonId: '',
  deviceId: '',
  topic: '历史场次补录',
  planStartTime: '2020-01-15T20:00',
  supplementReason: '',
  gmv: 100,
})
type RegOptionAccount = {
  id: number
  accountNo: string
  accountName: string
  platform: string
  realnamePersonId: number
  holderUserId: number
}
type RegOptionPerson = { id: number; realName: string; status: string }
type RegOptionPhone = { id: number; label: string }
type RegOptionDevice = { id: number; assetCode: string; assetName: string; assetType: string }
type RegOptionUser = { id: number; nickname: string; username: string }

const regOptions = reactive({
  currentUserId: 0,
  accounts: [] as RegOptionAccount[],
  realnames: [] as RegOptionPerson[],
  phones: [] as RegOptionPhone[],
  devices: [] as RegOptionDevice[],
  users: [] as RegOptionUser[],
})
const regGaps = ref<string[]>([])
const certPreview = ref<{ level: string; detail: string; blocked?: boolean } | null>(null)
const reg = reactive({
  accountId: '',
  realnamePersonId: '',
  responsibleUserId: '',
  phoneId: '',
  deviceIds: [] as number[],
  platform: '',
  topic: '',
  planStartTime: '',
})
let clientToken = ''

const detailOpen = ref(false)
const detail = ref<any>(null)
const metrics = ref<any>(null)
const report = ref<any>(null)
const reportLoaded = ref(false)
let detailTicket = 0
const alarms = ref<any[]>([])
const tab = ref('基本信息')
const tabs = ['基本信息', '直播数据', '风控登记', '下播与 GMV', '关联']
const reportForm = reactive({
  actualStart: '',
  actualEnd: '',
  gmv: '',
  orderCount: '',
  viewerCount: '',
  peakOnline: '',
  newFans: '',
  refundAmount: '',
  adCost: '',
})
const costLines = ref<{ costType: string; amount: unknown; remark?: string }[]>([])
const costDraft = reactive({ costType: 'GIFT', amount: '' })

const supplementGaps = computed(() => {
  const gaps: string[] = []
  if (!Number(sup.accountId)) gaps.push('account')
  if (!Number(sup.realnamePersonId)) gaps.push('person')
  if (!Number(sup.deviceId)) gaps.push('device')
  if (!String(sup.topic || '').trim()) gaps.push('topic')
  if (!String(sup.planStartTime || '').trim()) gaps.push('plan')
  if (!String(sup.supplementReason || '').trim()) gaps.push('reason')
  return gaps
})
const pendingEmptyTitle = computed(() => {
  if (positiveId(pendingOwner.value)) return '该责任人暂无待录入'
  if (overdueOnly.value) return '暂无超过 24 小时的待录入'
  return '暂无待录入场次'
})
const pendingEmptyHint = computed(() => {
  if (positiveId(pendingOwner.value)) return '换一个责任人，或清空后再查全部待录入。'
  if (overdueOnly.value) return '取消「仅看超过 24 小时」可看未超时的待录入场次。'
  return '下播后 24 小时未提交会标红，并写入站内待办。钉钉与短信只留本地桩，不外发。'
})
const reportUvText = computed(() => {
  const gmv = Number(reportForm.gmv)
  const viewers = Number(reportForm.viewerCount)
  if (!Number.isFinite(gmv) || !Number.isFinite(viewers) || viewers <= 0) return '—'
  return (gmv / viewers).toFixed(2)
})

function clockText(iso: string) {
  const ms = Date.parse(iso)
  if (!Number.isFinite(ms)) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(ms)
}

function pendingRangeText(row: { actualStart?: string; actualEnd?: string }) {
  const startText = String(row.actualStart || '').trim()
  const endText = String(row.actualEnd || '').trim()
  const start = Date.parse(startText)
  const end = Date.parse(endText)
  if (!startText || !endText || !Number.isFinite(start) || !Number.isFinite(end) || end <= start) return ''
  const minutes = Math.floor((end - start) / 60000)
  return `${clockText(startText)} ~ ${clockText(endText)}（${minutes} 分钟）`
}

function supplementGap(key: string) {
  return supplementGaps.value.includes(key)
}

const entryOpen = computed(() => detail.value?.sessionStatus === 'ENDED')
const reportLocked = computed(() => !entryOpen.value || (!!report.value && report.value.entryStatus !== 'DRAFT'))
const canCorrect = computed(
  () => entryOpen.value && !!report.value && (report.value.entryStatus === 'SUBMITTED' || report.value.entryStatus === 'CONFIRMED'),
)
const showRiskRun = computed(() => {
  const status = detail.value?.sessionStatus
  return status === 'PENDING_RISK_CHECK' || status === 'APPROVED'
})
const showStart = computed(() => detail.value?.sessionStatus === 'APPROVED' && !!detail.value?.startAllowed)
const financeView = computed(() => report.value?.fieldScope === 'FINANCE')
const showOpsFields = computed(() => !financeView.value)
const showCostEditor = computed(() => !financeView.value && (!reportLocked.value || correcting.value))

const reportDurationText = computed(() => {
  const startText = reportForm.actualStart.trim()
  const endText = reportForm.actualEnd.trim()
  if (!startText || !endText) return '—'
  const start = Date.parse(startText)
  const end = Date.parse(endText)
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return '—（结束须晚于开始）'
  return `${Math.floor((end - start) / 60000)} 分钟`
})

function displayMoney(value: unknown) {
  if (value === '***') return '***'
  if (value === '' || value === null || value === undefined) return '—'
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed.toFixed(2) : '—'
}

function costLabel(kind: string) {
  const map: Record<string, string> = { AD: '投放', RECHARGE: '冲话费', GIFT: '打赏', SAMPLE: '样品' }
  return map[kind] || kind || '成本'
}

function resetReportForm() {
  reportForm.actualStart = ''
  reportForm.actualEnd = ''
  reportForm.gmv = ''
  reportForm.orderCount = ''
  reportForm.viewerCount = ''
  reportForm.peakOnline = ''
  reportForm.newFans = ''
  reportForm.refundAmount = ''
  reportForm.adCost = ''
}

const liveAov = computed(() => {
  const gmv = Number(reportForm.gmv)
  const orders = Number(reportForm.orderCount)
  if (reportForm.gmv === '' || reportForm.orderCount === '' || !Number.isFinite(gmv) || !Number.isFinite(orders) || orders <= 0) return '—'
  return (gmv / orders).toFixed(2)
})

const liveRoas = computed(() => {
  const gmv = Number(reportForm.gmv)
  const ad = Number(reportForm.adCost)
  if (reportForm.gmv === '' || reportForm.adCost === '' || reportForm.adCost === '***' || !Number.isFinite(gmv) || !Number.isFinite(ad) || ad <= 0) return '—'
  return (gmv / ad).toFixed(2)
})

function applyReport(data: Record<string, unknown> | null) {
  if (!data) {
    resetReportForm()
    costLines.value = []
    costDraft.amount = ''
    return
  }
  reportForm.actualStart = String(data.actualStart || '')
  reportForm.actualEnd = String(data.actualEnd || '')
  reportForm.gmv = String(data.gmv ?? '')
  reportForm.orderCount = String(data.orderCount ?? '')
  reportForm.viewerCount = String(data.viewerCount ?? '')
  reportForm.peakOnline = String(data.peakOnline ?? '')
  reportForm.newFans = String(data.newFans ?? '')
  reportForm.refundAmount = String(data.refundAmount ?? '')
  reportForm.adCost = data.adCost === '***' ? '***' : String(data.adCost ?? '')
  const details = data.costDetails
  costLines.value = Array.isArray(details)
    ? details.map((item) => ({
        costType: String((item as { costType?: string }).costType || ''),
        amount: (item as { amount?: unknown }).amount,
        remark: String((item as { remark?: string }).remark || ''),
      }))
    : []
  costDraft.amount = ''
}

function nullableNumber(value: unknown) {
  if (value === '' || value === null || value === undefined) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function reportPayload() {
  const payload: Record<string, unknown> = {
    actualStart: reportForm.actualStart.trim() || null,
    actualEnd: reportForm.actualEnd.trim() || null,
    gmv: nullableNumber(reportForm.gmv),
    refundAmount: nullableNumber(reportForm.refundAmount),
    orderCount: nullableNumber(reportForm.orderCount),
    viewerCount: nullableNumber(reportForm.viewerCount),
    peakOnline: nullableNumber(reportForm.peakOnline),
    newFans: nullableNumber(reportForm.newFans),
    adCost: reportForm.adCost === '***' ? null : nullableNumber(reportForm.adCost),
  }
  const details = costLines.value
    .filter((item) => item.amount !== '***')
    .map((item) => ({
      costType: item.costType,
      amount: nullableNumber(item.amount),
      remark: item.remark || undefined,
    }))
  if (String(costDraft.amount).trim() !== '') {
    details.push({ costType: costDraft.costType, amount: nullableNumber(costDraft.amount), remark: undefined })
  }
  if (details.length) payload.costDetails = details
  return payload
}

const correctionReasonBad = computed(() => correcting.value && reportError.value.includes('更正原因'))

const numberFieldLabel: Record<string, string> = {
  gmv: 'GMV',
  refundAmount: '退款',
  adCost: '投放成本',
  orderCount: '订单数',
  viewerCount: '观看人数',
  peakOnline: '峰值在线',
  newFans: '涨粉',
  amount: '成本金额',
}

function fieldMissing(key: string) {
  return reportMissing.value.includes(key) || reportBadField.value === key
}

const detailTitle = computed(() => (detail.value ? `场次 ${detail.value.sessionCode}` : '场次详情'))
const overdueCards = computed(() => pendingRows.value.filter((row) => row.overdue))

function positiveId(value: unknown) {
  const text = String(value ?? '').trim()
  if (!/^[1-9]\d*$/.test(text)) return null
  return Number(text)
}

const dateRangeHint = computed(() => {
  const from = query.timeFrom.trim()
  const to = query.timeTo.trim()
  if ((from && !to) || (!from && to)) return '开播起止要一起选，只填一侧不会收窄日期。'
  return ''
})

const sessionsEmptyHint = computed(() => {
  const narrowed =
    query.sessionCode.trim() ||
    positiveId(query.accountId) ||
    positiveId(query.responsibleUserId) ||
    query.sessionStatus ||
    query.platform ||
    query.riskLevel ||
    query.isSupplement ||
    query.timeFrom ||
    query.timeTo
  return narrowed
    ? '没有符合当前账号、责任人或筛选条件的场次。'
    : '登记后生成 19 位场次 ID。直播数据页只读 Football 直播间。'
})

function ledgerQueryParams(withPage: boolean) {
  const params = new URLSearchParams()
  if (withPage) {
    params.set('pageNo', String(pageNo.value))
    params.set('pageSize', String(pageSize))
  }
  const sessionCode = query.sessionCode.trim()
  if (sessionCode) params.set('sessionCode', sessionCode)
  const accountId = positiveId(query.accountId)
  if (accountId) params.set('accountId', String(accountId))
  const ownerId = positiveId(query.responsibleUserId)
  if (ownerId) params.set('responsibleUserId', String(ownerId))
  if (query.sessionStatus) params.set('sessionStatus', query.sessionStatus)
  if (query.platform) params.set('platform', query.platform)
  if (query.riskLevel) params.set('riskLevel', query.riskLevel)
  if (query.isSupplement === 'true' || query.isSupplement === 'false') params.set('isSupplement', query.isSupplement)
  if (query.timeFrom && query.timeTo) {
    params.append('timeRange', query.timeFrom)
    params.append('timeRange', query.timeTo)
  }
  return params
}

function bindCorrections(source: any) {
  correctionSlips.value = Array.isArray(source?.corrections) ? source.corrections : []
}

function minuteText(value: unknown) {
  const text = String(value || '').trim()
  if (!text) return '—'
  return text.replace('T', ' ').slice(0, 16)
}

const SESSION_STATUS_TEXT: Record<string, string> = {
  PENDING_RISK_CHECK: '待风控',
  APPROVED: '已放行',
  LIVE: '直播中',
  ENDED: '已下播',
  CANCELLED: '已取消',
}
const RISK_TEXT: Record<string, string> = { GREEN: '绿', YELLOW: '黄', RED: '红' }
const ENTRY_TEXT: Record<string, string> = {
  DRAFT: '草稿',
  SUBMITTED: '已提交',
  CONFIRMED: '已核准',
  PENDING_RISK_CHECK: '待风控',
  LIVE: '直播中',
}
const PLATFORM_TEXT: Record<string, string> = {
  DOUYIN: '抖音',
  KUAISHOU: '快手',
  WECHAT_CHANNELS: '视频号',
  OTHER: '其他',
}

function sessionStatusText(row?: { sessionStatus?: string; isSupplement?: boolean; approverUserId?: number | null }) {
  if (row?.isSupplement && !row?.approverUserId) return '待审批'
  return SESSION_STATUS_TEXT[row?.sessionStatus || ''] || row?.sessionStatus || '—'
}

function riskText(level?: string) {
  if (!level) return '—'
  return RISK_TEXT[level] || level
}

function entryText(status?: string) {
  if (!status) return '—'
  return ENTRY_TEXT[status] || status
}

function platformText(code?: string) {
  if (!code) return '—'
  return PLATFORM_TEXT[code] || code
}

function roomStatusLabel(status: unknown) {
  const map: Record<string, string> = { '1': '未开始', '2': '直播中', '3': '已结束', '4': '过期', '5': '暂停' }
  return map[String(status ?? '')] || '—'
}

function deviceLink(item: { kind?: string; assetCode?: string; assetName?: string }) {
  const keyword = item.assetCode || item.assetName || ''
  if (item.kind === 'PHONE') return { path: '/ims/corp/device/phone', query: keyword ? { keyword } : {} }
  return { path: '/ims/corp/device/live', query: keyword ? { keyword } : {} }
}

function syncLabel(v: string | undefined) {
  const map: Record<string, string> = {
    UNLINKED: '未关联',
    PENDING: '待同步',
    SYNCED: '已同步',
    FAILED: '同步失败',
  }
  return map[v || ''] || v || '—'
}

async function loadList() {
  loading.value = true
  error.value = ''
  slowQueryHint.value = ''
  const started = Date.now()
  try {
    const res = await apiGet(`/live/sessions/list?${ledgerQueryParams(true).toString()}`)
    rows.value = res.list || []
    total.value = res.total || 0
    const board = res.stats || {}
    stats.todayPendingStart = Number(board.todayPendingStart || 0)
    stats.liveCount = Number(board.liveCount || 0)
    stats.entryDue24h = Number(board.entryDue24h || 0)
    stats.monthConfirmedGmv = Number(board.monthConfirmedGmv || 0)
  } catch (e: unknown) {
    error.value = errorMessage(e)
    rows.value = []
    total.value = 0
  } finally {
    if (Date.now() - started >= 3000) {
      slowQueryHint.value = '查询超过 3 秒，请缩小开播日期区间后再查。'
    }
    loading.value = false
  }
}

function searchList() {
  pageNo.value = 1
  loadList()
}

function gotoPage(page: number) {
  if (page < 1 || page > pageCount.value || page === pageNo.value) return
  pageNo.value = page
  loadList()
}

function resetQuery() {
  pageNo.value = 1
  query.sessionCode = ''
  query.accountId = ''
  query.responsibleUserId = ''
  query.sessionStatus = ''
  query.platform = ''
  query.riskLevel = ''
  query.isSupplement = ''
  query.timeFrom = ''
  query.timeTo = ''
  loadList()
}

async function saveLedgerFile(downloadUrl: string, fileName: string) {
  const token = localStorage.getItem('ims_access')
  const fileRes = await fetch(downloadUrl, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!fileRes.ok) {
    let body: unknown = {}
    try {
      body = await fileRes.json()
    } catch {
      body = {}
    }
    throw body
  }
  const blob = await fileRes.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = fileName || 'live_ledger.xlsx'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(a.href)
}

function unwrapError(error: unknown) {
  if (error && typeof error === 'object' && 'response' in error) {
    const data = (error as { response?: { data?: unknown } }).response?.data
    if (data && typeof data === 'object') return data
  }
  return error
}

function bizError(error: unknown) {
  const body = unwrapError(error) as { code?: number; msg?: string }
  if (body && typeof body === 'object' && typeof body.code === 'number' && body.code !== 0) {
    return `${body.code} ${body.msg || ''}`.trim()
  }
  return errorMessage(error)
}

async function exportLedger() {
  exporting.value = true
  exportNote.value = ''
  exportError.value = ''
  exportReceipt.value = null
  try {
    const res = await http.get(`/live/ledger/export?${ledgerQueryParams(false).toString()}`)
    const data = res.data.data || {}
    exportNote.value = data.message || '导出任务已提交'
    const downloadUrl = String(data.downloadUrl || '')
    exportReceipt.value = downloadUrl
      ? {
          exportTaskId: String(data.exportTaskId || ''),
          downloadUrl,
          fileName: String(data.fileName || 'live_ledger.xlsx'),
        }
      : null
    if (exportReceipt.value) await saveLedgerFile(exportReceipt.value.downloadUrl, exportReceipt.value.fileName)
  } catch (e: unknown) {
    exportNote.value = ''
    exportError.value = bizError(e)
  } finally {
    exporting.value = false
  }
}

async function claimExport() {
  if (!exportReceipt.value) return
  exporting.value = true
  exportError.value = ''
  try {
    await saveLedgerFile(exportReceipt.value.downloadUrl, exportReceipt.value.fileName)
  } catch (e: unknown) {
    exportError.value = bizError(e)
  } finally {
    exporting.value = false
  }
}

const registerTitle = computed(() => (editingCode.value ? '重新登记' : '开播登记'))

function riskColor(level: string | undefined) {
  if (level === 'RED') return 'var(--red)'
  if (level === 'YELLOW') return '#b8860b'
  if (level === 'GREEN') return 'var(--green)'
  return ''
}

function checkColor(result: string) {
  if (result === 'FAIL') return 'var(--red)'
  if (result === 'WARN') return '#b8860b'
  return 'var(--green)'
}

function checkItemLabel(item: string) {
  const labels: Record<string, string> = {
    CERT_VALID: '证件有效性',
    ACCOUNT_STATUS: '账号状态',
    BALANCE: '话费余额',
    BLACKLIST: '黑名单词',
    DEVICE_OWNER: '设备归属',
  }
  return labels[item] || item
}

function checkResultLabel(result: string) {
  if (result === 'FAIL') return '不通过'
  if (result === 'WARN') return '预警'
  if (result === 'PASS') return '通过'
  return result
}

function shanghaiLocalInput(date: Date) {
  const text = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(date)
  return text.replace(' ', 'T')
}

function planIso(local: string) {
  if (!local) return ''
  return local.length === 16 ? `${local}:00+08:00` : local
}

function supplementEndIso(local: string) {
  const start = new Date(planIso(local))
  if (Number.isNaN(start.getTime())) return ''
  const end = new Date(start.getTime() + 2 * 60 * 60 * 1000)
  const text = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  }).format(end)
  return `${text.replace(' ', 'T')}+08:00`
}

function planIsFuture(local: string) {
  if (!local) return false
  const parsed = new Date(planIso(local))
  return !Number.isNaN(parsed.getTime()) && parsed.getTime() > Date.now()
}

function defaultPlanLocal() {
  return shanghaiLocalInput(new Date(Date.now() + 2 * 60 * 60 * 1000))
}

function isoToLocal(value: string) {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value.slice(0, 16)
  return shanghaiLocalInput(parsed)
}

function regGap(key: string) {
  return regGaps.value.includes(key)
}

const planGapText = computed(() => {
  if (!reg.planStartTime) return '必填项，请填写'
  return '计划开播须晚于当前时间'
})

function resetReg() {
  reg.accountId = ''
  reg.realnamePersonId = ''
  reg.responsibleUserId = regOptions.currentUserId ? String(regOptions.currentUserId) : ''
  reg.phoneId = ''
  reg.deviceIds = []
  reg.platform = ''
  reg.topic = ''
  reg.planStartTime = defaultPlanLocal()
  regGaps.value = []
  certPreview.value = null
}

async function loadRegOptions() {
  const data = await apiGet('/live/register/options')
  regOptions.currentUserId = Number(data.currentUserId || 0)
  regOptions.accounts = data.accounts || []
  regOptions.realnames = data.realnames || []
  regOptions.phones = data.phones || []
  regOptions.devices = data.devices || []
  regOptions.users = data.users || []
  if (!reg.responsibleUserId && regOptions.currentUserId) {
    reg.responsibleUserId = String(regOptions.currentUserId)
  }
}

function onAccountPicked() {
  const hit = regOptions.accounts.find((item) => String(item.id) === reg.accountId)
  if (!hit) return
  if (hit.platform) reg.platform = hit.platform
  if (hit.realnamePersonId) {
    reg.realnamePersonId = String(hit.realnamePersonId)
    loadCertPreview()
  }
  if (hit.holderUserId) reg.responsibleUserId = String(hit.holderUserId)
}

function toggleDevice(id: number) {
  if (reg.deviceIds.includes(id)) reg.deviceIds = reg.deviceIds.filter((item) => item !== id)
  else reg.deviceIds = [...reg.deviceIds, id]
}

async function loadCertPreview() {
  certPreview.value = null
  const id = Number(reg.realnamePersonId)
  if (!id) return
  try {
    certPreview.value = await apiGet('/live/register/cert-preview', { realnamePersonId: id })
  } catch (e: unknown) {
    certPreview.value = { level: 'FAIL', detail: bizError(e) }
  }
}

function collectRegGaps() {
  const gaps: string[] = []
  if (!reg.accountId) gaps.push('account')
  if (!reg.realnamePersonId) gaps.push('person')
  if (!reg.responsibleUserId) gaps.push('owner')
  if (!reg.phoneId) gaps.push('phone')
  if (regOptions.devices.length && !reg.deviceIds.length) gaps.push('devices')
  if (!reg.platform) gaps.push('platform')
  if (!String(reg.topic || '').trim()) gaps.push('topic')
  if (!reg.planStartTime || !planIsFuture(reg.planStartTime)) gaps.push('plan')
  return gaps
}

async function openRegister() {
  editingCode.value = ''
  clientToken = crypto.randomUUID()
  registerError.value = ''
  resetReg()
  registerOpen.value = true
  try {
    await loadRegOptions()
  } catch (e: unknown) {
    registerError.value = bizError(e)
  }
}

function closeRegister() {
  const code = editingCode.value
  registerOpen.value = false
  editingCode.value = ''
  if (code) {
    openDetail({ sessionCode: code })
    tab.value = '风控登记'
  }
}

async function openEdit() {
  if (!detail.value) return
  const current = detail.value
  editingCode.value = current.sessionCode
  registerError.value = ''
  regGaps.value = []
  registerOpen.value = true
  try {
    await loadRegOptions()
  } catch (e: unknown) {
    registerError.value = bizError(e)
  }
  reg.accountId = current.accountId ? String(current.accountId) : ''
  reg.realnamePersonId = current.realnamePersonId ? String(current.realnamePersonId) : ''
  reg.responsibleUserId = current.responsibleUserId ? String(current.responsibleUserId) : ''
  const raw = (current.deviceAssetIds || []) as Array<number | { kind?: string; id?: number }>
  const phones: number[] = []
  const assets: number[] = []
  for (const item of raw) {
    if (item && typeof item === 'object') {
      const id = Number(item.id)
      if (!id) continue
      if (String(item.kind || '').toUpperCase() === 'ASSET') assets.push(id)
      else phones.push(id)
    } else if (Number(item)) {
      const id = Number(item)
      if (regOptions.devices.some((row) => row.id === id)) assets.push(id)
      else phones.push(id)
    }
  }
  reg.phoneId = phones.length ? String(phones[0]) : ''
  reg.deviceIds = assets
  reg.platform = current.platform || ''
  reg.topic = current.topic || ''
  reg.planStartTime = isoToLocal(current.planStartTime || '') || defaultPlanLocal()
  if (reg.realnamePersonId) await loadCertPreview()
}

async function submitRegister() {
  hint.value = ''
  registerError.value = ''
  regGaps.value = collectRegGaps()
  if (regGaps.value.length) return
  if (String(reg.topic).trim().length > 256) {
    registerError.value = '主题不能超过 256 字'
    return
  }
  try {
    const deviceAssetIds = [
      { kind: 'PHONE', id: Number(reg.phoneId) },
      ...reg.deviceIds
        .filter((id) => id !== Number(reg.phoneId))
        .map((id) => ({ kind: 'ASSET', id })),
    ]
    const body = {
      accountId: Number(reg.accountId),
      realnamePersonId: Number(reg.realnamePersonId),
      responsibleUserId: Number(reg.responsibleUserId),
      deviceAssetIds,
      platform: reg.platform,
      topic: reg.topic.trim(),
      planStartTime: planIso(reg.planStartTime),
      planEndTime: '',
    }
    if (editingCode.value) {
      const code = editingCode.value
      await apiPut(`/live/register/${code}`, body)
      registerOpen.value = false
      editingCode.value = ''
      hint.value = `已按原场次整改 ${code}`
      await loadList()
      await openDetail({ sessionCode: code })
      tab.value = '风控登记'
      return
    }
    const data = await apiPost('/live/register', body, { headers: { clientToken } })
    registerOpen.value = false
    hint.value = `已登记 ${data.sessionCode}`
    await loadList()
    openDetail(data)
    tab.value = '风控登记'
  } catch (e: unknown) {
    registerError.value = bizError(e)
    hint.value = registerError.value
  }
}

const basicLines = computed(() => {
  if (!detail.value) return []
  const d = detail.value
  return [
    { k: '场次 ID', v: d.sessionCode },
    { k: '账号', v: d.accountNo },
    { k: '实名人', v: d.realnameName },
    { k: '责任人', v: d.responsibleUserName },
    { k: '主题', v: d.topic },
    { k: '状态', v: sessionStatusText(d) },
    { k: '平台', v: platformText(d.platform) },
    { k: '计划开播', v: minuteText(d.planStartTime) },
    { k: '实际开播', v: minuteText(d.actualStart) },
    { k: '实际下播', v: minuteText(d.actualEnd) },
    { k: '实际时长', v: d.durationMinutes == null ? '—' : `${d.durationMinutes} 分钟` },
    { k: '取消原因', v: d.cancelReason || '—' },
    { k: '补录', v: d.isSupplement ? d.supplementReason || '待审批' : '否' },
    { k: 'Football 直播间', v: d.footballRoomId || '—' },
  ]
})

const riskConclusion = computed(() => {
  const level = detail.value?.riskLevel as string | undefined
  const status = detail.value?.sessionStatus as string | undefined
  if (level === 'GREEN') return '绿色自动放行，可直接确认开播'
  if (level === 'YELLOW' && status === 'APPROVED') return '黄色待审批，已放行，可直接确认开播'
  if (level === 'YELLOW') return '黄色待审批，等待审批'
  if (level === 'RED') return '红色禁止开播，请整改后重新登记'
  return ''
})

const beforeLive = computed(() => {
  const status = detail.value?.sessionStatus
  return status === 'PENDING_RISK_CHECK' || status === 'APPROVED'
})

const showReregister = computed(() => beforeLive.value && detail.value?.riskLevel === 'RED')
const showEdit = computed(() => beforeLive.value && detail.value?.riskLevel !== 'RED')
const showCancel = computed(() => beforeLive.value)
const showEnd = computed(() => detail.value?.sessionStatus === 'LIVE' && !!detail.value?.endAllowed)

const startBlockedHint = computed(() => {
  const status = detail.value?.sessionStatus as string | undefined
  if (!status || status === 'APPROVED' || status === 'LIVE' || status === 'ENDED') return ''
  if (status === 'CANCELLED') return '已取消不可开播'
  return '未放行不可开播'
})

const showYellowApprove = computed(
  () => detail.value?.riskLevel === 'YELLOW' && detail.value?.sessionStatus === 'PENDING_RISK_CHECK',
)

const showSupplementApprove = computed(
  () => !!detail.value?.isSupplement && !detail.value?.approverUserId && !!detail.value?.supplementApproveAllowed,
)

async function openDetail(row: any) {
  const ticket = ++detailTicket
  reportLoaded.value = false
  detailOpen.value = true
  tab.value = '基本信息'
  cancelForm.value = false
  actionError.value = ''
  reportError.value = ''
  reportMissing.value = []
  syncError.value = ''
  correcting.value = false
  correctionReason.value = ''
  correctionTrace.value = null
  const code = row.sessionCode
  const session = await apiGet(`/live/sessions/${code}`)
  if (ticket !== detailTicket) return
  detail.value = session
  metrics.value = session.metricsSnapshot || (await apiGet(`/live/sessions/${code}/metrics`))
  if (ticket !== detailTicket) return
  report.value = session.report || (await apiGet(`/live/report/${code}`))
  if (ticket !== detailTicket) return
  applyReport(report.value)
  bindCorrections(Array.isArray(detail.value?.corrections) ? detail.value : report.value)
  reportLoaded.value = true
  const alarmRes = await apiGet('/live/alarm/records', { sessionCode: code, pageNo: 1, pageSize: 10 })
  if (ticket !== detailTicket) return
  alarms.value = alarmRes.list || []
}

async function openPending() {
  view.value = 'pending'
  await loadPending()
}

function resetPending() {
  pendingOwner.value = ''
  overdueOnly.value = false
  loadPending()
}

async function loadPending() {
  pendingLoading.value = true
  pendingHint.value = ''
  pendingError.value = ''
  try {
    const ownerId = positiveId(pendingOwner.value)
    const res = await http.get('/live/report/pending', {
      params: {
        pageNo: 1,
        pageSize: 20,
        overdueOnly: overdueOnly.value ? true : undefined,
        responsibleUserId: ownerId || undefined,
      },
    })
    const data = res.data.data || {}
    pendingRows.value = data.list || []
    overdueCount.value = Number(data.overdueCount || 0)
  } catch (error: unknown) {
    const body = error as { code?: number; msg?: string; data?: { list?: any[]; overdueCount?: number } }
    if (body?.code === 1048) {
      pendingRows.value = body.data?.list || []
      overdueCount.value = Number(body.data?.overdueCount || pendingRows.value.filter((row) => row.overdue).length)
      pendingHint.value = `1048 ${body.msg || '24小时录入超时督办'}`
      return
    }
    pendingRows.value = []
    overdueCount.value = 0
    pendingError.value = bizError(error)
  } finally {
    pendingLoading.value = false
  }
}

async function switchTab(name: string) {
  tab.value = name
  if (!detail.value) return
  const code = detail.value.sessionCode
  if (name === '直播数据') {
    metrics.value = await apiGet(`/live/sessions/${code}/metrics`)
  }
  if (name === '关联') {
    const alarmRes = await apiGet('/live/alarm/records', { sessionCode: code, pageNo: 1, pageSize: 10 })
    alarms.value = alarmRes.list || []
  }
}

async function bindRoom() {
  if (!detail.value) return
  syncError.value = ''
  const roomId = roomIdDraft.value.trim()
  if (!roomId) {
    syncError.value = '请填写直播间 ID'
    return
  }
  try {
    metrics.value = await apiPost(`/live/sessions/${detail.value.sessionCode}/football-sync`, { footballRoomId: roomId })
    hint.value = '已绑定并同步 Football 直播间'
    await refreshDetail()
  } catch (e: unknown) {
    syncError.value = bizError(e)
    hint.value = syncError.value
  }
}

async function doSync() {
  if (!detail.value) return
  syncError.value = ''
  try {
    metrics.value = await apiPost(`/live/sessions/${detail.value.sessionCode}/football-sync`, {})
    hint.value = '已同步 Football 直播间'
    await refreshDetail()
  } catch (e: unknown) {
    syncError.value = bizError(e)
    hint.value = syncError.value
  }
}

async function refreshDetail() {
  if (!detail.value) return
  detail.value = await apiGet(`/live/sessions/${detail.value.sessionCode}`)
}

async function doRisk() {
  if (!detail.value) return
  actionError.value = ''
  try {
    await apiPost(`/live/register/${detail.value.sessionCode}/risk-check`, {})
  } catch (e: unknown) {
    actionError.value = bizError(e)
    hint.value = actionError.value
  }
  await refreshDetail()
}

async function startFromRow(row: any) {
  await openDetail(row)
  tab.value = '风控登记'
  await doStart()
}

async function doCancel() {
  if (!detail.value) return
  actionError.value = ''
  if (!cancelReason.value.trim()) {
    actionError.value = '取消原因必填'
    return
  }
  try {
    await apiPut(`/live/register/${detail.value.sessionCode}/cancel`, { cancelReason: cancelReason.value.trim() })
    hint.value = '场次已取消'
    cancelReason.value = ''
    cancelForm.value = false
  } catch (e: unknown) {
    actionError.value = bizError(e)
    hint.value = actionError.value
  }
  await refreshDetail()
  await loadList()
}

async function doStart() {
  if (!detail.value) return
  actionError.value = ''
  try {
    await apiPut(`/live/register/${detail.value.sessionCode}/start`, {})
    hint.value = '已确认开播'
  } catch (e: unknown) {
    actionError.value = bizError(e)
    hint.value = actionError.value
  }
  await refreshDetail()
  await loadList()
}

function askEnd(row?: { sessionCode?: string }) {
  endCode.value = row?.sessionCode || detail.value?.sessionCode || ''
  endAsk.value = !!endCode.value
}

async function doEnd() {
  if (!endCode.value) return
  actionError.value = ''
  try {
    await apiPut(`/live/register/${endCode.value}/end`, {})
    hint.value = '已确认下播'
    endAsk.value = false
  } catch (e: unknown) {
    actionError.value = bizError(e)
    hint.value = actionError.value
    return
  }
  if (detail.value?.sessionCode === endCode.value) await refreshDetail()
  await loadList()
}

async function doApprove(pass: boolean) {
  if (!detail.value) return
  actionError.value = ''
  if (!approveComment.value.trim()) {
    actionError.value = '审批意见必填'
    return
  }
  try {
    await apiPut(`/live/register/${detail.value.sessionCode}/approve`, {
      approve: pass,
      comment: approveComment.value.trim(),
    })
    hint.value = pass ? '黄级已放行' : '已拒绝，请整改'
    approveComment.value = ''
  } catch (e: unknown) {
    actionError.value = bizError(e)
    hint.value = actionError.value
  }
  await refreshDetail()
}

async function openSupplement() {
  supplementError.value = ''
  sup.supplementReason = ''
  sup.accountId = ''
  sup.realnamePersonId = ''
  sup.deviceId = ''
  await loadRegOptions().catch(() => null)
  supplementOpen.value = true
}

async function submitSupplement() {
  supplementError.value = ''
  try {
    const data = await apiPost('/live/ledger/supplement', {
      sessionCreate: {
        accountId: Number(sup.accountId),
        realnamePersonId: Number(sup.realnamePersonId),
        responsibleUserId: regOptions.currentUserId || 1,
        deviceAssetIds: [Number(sup.deviceId)],
        platform: regOptions.accounts.find((item) => String(item.id) === sup.accountId)?.platform || 'DOUYIN',
        topic: sup.topic,
        planStartTime: planIso(sup.planStartTime),
        planEndTime: '',
      },
      sessionReport: {
        actualStart: planIso(sup.planStartTime),
        actualEnd: supplementEndIso(sup.planStartTime),
        durationMinutes: 120,
        gmv: sup.gmv,
        refundAmount: 0,
        orderCount: 1,
        viewerCount: 10,
        peakOnline: 5,
        newFans: 1,
        adCost: 0,
      },
      supplementReason: sup.supplementReason,
    })
    supplementOpen.value = false
    hint.value = `补录已提交 ${data.sessionCode}`
    await loadList()
    openDetail(data)
    tab.value = '风控登记'
  } catch (e: unknown) {
    supplementError.value = bizError(e)
    hint.value = supplementError.value
  }
}

async function doSupplementApprove(pass: boolean) {
  if (!detail.value) return
  actionError.value = ''
  if (pass && !supplementComment.value.trim()) {
    actionError.value = '审批意见必填'
    return
  }
  try {
    await apiPut(`/live/ledger/supplement/${detail.value.id}/approve`, {
      approve: pass,
      comment: supplementComment.value.trim(),
    })
    hint.value = pass ? '补录已审批入库' : '补录已退回'
    supplementComment.value = ''
  } catch (e: unknown) {
    actionError.value = bizError(e)
    hint.value = actionError.value
  }
  await refreshDetail()
  await loadList()
}

async function saveDraft() {
  if (!detail.value) return
  if (detail.value.sessionStatus !== 'ENDED') {
    reportError.value = '场次未下播，下播录入在状态为已下播后开放'
    return
  }
  reportError.value = ''
  reportMissing.value = []
  try {
    await apiPut(`/live/report/${detail.value.sessionCode}`, reportPayload())
    report.value = await apiGet(`/live/report/${detail.value.sessionCode}`)
    applyReport(report.value)
    hint.value = '草稿已保存'
  } catch (e: unknown) {
    reportError.value = bizError(e)
    hint.value = reportError.value
  }
}

async function submitReport() {
  if (!detail.value) return
  if (detail.value.sessionStatus !== 'ENDED') {
    reportError.value = '场次未下播，下播录入在状态为已下播后开放'
    return
  }
  reportError.value = ''
  reportMissing.value = []
  reportBadField.value = ''
  try {
    report.value = await apiPost(`/live/report/${detail.value.sessionCode}`, reportPayload())
    applyReport(report.value)
    correcting.value = false
    hint.value = '下播数据已提交'
    await refreshDetail()
    await loadList()
  } catch (e: unknown) {
    const body = e as { data?: { missing?: string[]; field?: string } }
    reportMissing.value = body.data?.missing || []
    reportBadField.value = body.data?.field || ''
    const label = numberFieldLabel[reportBadField.value]
    reportError.value = label ? `${bizError(e)}（${label}）` : bizError(e)
    hint.value = reportError.value
  }
}

function openCorrection() {
  originalReport.actualStart = reportForm.actualStart
  originalReport.actualEnd = reportForm.actualEnd
  originalReport.gmv = reportForm.gmv
  originalReport.orderCount = reportForm.orderCount
  originalReport.viewerCount = reportForm.viewerCount
  originalReport.peakOnline = reportForm.peakOnline
  originalReport.newFans = reportForm.newFans
  originalReport.refundAmount = reportForm.refundAmount
  originalReport.adCost = reportForm.adCost
  correcting.value = true
  correctionReason.value = ''
  reportError.value = ''
}

async function submitCorrection() {
  if (!detail.value) return
  reportError.value = ''
  reportBadField.value = ''
  if (!correctionReason.value.trim()) {
    reportError.value = '更正原因必填'
    return
  }
  try {
    const data = await apiPost(`/live/report/${detail.value.sessionCode}/correction`, {
      ...reportPayload(),
      correctionReason: correctionReason.value.trim(),
    })
    correctionTrace.value = data
    correcting.value = false
    report.value = await apiGet(`/live/report/${detail.value.sessionCode}`)
    applyReport(report.value)
    bindCorrections(report.value)
    hint.value = `更正单 ${data.correctionId} 已留痕`
  } catch (e: unknown) {
    const body = e as { data?: { field?: string } }
    reportBadField.value = body.data?.field || ''
    const label = numberFieldLabel[reportBadField.value]
    reportError.value = label ? `${bizError(e)}（${label}）` : bizError(e)
    hint.value = reportError.value
  }
}

async function confirmReport() {
  if (!detail.value) return
  reportError.value = ''
  try {
    await apiPut(`/live/report/${detail.value.sessionCode}/confirm`, {})
    report.value = await apiGet(`/live/report/${detail.value.sessionCode}`)
    applyReport(report.value)
    hint.value = '下播数据已核准'
    await loadList()
  } catch (e: unknown) {
    reportError.value = bizError(e)
    hint.value = reportError.value
  }
}

onMounted(async () => {
  const code = typeof route.query.sessionCode === 'string' ? route.query.sessionCode.trim() : ''
  if (code) query.sessionCode = code
  await loadRegOptions().catch(() => null)
  await loadList()
  if (code) await openDetail({ sessionCode: code })
})
</script>
