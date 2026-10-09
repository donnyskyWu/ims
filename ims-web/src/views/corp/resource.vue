<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>{{ meta.title }}</h1>
        <div class="sub">{{ meta.sub }}</div>
      </div>
      <div v-if="kind === 'sim-card'" class="acts">
        <button class="btn btn-pri" type="button" @click="openCreate">新建手机卡</button>
      </div>
      <div v-else-if="kind === 'certificate'" class="acts">
        <button class="btn btn-sec" type="button" data-testid="corp-cert-scan-btn" @click="openScan">扫描到期</button>
        <button class="btn btn-pri" type="button" data-testid="corp-cert-create-btn" @click="openCertCreate">录入证件</button>
      </div>
    </div>
    <div
      v-if="kind === 'certificate' && digitalReady"
      class="hint"
      :class="{ bad: digitalShort }"
      data-testid="corp-cert-digital-banner"
    >
      <template v-if="digitalEmpty">
        数字化率暂无应数字化档案（目标&gt;95%，BR-005） · 应数字化 0 · 已数字化 0
      </template>
      <template v-else>
        数字化率 {{ digitalPercent }}（目标&gt;95%，BR-005）
        · 应数字化 {{ digital.totalExpected }} · 已数字化 {{ digital.digitalizedCount }}
        · {{ digitalShort ? '未达标' : '达标' }}
      </template>
      <button class="btn btn-txt btn-sm" type="button" data-testid="corp-cert-digital-open" @click="digitalOpen = true">查看统计</button>
    </div>
    <div
      v-else-if="kind === 'certificate' && digitalError"
      class="hint bad"
      data-testid="corp-cert-digital-banner"
    >
      数字化率暂不可用。{{ digitalError }}
      <button class="btn btn-txt btn-sm" type="button" data-testid="corp-cert-digital-retry" @click="loadDigital">重试</button>
    </div>
    <form class="qbar" @submit.prevent="search">
      <input v-model="keyword" :placeholder="meta.placeholder" style="width: 180px" />
      <input
        v-if="kind === 'company'"
        v-model="creditCode"
        placeholder="信用代码"
        style="width: 160px"
        data-testid="master-company-credit"
      />
      <select
        v-if="kind === 'company'"
        v-model="industry"
        style="width: 140px"
        data-testid="master-company-industry"
      >
        <option value="">全部行业</option>
        <option v-for="item in industries" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <select v-if="kind === 'realname'" v-model="idType" style="width: 140px" data-testid="master-realname-idtype">
        <option value="">全部证件类型</option>
        <option v-for="item in idTypes" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <select v-if="kind === 'sim-card'" v-model="operator" style="width: 120px" data-testid="master-sim-operator">
        <option value="">全部运营商</option>
        <option v-for="item in operators" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <select v-if="kind === 'sim-card'" v-model="realnameId" style="width: 140px" data-testid="master-sim-realname">
        <option value="">全部实名人</option>
        <option v-for="person in persons" :key="person.id" :value="String(person.id)">{{ person.realName }}</option>
      </select>
      <select
        v-if="statusChoices.length"
        v-model="status"
        style="width: 120px"
        :data-testid="kind === 'sim-card' ? 'master-sim-status' : undefined"
      >
        <option value="">全部状态</option>
        <option v-for="item in statusChoices" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="reset">重置</button>
    </form>
    <p v-if="kind === 'certificate' && originalNote" class="hint" data-testid="corp-cert-original-note">{{ originalNote }}</p>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th v-for="col in meta.columns" :key="col">{{ col }}</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td :colspan="meta.columns.length + 1" style="white-space: normal">
                <div class="empty"><div class="et">加载中</div></div>
              </td>
            </tr>
            <tr v-else-if="!rows.length">
              <td :colspan="meta.columns.length + 1" style="white-space: normal">
                <div class="empty" :data-testid="kind === 'certificate' ? 'corp-cert-list-empty' : undefined">
                  <div class="et">{{ error || (kind === 'certificate' ? listEmptyTitle : emptyTitle) }}</div>
                  <div class="es">{{ error ? meta.emptyHint : kind === 'certificate' ? listEmptyHint : emptyHintText }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="String(row.id)">
              <td v-for="key in meta.keys" :key="key">{{ show(row, key) }}</td>
              <td>
                <button
                  class="btn btn-txt btn-sm"
                  type="button"
                  :data-testid="kind === 'certificate' ? 'corp-cert-view-btn' : undefined"
                  @click="openDetail(row)"
                >
                  {{ kind === 'certificate' ? '查看' : '详情' }}
                </button>
                <button
                  v-if="kind === 'certificate'"
                  class="btn btn-txt btn-sm"
                  type="button"
                  data-testid="corp-cert-file-btn"
                  @click="openFileUrl(row)"
                >
                  原图
                </button>
                <button v-if="kind === 'sim-card'" class="btn btn-txt btn-sm" type="button" @click="openEdit(row)">编辑</button>
                <button
                  v-if="kind === 'certificate' && row.status === 'PENDING_REVIEW'"
                  class="btn btn-txt btn-sm"
                  type="button"
                  data-testid="corp-cert-review-btn"
                  @click="openReview(row)"
                >
                  审核
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
    <p v-if="kind === 'company'" class="hint" data-testid="master-company-industry-hint">
      行业来自字典 dict_industry。未列入字典的行业不会出现在下拉里。
    </p>
    <p class="hint">{{ meta.hint }}</p>
    <div v-if="kind === 'certificate'" data-testid="corp-cert-expire-panel">
      <div class="sec rowline" style="justify-content: space-between; align-items: baseline">
        <span>到期预警</span>
        <span data-testid="corp-cert-expire-stats">黄色 {{ expireStats.yellow }} · 红色 {{ expireStats.red }} · 锁定 {{ expireStats.locked }} · 本月换证 {{ expireStats.renewed }}</span>
      </div>
      <p v-if="scanMessage" class="hint" data-testid="corp-cert-scan-message">{{ scanMessage }}</p>
      <p v-if="renewMessage" class="hint" data-testid="corp-cert-renew-message">{{ renewMessage }}</p>
      <p v-if="remindMessage" class="hint" data-testid="corp-cert-remind-message">{{ remindMessage }}</p>
      <form class="qbar" data-testid="corp-cert-expire-filters" @submit.prevent="searchExpire">
        <input v-model="expireHolder" placeholder="预警持有人" style="width: 180px" data-testid="corp-cert-expire-holder" />
        <select v-model="expireLevel" data-testid="corp-cert-expire-level" style="width: 120px">
          <option value="">全部级别</option>
          <option value="YELLOW">黄色</option>
          <option value="RED">红色</option>
          <option value="LOCKED">锁定</option>
        </select>
        <select v-model="expireStatus" data-testid="corp-cert-expire-status" style="width: 120px">
          <option value="">全部状态</option>
          <option value="WARNING">预警中</option>
          <option value="RENEW_RESOLVED">已换证</option>
          <option value="EXPIRED_LOCKED">已锁定</option>
        </select>
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="corp-cert-expire-search">筛选</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="corp-cert-expire-reset" @click="resetExpire">重置</button>
      </form>
      <div class="tbl-block">
        <div class="expire-wrap">
          <table data-testid="corp-cert-expire-table">
            <thead>
              <tr>
                <th>持有人</th>
                <th>证件号</th>
                <th>有效期至</th>
                <th>剩余天数</th>
                <th>预警级别</th>
                <th>通知</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="expireLoading">
                <td colspan="8" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!expireRows.length">
                <td colspan="8" style="white-space: normal">
                  <div class="empty" data-testid="corp-cert-expire-empty">
                    <div class="et">{{ expireEmptyTitle }}</div>
                    <div v-if="expireEmptyHint" class="es">{{ expireEmptyHint }}</div>
                  </div>
                </td>
              </tr>
              <tr v-for="row in expireRows" v-else :key="String(row.id)">
                <td>{{ show(row, 'holderName') }}</td>
                <td>{{ show(row, 'certNoMasked') }}</td>
                <td>{{ show(row, 'expireDate') }}</td>
                <td>{{ show(row, 'remainDays') }}</td>
                <td>
                  <span data-testid="corp-cert-level" :style="levelStyle(String(row.level || ''))">{{ levelLabel(String(row.level || '')) }}</span>
                </td>
                <td data-testid="corp-cert-notify">{{ notifyText(row) }}</td>
                <td>{{ expireStatusLabel(String(row.status || '')) }}</td>
                <td>
                  <template v-if="row.status === 'WARNING' || row.status === 'EXPIRED_LOCKED'">
                    <button class="btn btn-txt btn-sm" type="button" data-testid="corp-cert-renew-btn" @click="openRenew(row)">换证</button>
                    <button class="btn btn-txt btn-sm" type="button" data-testid="corp-cert-renew-finish" @click="openRenewFinish(row)">完成换证</button>
                    <button class="btn btn-txt btn-sm" type="button" data-testid="corp-cert-remind-btn" @click="openRemind(row)">催办</button>
                  </template>
                  <span v-else class="hint">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    <div v-if="kind === 'certificate' && levelReady" data-testid="corp-cert-level-panel">
      <div class="sec">查看级别</div>
      <p class="hint">默认全员 L1，不可看原图。L2 按角色编码，水印透明度 0.05 到 0.3。L3 只放管理员或行政白名单。保存后下次查看即按新级别。</p>
      <div class="tbl-block">
        <div class="expire-wrap">
          <table data-testid="corp-cert-level-table">
            <thead>
              <tr>
                <th>级别</th>
                <th>适用范围</th>
                <th>水印样式</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>L1</td>
                <td>默认全员</td>
                <td>不可看原图</td>
              </tr>
              <tr>
                <td>L2</td>
                <td>{{ levelRole || '未配置' }}</td>
                <td>透明度 {{ opacityText }} · {{ positionLabel }}</td>
              </tr>
              <tr>
                <td>L3</td>
                <td>{{ l3Label }}</td>
                <td>明文，禁止下载</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <p class="hint" data-testid="corp-cert-level-current">当前 L2 角色：{{ levelRole || '未配置' }} · 白名单 {{ levelWhitelist.length }} 人 · 透明度 {{ opacityText }} · 位置 {{ positionLabel }}</p>
      <form class="qbar" @submit.prevent="saveLevel">
        <input v-model="levelRole" placeholder="角色编码，如 sys:admin" style="width: 220px" data-testid="corp-cert-level-role" />
        <select v-model="levelValue" style="width: 100px" data-testid="corp-cert-level-select">
          <option value="2">L2</option>
        </select>
        <input v-model.number="levelOpacity" type="range" min="0.05" max="0.3" step="0.01" data-testid="corp-cert-level-opacity-range" />
        <input v-model.number="levelOpacity" type="number" min="0.05" max="0.3" step="0.01" style="width: 80px" data-testid="corp-cert-level-opacity" />
        <select v-model="levelPosition" style="width: 120px" data-testid="corp-cert-level-position">
          <option v-for="item in watermarkPositions" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="corp-cert-level-save">保存级别</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="corp-cert-level-reset" @click="resetLevel">恢复默认</button>
      </form>
      <form class="qbar" @submit.prevent="saveWhitelist">
        <select v-model="l3UserId" style="width: 220px" data-testid="corp-cert-l3-user">
          <option value="">选择白名单用户</option>
          <option v-for="user in users" :key="String(user.id)" :value="String(user.id)">{{ user.nickname || user.username }}</option>
        </select>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="corp-cert-l3-save">保存白名单</button>
      </form>
      <div data-testid="corp-cert-l3-list">
        <p v-if="!levelWhitelist.length" class="hint" data-testid="corp-cert-l3-empty">白名单为空</p>
        <p v-for="id in levelWhitelist" v-else :key="id" class="hint" data-testid="corp-cert-l3-item">
          {{ userLabel(id) }}
          <button class="btn btn-txt btn-sm" type="button" data-testid="corp-cert-l3-remove" @click="removeWhitelist(id)">移除</button>
        </p>
      </div>
      <p v-if="levelMessage" class="hint" data-testid="corp-cert-level-message">{{ levelMessage }}</p>
    </div>
    <div v-if="kind === 'certificate' && !levelReady && levelError" class="empty" data-testid="corp-cert-level-unavailable">
      <div class="et">级别配置暂不可用</div>
      <div class="es">{{ levelError }}</div>
      <button class="btn btn-sec btn-sm" type="button" data-testid="corp-cert-level-retry" @click="loadLevelConfig">重试</button>
    </div>
    <div v-if="kind === 'certificate'" data-testid="corp-cert-audit-panel">
      <div class="sec">查看审计</div>
      <form class="qbar" @submit.prevent="searchAudit">
        <input v-model="auditHolder" placeholder="证件持有人或编号" style="width: 180px" data-testid="corp-cert-audit-holder" />
        <select v-model="auditViewer" style="width: 140px" data-testid="corp-cert-audit-viewer">
          <option value="">全部查看人</option>
          <option v-for="user in users" :key="user.id" :value="user.id">{{ user.nickname || user.username }}</option>
        </select>
        <select v-model="auditLevel" style="width: 110px" data-testid="corp-cert-audit-level">
          <option value="">全部级别</option>
          <option value="1">L1</option>
          <option value="2">L2</option>
          <option value="3">L3</option>
        </select>
        <input v-model="auditFrom" type="date" data-testid="corp-cert-audit-from" />
        <input v-model="auditTo" type="date" data-testid="corp-cert-audit-to" />
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="corp-cert-audit-search">查询</button>
        <button class="btn btn-sec btn-sm" type="button" @click="resetAudit">重置</button>
      </form>
      <p class="hint" data-testid="corp-cert-audit-total">共 {{ auditTotal }} 条</p>
      <p v-if="auditError" class="hint bad" data-testid="corp-cert-audit-error">{{ auditError }}</p>
      <div class="tbl-block">
        <div class="expire-wrap">
          <table data-testid="corp-cert-audit-table">
            <thead>
              <tr>
                <th>查看人</th>
                <th>证件</th>
                <th>级别</th>
                <th>水印</th>
                <th>时长</th>
                <th>IP/设备</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="auditLoading">
                <td colspan="7" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!auditRows.length">
                <td colspan="7" style="white-space: normal">
                  <div class="empty">
                    <div class="et">没有查看记录</div>
                    <div v-if="auditFiltered" class="es" data-testid="corp-cert-audit-empty">当前筛选下没有匹配的查看记录</div>
                  </div>
                </td>
              </tr>
              <tr v-for="row in auditRows" v-else :key="String(row.id)">
                <td>{{ show(row, 'viewerName') }}</td>
                <td>{{ show(row, 'certLabel') }}</td>
                <td>{{ viewLevelLabel(row.viewLevel) }}</td>
                <td>{{ show(row, 'watermarkText') }}</td>
                <td>{{ durationLabel(row.viewDuration) }}</td>
                <td data-testid="corp-cert-audit-ip">{{ ipDevice(row) }}</td>
                <td>{{ show(row, 'createdAt') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="pager" data-testid="corp-cert-audit-pager">
        <span class="pg-total">第 {{ auditPageNo }} / {{ auditPageCount }} 页</span>
        <span class="pg-n" :class="{ dis: auditPageNo <= 1 }" @click="gotoAudit(auditPageNo - 1)">‹</span>
        <span class="pg-n" :class="{ dis: auditPageNo >= auditPageCount }" @click="gotoAudit(auditPageNo + 1)">›</span>
      </div>
      <div class="sec">异常访问</div>
      <div data-testid="corp-cert-risk-report">
        <p class="hint">
          近 1 小时成功查看超过 10 次。异常次数 {{ riskTotal }}。单证第 11 次会被 1035 拦住，不写入本表。
          <button class="btn btn-txt btn-sm" type="button" data-testid="corp-cert-risk-export" @click="openRiskExport">导出报告</button>
        </p>
        <p v-if="riskExportNote" class="hint" data-testid="corp-cert-risk-export-result">{{ riskExportNote }}</p>
        <div class="tbl-block">
          <div class="expire-wrap">
            <table data-testid="corp-cert-risk-table">
              <thead>
                <tr>
                  <th>查看人</th>
                  <th>近 1 小时次数</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!riskUsers.length">
                  <td colspan="2" style="white-space: normal"><div class="empty"><div class="et">当前没有超过 10 次的访问</div></div></td>
                </tr>
                <tr v-for="item in riskUsers" v-else :key="String(item.userId)">
                  <td>{{ item.name || '—' }}</td>
                  <td>{{ item.viewsInLastHour }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    <ProtoDrawer
      :open="detailOpen"
      :title="meta.detailTitle"
      width="520px"
      :data-testid="kind === 'certificate' ? 'corp-cert-detail-drawer' : undefined"
      @close="detailOpen = false"
    >
      <div v-if="detail" class="formrow one">
        <div v-for="item in detailLines" :key="item.label" class="fld">
          <label>{{ item.label }}</label>
          <div>{{ item.value }}</div>
        </div>
      </div>
      <div
        v-if="kind === 'certificate' && viewError"
        class="hint bad"
        data-testid="corp-cert-view-error"
      >
        {{ viewError }}
      </div>
      <div
        v-else-if="kind === 'certificate' && detail"
        class="hint"
        data-testid="corp-cert-watermark-hint"
      >
        水印：{{ detail.watermarkText || '当前查看没有水印文本' }}。本接口不返回原图。
      </div>
      <div v-if="kind === 'certificate'" data-testid="corp-cert-detail-audit">
        <div class="sec">最近查看</div>
        <p v-if="detailAuditLoading" class="hint">加载最近查看</p>
        <p v-else-if="detailAuditError" class="hint">{{ detailAuditError }}</p>
        <p v-else-if="!detailAudits.length" class="hint" data-testid="corp-cert-detail-audit-empty">暂无查看记录</p>
        <p v-for="row in detailAudits" v-else :key="String(row.id)" class="hint" data-testid="corp-cert-detail-audit-row">
          {{ show(row, 'viewerName') }} · {{ viewLevelLabel(row.viewLevel) }} · {{ durationLabel(row.viewDuration) }} · {{ show(row, 'createdAt') }}
        </p>
      </div>
      <div v-if="kind === 'realname'" class="hint">中介人与关联账号暂无。契约没有实名人写入接口。</div>
      <div v-if="kind === 'sim-card' && detail" class="hint">关联账号 {{ linkedCount }} 个。平台账号在下一片接入前这里是空列表。</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="detailOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="digitalOpen" title="数字化率统计" width="480px" @close="digitalOpen = false">
      <div data-testid="corp-cert-digital-modal">
        <div class="formrow one"><div class="fld"><label>应数字化</label><div data-testid="corp-cert-digital-expected">{{ digital.totalExpected }}</div></div></div>
        <div class="formrow one"><div class="fld"><label>已数字化</label><div data-testid="corp-cert-digital-count">{{ digital.digitalizedCount }}</div></div></div>
        <div class="formrow one"><div class="fld"><label>数字化率</label><div data-testid="corp-cert-digital-rate">{{ digitalPercent }}</div></div></div>
        <p v-if="digitalEmpty" class="hint" data-testid="corp-cert-digital-empty">暂无应数字化档案。</p>
        <p v-else class="hint">目标线 95%。未回收档案计入应数字化；已审核且有扫描件计入已数字化。{{ digitalShort ? '未达标' : '达标' }}。</p>
        <p class="hint" data-testid="corp-cert-digital-type-empty">按证件类型的缺口暂无分项，仅展示合计。</p>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="digitalOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="fileOpen" title="原图链接" width="520px" @close="fileOpen = false">
      <div v-if="fileError" class="hint bad" data-testid="corp-cert-file-error">{{ fileError }}</div>
      <div v-else-if="fileResult" data-testid="corp-cert-file-result">
        <p class="hint" data-testid="corp-cert-file-ttl">有效 {{ fileResult.expiresInSeconds }} 秒。禁止下载。</p>
        <p v-if="fileResult.watermark" class="hint" data-testid="corp-cert-file-watermark">
          水印：{{ fileResult.watermark.text || '—' }}
          <span data-testid="corp-cert-file-style"> · 透明度 {{ opacityTextOf(fileResult.watermark.opacity) }} · {{ positionLabelOf(fileResult.watermark.position) }}</span>
        </p>
        <p v-else class="hint" data-testid="corp-cert-file-plain">明文预览，禁止下载。</p>
        <p class="hint" data-testid="corp-cert-file-url">{{ fileResult.signedUrl }}</p>
        <p v-if="filePreview" class="hint" data-testid="corp-cert-file-preview">{{ filePreview }}</p>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="fileOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="formOpen" :title="editingId ? '编辑手机卡' : '新建手机卡'" width="480px" @close="formOpen = false">
      <div class="formrow one"><div class="fld"><label>手机号<i class="req">*</i></label><input v-model="form.phoneNumber" placeholder="11 位，编辑时留空表示不改" /></div></div>
      <div class="formrow one">
        <div class="fld">
          <label>是否主卡<i class="req">*</i></label>
          <select v-model="form.isPrimary">
            <option v-for="item in yesNo" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>运营商<i class="req">*</i></label>
          <select v-model="form.operator">
            <option v-for="item in operators" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>归属人<i class="req">*</i></label>
          <select v-model="form.assignedUserId">
            <option value="">请选择本地用户</option>
            <option v-for="user in users" :key="user.id" :value="user.id">{{ user.nickname || user.username }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>实名人</label>
          <select v-model="form.realnameId">
            <option value="">可不选</option>
            <option v-for="person in persons" :key="person.id" :value="person.id">{{ person.realName }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>状态<i class="req">*</i></label>
          <select v-model="form.status">
            <option v-for="item in simStatus" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one"><div class="fld"><label>套餐</label><input v-model="form.packageName" /></div></div>
      <div class="formrow one"><div class="fld"><label>月租</label><input v-model="form.monthlyRent" /></div></div>
      <div class="formrow one"><div class="fld"><label>ICCID</label><input v-model="form.iccid" /></div></div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="formOpen = false">取消</button>
        <button class="btn btn-pri" type="button" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="certFormOpen" title="录入证件" width="480px" @close="certFormOpen = false">
      <div class="formrow one"><div class="fld"><label>持有人<i class="req">*</i></label><input v-model="certForm.holderName" data-testid="corp-cert-holder" placeholder="姓名" /></div></div>
      <div class="formrow one">
        <div class="fld">
          <label>证件类型<i class="req">*</i></label>
          <select v-model="certForm.certType" data-testid="corp-cert-type">
            <option value="IDCARD">身份证</option>
            <option value="PASSPORT">护照</option>
            <option value="OTHER">其他</option>
          </select>
        </div>
      </div>
      <div class="formrow one"><div class="fld"><label>证件号<i class="req">*</i></label><input v-model="certForm.certNoPlain" data-testid="corp-cert-no" placeholder="至少 8 位，接口只回脱敏值" /></div></div>
      <div class="formrow one"><div class="fld"><label>签发日期<i class="req">*</i></label><input v-model="certForm.issueDate" type="date" data-testid="corp-cert-issue" /></div></div>
      <div class="formrow one"><div class="fld"><label>有效期至<i class="req">*</i></label><input v-model="certForm.expireDate" type="date" data-testid="corp-cert-expire-date" /></div></div>
      <div class="formrow one"><div class="fld"><label>扫描件标识<i class="req">*</i></label><input v-model="certForm.fileKey" data-testid="corp-cert-file-key" /></div></div>
      <div class="formrow one">
        <div class="fld">
          <label>原件</label>
          <input type="file" accept=".txt,.pdf,.png,.jpg,.jpeg" data-testid="corp-cert-original-file" @change="onOriginalFile" />
        </div>
      </div>
      <p v-if="ocrNote" class="hint" data-testid="corp-cert-ocr">{{ ocrNote }}</p>
      <div class="hint">原件落在服务端目录。再次上传生成新版本，不覆盖已归档文件。识别失败可手工填写。不选文件时仍可用扫描件标识。</div>
      <div class="acts" style="margin-bottom: 8px">
        <button class="btn btn-sec btn-sm" type="button" data-testid="corp-cert-ocr-confirm" :disabled="ocrBusy" @click="confirmOriginal">确认识别</button>
      </div>
      <div class="hint">提交后为待审。审核生效后才参与到期扫描。本期不返回原图。</div>
      <div v-if="certFormError" class="hint bad" data-testid="corp-cert-form-error">{{ certFormError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="certFormOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-cert-save" :disabled="certSaving" @click="saveCert">{{ certSaving ? '提交中…' : '提交审核' }}</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="reviewOpen" title="审核证件" width="420px" @close="reviewOpen = false">
      <div class="formrow one">
        <div class="fld"><label>持有人</label><div>{{ reviewRow?.holderName || '—' }}</div></div>
        <div class="fld"><label>证件号</label><div>{{ reviewRow?.certNoMasked || '—' }}</div></div>
        <div class="fld"><label>有效期至</label><div>{{ reviewRow?.expireDate || '—' }}</div></div>
      </div>
      <div v-if="reviewError" class="hint bad">{{ reviewError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="reviewOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-cert-review-approve" :disabled="reviewSaving" @click="approveCert">通过</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="renewOpen" title="换证" width="480px" @close="renewOpen = false">
      <div class="formrow one">
        <div class="fld"><label>持有人</label><div data-testid="corp-cert-renew-holder">{{ renewTarget?.holderName || '—' }}</div></div>
        <div class="fld"><label>证件类型</label><div>{{ typeLabel(String(renewTarget?.certType || '')) }}</div></div>
        <div class="fld"><label>原有效期</label><div>{{ renewTarget?.expireDate || '—' }}</div></div>
        <div class="fld"><label>当前预警</label><div>{{ levelLabel(String(renewTarget?.level || '')) }}</div></div>
      </div>
      <div class="formrow one"><div class="fld"><label>新证件号<i class="req">*</i></label><input v-model="renewForm.certNoPlain" data-testid="corp-cert-renew-no" placeholder="至少 8 位，接口只回脱敏值" /></div></div>
      <div class="formrow one"><div class="fld"><label>签发日期<i class="req">*</i></label><input v-model="renewForm.issueDate" type="date" data-testid="corp-cert-renew-issue" /></div></div>
      <div class="formrow one"><div class="fld"><label>新有效期<i class="req">*</i></label><input v-model="renewForm.expireDate" type="date" data-testid="corp-cert-renew-expire" /></div></div>
      <div class="formrow one"><div class="fld"><label>扫描件标识<i class="req">*</i></label><input v-model="renewForm.fileKey" data-testid="corp-cert-renew-file" /></div></div>
      <div class="formrow one"><div class="fld"><label>备注</label><input v-model="renewForm.remark" data-testid="corp-cert-renew-remark" /></div></div>
      <div class="hint">新证提交后为待审。审核生效后点「完成换证」：旧证保留为已回收历史，黄/红/锁定预警解除，工作台待办完成。新有效期须晚于旧证，且超出 30 天。</div>
      <div v-if="renewError" class="hint bad" data-testid="corp-cert-renew-error">{{ renewError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="renewOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-cert-renew-save" :disabled="renewSaving" @click="saveRenew">{{ renewSaving ? '提交中…' : '提交新证' }}</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="renewFinishOpen" title="完成换证" width="440px" @close="renewFinishOpen = false">
      <div class="formrow one">
        <div class="fld"><label>持有人</label><div>{{ renewFinishTarget?.holderName || '—' }}</div></div>
        <div class="fld"><label>原有效期</label><div>{{ renewFinishTarget?.expireDate || '—' }}</div></div>
        <div class="fld"><label>新证有效期</label><div data-testid="corp-cert-renew-new-expire">{{ renewCandidate?.expireDate || '—' }}</div></div>
      </div>
      <div class="hint">确认后旧证归档为历史（已回收），本条预警变为已换证，工作台中对应待办完成。</div>
      <div v-if="renewFinishError" class="hint bad" data-testid="corp-cert-renew-finish-error">{{ renewFinishError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="renewFinishOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-cert-renew-confirm" :disabled="renewFinishSaving || !renewCandidate" @click="confirmRenew">{{ renewFinishSaving ? '提交中…' : '确认换证' }}</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="remindOpen" title="催办" width="360px" @close="remindOpen = false">
      <div class="hint">选择渠道后写入工作台待办。不选渠道时工作台和钉钉都记一笔。重复催办会再写一条，不占用扫描的同级不重复限额。钉钉只记渠道，不外发。</div>
      <div class="formrow one">
        <div class="fld">
          <label>渠道</label>
          <select v-model="remindChannel" data-testid="corp-cert-remind-channel">
            <option value="">双渠道</option>
            <option value="APP">工作台</option>
            <option value="DINGTALK">钉钉</option>
          </select>
        </div>
      </div>
      <p v-if="remindError" class="hint bad">{{ remindError }}</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="remindOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-cert-remind-confirm" :disabled="remindSaving" @click="confirmRemind">{{ remindSaving ? '提交中…' : '确认催办' }}</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="riskExportOpen" title="导出异常访问报告" width="420px" @close="riskExportOpen = false">
      <p class="hint" data-testid="corp-cert-risk-export-modal">
        {{
          riskUsers.length
            ? `将导出 ${riskUsers.length} 名高频查看人。仅生成本地说明，不外发。`
            : '当前没有可导出的异常访问。确认后仍只生成本地说明，不外发。'
        }}
      </p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="riskExportOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-cert-risk-export-confirm" @click="confirmRiskExport">确认导出</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="scanOpen" title="扫描到期" width="420px" @close="scanOpen = false">
      <div class="hint">按今日扫描已生效证件：剩余 30 天黄色、7 天红色、当天锁定，并写入工作台提醒。同一级别不重复推送。</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="scanOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-cert-scan-confirm" :disabled="scanSaving" @click="confirmScan">{{ scanSaving ? '扫描中…' : '确认扫描' }}</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { http, errorMessage } from '../../api/http'
import { asList, asTotal } from '../../api/read'

type Row = Record<string, unknown>
type Opt = { value: string; label: string }
type WatermarkStyle = { opacity: number; position: string }

const watermarkPositions: Opt[] = [
  { value: 'center', label: '居中' },
  { value: 'top-left', label: '左上' },
  { value: 'top-right', label: '右上' },
  { value: 'bottom-left', label: '左下' },
  { value: 'bottom-right', label: '右下' },
  { value: 'top', label: '上' },
  { value: 'bottom', label: '下' },
  { value: 'left', label: '左' },
  { value: 'right', label: '右' },
]

const route = useRoute()
const kind = computed(() => String(route.params.kind || 'company'))
const rows = ref<Row[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const creditCode = ref('')
const industry = ref('')
const idType = ref('')
const operator = ref('')
const realnameId = ref('')
const status = ref('')
const phoneHint = ref('')
const idTypes = ref<Opt[]>([
  { value: 'ID_CARD', label: '身份证' },
  { value: 'PASSPORT', label: '护照' },
  { value: 'HK_MACAO', label: '港澳通行证' },
  { value: 'TAIWAN', label: '台湾通行证' },
])
const fallbackIndustry: Opt[] = [
  { value: 'SPORT', label: '体育' },
  { value: 'ESPORTS', label: '电竞' },
  { value: 'MEDIA', label: '传媒' },
  { value: 'OTHER', label: '其他' },
]
const industries = ref<Opt[]>(fallbackIndustry)
const loading = ref(false)
const error = ref('')
const detailOpen = ref(false)
const detail = ref<Row | null>(null)
const viewError = ref('')
const detailAudits = ref<Row[]>([])
const detailAuditError = ref('')
const detailAuditLoading = ref(false)
const digitalOpen = ref(false)
const digital = reactive({ totalExpected: 0, digitalizedCount: 0, digitalizedRate: 1 })
const digitalReady = ref(false)
const digitalError = ref('')
const fileOpen = ref(false)
const fileError = ref('')
const filePreview = ref('')
const fileResult = ref<{
  expiresInSeconds?: number
  signedUrl?: string
  watermark?: { text?: string; opacity?: number; position?: string }
} | null>(null)
const levelReady = ref(false)
const levelError = ref('')
const levelRole = ref('')
const levelValue = ref('2')
const levelWhitelist = ref<number[]>([])
const levelOpacity = ref(0.12)
const levelPosition = ref('bottom-right')
const levelMessage = ref('')
const l3UserId = ref('')
const digitalPercent = computed(() => `${(Number(digital.digitalizedRate || 0) * 100).toFixed(2)}%`)
const digitalEmpty = computed(() => digitalReady.value && digital.totalExpected === 0)
const digitalShort = computed(() => digitalReady.value && !digitalEmpty.value && Number(digital.digitalizedRate) < 0.95)
const listFiltered = computed(() => !!(keyword.value.trim() || status.value))
const listEmptyTitle = computed(() => {
  if (kind.value === 'certificate' && listFiltered.value) return '当前筛选下没有证件'
  return meta.value.empty
})
const listEmptyHint = computed(() => {
  if (kind.value === 'certificate' && listFiltered.value) return '换一个持有人或状态，或重置筛选。'
  return meta.value.emptyHint
})
const certFormOpen = ref(false)
const certSaving = ref(false)
const certFormError = ref('')
const certForm = reactive({
  holderName: '',
  certType: 'IDCARD',
  certNoPlain: '',
  issueDate: '2020-01-01',
  expireDate: '',
  fileKey: 'local/cert/upload',
})
const originalKey = ref('')
const ocrNote = ref('')
const ocrBusy = ref(false)
const originalNote = ref('')
const reviewOpen = ref(false)
const reviewSaving = ref(false)
const reviewError = ref('')
const reviewRow = ref<Row | null>(null)
const scanOpen = ref(false)
const scanSaving = ref(false)
const scanMessage = ref('')
const renewOpen = ref(false)
const renewSaving = ref(false)
const renewError = ref('')
const renewMessage = ref('')
const renewTarget = ref<Row | null>(null)
const renewForm = reactive({
  certNoPlain: '',
  issueDate: '2024-01-01',
  expireDate: '',
  fileKey: 'local/cert/renew',
  remark: '',
})
const renewFinishOpen = ref(false)
const renewFinishSaving = ref(false)
const renewFinishError = ref('')
const renewFinishTarget = ref<Row | null>(null)
const renewCandidate = ref<Row | null>(null)
const expireRows = ref<Row[]>([])
const expireLoading = ref(false)
const expireError = ref('')
const expireHolder = ref('')
const expireLevel = ref('')
const expireStatus = ref('')
const expireStats = reactive({ yellow: 0, red: 0, locked: 0, renewed: 0 })
const expireFiltered = computed(() => !!(expireHolder.value.trim() || expireLevel.value || expireStatus.value))
const expireEmptyTitle = computed(() => {
  if (expireError.value) return expireError.value
  if (expireFiltered.value) return '没有符合筛选的到期预警'
  return '当前无到期预警'
})
const expireEmptyHint = computed(() => (expireFiltered.value ? '换一个预警级别或状态，或重置筛选。' : ''))
const remindOpen = ref(false)
const remindSaving = ref(false)
const remindError = ref('')
const remindMessage = ref('')
const remindChannel = ref('')
const remindTarget = ref<Row | null>(null)
const auditHolder = ref('')
const auditViewer = ref('')
const auditLevel = ref('')
const auditFrom = ref('')
const auditTo = ref('')
const auditPageNo = ref(1)
const auditPageSize = 20
const auditRows = ref<Row[]>([])
const auditTotal = ref(0)
const auditLoading = ref(false)
const auditError = ref('')
const auditPageCount = computed(() => Math.max(1, Math.ceil(auditTotal.value / auditPageSize)))
const auditFiltered = computed(() =>
  Boolean(auditHolder.value.trim() || auditViewer.value || auditLevel.value || auditFrom.value || auditTo.value),
)
const opacityText = computed(() => opacityTextOf(levelOpacity.value))
const positionLabel = computed(() => positionLabelOf(levelPosition.value))
const l3Label = computed(() => {
  if (!levelWhitelist.value.length) return '未配置'
  const names = levelWhitelist.value.map((id) => {
    const user = users.value.find((item) => Number(item.id) === id)
    return user?.nickname || user?.username || String(id)
  })
  return `白名单 ${names.join('、')}`
})
const riskUsers = ref<{ userId: number; name: string; viewsInLastHour: number }[]>([])
const riskTotal = ref(0)
const riskExportOpen = ref(false)
const riskExportNote = ref('')
const formOpen = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formError = ref('')
const users = ref<{ id: string; username: string; nickname: string }[]>([])
const persons = ref<{ id: number; realName: string }[]>([])
const yesNo = ref<Opt[]>([])
const operators = ref<Opt[]>([])
const simStatus = ref<Opt[]>([])
const form = reactive({
  phoneNumber: '',
  isPrimary: 'NO',
  operator: 'MOBILE',
  assignedUserId: '',
  realnameId: '',
  status: 'IN_USE',
  packageName: '',
  monthlyRent: '',
  iccid: '',
})

const specs: Record<string, {
  title: string
  sub: string
  placeholder: string
  empty: string
  emptyHint: string
  hint: string
  detailTitle: string
  columns: string[]
  keys: string[]
  statusOptions: Opt[]
}> = {
  company: {
    title: '公司管理',
    sub: 'CORP-R · 只查询 · GET /corp/resource/company/page',
    placeholder: '公司名称',
    empty: '没有公司',
    emptyHint: '契约只有分页和详情，这里不能新建。',
    hint: '公司、实名人按契约只做查询。信用代码和法人来自详情，不提供写入。',
    detailTitle: '公司详情',
    columns: ['公司', '信用代码', '行业', '法人', '容量', '已注册', '剩余', '状态'],
    keys: ['companyName', 'creditCode', 'industry', 'legalName', 'mpCapacityStandard', 'mpRegisteredCount', 'mpRemaining', 'status'],
    statusOptions: [
      { value: 'ENABLED', label: '启用' },
      { value: 'DISABLED', label: '停用' },
    ],
  },
  realname: {
    title: '实名人管理',
    sub: 'CORP-R · 姓名、证件号、手机由接口脱敏',
    placeholder: '姓名',
    empty: '没有实名人',
    emptyHint: '契约只有分页和详情。',
    hint: '列表不返回证件号和手机明文。没有新建接口。',
    detailTitle: '实名人详情',
    columns: ['姓名', '证件类型', '证件号', '手机', '状态'],
    keys: ['realName', 'idType', 'idCardMasked', 'phoneMasked', 'status'],
    statusOptions: [
      { value: 'ENABLED', label: '启用' },
      { value: 'DISABLED', label: '停用' },
    ],
  },
  'sim-card': {
    title: '手机卡管理',
    sub: 'CORP-R · 号码脱敏 · 归属人只选本地用户',
    placeholder: '完整手机号',
    empty: '没有手机卡',
    emptyHint: '可以新建。号码和 ICCID 只以脱敏值返回。',
    hint: 'POST/PUT /corp/resource/sim-card。关联账号等平台账号片接入。',
    detailTitle: '手机卡详情',
    columns: ['号码', '实名人', '运营商', '归属人', '月租', '状态'],
    keys: ['phoneNumber', 'realNameMasked', 'operator', 'assignedUserName', 'monthlyRent', 'status'],
    statusOptions: [],
  },
  certificate: {
    title: '证件管理',
    sub: 'CORP-R · 索引分页 · 数字化率 · 到期预警 · 分级原图',
    placeholder: '持有人',
    empty: '没有证件档案',
    emptyHint: '可以录入。审核生效后参与到期扫描。',
    hint: '录入 POST /cert/archive/upload，审核 PUT /cert/archive/{id}/review，扫描 POST /cert/expire/scan，催办 PUT /cert/expire/{id}/remind。查看审计 GET /cert/security/view-logs。证件号只显示脱敏值。同一证件 1 小时内第 11 次查看返回 1035。',
    detailTitle: '证件查看',
    columns: ['持有人', '类型', '证件号', '有效期', '状态'],
    keys: ['holderName', 'certType', 'certNoMasked', 'expireDate', 'status'],
    statusOptions: [
      { value: 'PENDING_REVIEW', label: '待审' },
      { value: 'EFFECTIVE', label: '生效' },
      { value: 'EXPIRING', label: '即将到期' },
      { value: 'EXPIRED', label: '已过期' },
      { value: 'RECYCLED', label: '已回收' },
    ],
  },
}

const meta = computed(() => specs[kind.value] || specs.company)
const statusChoices = computed(() => (kind.value === 'sim-card' ? simStatus.value : meta.value.statusOptions))
const hasFilter = computed(() =>
  Boolean(
    keyword.value.trim() ||
      creditCode.value.trim() ||
      industry.value ||
      idType.value ||
      operator.value ||
      realnameId.value ||
      status.value,
  ),
)
const emptyTitle = computed(() => {
  if (phoneHint.value) return phoneHint.value
  if (hasFilter.value) return '没有符合筛选的记录'
  return meta.value.empty
})
const emptyHintText = computed(() => {
  if (phoneHint.value) return '号码按完整手机号精确匹配，不支持片段。'
  if (kind.value === 'company' && industry.value) return '这个行业下没有公司。换一项，或点重置看全部。'
  if (hasFilter.value) return '换个条件，或点重置看全部。'
  return meta.value.emptyHint
})
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pageList = computed(() => {
  const end = Math.min(pageCount.value, Math.max(pageNo.value + 2, 5))
  const start = Math.max(1, end - 4)
  const list: number[] = []
  for (let i = start; i <= Math.min(pageCount.value, start + 4); i += 1) list.push(i)
  return list
})
const linkedCount = computed(() => {
  const list = detail.value?.linkedAccounts
  return Array.isArray(list) ? list.length : 0
})
const detailLines = computed(() => {
  if (!detail.value) return []
  return meta.value.keys.map((key) => ({ label: labelOf(key), value: show(detail.value || {}, key) }))
})

const labels: Record<string, string> = {
  companyName: '公司',
  creditCode: '信用代码',
  industry: '行业',
  legalName: '法人',
  mpCapacityStandard: '容量',
  mpRegisteredCount: '已注册',
  mpRemaining: '剩余',
  status: '状态',
  realName: '姓名',
  idType: '证件类型',
  idCardMasked: '证件号',
  phoneMasked: '手机',
  phoneNumber: '号码',
  realNameMasked: '实名人',
  operator: '运营商',
  assignedUserName: '归属人',
  monthlyRent: '月租',
  holderName: '持有人',
  certType: '类型',
  certNoMasked: '证件号',
  expireDate: '有效期',
}

function labelOf(key: string) {
  return labels[key] || key
}

function show(row: Row, key: string) {
  const value = row[key]
  if (value === undefined || value === null || value === '') return '—'
  if (key === 'status') return statusLabel(String(value))
  if (key === 'industry') return industries.value.find((item) => item.value === value)?.label || String(value)
  if (key === 'operator') return operators.value.find((item) => item.value === value)?.label || String(value)
  if (key === 'idType' || key === 'certType') return typeLabel(String(value))
  return String(value)
}

function statusLabel(value: string) {
  const found = [...meta.value.statusOptions, ...simStatus.value].find((item) => item.value === value)
  if (found) return found.label
  if (value === 'ENABLED') return '启用'
  if (value === 'DISABLED') return '停用'
  return value
}

function levelLabel(value: string) {
  if (value === 'YELLOW') return '黄色'
  if (value === 'RED') return '红色'
  if (value === 'LOCKED') return '锁定'
  return value || '—'
}

function levelStyle(value: string) {
  if (value === 'YELLOW') return 'color:#a16207;font-weight:600'
  if (value === 'RED') return 'color:#b91c1c;font-weight:600'
  if (value === 'LOCKED') return 'color:#7f1d1d;font-weight:700'
  return ''
}

function expireStatusLabel(value: string) {
  if (value === 'WARNING') return '预警中'
  if (value === 'EXPIRED_LOCKED') return '已锁定'
  if (value === 'RENEW_RESOLVED') return '已换证'
  return value || '—'
}

function openCertCreate() {
  certForm.holderName = ''
  certForm.certType = 'IDCARD'
  certForm.certNoPlain = ''
  certForm.issueDate = '2020-01-01'
  certForm.expireDate = ''
  certForm.fileKey = 'local/cert/upload'
  certFormError.value = ''
  originalKey.value = ''
  ocrNote.value = ''
  certFormOpen.value = true
}

function applyOcrFields(fields: Record<string, string>) {
  if (fields.holderName) certForm.holderName = fields.holderName
  if (fields.certNo) certForm.certNoPlain = fields.certNo
  if (fields.issueDate) certForm.issueDate = fields.issueDate
  if (fields.expireDate) certForm.expireDate = fields.expireDate
}

async function onOriginalFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files && input.files[0] ? input.files[0] : null
  if (!file) return
  if (file.size > 20 * 1024 * 1024) {
    certFormError.value = '原件不能超过 20MB'
    return
  }
  ocrBusy.value = true
  certFormError.value = ''
  try {
    const body = new FormData()
    body.append('file', file)
    const res = await http.post('/cert/archive/original', body)
    const data = (res.data?.data || {}) as {
      fileKey?: string
      ocrResult?: { recognizeStatus?: string; recognizedFields?: Record<string, string> }
    }
    originalKey.value = String(data.fileKey || '')
    certForm.fileKey = originalKey.value || certForm.fileKey
    const ocr = data.ocrResult || {}
    const fields = ocr.recognizedFields || {}
    applyOcrFields(fields)
    if (ocr.recognizeStatus === 'PENDING_CONFIRM') {
      ocrNote.value = `OCR 待确认 · ${fields.holderName || '未命名'}`
    } else {
      ocrNote.value = 'OCR 未识别，请手工填写'
    }
  } catch (e: unknown) {
    ocrNote.value = ''
    certFormError.value = errorMessage(e)
  } finally {
    ocrBusy.value = false
  }
}

async function confirmOriginal() {
  if (!originalKey.value) {
    ocrNote.value = '请先上传原件'
    return
  }
  ocrBusy.value = true
  try {
    await http.post('/cert/archive/original/confirm', {
      fileKey: originalKey.value,
      action: 'CONFIRM',
      recognizedFields: {
        holderName: certForm.holderName.trim(),
        certNo: certForm.certNoPlain.trim(),
        issueDate: certForm.issueDate,
        expireDate: certForm.expireDate,
      },
    })
    ocrNote.value = '已确认'
  } catch (e: unknown) {
    ocrNote.value = errorMessage(e)
  } finally {
    ocrBusy.value = false
  }
}

async function saveCert() {
  certSaving.value = true
  certFormError.value = ''
  try {
    const res = await http.post('/cert/archive/upload', {
      holderName: certForm.holderName.trim(),
      certType: certForm.certType,
      certNoPlain: certForm.certNoPlain.trim(),
      fileKey: certForm.fileKey.trim(),
      issueDate: certForm.issueDate,
      expireDate: certForm.expireDate,
    })
    const id = Number(res.data?.data?.id || 0)
    if (originalKey.value && id) {
      const bound = await http.post('/cert/archive/original/bind', {
        fileKey: originalKey.value,
        certId: id,
      })
      const version = Number(bound.data?.data?.version || 0)
      originalNote.value = `原件 v${version} 已归档，历史版本保留`
    }
    certFormOpen.value = false
    await load()
    await loadDigital()
  } catch (e: unknown) {
    certFormError.value = errorMessage(e)
  } finally {
    certSaving.value = false
  }
}

function openReview(row: Row) {
  reviewRow.value = row
  reviewError.value = ''
  reviewOpen.value = true
}

async function approveCert() {
  const id = reviewRow.value?.id
  if (id === undefined || id === null || id === '') {
    reviewError.value = '缺少证件 id'
    return
  }
  reviewSaving.value = true
  reviewError.value = ''
  try {
    await http.put(`/cert/archive/${id}/review`, { action: 'APPROVE' })
    reviewOpen.value = false
    await load()
    await loadDigital()
  } catch (e: unknown) {
    reviewError.value = errorMessage(e)
  } finally {
    reviewSaving.value = false
  }
}

function openScan() {
  scanOpen.value = true
}

function openRemind(row: Row) {
  remindTarget.value = row
  remindChannel.value = 'APP'
  remindError.value = ''
  remindOpen.value = true
}

async function confirmRemind() {
  const target = remindTarget.value
  if (!target) {
    remindError.value = '缺少预警记录'
    return
  }
  remindSaving.value = true
  remindError.value = ''
  try {
    const body: Record<string, string> = {}
    if (remindChannel.value) body.remindChannel = remindChannel.value
    const res = await http.put(`/cert/expire/${target.id}/remind`, body)
    const at = String(res.data?.data?.remindedAt || '')
    remindOpen.value = false
    remindMessage.value = `已催办 ${at}。工作台已写入待办。重复催办会再写一条。钉钉未外发。`
    await loadExpire()
  } catch (e: unknown) {
    remindError.value = bizError(e)
  } finally {
    remindSaving.value = false
  }
}

function viewLevelLabel(value: unknown) {
  const level = Number(value)
  if (level === 1 || level === 2 || level === 3) return `L${level}`
  return '—'
}

function opacityTextOf(value: unknown) {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return '0.12'
  return amount.toFixed(2)
}

function positionLabelOf(value: unknown) {
  const code = String(value || '')
  return watermarkPositions.find((item) => item.value === code)?.label || code || '右下'
}

function roundedOpacity(value: number) {
  return Math.round(value * 100) / 100
}

function styleError(opacity: number, position: string) {
  if (!(opacity >= 0.05 && opacity <= 0.3)) return '水印透明度须在 0.05 到 0.3'
  if (!watermarkPositions.some((item) => item.value === position)) return '水印位置不合法'
  return ''
}

function ipDevice(row: Row) {
  const ip = String(row.ip || '').trim()
  const device = String(row.device || '').trim()
  const short = device.length > 48 ? `${device.slice(0, 48)}…` : device
  if (!ip && !short) return '—'
  if (!short) return ip
  if (!ip) return short
  return `${ip} / ${short}`
}

function durationLabel(value: unknown) {
  const seconds = Number(value)
  if (!Number.isFinite(seconds) || seconds < 0) return '—'
  const whole = Math.floor(seconds)
  if (whole < 60) return `${whole} 秒`
  return `${Math.floor(whole / 60)} 分 ${whole % 60} 秒`
}

async function loadAuditUsers() {
  if (users.value.length) return
  try {
    const res = await http.get('/system/user/page', { params: { pageNo: 1, pageSize: 100 } })
    users.value = asList(res.data?.data) as unknown as { id: string; username: string; nickname: string }[]
  } catch {
    users.value = []
  }
}

async function loadRisk() {
  const res = await http.get('/cert/security/risk-report')
  const data = res.data?.data || {}
  riskUsers.value = Array.isArray(data.highFrequencyUsers) ? data.highFrequencyUsers : []
  riskTotal.value = Number(data.abnormalTotal || 0)
}

function userLabel(id: number) {
  const user = users.value.find((item) => Number(item.id) === id)
  return user?.nickname || user?.username || String(id)
}

function levelRules() {
  const role = levelRole.value.trim()
  return role ? [{ target: 'ROLE', targetCode: role, viewLevel: 2 }] : []
}

function openRiskExport() {
  riskExportOpen.value = true
}

function confirmRiskExport() {
  const count = riskUsers.value.length
  const names = riskUsers.value.map((item) => item.name || '未命名').join('、')
  riskExportNote.value = count
    ? `已生成异常访问报告（本地桩，未外发）。共 ${count} 人：${names}`
    : '已生成异常访问报告（本地桩，未外发）。共 0 人。'
  riskExportOpen.value = false
}

async function loadAudit() {
  auditLoading.value = true
  auditError.value = ''
  try {
    if ((auditFrom.value && !auditTo.value) || (!auditFrom.value && auditTo.value)) {
      auditRows.value = []
      auditTotal.value = 0
      auditError.value = '请同时填写开始和结束日期'
      return
    }
    if (auditFrom.value && auditTo.value && auditFrom.value > auditTo.value) {
      auditRows.value = []
      auditTotal.value = 0
      auditError.value = '开始日期不能晚于结束日期'
      return
    }
    const params: Record<string, unknown> = { pageNo: auditPageNo.value, pageSize: auditPageSize }
    const holder = auditHolder.value.trim()
    if (holder) {
      if (/^\d+$/.test(holder)) {
        params.certId = Number(holder)
      } else {
        const found = await http.get('/corp/resource/certificate/page', {
          params: { pageNo: 1, pageSize: 20, holderName: holder },
        })
        const list = asList(found.data?.data)
        const exact = list.find((item) => String(item.holderName) === holder) || list[0]
        if (!exact) {
          auditRows.value = []
          auditTotal.value = 0
          auditError.value = '没有匹配的证件'
          await loadRisk()
          return
        }
        params.certId = Number(exact.id)
      }
    }
    if (auditViewer.value) params.viewerUserId = Number(auditViewer.value)
    if (auditLevel.value) params.viewLevel = Number(auditLevel.value)
    if (auditFrom.value && auditTo.value) {
      params.timeRange = [`${auditFrom.value} 00:00:00`, `${auditTo.value} 23:59:59`]
    }
    const res = await http.get('/cert/security/view-logs', {
      params,
      paramsSerializer: { indexes: null },
    })
    const data = res.data?.data
    auditRows.value = asList(data)
    auditTotal.value = asTotal(data, auditRows.value.length)
    await loadRisk()
  } catch (e: unknown) {
    auditRows.value = []
    auditTotal.value = 0
    auditError.value = bizError(e)
  } finally {
    auditLoading.value = false
  }
}

function searchAudit() {
  auditPageNo.value = 1
  return loadAudit()
}

function gotoAudit(page: number) {
  if (page < 1 || page > auditPageCount.value || page === auditPageNo.value) return
  auditPageNo.value = page
  loadAudit()
}

function resetAudit() {
  auditHolder.value = ''
  auditViewer.value = ''
  auditLevel.value = ''
  auditFrom.value = ''
  auditTo.value = ''
  searchAudit()
}

function bizError(error: unknown) {
  if (error && typeof error === 'object' && 'code' in error) {
    const body = error as { code?: number; msg?: string }
    if (typeof body.code === 'number' && body.code !== 0) {
      return `${body.code} ${body.msg || ''}`.trim()
    }
  }
  return errorMessage(error)
}

function openRenew(row: Row) {
  renewTarget.value = row
  renewForm.certNoPlain = ''
  renewForm.issueDate = '2024-01-01'
  renewForm.expireDate = ''
  renewForm.fileKey = 'local/cert/renew'
  renewForm.remark = ''
  renewError.value = ''
  renewOpen.value = true
}

async function saveRenew() {
  const target = renewTarget.value
  if (!target) {
    renewError.value = '缺少预警记录'
    return
  }
  renewSaving.value = true
  renewError.value = ''
  try {
    await http.post('/cert/archive/upload', {
      holderName: String(target.holderName || '').trim(),
      certType: String(target.certType || 'IDCARD'),
      certNoPlain: renewForm.certNoPlain.trim(),
      fileKey: renewForm.fileKey.trim(),
      issueDate: renewForm.issueDate,
      expireDate: renewForm.expireDate,
    })
    renewOpen.value = false
    renewMessage.value = '新证已提交待审。审核生效后点「完成换证」，旧证会保留为历史。'
    await load()
  } catch (e: unknown) {
    renewError.value = bizError(e)
  } finally {
    renewSaving.value = false
  }
}

async function openRenewFinish(row: Row) {
  renewFinishTarget.value = row
  renewCandidate.value = null
  renewFinishError.value = ''
  renewFinishOpen.value = true
  try {
    const res = await http.get('/corp/resource/certificate/page', {
      params: { pageNo: 1, pageSize: 50, holderName: String(row.holderName || '') },
    })
    const list = asList(res.data?.data)
    const found = list.find(
      (item) =>
        item.holderName === row.holderName &&
        item.certType === row.certType &&
        item.status === 'EFFECTIVE' &&
        Number(item.id) !== Number(row.certId),
    )
    renewCandidate.value = found || null
    if (!found) renewFinishError.value = '请先提交新证并审核生效'
  } catch (e: unknown) {
    renewFinishError.value = bizError(e)
  }
}

async function confirmRenew() {
  const target = renewFinishTarget.value
  const candidate = renewCandidate.value
  if (!target || !candidate) {
    renewFinishError.value = '请先提交新证并审核生效'
    return
  }
  renewFinishSaving.value = true
  renewFinishError.value = ''
  try {
    await http.put(`/cert/expire/${target.id}/renew`, {
      newCertId: Number(candidate.id),
      remark: renewForm.remark.trim() || undefined,
    })
    renewFinishOpen.value = false
    renewMessage.value = '换证完成：旧证已归档为历史，预警已解除，工作台待办已完成。'
    await Promise.all([load(), loadExpire()])
  } catch (e: unknown) {
    renewFinishError.value = bizError(e)
  } finally {
    renewFinishSaving.value = false
  }
}

async function loadExpire() {
  expireLoading.value = true
  expireError.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    const text = expireHolder.value.trim()
    if (text) params.holderName = text
    if (expireLevel.value) params.level = expireLevel.value
    if (expireStatus.value) params.status = expireStatus.value
    const [listRes, statsRes] = await Promise.all([
      http.get('/cert/expire/list', { params }),
      http.get('/cert/expire/stats'),
    ])
    const data = listRes.data?.data
    expireRows.value = asList(data)
    const stats = statsRes.data?.data || {}
    expireStats.yellow = Number(stats.yellowCount || 0)
    expireStats.red = Number(stats.redCount || 0)
    expireStats.locked = Number(stats.lockedCount || 0)
    expireStats.renewed = Number(stats.renewedThisMonth || 0)
  } catch (e: unknown) {
    expireRows.value = []
    expireError.value = errorMessage(e)
  } finally {
    expireLoading.value = false
  }
}

function searchExpire() {
  loadExpire()
}

function resetExpire() {
  expireHolder.value = ''
  expireLevel.value = ''
  expireStatus.value = ''
  loadExpire()
}

function notifyText(row: Row) {
  const summary = String(row.notifiedSummary || '尚未通知')
  const at = String(row.lastRemindedAt || '')
  if (at) return `${summary} · 催办 ${at}`
  return summary
}

async function confirmScan() {
  scanSaving.value = true
  try {
    const res = await http.post('/cert/expire/scan')
    scanMessage.value = String(res.data?.data?.message || '扫描完成')
    scanOpen.value = false
    await Promise.all([load(), loadExpire()])
  } catch (e: unknown) {
    scanMessage.value = errorMessage(e)
    scanOpen.value = false
  } finally {
    scanSaving.value = false
  }
}

function typeLabel(value: string) {
  const map: Record<string, string> = {
    ID_CARD: '身份证',
    PASSPORT: '护照',
    HK_MACAO: '港澳通行证',
    TAIWAN: '台湾通行证',
    IDCARD: '身份证',
    OTHER: '其他',
  }
  return map[value] || value
}

function params() {
  phoneHint.value = ''
  const query: Record<string, string | number> = { pageNo: pageNo.value, pageSize: pageSize.value }
  const text = keyword.value.trim()
  if (text) {
    if (kind.value === 'company') query.companyName = text
    if (kind.value === 'realname') query.realName = text
    if (kind.value === 'sim-card') {
      if (!/^1\d{10}$/.test(text)) phoneHint.value = '请输入完整 11 位手机号'
      else query.phoneNumber = text
    }
    if (kind.value === 'certificate') query.holderName = text
  }
  const code = creditCode.value.trim()
  if (kind.value === 'company' && code) query.creditCode = code
  if (kind.value === 'company' && industry.value) query.industry = industry.value
  if (kind.value === 'realname' && idType.value) query.idType = idType.value
  if (kind.value === 'sim-card' && operator.value) query.operator = operator.value
  if (kind.value === 'sim-card' && realnameId.value) query.realnameId = Number(realnameId.value)
  if (status.value) query.status = status.value
  return query
}

async function load() {
  loading.value = true
  error.value = ''
  const query = params()
  if (phoneHint.value) {
    rows.value = []
    total.value = 0
    loading.value = false
    return
  }
  try {
    const res = await http.get(`/corp/resource/${kind.value}/page`, { params: query })
    const data = res.data?.data
    rows.value = asList(data)
    total.value = asTotal(data, rows.value.length)
  } catch (e: unknown) {
    rows.value = []
    total.value = 0
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function search() {
  pageNo.value = 1
  load()
}

function reset() {
  keyword.value = ''
  creditCode.value = ''
  industry.value = ''
  idType.value = ''
  operator.value = ''
  realnameId.value = ''
  status.value = ''
  phoneHint.value = ''
  search()
}

function goto(page: number) {
  if (page < 1 || page > pageCount.value || page === pageNo.value) return
  pageNo.value = page
  load()
}

function changeSize(event: Event) {
  pageSize.value = Number((event.target as HTMLSelectElement).value)
  pageNo.value = 1
  load()
}

async function loadDigital() {
  digitalError.value = ''
  try {
    const res = await http.get('/cert/archive/digital-metrics')
    const data = res.data?.data || {}
    digital.totalExpected = Number(data.totalExpected || 0)
    digital.digitalizedCount = Number(data.digitalizedCount || 0)
    digital.digitalizedRate = Number(data.digitalizedRate ?? 1)
    digitalReady.value = true
  } catch (e: unknown) {
    if (!digitalReady.value) digitalError.value = errorMessage(e)
  } finally {
    digitalReady.value = true
  }
}

function applyLevel(data: Record<string, unknown>) {
  const rules = Array.isArray(data.rules) ? data.rules : []
  const first = rules.find((item) => item && typeof item === 'object' && (item as { target?: string }).target === 'ROLE') as
    | { targetCode?: string; viewLevel?: number }
    | undefined
  levelRole.value = first?.targetCode || ''
  levelValue.value = String(first?.viewLevel || 2)
  const raw = Array.isArray(data.l3Whitelist) ? data.l3Whitelist : []
  levelWhitelist.value = raw.map((item) => Number(item)).filter((item) => Number.isFinite(item))
  levelOpacity.value = Number(data.opacity ?? 0.12)
  levelPosition.value = String(data.position || 'bottom-right')
}

async function loadLevelConfig() {
  try {
    const res = await http.get('/cert/security/level-config')
    applyLevel((res.data?.data || {}) as Record<string, unknown>)
    levelReady.value = true
    levelError.value = ''
  } catch (e: unknown) {
    levelReady.value = false
    levelError.value = errorMessage(e)
  }
}

async function putLevel(
  rules: Array<{ target: string; targetCode: string; viewLevel: number }>,
  whitelist: number[],
  style?: WatermarkStyle,
) {
  const opacity = roundedOpacity(style?.opacity ?? Number(levelOpacity.value))
  const position = (style?.position ?? levelPosition.value).trim()
  const problem = styleError(opacity, position)
  if (problem) {
    levelMessage.value = problem
    return
  }
  await http.put('/cert/security/level-config', {
    rules,
    l3Whitelist: whitelist,
    opacity,
    position,
  })
  levelMessage.value = '已保存，下次查看即按新级别'
  await loadLevelConfig()
}

async function saveLevel() {
  levelMessage.value = ''
  const role = levelRole.value.trim()
  if (!role) {
    levelMessage.value = '角色编码必填'
    return
  }
  try {
    await putLevel([{ target: 'ROLE', targetCode: role, viewLevel: 2 }], levelWhitelist.value)
  } catch (e: unknown) {
    levelMessage.value = errorMessage(e)
  }
}

async function resetLevel() {
  levelMessage.value = ''
  levelOpacity.value = 0.12
  levelPosition.value = 'bottom-right'
  try {
    await putLevel([], [], { opacity: 0.12, position: 'bottom-right' })
    levelMessage.value = '已恢复默认，全员 L1'
  } catch (e: unknown) {
    levelMessage.value = errorMessage(e)
  }
}

async function saveWhitelist() {
  levelMessage.value = ''
  const userId = Number(l3UserId.value)
  if (!userId) {
    levelMessage.value = '请选择白名单用户'
    return
  }
  if (levelWhitelist.value.includes(userId)) {
    levelMessage.value = '该用户已在白名单'
    return
  }
  try {
    await putLevel(levelRules(), [...levelWhitelist.value, userId])
  } catch (e: unknown) {
    levelMessage.value = errorMessage(e)
  }
}

async function removeWhitelist(userId: number) {
  levelMessage.value = ''
  try {
    await putLevel(
      levelRules(),
      levelWhitelist.value.filter((id) => id !== userId),
    )
    levelMessage.value = '已移出白名单，下次查看即按新级别'
  } catch (e: unknown) {
    levelMessage.value = errorMessage(e)
  }
}

async function openFileUrl(row: Row) {
  fileError.value = ''
  filePreview.value = ''
  fileResult.value = null
  fileOpen.value = true
  detailOpen.value = false
  try {
    const res = await http.get(`/cert/archive/${row.id}/file-url`)
    const data = res.data?.data || {}
    fileResult.value = data
    const signed = String(data.signedUrl || '')
    const path = signed.replace(/^\/admin-api\/ims/, '')
    if (path) {
      const preview = await http.get(path)
      filePreview.value = String(preview.data?.data?.preview || '')
    }
  } catch (e: unknown) {
    fileError.value = errorMessage(e)
    fileResult.value = null
  }
}

async function loadDetailAudit(certId: number) {
  detailAudits.value = []
  detailAuditError.value = ''
  detailAuditLoading.value = true
  try {
    const res = await http.get('/cert/security/view-logs', {
      params: { certId, pageNo: 1, pageSize: 5 },
    })
    detailAudits.value = asList(res.data?.data).slice(0, 5)
  } catch (e: unknown) {
    const msg = bizError(e)
    detailAuditError.value = msg.includes('1008') ? '仅系统管理员可查看审计摘要' : msg
  } finally {
    detailAuditLoading.value = false
  }
}

async function openDetail(row: Row) {
  detail.value = null
  viewError.value = ''
  detailAudits.value = []
  detailAuditError.value = ''
  detailOpen.value = true
  const id = row.id
  const url = kind.value === 'certificate' ? `/corp/resource/certificate/${id}/view` : `/corp/resource/${kind.value}/${id}`
  try {
    const res = await http.get(url)
    const data = res.data?.data || {}
    detail.value = kind.value === 'certificate' ? { ...(data.indexInfo || {}), watermarkText: data.watermarkText } : data
  } catch (e: unknown) {
    if (kind.value === 'certificate') {
      viewError.value = errorMessage(e)
      detail.value = null
    } else {
      detail.value = { status: errorMessage(e) }
    }
  }
  if (kind.value === 'certificate') {
    const certId = Number(id)
    if (Number.isFinite(certId)) await loadDetailAudit(certId)
  }
}

async function prepareCompany() {
  try {
    const rows = await loadDict('dict_industry')
    if (rows.length) industries.value = rows
  } catch {
    /* 字典失败时保留本地行业 */
  }
}

async function loadDict(dictType: string) {
  const res = await http.get('/system/dict-data/list', { params: { dictType } })
  return asList(res.data?.data)
    .filter((row) => row.status === 'ENABLED')
    .map((row) => ({ value: String(row.dictValue), label: String(row.dictLabel) }))
}

async function prepareRealname() {
  try {
    const rows = await loadDict('dict_id_type')
    if (rows.length) idTypes.value = rows
  } catch {
    /* 字典失败时保留本地证件类型 */
  }
}

async function prepareSim() {
  const [yn, ops, st, userPage, personPage] = await Promise.all([
    loadDict('dict_yes_no'),
    loadDict('dict_sim_operator'),
    loadDict('dict_sim_status'),
    http.get('/system/user/page', { params: { pageNo: 1, pageSize: 100 } }),
    http.get('/corp/resource/realname/page', { params: { pageNo: 1, pageSize: 100, status: 'ENABLED' } }),
  ])
  yesNo.value = yn
  operators.value = ops
  simStatus.value = st
  specs['sim-card'].statusOptions = st
  users.value = asList(userPage.data?.data) as unknown as { id: string; username: string; nickname: string }[]
  persons.value = asList(personPage.data?.data) as unknown as { id: number; realName: string }[]
}

function openCreate() {
  editingId.value = null
  form.phoneNumber = ''
  form.isPrimary = 'NO'
  form.operator = 'MOBILE'
  form.assignedUserId = users.value[0]?.id || ''
  form.realnameId = ''
  form.status = 'IN_USE'
  form.packageName = ''
  form.monthlyRent = ''
  form.iccid = ''
  formError.value = ''
  formOpen.value = true
}

function openEdit(row: Row) {
  editingId.value = Number(row.id)
  form.phoneNumber = ''
  form.isPrimary = String(row.isPrimary || 'NO')
  form.operator = String(row.operator || 'MOBILE')
  form.assignedUserId = String(row.assignedUserId || '')
  form.realnameId = row.realnameId ? String(row.realnameId) : ''
  form.status = String(row.status || 'IN_USE')
  form.packageName = String(row.packageName || '')
  form.monthlyRent = String(row.monthlyRent || '')
  form.iccid = ''
  formError.value = ''
  formOpen.value = true
}

async function save() {
  saving.value = true
  formError.value = ''
  const payload: Record<string, unknown> = {
    isPrimary: form.isPrimary,
    operator: form.operator,
    assignedUserId: Number(form.assignedUserId),
    status: form.status,
    packageName: form.packageName,
    realnameId: form.realnameId ? Number(form.realnameId) : undefined,
  }
  if (form.phoneNumber.trim()) payload.phoneNumber = form.phoneNumber.trim()
  if (form.monthlyRent.trim()) payload.monthlyRent = form.monthlyRent.trim()
  if (form.iccid.trim()) payload.iccid = form.iccid.trim()
  try {
    if (editingId.value) await http.put(`/corp/resource/sim-card/${editingId.value}`, payload)
    else await http.post('/corp/resource/sim-card', payload)
    formOpen.value = false
    await load()
  } catch (e: unknown) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

watch(kind, async () => {
  keyword.value = ''
  creditCode.value = ''
  industry.value = ''
  idType.value = ''
  operator.value = ''
  realnameId.value = ''
  status.value = ''
  phoneHint.value = ''
  pageNo.value = 1
  detailOpen.value = false
  viewError.value = ''
  formOpen.value = false
  certFormOpen.value = false
  reviewOpen.value = false
  scanOpen.value = false
  renewOpen.value = false
  renewFinishOpen.value = false
  remindOpen.value = false
  fileOpen.value = false
  digitalOpen.value = false
  riskExportOpen.value = false
  if (kind.value === 'company') await prepareCompany()
  if (kind.value === 'sim-card' && !operators.value.length) {
    try {
      await prepareSim()
    } catch {
      /* 字典失败时列表仍可打开 */
    }
  }
  if (kind.value === 'realname') await prepareRealname()
  load()
  if (kind.value === 'certificate') {
    await loadAuditUsers()
    await Promise.all([loadExpire(), searchAudit(), loadDigital(), loadLevelConfig()])
  }
})

onMounted(async () => {
  if (kind.value === 'company') await prepareCompany()
  if (kind.value === 'realname') await prepareRealname()
  if (kind.value === 'sim-card') {
    try {
      await prepareSim()
    } catch {
      /* 字典失败时列表仍可打开 */
    }
  }
  await load()
  if (kind.value === 'certificate') {
    await loadAuditUsers()
    await Promise.all([loadExpire(), searchAudit(), loadDigital(), loadLevelConfig()])
  }
})
</script>

<style scoped>
.expire-wrap {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: var(--r) var(--r) 0 0;
  background: #fff;
}
</style>
