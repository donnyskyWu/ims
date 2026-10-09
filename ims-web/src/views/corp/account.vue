<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>{{ meta.title }}</h1>
        <div class="sub">{{ meta.sub }}</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" @click="openCreate">登记账号</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      UX-M4 P-M4-008 · <code>platformType={{ meta.platform }}</code> · 采集 Tab 见 ADR-047 ·
      <b>≠</b> 数据采集·竞品账号配置。
    </p>
    <form class="qbar" @submit.prevent="search">
      <input v-model="keyword" placeholder="账号编号/昵称" style="width: 130px" />
      <input v-model="ipGroupKeyword" placeholder="IP 组" style="width: 100px" />
      <select v-model="status" style="width: 100px">
        <option value="">全部状态</option>
        <option v-for="item in statusOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="reset">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>账号编号</th>
              <th>昵称</th>
              <th>责任人</th>
              <th>实名人</th>
              <th>状态</th>
              <th>采集</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7" style="white-space: normal">
                <div class="empty"><div class="et">加载中</div></div>
              </td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="7" style="white-space: normal">
                <div class="empty">
                  <div class="et">{{ error || '暂无该平台账号' }}</div>
                  <div class="es">请先在资源管理完成主数据，再通过登记账号创建。</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="String(row.id)">
              <td class="mono num" style="color: var(--blue); cursor: pointer" @click="openDetail(row)">{{ row.accountNo }}</td>
              <td style="font-weight: 500">{{ row.nickname }}</td>
              <td>{{ row.holderUserName || '—' }}</td>
              <td>{{ row.realNameMasked || '—' }}</td>
              <td>{{ statusLabel(String(row.status)) }}</td>
              <td>{{ row.collectBindSummary }}</td>
              <td class="acts-cell">
                <button class="btn btn-sec btn-sm" type="button" @click="openDetail(row)">详情</button>
                <button
                  v-if="row.status === 'IN_POOL' || row.status === 'IN_USE' || row.status === 'FROZEN'"
                  class="btn btn-pri btn-sm"
                  type="button"
                  data-testid="acct-checkout-open"
                  @click="openCheckout(row)"
                >
                  领用
                </button>
                <button
                  v-if="row.status === 'IN_USE'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  @click="openReturn(row)"
                >
                  归还
                </button>
                <button
                  v-if="row.status === 'IN_USE'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="acct-recall-open"
                  @click="openRecall(row)"
                >
                  收回
                </button>
                <button
                  v-if="row.status === 'FROZEN'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="acct-unfreeze-open"
                  @click="openUnfreeze(row)"
                >
                  解冻
                </button>
                <button
                  v-if="(row.status === 'IN_USE' && !pendingFor(row)) || row.status === 'FROZEN'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="acct-transfer-open"
                  @click="openTransfer(row)"
                >
                  流转
                </button>
                <button
                  v-if="canConfirmTransfer(row)"
                  class="btn btn-pri btn-sm"
                  type="button"
                  data-testid="acct-transfer-confirm-open"
                  @click="openTransferConfirm(pendingFor(row))"
                >
                  确认接收
                </button>
                <button
                  v-if="row.status !== 'CANCELLED'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="acct-recharge-open"
                  @click="openRecharge(row)"
                >
                  冲话费
                </button>
                <button
                  v-if="row.status !== 'CANCELLED'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="acct-verify-open"
                  @click="openVerify(row)"
                >
                  账实核对
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager">
        <span class="pg-total">共 {{ total }} 条</span>
        <select class="pg-size" :value="pageSize" @change="changeSize">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
        </select>
        <span>条/页</span>
        <span class="pg-sp"></span>
        <span class="pg-n" :class="{ dis: pageNo <= 1 }" @click="goto(pageNo - 1)">‹</span>
        <span v-for="n in pageList" :key="n" class="pg-n" :class="{ on: n === pageNo }" @click="goto(n)">{{ n }}</span>
        <span class="pg-n" :class="{ dis: pageNo >= pageCount }" @click="goto(pageNo + 1)">›</span>
      </div>
    </div>
    <p class="hint">
      GET /corp/account/page?platformType={{ meta.platform }} · 「领用」→ POST /account/apply（在用再领用 1021 · 冻结 1022）· 流转 → POST /account/transfer · 收回 → POST /account/transfer（RECALL · 直接 FROZEN）· 账号已绑定资产时提交或确认后提示同步办理资产转移（不阻断）· 解冻 → POST /account/{id}/unfreeze（FROZEN → IN_POOL）· 归还 → POST /account/return/submit · 冲话费 → POST /account/recharge · 未核对可 PUT /account/recharge/{id} · 已核对由管理员 POST /account/recharge/{id}/unlock 后再编辑 · 账实核对 → POST /account/recharge/verify（差异率 ≥ 2% 为 1026）· 成本汇总 → GET /account/recharge/summary · 导出 → GET /account/recharge/summary/export
    </p>

    <div data-testid="acct-recharge-list" class="recharge-list">
      <div class="pg-h" style="margin-top: 8px">
        <div>
          <h2 style="font-size: 16px; margin: 0">冲话费记录</h2>
          <div class="sub">GET /account/recharge/list · 账号 / 核对状态 / 充值月份 / 渠道 · 月份留空则不过滤 · 金额 &gt; 5000 须凭证（1025）· 凭证仅财务角色可见 · 未核对可编辑 · 已核对须管理员解锁后再编辑 · 差异记录须先有财务核查工单</div>
        </div>
      </div>
      <form class="qbar" data-testid="acct-recharge-filters" @submit.prevent="searchRecharges">
        <label>
          账号
          <input
            v-model="rechargeFilters.accountNo"
            data-testid="acct-recharge-filter-account"
            placeholder="账号编号"
            style="width: 140px"
          />
        </label>
        <label>
          核对状态
          <select v-model="rechargeFilters.verifyStatus" data-testid="acct-recharge-filter-status">
            <option value="">全部</option>
            <option value="UNVERIFIED">未核对</option>
            <option value="MATCHED">一致</option>
            <option value="DIFF">差异</option>
          </select>
        </label>
        <label>
          充值月份
          <input v-model="rechargeFilters.month" data-testid="acct-recharge-filter-month" type="month" />
        </label>
        <label>
          渠道
          <select v-model="rechargeFilters.channel" data-testid="acct-recharge-filter-channel">
            <option value="">全部</option>
            <option v-for="item in rechargeChannels" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="acct-recharge-query" :disabled="rechargeListBusy">筛选</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="acct-recharge-reset" :disabled="rechargeListBusy" @click="resetRechargeFilters">
          清空条件
        </button>
      </form>
      <p v-if="rechargeFilterMsg" class="hint" data-testid="acct-recharge-filter-msg">{{ rechargeFilterMsg }}</p>
      <div class="recharge-table">
        <table>
          <thead>
            <tr>
              <th>账号</th>
              <th>金额</th>
              <th>渠道</th>
              <th>充值日期</th>
              <th>凭证</th>
              <th>核对</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!rechargeRows.length">
              <td colspan="7" data-testid="acct-recharge-empty">{{ rechargeFilterMsg || '暂无冲话费记录' }}</td>
            </tr>
            <tr v-for="item in rechargeRows" :key="String(item.id)" data-testid="acct-recharge-row">
              <td class="mono">{{ item.accountNo }}</td>
              <td class="num">¥{{ moneyText(item.amount) }}</td>
              <td>{{ channelLabel(String(item.channel || '')) }}</td>
              <td>{{ item.rechargeDate }}</td>
              <td>
                <span v-if="item.voucherUrl">{{ item.voucherUrl }}</span>
                <span v-else-if="item.voucherAttached">仅财务可见</span>
                <span v-else>—</span>
              </td>
              <td>
                {{ verifyLabel(String(item.verifyStatus || '')) }}
                <span v-if="item.verifyDiff != null"> ¥{{ moneyText(item.verifyDiff) }}</span>
              </td>
              <td>
                <button
                  v-if="!item.verifyStatus || item.verifyStatus === 'UNVERIFIED'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="acct-recharge-edit"
                  @click="openRechargeEdit(item)"
                >
                  编辑
                </button>
                <button
                  v-else
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="acct-recharge-unlock"
                  @click="openUnlock(item)"
                >
                  解锁
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div data-testid="acct-recharge-summary" class="recharge-list">
      <div class="pg-h" style="margin-top: 8px">
        <div>
          <h2 style="font-size: 16px; margin: 0">成本汇总报表</h2>
          <div class="sub">GET /account/recharge/summary · 期间按月过滤 · 维度：账号 / 部门 / 平台 · 合计与当月冲话费记录一致 · 可导出 xlsx / csv</div>
        </div>
      </div>
      <form class="qbar" data-testid="acct-summary-filters" @submit.prevent="loadSummary">
        <label>
          期间
          <input v-model="summaryForm.month" data-testid="acct-summary-month" type="month" />
        </label>
        <label>
          维度
          <select v-model="summaryForm.groupBy" data-testid="acct-summary-groupby">
            <option v-for="item in summaryGroups" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="acct-summary-query" :disabled="summaryBusy">汇总</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="acct-summary-export-xlsx" :disabled="exportBusy" @click="exportSummary('XLSX')">
          导出 XLSX
        </button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="acct-summary-export-csv" :disabled="exportBusy" @click="exportSummary('CSV')">
          导出 CSV
        </button>
      </form>
      <p v-if="summaryMsg" class="hint" data-testid="acct-summary-msg">{{ summaryMsg }}</p>
      <p v-if="exportNote" class="hint" data-testid="acct-summary-export-note">{{ exportNote }}</p>
      <div class="recharge-table">
        <table data-testid="acct-summary-table">
          <thead>
            <tr>
              <th>维度</th>
              <th>金额</th>
              <th>笔数</th>
              <th>差异金额</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!summaryRows.length">
              <td colspan="4" data-testid="acct-summary-empty">该月无冲话费记录</td>
            </tr>
            <tr v-for="item in summaryRows" :key="item.dimKey" data-testid="acct-summary-row">
              <td>{{ item.dimLabel }}</td>
              <td class="num">¥{{ moneyText(item.totalAmount) }}</td>
              <td>{{ item.recordCount }}</td>
              <td class="num">¥{{ moneyText(item.diffAmount) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="hint" data-testid="acct-summary-totals">
        合计 ¥{{ moneyText(summaryTotals.totalAmount) }} · {{ summaryTotals.recordCount }} 笔 · 差异 ¥{{ moneyText(summaryTotals.diffAmount) }}
      </p>
    </div>

    <ProtoDrawer :open="detailOpen" :title="`${meta.title} · 详情`" width="640px" @close="detailOpen = false">
      <div v-if="detail" class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="btn btn-sm"
          :class="activeTab === tab.id ? 'btn-pri' : 'btn-sec'"
          type="button"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>
      <div v-if="detail && activeTab === 'basic'" class="formrow one">
        <div v-for="item in basicLines" :key="item.label" class="fld">
          <label>{{ item.label }}</label>
          <div>{{ item.value }}</div>
        </div>
      </div>
      <div v-if="detail && activeTab === 'collect'" class="formrow one">
        <p class="hint">凭证保存后须「导入 Collector」完成 bind，否则采集任务会报未绑定。</p>
        <div class="fld">
          <label>绑定状态</label>
          <div>{{ collectSummary }}</div>
        </div>
        <div v-if="bindInfo" class="fld">
          <label>Collector account_id</label>
          <div class="mono">{{ bindInfo.collectorAccountId || '—' }}</div>
        </div>
        <div v-if="bindInfo" class="fld">
          <label>最近探活</label>
          <div>{{ bindInfo.lastProbeAt || '—' }} {{ bindInfo.connStatus === 'SUCCESS' ? '成功' : bindInfo.connStatus === 'FAILED' ? '失败' : '' }}</div>
        </div>
        <div class="fld">
          <label>凭证</label>
          <div :data-testid="meta.platform === 'DOUYIN' ? 'dy-tab-mask' : meta.platform === 'WECHAT_CHANNELS' ? 'wx-tab-mask' : 'ks-tab-mask'">
            {{ detail.credentialMask || (detail.hasCookie ? '已配置（脱敏）' : '未配置') }}
          </div>
        </div>
        <template v-if="meta.platform === 'DOUYIN'">
          <div class="fld">
            <label>平台账号 ID</label>
            <div class="mono" data-testid="dy-tab-platform-id">{{ detail.platformAccountId || '—' }}</div>
          </div>
          <div class="fld">
            <label>凭证引用</label>
            <div class="mono">{{ detail.credentialRef || '—' }}</div>
          </div>
          <div class="fld">
            <label>采集健康</label>
            <div data-testid="dy-tab-health">{{ detail.healthLabel || '—' }}</div>
          </div>
          <div class="fld">
            <label>最新粉丝</label>
            <div data-testid="dy-tab-follower">{{ followerText(detail) }}</div>
          </div>
          <h3 style="margin: 8px 0; font-size: 14px">粉丝日快照</h3>
          <table data-testid="dy-tab-follower-daily">
            <thead>
              <tr>
                <th>统计日</th>
                <th>粉丝数</th>
                <th>新增</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!followerDailyOf(detail).length">
                <td colspan="3">暂无粉丝日快照</td>
              </tr>
              <tr v-for="snap in followerDailyOf(detail)" :key="String(snap.statDate)">
                <td>{{ snap.statDate }}</td>
                <td data-testid="dy-tab-follower-count">{{ snap.followerCount }}</td>
                <td>{{ snap.newFollowerCount }}</td>
              </tr>
            </tbody>
          </table>
          <p class="hint">
            定时采集与立即采集见
            <router-link to="/ims/collect/douyin">抖音内部账号采集</router-link>
            。
          </p>
          <h3 style="margin: 8px 0; font-size: 14px">作品日快照</h3>
          <table data-testid="dy-tab-video-snapshot">
            <thead>
              <tr>
                <th>作品</th>
                <th>统计日</th>
                <th>播放</th>
                <th>点赞</th>
                <th>评论</th>
                <th>转发</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!videoSnapshotsOf(detail).length">
                <td colspan="6">暂无作品日快照</td>
              </tr>
              <tr v-for="snap in videoSnapshotsOf(detail)" :key="String(snap.videoId) + String(snap.statDate)">
                <td class="mono">{{ snap.videoId }}</td>
                <td>{{ snap.statDate }}</td>
                <td data-testid="dy-tab-video-play">{{ snap.playCount }}</td>
                <td>{{ snap.likeCount }}</td>
                <td>{{ snap.commentCount }}</td>
                <td>{{ snap.shareCount }}</td>
              </tr>
            </tbody>
          </table>
          <h3 style="margin: 8px 0; font-size: 14px">采集记录</h3>
          <table data-testid="dy-tab-logs">
            <thead>
              <tr>
                <th>状态</th>
                <th>条数</th>
                <th>开始时间</th>
                <th>错误</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!dyLogs.length">
                <td colspan="4">暂无采集记录</td>
              </tr>
              <tr v-for="row in dyLogs" :key="row.id">
                <td data-testid="dy-tab-log-status">{{ row.statusLabel || row.status }}</td>
                <td data-testid="dy-tab-log-count">{{ row.recordCount }}</td>
                <td>{{ row.startedAt }}</td>
                <td>{{ row.errorSummary || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </template>
        <template v-if="meta.platform === 'KUAISHOU'">
          <div class="fld">
            <label>平台账号 ID</label>
            <input v-model="ksPlatformAccountId" data-testid="ks-tab-platform-id" />
          </div>
          <div class="fld">
            <label>凭证引用</label>
            <div class="mono">{{ detail.credentialRef || '—' }}</div>
          </div>
          <div class="fld">
            <label>采集健康</label>
            <div data-testid="ks-tab-health">{{ detail.healthLabel || '—' }}</div>
          </div>
          <div class="fld">
            <label>最新粉丝</label>
            <div data-testid="ks-tab-follower">{{ followerText(detail) }}</div>
          </div>
          <h3 style="margin: 8px 0; font-size: 14px">粉丝日快照</h3>
          <table data-testid="ks-tab-follower-daily">
            <thead>
              <tr>
                <th>统计日</th>
                <th>粉丝数</th>
                <th>新增</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!followerDailyOf(detail).length">
                <td colspan="3">暂无粉丝日快照</td>
              </tr>
              <tr v-for="snap in followerDailyOf(detail)" :key="String(snap.statDate)">
                <td>{{ snap.statDate }}</td>
                <td data-testid="ks-tab-follower-count">{{ snap.followerCount }}</td>
                <td>{{ snap.newFollowerCount }}</td>
              </tr>
            </tbody>
          </table>
          <h3 style="margin: 8px 0; font-size: 14px">作品日快照</h3>
          <table data-testid="ks-tab-video-snapshot">
            <thead>
              <tr>
                <th>作品</th>
                <th>统计日</th>
                <th>播放</th>
                <th>点赞</th>
                <th>评论</th>
                <th>转发</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!videoSnapshotsOf(detail).length">
                <td colspan="6">暂无作品日快照</td>
              </tr>
              <tr v-for="snap in videoSnapshotsOf(detail)" :key="String(snap.videoId) + String(snap.statDate)">
                <td class="mono">{{ snap.videoId }}</td>
                <td>{{ snap.statDate }}</td>
                <td data-testid="ks-tab-video-play">{{ snap.playCount }}</td>
                <td>{{ snap.likeCount }}</td>
                <td>{{ snap.commentCount }}</td>
                <td>{{ snap.shareCount }}</td>
              </tr>
            </tbody>
          </table>
          <div class="fld">
            <label>更新凭证（不明文回显）</label>
            <input v-model="ksCredential" type="password" autocomplete="new-password" placeholder="留空则不修改" data-testid="ks-tab-credential" />
          </div>
          <button class="btn btn-sec btn-sm" type="button" @click="saveKsCredential">保存快手凭证</button>
          <p class="hint">
            定时采集与立即采集见
            <router-link to="/ims/collect/kuaishou">快手内部账号采集</router-link>
            。
          </p>
        </template>
        <template v-if="meta.platform === 'WECHAT_CHANNELS'">
          <div class="fld">
            <label>平台账号 ID</label>
            <div class="mono" data-testid="wx-tab-platform-id">{{ detail.platformAccountId || '—' }}</div>
          </div>
          <div class="fld">
            <label>凭证引用</label>
            <div class="mono">{{ detail.credentialRef || '—' }}</div>
          </div>
          <div class="fld">
            <label>采集健康</label>
            <div data-testid="wx-tab-health">{{ detail.healthLabel || '—' }}</div>
          </div>
          <div class="fld">
            <label>最新粉丝</label>
            <div data-testid="wx-tab-follower">{{ followerText(detail) }}</div>
          </div>
          <h3 style="margin: 8px 0; font-size: 14px">粉丝日快照</h3>
          <table data-testid="wx-tab-follower-daily">
            <thead>
              <tr>
                <th>统计日</th>
                <th>粉丝数</th>
                <th>新增</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!followerDailyOf(detail).length">
                <td colspan="3">暂无粉丝日快照</td>
              </tr>
              <tr v-for="snap in followerDailyOf(detail)" :key="String(snap.statDate)">
                <td>{{ snap.statDate }}</td>
                <td data-testid="wx-tab-follower-count">{{ snap.followerCount }}</td>
                <td>{{ snap.newFollowerCount }}</td>
              </tr>
            </tbody>
          </table>
          <p class="hint">
            定时采集与立即采集见
            <router-link to="/ims/collect/wechat-channels">视频号内部账号采集</router-link>
            。
          </p>
          <h3 style="margin: 8px 0; font-size: 14px">采集记录</h3>
          <table data-testid="wx-tab-logs">
            <thead>
              <tr>
                <th>状态</th>
                <th>条数</th>
                <th>开始时间</th>
                <th>错误</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!wxLogs.length">
                <td colspan="4">暂无采集记录</td>
              </tr>
              <tr v-for="row in wxLogs" :key="row.id">
                <td data-testid="wx-tab-log-status">{{ row.statusLabel || row.status }}</td>
                <td data-testid="wx-tab-log-count">{{ row.recordCount }}</td>
                <td>{{ row.startedAt }}</td>
                <td>{{ row.errorSummary || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </template>
        <p class="hint">本 Tab 为 ADR-047 平台账号采集配置，不是 COLLECT 竞品账号配置。</p>
        <div class="acts" style="margin-top: 12px">
          <button class="btn btn-sec btn-sm" type="button" :disabled="!detail.hasCookie" @click="importCollector">导入 Collector</button>
          <button class="btn btn-sec btn-sm" type="button" @click="testConnection">测试连接</button>
        </div>
        <p v-if="collectMsg" class="hint">{{ collectMsg }}</p>
      </div>
      <div v-if="detail && activeTab === 'timeline'">
        <p v-if="timelineLoading" class="hint">加载时间线…</p>
        <p v-else-if="timelineError" class="hint">{{ timelineError }}</p>
        <ul v-else-if="timelineEvents.length" class="timeline-list">
          <li v-for="ev in timelineEvents" :key="ev.id">
            <span class="mono">{{ ev.eventTime }}</span>
            <strong>{{ ev.eventType }}</strong>
            {{ ev.snapshotSummary }}
            <span v-if="ev.refNo" class="hint">（{{ ev.refNo }}）</span>
          </li>
        </ul>
        <p v-else class="hint">暂无领用/归还事件</p>
      </div>
      <div v-if="detail && activeTab === 'asset'" class="hint">关联资产需 ASSET 反向穿透接口，契约未在本片实现。</div>
      <template #foot>
        <button
          v-if="detail && detail.status === 'IN_POOL'"
          class="btn btn-pri"
          type="button"
          @click="openCheckout(detail)"
        >
          领用
        </button>
        <button
          v-if="detail && detail.status === 'IN_USE'"
          class="btn btn-sec"
          type="button"
          @click="openReturn(detail)"
        >
          归还
        </button>
        <button class="btn btn-sec" type="button" @click="detailOpen = false">关闭</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="checkoutOpen" title="发起账号领用" width="520px" @close="closeCheckout">
      <div v-if="checkoutAccount" class="formrow one">
        <div class="fld">
          <label>账号</label>
          <div>{{ checkoutAccount.accountNo }} · {{ checkoutAccount.nickname }}</div>
        </div>
      </div>
      <template v-if="!checkoutApplyId">
        <div class="formrow one">
          <div class="fld">
            <label>用途说明<i class="req">*</i></label>
            <input v-model="checkoutForm.purpose" placeholder="直播/内容用途" />
          </div>
        </div>
        <div class="formrow one">
          <div class="fld">
            <label>计划开始<i class="req">*</i></label>
            <input v-model="checkoutForm.planStart" type="date" />
          </div>
        </div>
        <div class="formrow one">
          <div class="fld">
            <label>计划结束<i class="req">*</i></label>
            <input v-model="checkoutForm.planEnd" type="date" />
          </div>
        </div>
        <p v-if="checkoutMsg" class="hint" data-testid="acct-checkout-msg">{{ checkoutMsg }}</p>
      </template>
      <template v-else>
        <p class="hint">申请单 {{ checkoutApplyNo }} · 状态 {{ checkoutStepLabel }}</p>
        <div v-if="checkoutStep === 'PENDING_APPROVAL'" class="acts" style="margin-top: 12px">
          <button class="btn btn-pri btn-sm" type="button" :disabled="checkoutBusy" @click="approveCheckout">审批通过</button>
        </div>
        <div v-if="checkoutStep === 'PENDING_HANDOVER'" class="formrow one" style="margin-top: 12px">
          <label><input v-model="checkoutHandover.passwordReset" type="checkbox" /> 密码已重置</label>
          <label><input v-model="checkoutHandover.mobileRebound" type="checkbox" /> 绑定手机已换</label>
          <button class="btn btn-pri btn-sm" type="button" :disabled="checkoutBusy" @click="confirmCheckout">确认领用生效</button>
        </div>
        <div v-if="checkoutStep === 'DONE'" class="hint">领用已生效，账号状态应为「在用」。</div>
        <p v-if="checkoutMsg" class="hint">{{ checkoutMsg }}</p>
      </template>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="closeCheckout">取消</button>
        <button
          v-if="!checkoutApplyId"
          class="btn btn-pri"
          type="button"
          :disabled="checkoutBusy"
          @click="submitCheckout"
        >
          提交申请
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="transferOpen" title="发起账号流转" width="560px" @close="closeTransfer">
      <div v-if="transferAccount" data-testid="acct-transfer-drawer" class="formrow one">
        <div class="fld">
          <label>账号</label>
          <div>{{ transferAccount.accountNo }} · {{ transferAccount.nickname }}</div>
        </div>
        <div class="fld">
          <label>原责任人</label>
          <div>{{ transferAccount.holderUserName || '—' }}</div>
        </div>
        <div class="fld">
          <label>新责任人<i class="req">*</i></label>
          <select v-model.number="transferForm.toUserId" data-testid="acct-transfer-to">
            <option :value="0">请选择</option>
            <option v-for="user in transferUsers" :key="user.id" :value="user.id">{{ user.label }}</option>
          </select>
        </div>
        <div class="fld">
          <label>原因分类<i class="req">*</i></label>
          <select v-model="transferForm.reasonType" data-testid="acct-transfer-reason">
            <option v-for="item in transferReasons" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
        <div class="fld">
          <label>交接说明<i class="req">*</i></label>
          <input v-model="transferForm.remark" data-testid="acct-transfer-remark" placeholder="交接说明" />
        </div>
        <p v-if="transferResult" class="hint" data-testid="acct-transfer-status">
          流转单 {{ transferResult.transferNo }} · 审批流：待新责任人确认
        </p>
        <p v-if="transferMsg" class="hint" data-testid="acct-transfer-msg">{{ transferMsg }}</p>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="closeTransfer">关闭</button>
        <button
          v-if="!transferResult"
          class="btn btn-pri"
          type="button"
          data-testid="acct-transfer-submit"
          :disabled="transferBusy"
          @click="submitTransfer"
        >
          提交流转
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="recallOpen" title="收回至冻结" width="520px" @close="closeRecall">
      <div v-if="recallAccount" data-testid="acct-recall-drawer" class="formrow one">
        <div class="fld">
          <label>账号</label>
          <div>{{ recallAccount.accountNo }} · {{ recallAccount.nickname }}</div>
        </div>
        <div class="fld">
          <label>原责任人</label>
          <div>{{ recallAccount.holderUserName || '—' }}</div>
        </div>
        <div class="fld">
          <label>原因分类<i class="req">*</i></label>
          <select v-model="recallForm.reasonType" data-testid="acct-recall-reason">
            <option v-for="item in transferReasons" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
        <div class="fld">
          <label>交接说明<i class="req">*</i></label>
          <input v-model="recallForm.remark" data-testid="acct-recall-remark" placeholder="收回说明" />
        </div>
        <p class="hint">收回后直接生效，账号进入冻结态（FROZEN）。领用与流转将被 1022 拦截。</p>
        <p v-if="recallResult" class="hint" data-testid="acct-recall-status">
          收回单 {{ recallResult.transferNo }} · 已生效 · 状态 FROZEN
        </p>
        <p v-if="recallMsg" class="hint" data-testid="acct-recall-msg">{{ recallMsg }}</p>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="closeRecall">关闭</button>
        <button
          v-if="!recallResult"
          class="btn btn-pri"
          type="button"
          data-testid="acct-recall-submit"
          :disabled="recallBusy"
          @click="submitRecall"
        >
          提交收回
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="unfreezeOpen" title="解冻回账号池" width="520px" @close="closeUnfreeze">
      <div v-if="unfreezeAccount" data-testid="acct-unfreeze-drawer" class="formrow one">
        <div class="fld">
          <label>账号</label>
          <div>{{ unfreezeAccount.accountNo }} · {{ unfreezeAccount.nickname }}</div>
        </div>
        <div class="fld">
          <label>当前状态</label>
          <div>冻结（FROZEN）</div>
        </div>
        <div class="fld">
          <label>解冻说明<i class="req">*</i></label>
          <input v-model="unfreezeRemark" data-testid="acct-unfreeze-remark" placeholder="解冻原因" />
        </div>
        <p class="hint">仅管理员可操作。解冻后账号回到账号池（IN_POOL），清空责任人，可再次领用。</p>
        <p v-if="unfreezeResult" class="hint" data-testid="acct-unfreeze-status">
          已解冻 · 状态 {{ unfreezeResult.status }}
        </p>
        <p v-if="unfreezeMsg" class="hint" data-testid="acct-unfreeze-msg">{{ unfreezeMsg }}</p>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="closeUnfreeze">关闭</button>
        <button
          v-if="!unfreezeResult"
          class="btn btn-pri"
          type="button"
          data-testid="acct-unfreeze-submit"
          :disabled="unfreezeBusy"
          @click="submitUnfreeze"
        >
          确认解冻
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="transferConfirmOpen" title="确认接收流转" width="520px" @close="transferConfirmOpen = false">
      <div v-if="transferConfirm" data-testid="acct-transfer-confirm-drawer" class="formrow one">
        <div class="fld">
          <label>流转单</label>
          <div class="mono">{{ transferConfirm.transferNo }}</div>
        </div>
        <div class="fld">
          <label>账号</label>
          <div class="mono">{{ transferConfirm.accountNo || '—' }}</div>
        </div>
        <div class="fld">
          <label>责任人</label>
          <div>{{ transferConfirm.fromUserName || '—' }} → {{ transferConfirm.toUserName || '—' }}</div>
        </div>
        <div class="fld">
          <label>交接说明</label>
          <div>{{ transferConfirm.remark || '—' }}</div>
        </div>
        <p class="hint">审批流：待确认 → 新责任人确认后生效，账号责任人即刻变更。</p>
        <p v-if="transferConfirmMsg" class="hint" data-testid="acct-transfer-confirm-msg">{{ transferConfirmMsg }}</p>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="transferConfirmOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="acct-transfer-confirm" :disabled="transferBusy" @click="confirmTransfer">
          确认接收
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="returnOpen" title="账号归还" width="480px" @close="returnOpen = false">
      <div v-if="returnAccount" class="formrow one">
        <div class="fld">
          <label>账号</label>
          <div>{{ returnAccount.accountNo }} · {{ returnAccount.nickname }}</div>
        </div>
        <div class="fld">
          <label>备注</label>
          <input v-model="returnRemark" placeholder="可选" />
        </div>
        <p v-if="returnMsg" class="hint">{{ returnMsg }}</p>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="returnOpen = false">取消</button>
        <button class="btn btn-pri" type="button" :disabled="returnBusy" @click="submitReturn">确认归还</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="rechargeOpen" :title="rechargeEditId ? '编辑冲话费' : '登记冲话费'" width="560px" @close="closeRecharge">
      <div v-if="rechargeAccount" data-testid="acct-recharge-drawer" class="formrow one">
        <div class="fld">
          <label>账号</label>
          <div>{{ rechargeAccount.accountNo }} · {{ rechargeAccount.nickname }}</div>
        </div>
        <div class="fld">
          <label>金额（元）<i class="req">*</i></label>
          <input v-model="rechargeForm.amount" data-testid="acct-recharge-amount" inputmode="decimal" placeholder="大于 0，两位小数" />
        </div>
        <div class="fld">
          <label>渠道<i class="req">*</i></label>
          <select v-model="rechargeForm.channel" data-testid="acct-recharge-channel">
            <option v-for="item in rechargeChannels" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
        <div class="fld">
          <label>充值日期<i class="req">*</i></label>
          <input v-model="rechargeForm.rechargeDate" data-testid="acct-recharge-date" type="date" />
        </div>
        <div class="fld">
          <label>凭证</label>
          <input v-model="rechargeForm.voucherUrl" data-testid="acct-recharge-voucher" placeholder="凭证号或 fileKey（金额大于 5000 必填）" />
        </div>
        <p v-if="rechargeNeedsVoucher" class="hint">金额超过 5000 元，未填凭证将返回 1025</p>
        <p v-if="rechargeMsg" class="hint" data-testid="acct-recharge-msg">{{ rechargeMsg }}</p>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="closeRecharge">取消</button>
        <button class="btn btn-pri" type="button" data-testid="acct-recharge-submit" :disabled="rechargeBusy" @click="submitRecharge">
          {{ rechargeEditId ? '保存更正' : '提交登记' }}
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="unlockOpen" title="解锁已核对记录" width="520px" @close="closeUnlock">
      <div v-if="unlockRow" data-testid="acct-unlock-drawer" class="formrow one">
        <div class="fld">
          <label>账号</label>
          <div>{{ unlockRow.accountNo }}</div>
        </div>
        <div class="fld">
          <label>金额 / 日期</label>
          <div>¥{{ moneyText(unlockRow.amount) }} · {{ unlockRow.rechargeDate }}</div>
        </div>
        <div class="fld">
          <label>核对状态</label>
          <div data-testid="acct-unlock-status">{{ verifyLabel(String(unlockRow.verifyStatus || '')) }}</div>
        </div>
        <p class="hint">已核对记录不能直接改。管理员解锁后回到未核对，才能再编辑。差异记录须已生成财务核查工单。</p>
        <p v-if="unlockMsg" class="hint" data-testid="acct-unlock-msg">{{ unlockMsg }}</p>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="closeUnlock">关闭</button>
        <button
          v-if="unlockRow && unlockRow.verifyStatus !== 'UNVERIFIED'"
          class="btn btn-pri"
          type="button"
          data-testid="acct-unlock-submit"
          :disabled="unlockBusy"
          @click="submitUnlock"
        >
          确认解锁
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="verifyOpen" title="月度账实核对" width="720px" @close="closeVerify">
      <div v-if="verifyAccount" data-testid="acct-verify-drawer" class="formrow one">
        <div class="fld">
          <label>账号</label>
          <div>{{ verifyAccount.accountNo }} · {{ verifyAccount.nickname }}</div>
        </div>
        <div class="fld">
          <label>核对月份<i class="req">*</i></label>
          <input v-model="verifyForm.month" data-testid="acct-verify-month" type="month" />
        </div>
        <div class="fld">
          <label>平台实际消费（元）<i class="req">*</i></label>
          <input
            v-model="verifyForm.platformConsumed"
            data-testid="acct-verify-platform"
            inputmode="decimal"
            placeholder="本地无平台拉取时录入后台消费"
          />
        </div>
        <p class="hint">差异率 = |冲话费总额 − 平台实际消费| / 平台实际消费。低于 2% 通过；达到或超过 2% 返回 1026，并生成财务核查工单。</p>
        <p v-if="verifyMsg" class="hint" data-testid="acct-verify-msg" :class="{ 'verify-over': verifyOver }">{{ verifyMsg }}</p>
        <div v-if="verifyResult" data-testid="acct-verify-result" class="verify-card" :class="{ 'verify-over': verifyOver }">
          <div data-testid="acct-verify-rate">差异率 {{ verifyResult.diffRateText }}</div>
          <div>
            冲话费 ¥{{ moneyText(verifyResult.totalRecharge) }} · 平台消费 ¥{{ moneyText(verifyResult.platformConsumed) }} · 差异 ¥{{ moneyText(verifyResult.diffAmount) }}
          </div>
          <div>核对状态：{{ verifyLabel(verifyResult.verifyStatus) }}</div>
          <div v-if="verifyResult.workOrderId" data-testid="acct-verify-ticket">已生成财务核查工单 #{{ verifyResult.workOrderId }}</div>
        </div>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="closeVerify">关闭</button>
        <button class="btn btn-pri" type="button" data-testid="acct-verify-submit" :disabled="verifyBusy" @click="submitVerify">
          触发核对
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="formOpen" title="登记平台账号" width="480px" @close="formOpen = false">
      <div class="formrow one"><div class="fld"><label>昵称<i class="req">*</i></label><input v-model="form.accountName" /></div></div>
      <div class="formrow one"><div class="fld"><label>公司 ID<i class="req">*</i></label><input v-model.number="form.companyId" placeholder="选择器：填已有公司 id" /></div></div>
      <div class="formrow one"><div class="fld"><label>IP 组 ID<i class="req">*</i></label><input v-model.number="form.ipGroupId" placeholder="选择器：填已有 IP 组 id" /></div></div>
      <div class="formrow one"><div class="fld"><label>实名人 ID</label><input v-model.number="form.realnameId" placeholder="可选" /></div></div>
      <div class="formrow one"><div class="fld"><label>责任人 ID<i class="req">*</i></label><input v-model.number="form.holderUserId" placeholder="ims_sys_user.id" /></div></div>
      <div class="formrow one"><div class="fld"><label>状态</label><select v-model="form.status"><option v-for="item in statusOptions" :key="item.value" :value="item.value">{{ item.label }}</option></select></div></div>
      <p class="hint">强关联须通过选择器；手输非法 id 时后端返回 1500/1501/1504。</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="formOpen = false">取消</button>
        <button class="btn btn-pri" type="button" @click="submitCreate">保存</button>
      </template>
    </ProtoDrawer>

    <div v-if="assetHintOpen" class="asset-hint-mask" data-testid="acct-asset-transfer-hint">
      <div class="asset-hint-card" role="dialog" aria-modal="true">
        <h2>资产同步转移</h2>
        <p data-testid="acct-asset-transfer-text">{{ assetHintText }}</p>
        <ul data-testid="acct-asset-transfer-list">
          <li v-for="item in assetHintAssets" :key="item.assetId" data-testid="acct-asset-transfer-item">
            {{ item.assetCode }} · {{ item.assetName }}
          </li>
        </ul>
        <p class="hint">账号流转已经提交，资产不会自动过户。请相关责任人另行办理资产转移。</p>
        <div class="asset-hint-acts">
          <button class="btn btn-sec" type="button" data-testid="acct-asset-transfer-skip" @click="skipAssetTransfer">
            仅转账号
          </button>
          <button class="btn btn-pri" type="button" data-testid="acct-asset-transfer-jump" @click="jumpAssetTransfer">
            跳转资产处理
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { useUserStore } from '../../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const currentUserId = computed(() => Number(userStore.profile?.userId || 0))

const PLATFORM_MAP: Record<string, { title: string; platform: string; sub: string }> = {
  'wechat-official': { title: '公众号', platform: 'WECHAT_OFFICIAL', sub: 'P-M4-008 · WECHAT_OFFICIAL · 08 CORP-A' },
  'wechat-channels': { title: '视频号', platform: 'WECHAT_CHANNELS', sub: 'P-M4-008 · WECHAT_CHANNELS + 采集 Tab · 08 CORP-A' },
  douyin: { title: '抖音', platform: 'DOUYIN', sub: 'P-M4-008 · DOUYIN + 内部账号采集 · 08 CORP-A' },
  kuaishou: { title: '快手', platform: 'KUAISHOU', sub: 'P-M4-008 · KUAISHOU + 内部账号采集 · 08 CORP-A' },
  xiaohongshu: { title: '小红书', platform: 'XIAOHONGSHU', sub: 'P-M4-008 · XIAOHONGSHU · 08 CORP-A' },
}

const meta = computed(() => {
  const slug = String(route.params.platform || 'douyin')
  return PLATFORM_MAP[slug] || PLATFORM_MAP.douyin
})

const statusOptions = [
  { value: 'IN_USE', label: '在用' },
  { value: 'IN_POOL', label: '池可领用' },
  { value: 'FROZEN', label: '冻结' },
  { value: 'RETURNED', label: '已归还' },
]

const tabs = [
  { id: 'basic', label: '基本信息' },
  { id: 'collect', label: '采集' },
  { id: 'timeline', label: '领用时间线' },
  { id: 'asset', label: '关联资产' },
]

const rows = ref<Record<string, unknown>[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const error = ref('')
const keyword = ref('')
const ipGroupKeyword = ref('')
const status = ref('')

const detailOpen = ref(false)
const detail = ref<Record<string, unknown> | null>(null)
const bindInfo = ref<Record<string, unknown> | null>(null)
const activeTab = ref('basic')
const collectMsg = ref('')
const collectSummary = ref('—')
const ksPlatformAccountId = ref('')
const ksCredential = ref('')
const dyLogs = ref<Array<Record<string, unknown>>>([])
const wxLogs = ref<Array<Record<string, unknown>>>([])

const timelineEvents = ref<
  { id: number; eventType: string; refNo: string; snapshotSummary: string; eventTime: string }[]
>([])
const timelineLoading = ref(false)
const timelineError = ref('')

const checkoutOpen = ref(false)
const checkoutAccount = ref<Record<string, unknown> | null>(null)
const checkoutApplyId = ref<number | null>(null)
const checkoutApplyNo = ref('')
const checkoutStep = ref('')
const checkoutBusy = ref(false)
const checkoutMsg = ref('')
const checkoutForm = reactive({
  purpose: 'E2E 内容直播领用',
  planStart: '',
  planEnd: '',
})
const checkoutHandover = reactive({ passwordReset: true, mobileRebound: false })

const returnOpen = ref(false)
const returnAccount = ref<Record<string, unknown> | null>(null)
const returnRemark = ref('')
const returnBusy = ref(false)
const returnMsg = ref('')

const rechargeChannels = [
  { value: 'ALIPAY', label: '支付宝' },
  { value: 'WECHAT', label: '微信' },
  { value: 'BANK', label: '银行卡' },
]
const rechargeRows = ref<Record<string, unknown>[]>([])
const rechargeFilters = reactive({
  accountNo: '',
  verifyStatus: '',
  month: '',
  channel: '',
})
const rechargeFilterMsg = ref('')
const rechargeListBusy = ref(false)
const summaryGroups = [
  { value: 'ACCOUNT', label: '账号' },
  { value: 'DEPT', label: '部门' },
  { value: 'PLATFORM', label: '平台' },
]
type SummaryRow = {
  dimKey: string
  dimLabel: string
  totalAmount: number
  recordCount: number
  diffAmount: number
}
const summaryForm = reactive({
  month: '',
  groupBy: 'ACCOUNT',
})
const summaryRows = ref<SummaryRow[]>([])
const summaryTotals = ref({ totalAmount: 0, recordCount: 0, diffAmount: 0 })
const summaryBusy = ref(false)
const summaryMsg = ref('')
const exportBusy = ref(false)
const exportNote = ref('')
const rechargeOpen = ref(false)
const rechargeEditId = ref<number | null>(null)
const rechargeAccount = ref<Record<string, unknown> | null>(null)
const rechargeBusy = ref(false)
const rechargeMsg = ref('')
const unlockOpen = ref(false)
const unlockRow = ref<Record<string, unknown> | null>(null)
const unlockBusy = ref(false)
const unlockMsg = ref('')
const rechargeForm = reactive({
  amount: '',
  channel: 'ALIPAY',
  rechargeDate: '',
  voucherUrl: '',
})

type VerifyResult = {
  verifyTaskId: string
  message: string
  diffRateText: string
  verifyStatus: string
  totalRecharge: number
  platformConsumed: number
  diffAmount: number
  overThreshold: boolean
  workOrderId?: number | null
}
const verifyOpen = ref(false)
const verifyAccount = ref<Record<string, unknown> | null>(null)
const verifyBusy = ref(false)
const verifyMsg = ref('')
const verifyResult = ref<VerifyResult | null>(null)
const verifyForm = reactive({
  month: '',
  platformConsumed: '',
})
const verifyOver = computed(() => !!verifyResult.value?.overThreshold || verifyMsg.value.startsWith('1026'))

type TransferRow = {
  id: number
  transferNo: string
  accountId: number
  accountNo: string
  toUserId: number
  fromUserId: number
  fromUserName: string
  toUserName: string
  status: string
  remark: string
  reasonType: string
}

type BoundAsset = {
  assetId: number
  assetCode: string
  assetName: string
  assetType?: string
  status?: string
}
type AssetHintPayload = {
  boundAssets?: BoundAsset[]
  assetTransferHint?: string | null
}
const assetHintOpen = ref(false)
const assetHintText = ref('')
const assetHintAssets = ref<BoundAsset[]>([])

function showAssetHint(data: AssetHintPayload | null | undefined) {
  const assets = data?.boundAssets || []
  if (!assets.length) return
  assetHintAssets.value = assets
  assetHintText.value = data?.assetTransferHint || `该账号绑定了 ${assets.length} 项资产，是否同步发起资产转移？`
  assetHintOpen.value = true
}

function skipAssetTransfer() {
  assetHintOpen.value = false
}

function jumpAssetTransfer() {
  assetHintOpen.value = false
  router.push('/ims/corp/device/office')
}

const transferReasons = [
  { value: 'TRANSFER_POSITION', label: '调岗' },
  { value: 'PRE_RESIGN', label: '离职前置' },
  { value: 'VIOLATION', label: '违规' },
  { value: 'BUSINESS_ADJUST', label: '业务调整' },
]
const pendingByAccount = ref<Record<number, TransferRow>>({})
const transferOpen = ref(false)
const transferAccount = ref<Record<string, unknown> | null>(null)
const transferUsers = ref<{ id: number; label: string }[]>([])
const transferBusy = ref(false)
const transferMsg = ref('')
const transferResult = ref<{ transferNo: string; status: string } | null>(null)
const transferForm = reactive({
  toUserId: 0,
  reasonType: 'BUSINESS_ADJUST',
  remark: 'E2E 账号流转交接',
})
const transferConfirmOpen = ref(false)
const transferConfirm = ref<TransferRow | null>(null)
const transferConfirmMsg = ref('')
const recallOpen = ref(false)
const recallAccount = ref<Record<string, unknown> | null>(null)
const recallBusy = ref(false)
const recallMsg = ref('')
const recallResult = ref<{ transferNo: string; status: string } | null>(null)
const recallForm = reactive({
  reasonType: 'BUSINESS_ADJUST',
  remark: 'E2E 账号收回冻结',
})
const unfreezeOpen = ref(false)
const unfreezeAccount = ref<Record<string, unknown> | null>(null)
const unfreezeBusy = ref(false)
const unfreezeMsg = ref('')
const unfreezeRemark = ref('E2E 管理员解冻回池')
const unfreezeResult = ref<{ status: string } | null>(null)

const rechargeNeedsVoucher = computed(() => {
  const amount = Number(rechargeForm.amount)
  return Number.isFinite(amount) && amount > 5000 && !rechargeForm.voucherUrl.trim()
})

const formOpen = ref(false)
const form = reactive({
  accountName: '',
  companyId: undefined as number | undefined,
  ipGroupId: undefined as number | undefined,
  realnameId: undefined as number | undefined,
  holderUserId: 1,
  status: 'IN_USE',
})

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pageList = computed(() => {
  const count = pageCount.value
  const current = pageNo.value
  const start = Math.max(1, current - 2)
  const end = Math.min(count, start + 4)
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})

const checkoutStepLabel = computed(() => {
  if (checkoutStep.value === 'PENDING_APPROVAL') return '待审批'
  if (checkoutStep.value === 'PENDING_HANDOVER') return '待交接确认'
  if (checkoutStep.value === 'DONE') return '已领用'
  return checkoutStep.value
})

function followerDailyOf(row: Record<string, unknown> | null) {
  const daily = row?.followerDaily
  return Array.isArray(daily) ? (daily as Array<Record<string, unknown>>) : []
}

function videoSnapshotsOf(row: Record<string, unknown> | null) {
  const snaps = row?.videoSnapshots
  return Array.isArray(snaps) ? (snaps as Array<Record<string, unknown>>) : []
}

function followerText(row: Record<string, unknown> | null) {
  if (!row || row.followerCount == null || row.followerCount === '') return '—'
  return row.followerStatDate ? `${row.followerCount}（${row.followerStatDate}）` : String(row.followerCount)
}

function statusLabel(code: string) {
  const hit = statusOptions.find((o) => o.value === code)
  return hit ? hit.label : code
}

function channelLabel(code: string) {
  const hit = rechargeChannels.find((o) => o.value === code)
  return hit ? hit.label : code
}

function verifyLabel(code: string) {
  if (code === 'MATCHED') return '一致'
  if (code === 'DIFF') return '差异'
  if (code === 'UNVERIFIED' || !code) return '未核对'
  return code
}

function previousMonthUtc() {
  const prev = new Date(Date.UTC(new Date().getUTCFullYear(), new Date().getUTCMonth() - 1, 1))
  const month = String(prev.getUTCMonth() + 1).padStart(2, '0')
  return `${prev.getUTCFullYear()}-${month}`
}

function moneyText(value: unknown) {
  const amount = Number(value)
  return Number.isFinite(amount) ? amount.toFixed(2) : '—'
}

function todayUtc() {
  return new Date().toISOString().slice(0, 10)
}

function bizMessage(error: unknown) {
  if (error && typeof error === 'object' && 'code' in error) {
    const body = error as { code?: number; msg?: string }
    if (typeof body.code === 'number' && body.code !== 0) {
      return `${body.code} ${body.msg || ''}`.trim()
    }
  }
  return errorMessage(error)
}

function defaultPlanDates() {
  const start = new Date()
  const end = new Date()
  end.setDate(end.getDate() + 30)
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  checkoutForm.planStart = fmt(start)
  checkoutForm.planEnd = fmt(end)
}

const basicLines = computed(() => {
  if (!detail.value) return []
  const d = detail.value
  return [
    { label: '账号编号', value: d.accountNo },
    { label: '昵称', value: d.nickname },
    { label: '平台', value: d.platformType },
    { label: 'IP 组', value: d.ipGroupName || d.ipGroupId },
    { label: '公司', value: d.companyName || d.companyId },
    { label: '实名人', value: d.realNameMasked || '—' },
    { label: '责任人', value: d.holderUserName || d.holderUserId },
    { label: '状态', value: statusLabel(String(d.status || '')) },
    { label: '采集摘要', value: d.collectBindSummary },
  ]
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/corp/account/page', {
      params: {
        pageNo: pageNo.value,
        pageSize: pageSize.value,
        platformType: meta.value.platform,
        keyword: keyword.value || undefined,
        status: status.value || undefined,
      },
    })
    const data = res.data?.data as { list: Record<string, unknown>[]; total: number }
    let list = data?.list || []
    if (ipGroupKeyword.value.trim()) {
      const key = ipGroupKeyword.value.trim()
      list = list.filter((row) => String(row.ipGroupName || '').includes(key))
    }
    rows.value = list
    total.value = data?.total || 0
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '加载失败'
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
    await loadRecharges()
    await loadSummary()
    await loadTransfers()
  }
}

function pendingFor(row: Record<string, unknown>) {
  return pendingByAccount.value[Number(row.id)] || null
}

function canConfirmTransfer(row: Record<string, unknown>) {
  const pending = pendingFor(row)
  return !!pending && Number(pending.toUserId) === currentUserId.value
}

async function loadTransfers() {
  try {
    const res = await http.get('/account/transfer/list', {
      params: { status: 'PENDING_CONFIRM', pageNo: 1, pageSize: 50 },
    })
    const data = res.data?.data as { list: TransferRow[] }
    const map: Record<number, TransferRow> = {}
    for (const item of data?.list || []) {
      map[Number(item.accountId)] = item
    }
    pendingByAccount.value = map
  } catch {
    pendingByAccount.value = {}
  }
  await openTransferFromQuery()
}

let openingTransferLink = false

async function openTransferFromQuery() {
  const transferId = Number(route.query.transferId || 0)
  if (!transferId) return
  const pending = Object.values(pendingByAccount.value).find((item) => Number(item.id) === transferId)
  if (!pending) return
  const hit = rows.value.find((row) => Number(row.id) === Number(pending.accountId))
  if (!hit) {
    if (openingTransferLink || keyword.value === pending.accountNo) return
    openingTransferLink = true
    keyword.value = pending.accountNo
    pageNo.value = 1
    try {
      await load()
    } finally {
      openingTransferLink = false
    }
    return
  }
  if (!transferConfirmOpen.value) openTransferConfirm(pending)
}

function rechargeFilterActive() {
  return Boolean(
    rechargeFilters.accountNo.trim() || rechargeFilters.verifyStatus || rechargeFilters.month || rechargeFilters.channel,
  )
}

async function resolveRechargeAccountId(): Promise<number | null | undefined> {
  const key = rechargeFilters.accountNo.trim()
  if (!key) return undefined
  const res = await http.get('/corp/account/page', {
    params: {
      pageNo: 1,
      pageSize: 50,
      platformType: meta.value.platform,
      keyword: key,
    },
  })
  const list = ((res.data?.data as { list?: Record<string, unknown>[] })?.list) || []
  const exact = list.find((row) => String(row.accountNo || '') === key)
  return exact ? Number(exact.id) : null
}

async function loadRecharges() {
  rechargeListBusy.value = true
  rechargeFilterMsg.value = ''
  try {
    const accountId = await resolveRechargeAccountId()
    if (accountId === null) {
      rechargeRows.value = []
      rechargeFilterMsg.value = '未找到该账号'
      return
    }
    const params: Record<string, unknown> = { pageNo: 1, pageSize: 20 }
    if (accountId) params.accountId = accountId
    if (rechargeFilters.verifyStatus) params.verifyStatus = rechargeFilters.verifyStatus
    if (rechargeFilters.month) params.month = rechargeFilters.month
    if (rechargeFilters.channel) params.channel = rechargeFilters.channel
    const res = await http.get('/account/recharge/list', { params })
    const data = res.data?.data as { list: Record<string, unknown>[] }
    rechargeRows.value = data?.list || []
    if (!rechargeRows.value.length && rechargeFilterActive()) {
      rechargeFilterMsg.value = '没有符合筛选条件的冲话费记录'
    }
  } catch {
    rechargeRows.value = []
    if (!rechargeFilterMsg.value) rechargeFilterMsg.value = '冲话费列表加载失败'
  } finally {
    rechargeListBusy.value = false
  }
}

function searchRecharges() {
  return loadRecharges()
}

function resetRechargeFilters() {
  rechargeFilters.accountNo = ''
  rechargeFilters.verifyStatus = ''
  rechargeFilters.month = ''
  rechargeFilters.channel = ''
  return loadRecharges()
}

async function loadSummary() {
  if (!summaryForm.month) summaryForm.month = todayUtc().slice(0, 7)
  summaryBusy.value = true
  summaryMsg.value = ''
  try {
    const res = await http.get('/account/recharge/summary', {
      params: { month: summaryForm.month, groupBy: summaryForm.groupBy },
    })
    const data = res.data?.data as { rows?: SummaryRow[]; totals?: typeof summaryTotals.value }
    summaryRows.value = data?.rows || []
    summaryTotals.value = data?.totals || { totalAmount: 0, recordCount: 0, diffAmount: 0 }
  } catch (e: unknown) {
    summaryRows.value = []
    summaryTotals.value = { totalAmount: 0, recordCount: 0, diffAmount: 0 }
    summaryMsg.value = bizMessage(e)
  } finally {
    summaryBusy.value = false
  }
}

function search() {
  pageNo.value = 1
  load()
}

function reset() {
  keyword.value = ''
  ipGroupKeyword.value = ''
  status.value = ''
  search()
}

function goto(n: number) {
  if (n < 1 || n > pageCount.value) return
  pageNo.value = n
  load()
}

function changeSize(ev: Event) {
  pageSize.value = Number((ev.target as HTMLSelectElement).value)
  pageNo.value = 1
  load()
}

async function loadTimeline(accountId: unknown) {
  timelineLoading.value = true
  timelineError.value = ''
  timelineEvents.value = []
  try {
    const res = await http.get(`/account/timeline/${accountId}`)
    const data = res.data?.data as { list: typeof timelineEvents.value }
    timelineEvents.value = data?.list || []
  } catch (e: unknown) {
    timelineError.value = e instanceof Error ? e.message : '时间线加载失败'
  } finally {
    timelineLoading.value = false
  }
}

async function loadDyLogs(accountId: unknown) {
  if (meta.value.platform !== 'DOUYIN' || !accountId) {
    dyLogs.value = []
    return
  }
  try {
    const res = await http.get('/collect/douyin/log/page', { params: { pageNo: 1, pageSize: 10, accountId } })
    dyLogs.value = res.data?.data?.list || []
  } catch {
    dyLogs.value = []
  }
}

async function loadWxLogs(accountId: unknown) {
  if (meta.value.platform !== 'WECHAT_CHANNELS' || !accountId) {
    wxLogs.value = []
    return
  }
  try {
    const res = await http.get('/collect/wechat-channels/log/page', { params: { pageNo: 1, pageSize: 10, accountId } })
    wxLogs.value = res.data?.data?.list || []
  } catch {
    wxLogs.value = []
  }
}

async function openDetail(row: Record<string, unknown>, tab = 'basic') {
  activeTab.value = tab
  collectMsg.value = ''
  const res = await http.get(`/corp/account/${row.id}`)
  const data = res.data?.data as Record<string, unknown>
  detail.value = data
  ksPlatformAccountId.value = String(data.platformAccountId || '')
  ksCredential.value = ''
  collectSummary.value = String(data.collectBindSummary || '—')
  if (tab === 'collect') {
    await loadDyLogs(row.id)
    await loadWxLogs(row.id)
  } else {
    dyLogs.value = []
    wxLogs.value = []
  }
  try {
    const bindRes = await http.get(`/corp/account/${row.id}/collector-bind`)
    bindInfo.value = bindRes.data?.data as Record<string, unknown>
  } catch {
    bindInfo.value = null
  }
  if (tab === 'timeline') {
    await loadTimeline(row.id)
  }
  detailOpen.value = true
}

function openCheckout(row: Record<string, unknown>) {
  checkoutAccount.value = row
  checkoutApplyId.value = null
  checkoutApplyNo.value = ''
  checkoutStep.value = ''
  checkoutMsg.value = ''
  checkoutHandover.passwordReset = true
  checkoutHandover.mobileRebound = false
  defaultPlanDates()
  checkoutOpen.value = true
}

function closeCheckout() {
  checkoutOpen.value = false
  checkoutAccount.value = null
  checkoutApplyId.value = null
}

async function submitCheckout() {
  if (!checkoutAccount.value) return
  checkoutBusy.value = true
  checkoutMsg.value = ''
  try {
    const res = await http.post('/account/apply', {
      accountId: checkoutAccount.value.id,
      purpose: checkoutForm.purpose,
      planStart: checkoutForm.planStart,
      planEnd: checkoutForm.planEnd,
    })
    const vo = res.data?.data as { id: number; applyNo: string; applyStatus: string }
    checkoutApplyId.value = vo.id
    checkoutApplyNo.value = vo.applyNo
    checkoutStep.value = vo.applyStatus
  } catch (e: unknown) {
    checkoutMsg.value = bizMessage(e)
  } finally {
    checkoutBusy.value = false
  }
}

async function approveCheckout() {
  if (!checkoutApplyId.value) return
  checkoutBusy.value = true
  checkoutMsg.value = ''
  try {
    await http.put(`/account/apply/${checkoutApplyId.value}/approve`, { action: 'APPROVE' })
    checkoutStep.value = 'PENDING_HANDOVER'
  } catch (e: unknown) {
    checkoutMsg.value = e instanceof Error ? e.message : '审批失败'
  } finally {
    checkoutBusy.value = false
  }
}

async function confirmCheckout() {
  if (!checkoutApplyId.value) return
  checkoutBusy.value = true
  checkoutMsg.value = ''
  try {
    await http.put(`/account/apply/${checkoutApplyId.value}/confirm`, {
      passwordReset: checkoutHandover.passwordReset,
      mobileRebound: checkoutHandover.mobileRebound,
    })
    checkoutStep.value = 'DONE'
    checkoutOpen.value = false
    await load()
    if (detail.value && String(detail.value.id) === String(checkoutAccount.value?.id)) {
      const res = await http.get(`/corp/account/${detail.value.id}`)
      detail.value = res.data?.data as Record<string, unknown>
    }
  } catch (e: unknown) {
    checkoutMsg.value = e instanceof Error ? e.message : '确认失败'
  } finally {
    checkoutBusy.value = false
  }
}

function closeTransfer() {
  transferOpen.value = false
  transferAccount.value = null
  transferResult.value = null
}

async function openTransfer(row: Record<string, unknown>) {
  transferAccount.value = row
  transferForm.toUserId = 0
  transferForm.reasonType = 'BUSINESS_ADJUST'
  transferForm.remark = 'E2E 账号流转交接'
  transferMsg.value = ''
  transferResult.value = null
  transferUsers.value = []
  transferOpen.value = true
  try {
    const res = await http.get('/system/user/page', { params: { pageNo: 1, pageSize: 100, status: 'ENABLED' } })
    const list = (res.data?.data?.list || []) as { id: string; nickname?: string; username?: string }[]
    const holderId = Number(row.holderUserId || 0)
    transferUsers.value = list
      .map((user) => ({
        id: Number(user.id),
        label: `${user.nickname || user.username || user.id}（${user.username || user.id}）`,
      }))
      .filter((user) => user.id > 0 && user.id !== holderId)
  } catch (e: unknown) {
    transferMsg.value = bizMessage(e)
  }
}

async function submitTransfer() {
  if (!transferAccount.value) return
  transferBusy.value = true
  transferMsg.value = ''
  try {
    if (!transferForm.toUserId) {
      transferMsg.value = '1001 新责任人必填'
      return
    }
    if (!transferForm.remark.trim()) {
      transferMsg.value = '1001 交接说明必填'
      return
    }
    const res = await http.post('/account/transfer', {
      accountId: transferAccount.value.id,
      transferType: 'TRANSFER',
      toUserId: transferForm.toUserId,
      reasonType: transferForm.reasonType,
      remark: transferForm.remark.trim(),
    })
    const vo = res.data?.data as { transferNo: string; status: string } & AssetHintPayload
    transferResult.value = vo
    transferMsg.value = `流转单 ${vo.transferNo} · 审批流：待新责任人确认`
    showAssetHint(vo)
    await loadTransfers()
  } catch (e: unknown) {
    transferMsg.value = bizMessage(e)
  } finally {
    transferBusy.value = false
  }
}

function closeRecall() {
  recallOpen.value = false
  recallAccount.value = null
  recallResult.value = null
}

function openRecall(row: Record<string, unknown>) {
  recallAccount.value = row
  recallForm.reasonType = 'BUSINESS_ADJUST'
  recallForm.remark = 'E2E 账号收回冻结'
  recallMsg.value = ''
  recallResult.value = null
  recallOpen.value = true
}

async function submitRecall() {
  if (!recallAccount.value) return
  recallBusy.value = true
  recallMsg.value = ''
  try {
    if (!recallForm.remark.trim()) {
      recallMsg.value = '1001 交接说明必填'
      return
    }
    const res = await http.post('/account/transfer', {
      accountId: recallAccount.value.id,
      transferType: 'RECALL',
      reasonType: recallForm.reasonType,
      remark: recallForm.remark.trim(),
    })
    const vo = res.data?.data as { transferNo: string; status: string } & AssetHintPayload
    recallResult.value = vo
    recallMsg.value = `收回单 ${vo.transferNo} · 已生效 · 状态 FROZEN`
    showAssetHint(vo)
    await load()
  } catch (e: unknown) {
    recallMsg.value = bizMessage(e)
  } finally {
    recallBusy.value = false
  }
}

function closeUnfreeze() {
  unfreezeOpen.value = false
  unfreezeAccount.value = null
  unfreezeResult.value = null
}

function openUnfreeze(row: Record<string, unknown>) {
  unfreezeAccount.value = row
  unfreezeRemark.value = 'E2E 管理员解冻回池'
  unfreezeMsg.value = ''
  unfreezeResult.value = null
  unfreezeOpen.value = true
}

async function submitUnfreeze() {
  if (!unfreezeAccount.value) return
  unfreezeBusy.value = true
  unfreezeMsg.value = ''
  try {
    if (!unfreezeRemark.value.trim()) {
      unfreezeMsg.value = '1001 解冻说明必填'
      return
    }
    const res = await http.post(`/account/${unfreezeAccount.value.id}/unfreeze`, {
      remark: unfreezeRemark.value.trim(),
    })
    const vo = res.data?.data as { status: string }
    unfreezeResult.value = vo
    unfreezeMsg.value = '已解冻 · 状态 IN_POOL'
    await load()
  } catch (e: unknown) {
    unfreezeMsg.value = bizMessage(e)
  } finally {
    unfreezeBusy.value = false
  }
}

function openTransferConfirm(row: TransferRow | null) {
  if (!row) return
  transferConfirm.value = row
  transferConfirmMsg.value = ''
  transferConfirmOpen.value = true
}

async function confirmTransfer() {
  if (!transferConfirm.value) return
  transferBusy.value = true
  transferConfirmMsg.value = ''
  try {
    const res = await http.put(`/account/transfer/${transferConfirm.value.id}/confirm`, { accept: true })
    transferConfirmMsg.value = '已生效'
    transferConfirmOpen.value = false
    showAssetHint(res.data?.data as AssetHintPayload)
    await load()
  } catch (e: unknown) {
    transferConfirmMsg.value = bizMessage(e)
  } finally {
    transferBusy.value = false
  }
}

function openReturn(row: Record<string, unknown>) {
  returnAccount.value = row
  returnRemark.value = ''
  returnMsg.value = ''
  returnOpen.value = true
}

async function submitReturn() {
  if (!returnAccount.value) return
  returnBusy.value = true
  returnMsg.value = ''
  try {
    await http.post('/account/return/submit', {
      accountId: returnAccount.value.id,
      remark: returnRemark.value || undefined,
    })
    returnOpen.value = false
    detailOpen.value = false
    await load()
  } catch (e: unknown) {
    returnMsg.value = e instanceof Error ? e.message : '归还失败'
  } finally {
    returnBusy.value = false
  }
}

async function saveKsCredential() {
  if (!detail.value) return
  collectMsg.value = ''
  try {
    const payload: Record<string, unknown> = { platformAccountId: ksPlatformAccountId.value }
    if (ksCredential.value) payload.cookie = ksCredential.value
    const res = await http.put(`/collect/kuaishou/account/${detail.value.id}`, payload)
    const account = res.data?.data?.account as Record<string, unknown> | undefined
    if (account) detail.value = { ...detail.value, ...account }
    ksCredential.value = ''
    collectMsg.value = `凭证已保存，掩码 ${account?.credentialMask || '已配置'}`
    await load()
  } catch (e: unknown) {
    collectMsg.value = errorMessage(e)
  }
}

async function importCollector() {
  if (!detail.value) return
  collectMsg.value = ''
  try {
    const bindRes = await http.post(`/corp/account/${detail.value.id}/collector-bind`, {})
    bindInfo.value = bindRes.data?.data as Record<string, unknown>
    collectSummary.value = '已绑定'
    collectMsg.value = '已导入 Collector，请用测试连接确认探活。'
    await load()
  } catch (e: unknown) {
    collectMsg.value = e instanceof Error ? e.message : '导入失败'
  }
}

async function testConnection() {
  if (!detail.value) return
  collectMsg.value = ''
  try {
    const bindRes = await http.post(`/corp/account/${detail.value.id}/collector-bind/test-connection`, {})
    bindInfo.value = bindRes.data?.data as Record<string, unknown>
    collectMsg.value = '探活成功'
  } catch (e: unknown) {
    collectMsg.value = e instanceof Error ? e.message : '探活失败'
  }
}

function openRecharge(row: Record<string, unknown>) {
  rechargeEditId.value = null
  rechargeAccount.value = row
  rechargeForm.amount = ''
  rechargeForm.channel = 'ALIPAY'
  rechargeForm.rechargeDate = todayUtc()
  rechargeForm.voucherUrl = ''
  rechargeMsg.value = ''
  rechargeOpen.value = true
}

function openRechargeEdit(item: Record<string, unknown>) {
  rechargeEditId.value = Number(item.id)
  rechargeAccount.value = {
    id: item.accountId,
    accountNo: item.accountNo,
    nickname: item.accountNo,
  }
  rechargeForm.amount = item.amount == null ? '' : String(item.amount)
  rechargeForm.channel = String(item.channel || 'ALIPAY')
  rechargeForm.rechargeDate = String(item.rechargeDate || '')
  rechargeForm.voucherUrl = String(item.voucherUrl || '')
  rechargeMsg.value = ''
  rechargeOpen.value = true
}

function closeRecharge() {
  rechargeOpen.value = false
  rechargeAccount.value = null
  rechargeEditId.value = null
}

function closeUnlock() {
  unlockOpen.value = false
  unlockRow.value = null
}

function openUnlock(item: Record<string, unknown>) {
  unlockRow.value = item
  unlockMsg.value = ''
  unlockOpen.value = true
}

async function submitUnlock() {
  if (!unlockRow.value) return
  unlockBusy.value = true
  unlockMsg.value = ''
  try {
    const res = await http.post(`/account/recharge/${unlockRow.value.id}/unlock`, {})
    const data = res.data?.data as { message?: string; verifyStatus?: string }
    unlockMsg.value = data?.message || '已解锁，可再次编辑'
    if (unlockRow.value) unlockRow.value = { ...unlockRow.value, verifyStatus: 'UNVERIFIED', verifyDiff: null }
    await loadRecharges()
  } catch (e: unknown) {
    unlockMsg.value = bizMessage(e)
  } finally {
    unlockBusy.value = false
  }
}

async function exportSummary(format: 'XLSX' | 'CSV') {
  exportBusy.value = true
  exportNote.value = ''
  try {
    if (!summaryForm.month) summaryForm.month = todayUtc().slice(0, 7)
    const res = await http.get('/account/recharge/summary/export', {
      params: { month: summaryForm.month, groupBy: summaryForm.groupBy, format },
    })
    const data = (res.data?.data || {}) as {
      downloadUrl?: string
      fileName?: string
      recordCount?: number
      totalAmount?: number
    }
    const downloadUrl = String(data.downloadUrl || '')
    const fileName = String(data.fileName || `recharge_summary.${format === 'CSV' ? 'csv' : 'xlsx'}`)
    if (!downloadUrl) {
      exportNote.value = '导出失败'
      return
    }
    const token = localStorage.getItem('ims_access')
    const fileRes = await fetch(downloadUrl, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!fileRes.ok) {
      exportNote.value = `导出失败（${fileRes.status}）`
      return
    }
    const blob = await fileRes.blob()
    const anchor = document.createElement('a')
    anchor.href = URL.createObjectURL(blob)
    anchor.download = fileName
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(anchor.href)
    const recordCount = Number(data.recordCount)
    const totalAmount = data.totalAmount ?? summaryTotals.value.totalAmount
    exportNote.value =
      Number.isFinite(recordCount) && recordCount === 0
        ? `该月无冲话费记录，已导出空表 ${fileName}`
        : `已导出 ${fileName} · ${summaryForm.month} · ${summaryForm.groupBy} · 合计 ¥${moneyText(totalAmount)}`
  } catch (e: unknown) {
    exportNote.value = bizMessage(e)
  } finally {
    exportBusy.value = false
  }
}

function closeVerify() {
  verifyOpen.value = false
  verifyAccount.value = null
}

function openVerify(row: Record<string, unknown>) {
  verifyAccount.value = row
  verifyForm.month = previousMonthUtc()
  verifyForm.platformConsumed = ''
  verifyMsg.value = ''
  verifyResult.value = null
  verifyOpen.value = true
}

async function submitVerify() {
  if (!verifyAccount.value) return
  verifyBusy.value = true
  verifyMsg.value = ''
  try {
    const platform = Number(verifyForm.platformConsumed)
    if (!verifyForm.month) {
      verifyMsg.value = '1001 核对月份格式不合法'
      return
    }
    if (!Number.isFinite(platform) || platform <= 0) {
      verifyMsg.value = '1001 平台实际消费须大于 0'
      return
    }
    const res = await http.post('/account/recharge/verify', {
      month: verifyForm.month,
      accountIds: [verifyAccount.value.id],
      platformConsumed: platform,
    })
    const data = res.data?.data as VerifyResult
    verifyResult.value = data
    verifyMsg.value = data?.message || '核对完成'
    await loadRecharges()
  } catch (e: unknown) {
    verifyMsg.value = bizMessage(e)
    const body = e as { data?: VerifyResult }
    verifyResult.value = body?.data ?? null
    if (body?.data) await loadRecharges()
  } finally {
    verifyBusy.value = false
  }
}

async function submitRecharge() {
  if (!rechargeAccount.value) return
  rechargeBusy.value = true
  rechargeMsg.value = ''
  try {
    const amount = Number(rechargeForm.amount)
    if (!Number.isFinite(amount) || amount <= 0) {
      rechargeMsg.value = '1001 金额格式不合法'
      return
    }
    const payload = {
      accountId: rechargeAccount.value.id,
      amount,
      channel: rechargeForm.channel,
      rechargeDate: rechargeForm.rechargeDate,
      voucherUrl: rechargeForm.voucherUrl.trim() || undefined,
    }
    if (rechargeEditId.value) {
      await http.put(`/account/recharge/${rechargeEditId.value}`, payload)
      rechargeMsg.value = '冲话费已更正'
    } else {
      await http.post('/account/recharge', payload, {
        headers: { clientToken: crypto.randomUUID().replace(/-/g, '') },
      })
      rechargeMsg.value = '冲话费已登记'
    }
    rechargeOpen.value = false
    await loadRecharges()
    await loadSummary()
  } catch (e: unknown) {
    rechargeMsg.value = bizMessage(e)
  } finally {
    rechargeBusy.value = false
  }
}

function openCreate() {
  form.accountName = ''
  form.companyId = undefined
  form.ipGroupId = undefined
  form.realnameId = undefined
  form.holderUserId = 1
  form.status = 'IN_USE'
  formOpen.value = true
}

async function submitCreate() {
  await http.post('/master/platform-account', {
    platformType: meta.value.platform,
    accountName: form.accountName,
    companyId: form.companyId,
    ipGroupId: form.ipGroupId,
    realnameId: form.realnameId || undefined,
    holderUserId: form.holderUserId,
    status: form.status,
  })
  formOpen.value = false
  load()
}

async function applyDeepLink() {
  const openId = route.query.openId
  if (!openId) return
  const tab = String(route.query.tab || 'basic')
  const hit = rows.value.find((r) => String(r.id) === String(openId))
  if (hit) {
    await openDetail(hit, tab)
    return
  }
  try {
    const res = await http.get(`/corp/account/${openId}`)
    const data = res.data?.data as Record<string, unknown>
    if (data) await openDetail({ id: openId, ...data }, tab)
  } catch {
    /* ignore */
  }
}

watch(
  () => route.params.platform,
  () => {
    pageNo.value = 1
    load().then(() => applyDeepLink())
  },
  { immediate: true },
)

watch(
  () => [route.query.openId, route.query.tab],
  () => {
    applyDeepLink()
  },
)

watch(
  () => route.query.transferId,
  () => {
    void openTransferFromQuery()
  },
)

watch(activeTab, (tab) => {
  if (tab === 'timeline' && detail.value?.id) {
    loadTimeline(detail.value.id)
  }
  if (tab === 'collect' && detail.value?.id) {
    loadDyLogs(detail.value.id)
    loadWxLogs(detail.value.id)
  }
})
</script>

<style scoped>
.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.acts-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.timeline-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.timeline-list li {
  padding: 8px 0;
  border-bottom: 1px solid var(--border, #eee);
}
.recharge-list {
  margin-top: 12px;
}
.recharge-table {
  overflow: auto;
}
.verify-card {
  padding: 12px;
  border: 1px solid var(--border, #eee);
  border-radius: 8px;
}
.verify-over {
  color: #c45656;
  font-weight: 600;
}
.asset-hint-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 300;
}
.asset-hint-card {
  width: min(480px, 92vw);
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}
.asset-hint-card h2 {
  margin: 0 0 8px;
  font-size: 18px;
}
.asset-hint-card ul {
  margin: 8px 0 12px;
  padding-left: 18px;
}
.asset-hint-acts {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
</style>
