<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>{{ meta.title }}</h1>
        <div class="sub">{{ meta.sub }}</div>
      </div>
      <div class="acts">
        <button v-if="kind === 'phone'" class="btn btn-pri" type="button" @click="openCreate">新建手机</button>
        <template v-else>
          <button v-if="kind === 'office'" class="btn btn-sec" type="button" data-testid="corp-asset-forward-open" @click="openForwardPerson">正向穿透</button>
          <button v-if="kind !== 'phone'" class="btn btn-sec" type="button" data-testid="corp-asset-entry-open" @click="openEntryReverse">账号/场次反查</button>
          <button v-if="kind === 'office'" class="btn btn-sec" type="button" data-testid="corp-asset-verify-open" @click="openVerify">关联校验</button>
          <button class="btn btn-sec" type="button" data-testid="corp-asset-import-btn" @click="openImport">采购导入</button>
          <button class="btn btn-pri" type="button" data-testid="corp-asset-create-btn" @click="openAssetCreate">资产登记</button>
        </template>
      </div>
    </div>
    <form class="qbar" @submit.prevent="search">
      <input
        v-model="keyword"
        :placeholder="meta.placeholder"
        style="width: 180px"
        :data-testid="kind === 'phone' ? undefined : 'corp-asset-keyword'"
      />
      <input
        v-if="kind === 'phone'"
        v-model="phoneModel"
        placeholder="型号"
        style="width: 140px"
        data-testid="master-phone-model"
      />
      <select v-if="kind === 'phone'" v-model="status" style="width: 120px">
        <option value="">全部状态</option>
        <option v-for="item in phoneStatus" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <template v-else>
        <select v-if="kind === 'live'" v-model="assetTypeFilter" style="width: 120px" data-testid="corp-asset-type-filter">
          <option value="">全部类型</option>
          <option value="LIVE">直播设备</option>
          <option value="SHOOT">拍摄设备</option>
        </select>
        <select v-model="status" style="width: 120px" data-testid="corp-asset-status-filter">
          <option value="">全部状态</option>
          <option v-for="item in assetStatusOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <select v-model="ownerFilter" style="width: 140px" data-testid="corp-asset-owner-filter">
          <option value="">全部责任人</option>
          <option value="none">未分配</option>
          <option v-for="user in users" :key="user.id" :value="String(user.id)">{{ user.nickname || user.username }}</option>
        </select>
        <label data-testid="corp-asset-link-gap-filter" style="display: inline-flex; align-items: center; gap: 4px">
          <input v-model="linkGapOnly" type="checkbox" />
          仅待补关联
        </label>
      </template>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="reset">重置</button>
      <button
        v-if="kind !== 'phone'"
        class="btn btn-sec btn-sm"
        type="button"
        data-testid="corp-asset-ledger-export"
        :disabled="exporting"
        @click="exportLedger"
      >
        导出台账
      </button>
    </form>
    <p v-if="kind !== 'phone'" class="hint" data-testid="corp-asset-link-gap-banner">
      当前筛选范围内待补关联 {{ linkGapTotal }} 台
      <button class="btn btn-txt" type="button" data-testid="corp-asset-link-gap-entry" @click="showLinkGap">只看这些</button>
    </p>
    <p v-if="ledgerExportNote" class="hint" data-testid="corp-asset-ledger-export-note">{{ ledgerExportNote }}</p>
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
                <div class="empty" :data-testid="kind === 'phone' ? undefined : 'corp-asset-list-empty'">
                  <div class="et">{{ error || emptyTitle }}</div>
                  <div class="es" :data-testid="kind === 'phone' ? undefined : 'corp-asset-list-empty-hint'">{{ emptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="String(row.id)">
              <td v-for="key in meta.keys" :key="key" :data-testid="cellTestId(key)">
                <template v-if="key === 'bindCount'">
                  <span>{{ show(row, key) }}</span>
                  <span v-if="row.linkGap" data-testid="corp-asset-link-gap" style="margin-left: 6px; color: #8b909a">待补关联</span>
                </template>
                <template v-else>{{ show(row, key) }}</template>
              </td>
              <td v-if="kind === 'phone'">
                <button class="btn btn-txt" type="button" @click="openDetail(row)">详情</button>
              </td>
              <td v-else>
                <button v-if="row.status === 'PENDING_REVIEW'" class="btn btn-txt" type="button" data-testid="corp-asset-checkout-btn" @click="openCheckout(row)">领用</button>
                <button v-if="row.status === 'IN_USE'" class="btn btn-txt" type="button" data-testid="corp-asset-use-btn" @click="openUse(row)">使用</button>
                <button v-if="row.status === 'IN_USE'" class="btn btn-txt" type="button" data-testid="corp-asset-return-btn" @click="openReturn(row)">归还</button>
                <button v-if="row.status === 'RETURNED'" class="btn btn-txt" type="button" data-testid="corp-asset-scrap-btn" @click="openScrap(row)">报废</button>
                <button class="btn btn-txt" type="button" data-testid="corp-asset-detail-btn" @click="openAssetDetail(row)">详情</button>
                <button v-if="kind === 'office'" class="btn btn-txt" type="button" data-testid="corp-asset-forward-btn" @click="openForwardAsset(row)">正向穿透</button>
                <button v-if="kind === 'office'" class="btn btn-txt" type="button" data-testid="corp-asset-reverse-btn" @click="openReverse(row)">反向穿透</button>
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
    <p class="hint">{{ meta.hint }}</p>
    <ProtoDrawer :open="detailOpen" title="手机详情" width="480px" @close="detailOpen = false">
      <div v-if="detail" class="formrow one">
        <div v-for="key in meta.keys" :key="key" class="fld">
          <label>{{ labelOf(key) }}</label>
          <div>{{ show(detail, key) }}</div>
        </div>
      </div>
      <div class="hint">绑定账号 0 个。没有实名人字段。影像只保存 key，不提供上传。</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="detailOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="formOpen" title="新建手机" width="480px" @close="formOpen = false">
      <div class="formrow one"><div class="fld"><label>手机号<i class="req">*</i></label><input v-model="form.phoneNumber" /></div></div>
      <div class="formrow one"><div class="fld"><label>编码</label><input v-model="form.phoneCode" /></div></div>
      <div class="formrow one"><div class="fld"><label>型号</label><input v-model="form.phoneModel" /></div></div>
      <div class="formrow one"><div class="fld"><label>设备编号</label><input v-model="form.deviceNumber" /></div></div>
      <div class="formrow one">
        <div class="fld">
          <label>保管人<i class="req">*</i></label>
          <select v-model="form.keeperId">
            <option value="">请选择本地用户</option>
            <option v-for="user in users" :key="user.id" :value="user.id">{{ user.nickname || user.username }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>类型</label>
          <select v-model="form.phoneType">
            <option value="">可不选</option>
            <option v-for="item in phoneTypes" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>状态<i class="req">*</i></label>
          <select v-model="form.status">
            <option v-for="item in phoneStatus" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
      </div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="formOpen = false">取消</button>
        <button class="btn btn-pri" type="button" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="importOpen" title="采购导入" width="640px" @close="importOpen = false">
      <p class="hint">CSV 表头：资产编号、资产名称、资产类型、规格、采购日期。合法行写入台账（待审核），非法行按行号和字段列出。已入库的行不会因为后面的错误行回滚。</p>
      <div class="formrow one">
        <div class="fld">
          <label>采购文件<i class="req">*</i></label>
          <input type="file" accept=".csv,text/csv" data-testid="corp-asset-import-file" @change="onImportFile" />
        </div>
      </div>
      <div v-if="importResult" data-testid="corp-asset-import-result">
        <p class="hint" data-testid="corp-asset-import-summary">{{ importSummary(importResult) }}</p>
        <p class="hint">批次 <span data-testid="corp-asset-import-batch">{{ importResult.batchNo }}</span></p>
        <ul v-if="importOk.length" data-testid="corp-asset-import-ok">
          <li v-for="item in importOk" :key="String(item.assetCode)">{{ item.assetCode }} · {{ item.assetName }} · 待审核</li>
        </ul>
        <table v-if="importErrors.length" data-testid="corp-asset-import-errors">
          <thead><tr><th>行号</th><th>字段</th><th>说明</th></tr></thead>
          <tbody>
            <tr v-for="item in importErrors" :key="String(item.rowNo) + String(item.field)" data-testid="corp-asset-import-error">
              <td>第 {{ item.rowNo }} 行</td>
              <td>{{ item.fieldLabel || item.field }}（{{ item.field }}）</td>
              <td>{{ item.message }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="importOpen = false">关闭</button>
        <button class="btn btn-pri" type="button" data-testid="corp-asset-import-save" :disabled="saving" @click="submitImport">{{ saving ? '导入中…' : '导入入台账' }}</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="assetCreateOpen" title="资产登记" width="480px" @close="assetCreateOpen = false">
      <div class="formrow one"><div class="fld"><label>资产编号<i class="req">*</i></label><input v-model="assetForm.assetCode" data-testid="corp-asset-code" /></div></div>
      <div class="formrow one"><div class="fld"><label>名称<i class="req">*</i></label><input v-model="assetForm.assetName" data-testid="corp-asset-name" /></div></div>
      <div class="formrow one"><div class="fld"><label>规格</label><input v-model="assetForm.spec" data-testid="corp-asset-spec" /></div></div>
      <div v-if="kind === 'live'" class="formrow one">
        <div class="fld">
          <label>类型</label>
          <select v-model="assetForm.assetType" data-testid="corp-asset-type">
            <option value="LIVE">直播设备</option>
            <option value="SHOOT">拍摄设备</option>
          </select>
        </div>
      </div>
      <div class="formrow one"><div class="fld"><label>采购日期</label><input v-model="assetForm.purchaseDate" type="date" data-testid="corp-asset-purchase" /></div></div>
      <div class="formrow one">
        <div class="fld">
          <label>实名人</label>
          <select v-model="assetForm.realnameId" data-testid="corp-asset-realname">
            <option value="">不挂接</option>
            <option v-for="person in persons" :key="person.id" :value="String(person.id)">{{ person.realName }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>上级资产编号</label>
          <input v-model="assetForm.parentAssetCode" data-testid="corp-asset-parent" placeholder="挂到已挂实名人的资产下" />
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>绑定账号</label>
          <input v-model="assetForm.accountNo" data-testid="corp-asset-bind-account" placeholder="账号编号，可空" />
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>绑定场次</label>
          <input v-model="assetForm.sessionCode" data-testid="corp-asset-bind-session" placeholder="场次编号，可空" />
        </div>
      </div>
      <p class="hint">实名人、账号、场次会在保存时校验：不存在为 1500，已停用或场次已取消为 1501，场次或账号不属于该实名人为 1001。</p>
      <div v-if="formError" class="hint bad" data-testid="corp-asset-form-error">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="assetCreateOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-asset-save" :disabled="saving" @click="saveAsset">{{ saving ? '保存中…' : '保存' }}</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="checkoutOpen" title="领用" width="480px" @close="checkoutOpen = false">
      <p class="hint">{{ activeAsset?.assetCode }} · {{ activeAsset?.assetName }}</p>
      <div class="formrow one">
        <div class="fld">
          <label>责任人<i class="req">*</i></label>
          <select v-model="assetForm.ownerUserId" data-testid="corp-asset-owner">
            <option value="">请选择本地用户</option>
            <option v-for="user in users" :key="user.id" :value="user.id">{{ user.nickname || user.username }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one"><div class="fld"><label>用途</label><input v-model="assetForm.purpose" data-testid="corp-asset-purpose" /></div></div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="checkoutOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-asset-checkout-save" :disabled="saving" @click="submitCheckout">确认领用</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="useOpen" title="使用" width="480px" @close="useOpen = false">
      <p class="hint">登记使用后状态仍为在用，之后才能归还。</p>
      <div class="formrow one"><div class="fld"><label>使用说明</label><input v-model="assetForm.remark" data-testid="corp-asset-use-remark" /></div></div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="useOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-asset-use-save" :disabled="saving" @click="submitUse">确认使用</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="returnOpen" title="归还" width="480px" @close="returnOpen = false">
      <p v-if="returnBlocked" class="hint bad" data-testid="corp-asset-return-blocked">尚未登记使用，不能归还。请先登记使用。</p>
      <p v-else class="hint" data-testid="corp-asset-return-ready">已登记使用，可以归还入库。</p>
      <div class="formrow one"><div class="fld"><label>说明</label><input v-model="assetForm.remark" data-testid="corp-asset-return-remark" /></div></div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="returnOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-asset-return-save" :disabled="saving || returnBlocked" @click="submitReturn">确认归还</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="scrapOpen" title="报废" width="480px" @close="scrapOpen = false">
      <div class="formrow one"><div class="fld"><label>报废原因<i class="req">*</i></label><input v-model="assetForm.remark" data-testid="corp-asset-scrap-reason" /></div></div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="scrapOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-asset-scrap-save" :disabled="saving" @click="submitScrap">确认报废</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="assetDetailOpen" title="资产详情" width="560px" @close="assetDetailOpen = false">
      <div v-if="assetDetail" class="formrow one">
        <div class="fld"><label>编号</label><div>{{ assetDetail.assetCode }}</div></div>
        <div class="fld"><label>名称</label><div>{{ assetDetail.assetName }}</div></div>
        <div class="fld"><label>状态</label><div data-testid="corp-asset-detail-status">{{ statusLabel(String(assetDetail.status || '')) }}</div></div>
        <div class="fld"><label>责任人</label><div>{{ assetDetail.ownerName || '—' }}</div></div>
        <div class="fld"><label>采购日期</label><div>{{ assetDetail.purchaseDate || '—' }}</div></div>
        <div class="fld"><label>采购批次</label><div data-testid="corp-asset-detail-batch">{{ assetDetail.purchaseBatchNo || '—' }}</div></div>
      </div>
      <table data-testid="corp-asset-timeline">
        <thead><tr><th>事件</th><th>状态</th><th>说明</th></tr></thead>
        <tbody>
          <tr v-for="event in timeline" :key="String(event.id)">
            <td>{{ eventLabel(String(event.eventType || '')) }}</td>
            <td>{{ statusLabel(String(event.toStatus || '')) }}</td>
            <td>{{ event.remark || '—' }}</td>
          </tr>
        </tbody>
      </table>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="assetDetailOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer v-if="kind === 'office'" :open="forwardOpen" title="正向穿透" width="560px" @close="forwardOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>实名人</label>
          <select v-model="forwardRealnameId" data-testid="asset-forward-realname">
            <option value="">请选择</option>
            <option v-for="person in persons" :key="person.id" :value="String(person.id)">{{ person.realName }}</option>
          </select>
        </div>
      </div>
      <button class="btn btn-pri btn-sm" type="button" data-testid="asset-forward-query" @click="queryForwardPerson">查询</button>
      <p v-if="forwardHint" class="hint">{{ forwardHint }}</p>
      <p v-if="forwardError" class="hint bad" data-testid="asset-forward-error">{{ forwardError }}</p>
      <ol v-if="forwardNodes.length" data-testid="asset-forward-chain">
        <li v-for="node in forwardNodes" :key="String(node.id)" data-testid="asset-forward-node">
          {{ node.layer === 'PERSON' ? '实名人' : `第${node.level}层` }} · {{ node.label }}
        </li>
      </ol>
      <p v-if="forwardEmpty" class="hint" data-testid="asset-forward-empty">该实名人下没有资产层级</p>
      <p v-else-if="!forwardAssetId && !forwardNodes.length && !forwardError" class="hint" data-testid="asset-forward-guide">请选择实名人并查询，再导出穿透报告</p>
      <div v-if="forwardSessions.length" data-testid="asset-forward-sessions">
        <p class="hint">场次层</p>
        <p v-for="item in forwardSessions" :key="String(item.sessionId)" data-testid="asset-forward-session">
          {{ item.sessionCode }} · {{ sessionStatusLabel(String(item.status || '')) }}
        </p>
      </div>
      <p v-if="forwardLayerError" class="hint bad" data-testid="asset-forward-session-error">
        {{ forwardLayerError }}
        <button class="btn btn-txt" type="button" data-testid="asset-forward-session-retry" @click="retryForwardLayers">重试</button>
      </p>
      <p v-else-if="forwardSessionEmpty" class="hint" data-testid="asset-forward-session-empty">该资产没有关联场次</p>
      <p
        v-if="forwardSessionEmpty && forwardFinance && !forwardFinance.costMasked"
        class="hint"
        data-testid="asset-forward-cost-empty"
      >
        没有关联场次，成本与收入记为 0
      </p>
      <p v-else-if="forwardFinance && forwardAssetId" class="hint" data-testid="asset-forward-finance">
        成本层 · 成本 <span data-testid="asset-forward-cost">{{ forwardFinance.costMasked ? '***' : money(forwardFinance.totalCost) }}</span>
        · 收入 <span data-testid="asset-forward-revenue">{{ money(forwardFinance.totalRevenue) }}</span>
      </p>
      <p v-if="exportNote && forwardOpen" class="hint" data-testid="asset-export-note">{{ exportNote }}</p>
      <div class="acts" style="margin-top: 12px">
        <button class="btn btn-pri btn-sm" type="button" data-testid="asset-forward-export" :disabled="exporting" @click="exportForward">导出穿透报告</button>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="forwardOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer v-if="kind === 'office'" :open="reverseOpen" title="反向穿透" width="560px" @close="reverseOpen = false">
      <p class="hint">{{ reverseHint }}</p>
      <p v-if="reverseError" class="hint bad" data-testid="asset-reverse-error">{{ reverseError }}</p>
      <table v-else data-testid="asset-reverse-holders">
        <thead><tr><th>使用人</th><th>状态</th></tr></thead>
        <tbody>
          <tr v-if="!reverseHolders.length">
            <td colspan="2">尚无使用人</td>
          </tr>
          <tr v-for="(holder, index) in reverseHolders" :key="index" data-testid="asset-reverse-row">
            <td data-testid="asset-reverse-user">{{ holder.userName || '—' }}</td>
            <td data-testid="asset-reverse-status">{{ holder.statusLabel }}</td>
          </tr>
        </tbody>
      </table>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="reverseOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer v-if="kind !== 'phone'" :open="entryOpen" title="账号/场次反查" width="720px" @close="entryOpen = false">
      <div class="acts" style="margin-bottom: 12px">
        <button class="btn btn-sm" :class="entryType === 'ACCOUNT' ? 'btn-pri' : 'btn-sec'" type="button" data-testid="asset-entry-account" @click="pickEntry('ACCOUNT')">按账号</button>
        <button class="btn btn-sm" :class="entryType === 'SESSION' ? 'btn-pri' : 'btn-sec'" type="button" data-testid="asset-entry-session" @click="pickEntry('SESSION')">按场次</button>
        <button v-if="kind === 'office'" class="btn btn-sm" :class="entryType === 'PERSON' ? 'btn-pri' : 'btn-sec'" type="button" data-testid="asset-entry-person" @click="pickEntry('PERSON')">按使用人</button>
      </div>
      <div v-if="entryType === 'ACCOUNT'" class="formrow one">
        <div class="fld">
          <label>账号编号</label>
          <input v-model="entryAccountNo" data-testid="asset-entry-account-no" placeholder="例如 AC-E2E-FIN" />
        </div>
      </div>
      <div v-else-if="entryType === 'SESSION'" class="formrow one">
        <div class="fld">
          <label>场次编号</label>
          <input v-model="entrySessionCode" data-testid="asset-entry-session-code" placeholder="IMS + 日期 + 平台码 + 序号" />
        </div>
      </div>
      <div v-else class="formrow one">
        <div class="fld">
          <label>使用人</label>
          <select v-model="entryUserId" data-testid="asset-entry-user">
            <option value="">请选择</option>
            <option v-for="user in users" :key="user.id" :value="String(user.id)">{{ user.nickname || user.username }}</option>
          </select>
        </div>
      </div>
      <label v-if="entryType === 'PERSON'" data-testid="asset-entry-include-history" style="display: inline-flex; align-items: center; gap: 6px; margin: 8px 0">
        <input type="checkbox" :checked="entryIncludeHistory" @change="toggleHistory" />
        含历史已归还
      </label>
      <button class="btn btn-pri btn-sm" type="button" data-testid="asset-entry-query" @click="queryEntry">查询</button>
      <button v-if="kind === 'office'" class="btn btn-sec btn-sm" type="button" data-testid="asset-entry-export" :disabled="exporting" @click="exportEntry">导出</button>
      <p v-if="exportNote && entryOpen" class="hint" data-testid="asset-export-note">{{ exportNote }}</p>
      <p v-if="!entryQueried && !entryError" class="hint" data-testid="asset-entry-guide">请选择入口维度并输入查询条件</p>
      <p v-if="entryError" class="hint bad" data-testid="asset-entry-error">{{ entryError }}</p>
      <p v-else-if="entrySummary" class="hint" data-testid="asset-entry-summary">{{ entrySummary }}</p>
      <table v-if="entryQueried && !entryError" data-testid="asset-entry-table">
        <thead><tr><th>资产编号</th><th>名称</th><th>状态</th><th>绑定</th><th>账号</th></tr></thead>
        <tbody>
          <tr v-if="!entryRows.length">
            <td colspan="5">没有绑定资产</td>
          </tr>
          <tr v-for="item in entryRows" :key="String(item.assetId)" data-testid="asset-entry-row">
            <td data-testid="asset-entry-code">{{ item.assetCode }}</td>
            <td>{{ item.assetName }}</td>
            <td data-testid="asset-entry-status">{{ statusLabel(String(item.status || '')) }}</td>
            <td>{{ bindLabel(String(item.bindType || '')) }}</td>
            <td>{{ item.relatedAccountNo || '—' }}</td>
          </tr>
        </tbody>
      </table>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="entryOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer v-if="kind === 'office'" :open="verifyOpen" title="登记关联校验" width="720px" @close="verifyOpen = false">
      <p class="hint">检查台账里的实名人、账号、场次是否存在、归属是否一致、状态是否允许。</p>
      <p class="hint" data-testid="asset-verify-schedule">定时校验：每周一凌晨全量，其余每日增量。打开本抽屉会补跑当日尚未执行的一次。</p>
      <p class="hint" data-testid="asset-verify-dingtalk">逾期未闭环会升级部门负责人。钉钉通知为本地桩，未外发。</p>
      <p data-testid="asset-verify-metrics">
        <span data-testid="asset-verify-complete" :class="metricClass(verifyMetrics?.relationCompleteRate)">完整率 {{ rateText(verifyMetrics?.relationCompleteRate) }}（目标 98%）</span>
        ·
        <span data-testid="asset-verify-consistency" :class="metricClass(verifyMetrics?.consistencyRate)">一致率 {{ rateText(verifyMetrics?.consistencyRate) }}（目标 98%）</span>
      </p>
      <div class="formrow one">
        <div class="fld">
          <label>只看资产编号</label>
          <input v-model="verifyAssetCode" data-testid="asset-verify-asset-code" placeholder="可空，填写后只看这台设备" />
        </div>
      </div>
      <button class="btn btn-pri btn-sm" type="button" data-testid="asset-verify-run" :disabled="verifyRunning" @click="runVerify">{{ verifyRunning ? '校验中…' : '开始校验' }}</button>
      <p v-if="verifyError" class="hint bad" data-testid="asset-verify-error">{{ verifyError }}</p>
      <p v-else-if="verifySummary" class="hint" data-testid="asset-verify-summary">{{ verifySummary }}</p>
      <p v-if="verifySummary && verifyAssetCode.trim() && !verifyErrors.length && !verifyError" class="hint" data-testid="asset-verify-clean">该资产没有关联异常</p>
      <table v-if="verifyErrors.length" data-testid="asset-verify-errors">
        <thead><tr><th>资产编号</th><th>类型</th><th>说明</th></tr></thead>
        <tbody>
          <tr v-for="item in verifyErrors" :key="String(item.id)" data-testid="asset-verify-row">
            <td data-testid="asset-verify-code">{{ item.assetCode }}</td>
            <td>{{ verifyTypeLabel(String(item.recordType || '')) }}</td>
            <td>{{ item.description }}</td>
          </tr>
        </tbody>
      </table>
      <div class="formrow">
        <div class="fld">
          <label>修复责任人</label>
          <select v-model="verifyOwnerId" data-testid="asset-verify-owner">
            <option value="">请选择</option>
            <option v-for="user in users" :key="user.id" :value="String(user.id)">{{ user.nickname || user.username }}</option>
          </select>
        </div>
        <div class="fld">
          <label>复核说明</label>
          <input v-model="verifyCloseRemark" data-testid="asset-verify-close-remark" maxlength="256" placeholder="闭环前填写" />
        </div>
      </div>
      <table v-if="verifyBatches.length" data-testid="asset-verify-batches">
        <thead><tr><th>批次</th><th>类型</th><th>范围</th><th>来源</th><th>异常</th><th>状态</th><th>限期</th><th></th></tr></thead>
        <tbody>
          <tr v-for="item in verifyBatches" :key="String(item.id)" data-testid="asset-verify-batch-row">
            <td class="mono" data-testid="asset-verify-batch-no">{{ item.batchNo }}</td>
            <td>{{ verifyTypeLabel(String(item.verifyType || '')) }}</td>
            <td data-testid="asset-verify-batch-scope">{{ item.scope === 'INCREMENT' ? '增量' : '全量' }}</td>
            <td data-testid="asset-verify-batch-trigger">{{ item.triggerMode === 'SCHEDULE' ? '定时' : '手动' }}</td>
            <td>{{ item.errorCount }}</td>
            <td data-testid="asset-verify-batch-status">{{ verifyTaskLabel(String(item.taskStatus || '')) }}</td>
            <td>
              {{ deadlineText(item.deadlineAt) }}
              <span v-if="item.overdue" class="hint bad" data-testid="asset-verify-overdue">逾期</span>
              <span v-if="item.escalateUserName" data-testid="asset-verify-escalated">已升级：{{ item.escalateUserName }}</span>
              <span v-if="item.escalateUserName" class="hint" data-testid="asset-verify-dingtalk-stub">钉钉未外发</span>
            </td>
            <td>
              <button v-if="item.taskStatus === 'PENDING_DISPATCH'" class="btn btn-sec btn-sm" type="button" data-testid="asset-verify-dispatch" @click="dispatchBatch(item)">派发</button>
              <button v-else-if="item.taskStatus === 'REPAIRING'" class="btn btn-pri btn-sm" type="button" data-testid="asset-verify-close" @click="closeBatch(item)">复核闭环</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="verifyBoardLoaded && !verifyBatches.length && !verifyError" class="hint" data-testid="asset-verify-empty">暂无校验数据，请先触发一次校验</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="verifyOpen = false">关闭</button>
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
type UserOpt = { id: string; username: string; nickname: string }
type PersonOpt = { id: number; realName: string }

const route = useRoute()
const kind = computed(() => String(route.params.kind || 'office'))
const rows = ref<Row[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const phoneModel = ref('')
const status = ref('')
const ownerFilter = ref('')
const assetTypeFilter = ref('')
const linkGapOnly = ref(false)
const linkGapTotal = ref(0)
const ledgerExportNote = ref('')
const loading = ref(false)
const error = ref('')
const detailOpen = ref(false)
const detail = ref<Row | null>(null)
const formOpen = ref(false)
const saving = ref(false)
const formError = ref('')
const users = ref<UserOpt[]>([])
const phoneStatus = ref<Opt[]>([])
const phoneTypes = ref<Opt[]>([])
const assetTypes = ref<Opt[]>([])
const assetStatuses = ref<Opt[]>([])
const assetCreateOpen = ref(false)
const importOpen = ref(false)
const importFile = ref<File | null>(null)
const importResult = ref<Row | null>(null)
const checkoutOpen = ref(false)
const useOpen = ref(false)
const returnOpen = ref(false)
const scrapOpen = ref(false)
const assetDetailOpen = ref(false)
const forwardOpen = ref(false)
const reverseOpen = ref(false)
const forwardRealnameId = ref('')
const forwardNodes = ref<Row[]>([])
const forwardError = ref('')
const forwardHint = ref('')
const reverseHolders = ref<Row[]>([])
const reverseError = ref('')
const reverseHint = ref('')
const entryOpen = ref(false)
const entryType = ref<'ACCOUNT' | 'SESSION' | 'PERSON'>('ACCOUNT')
const entryAccountNo = ref('')
const entrySessionCode = ref('')
const entryUserId = ref('')
const entryRows = ref<Row[]>([])
const entryError = ref('')
const entrySummary = ref('')
const entryQueried = ref(false)
const entryIncludeHistory = ref(true)
const SESSION_CODE = /^IMS\d{8}[A-Z]{3}\d{4}$/
const forwardAssetId = ref(0)
const forwardSessions = ref<Row[]>([])
const forwardSessionsLoaded = ref(false)
const forwardLayerError = ref('')
const forwardFinance = ref<Row | null>(null)
const verifyOpen = ref(false)
const verifyBoardLoaded = ref(false)
const verifyRunning = ref(false)
const verifyError = ref('')
const verifySummary = ref('')
const verifyErrors = ref<Row[]>([])
const verifyAssetCode = ref('')
const verifyMetrics = ref<Row | null>(null)
const verifyBatches = ref<Row[]>([])
const verifyOwnerId = ref('')
const verifyCloseRemark = ref('')
const exporting = ref(false)
const exportNote = ref('')
const persons = ref<PersonOpt[]>([])
const activeAsset = ref<Row | null>(null)
const returnBlocked = computed(() => !activeAsset.value?.used)
const forwardSessionEmpty = computed(
  () =>
    Boolean(forwardAssetId.value) &&
    forwardSessionsLoaded.value &&
    !forwardSessions.value.length &&
    !forwardLayerError.value &&
    !forwardError.value,
)
const assetDetail = ref<Row | null>(null)
const timeline = ref<Row[]>([])
const form = reactive({
  phoneNumber: '',
  phoneCode: '',
  phoneModel: '',
  deviceNumber: '',
  keeperId: '',
  phoneType: '',
  status: 'IN_USE',
})
const assetForm = reactive({
  assetCode: '',
  assetName: '',
  spec: '',
  assetType: 'OFFICE',
  purchaseDate: '',
  ownerUserId: '',
  purpose: '',
  remark: '',
  realnameId: '',
  parentAssetCode: '',
  accountNo: '',
  sessionCode: '',
})

const fallbackStatus: Opt[] = [
  { value: 'PENDING_REVIEW', label: '待审核' },
  { value: 'IN_USE', label: '在用' },
  { value: 'RETURNED', label: '已归还' },
  { value: 'SCRAPPED', label: '已报废' },
]
const fallbackType: Opt[] = [
  { value: 'OFFICE', label: '办公设备' },
  { value: 'LIVE', label: '直播设备' },
  { value: 'SHOOT', label: '拍摄设备' },
  { value: 'DIGITAL', label: '数码设备' },
]
const eventLabels: Record<string, string> = {
  REGISTER: '登记',
  CHECKOUT: '领用',
  USE: '使用',
  RETURN: '归还',
  SCRAP: '报废',
}

const specs: Record<string, {
  title: string
  sub: string
  placeholder: string
  empty: string
  emptyHint: string
  hint: string
  columns: string[]
  keys: string[]
}> = {
  office: {
    title: '办公设备管理',
    sub: 'CORP-D · 采购导入 → 领用 → 使用 → 归还 → 报废 · 实名人穿透',
    placeholder: '资产编号 / 名称',
    empty: '没有办公设备',
    emptyHint: '点「资产登记」或「采购导入」写入台账，再按领用、使用、归还、报废流转。',
    hint: 'GET /corp/device/office/page 读取 assetType=OFFICE。可按责任人、状态和待补关联筛选，并按当前条件导出台账。绑定账号数为 0 或责任人空时标为待补关联。登记时校验实名人、账号、场次：不存在 1500，已停用或场次已取消 1501，归属不对 1001。正向穿透可看场次层和成本层。关联校验扫描已入库的不一致项。',
    columns: ['编号', '名称', '类型', '规格', '采购日期', '状态', '责任人', '绑定账号数'],
    keys: ['assetCode', 'assetName', 'assetType', 'spec', 'purchaseDate', 'status', 'ownerName', 'bindCount'],
  },
  live: {
    title: '直播设备管理',
    sub: 'CORP-D · 直播与拍摄设备同一台账',
    placeholder: '资产编号 / 名称',
    empty: '没有直播设备',
    emptyHint: '登记时类型选直播设备或拍摄设备。流转与办公设备相同。',
    hint: 'GET /corp/device/live/page 合并 assetType=LIVE 与 SHOOT。类型、责任人和待补关联可筛选，导出台账沿用当前条件。',
    columns: ['编号', '名称', '类型', '规格', '采购日期', '状态', '责任人', '绑定账号数'],
    keys: ['assetCode', 'assetName', 'assetType', 'spec', 'purchaseDate', 'status', 'ownerName', 'bindCount'],
  },
  phone: {
    title: '手机设备管理',
    sub: 'MASTER-003 · 保管人只选本地用户 · 号码脱敏',
    placeholder: '设备编号 / 型号',
    empty: '没有手机',
    emptyHint: '可以新建。列表不显示实名人，手机资产没有这一列。',
    hint: 'POST /master/phone。CORP 的手机列表是同一份查询。',
    columns: ['号码', '编号', '型号', '类型', '保管人', '状态'],
    keys: ['phoneNumber', 'deviceNumber', 'phoneModel', 'phoneType', 'keeperName', 'status'],
  },
}

const meta = computed(() => specs[kind.value] || specs.office)
const phoneFiltering = computed(
  () => kind.value === 'phone' && Boolean(keyword.value.trim() || phoneModel.value.trim() || status.value),
)
const assetFiltering = computed(
  () =>
    kind.value !== 'phone' &&
    Boolean(keyword.value.trim() || status.value || ownerFilter.value || assetTypeFilter.value || linkGapOnly.value),
)
const emptyTitle = computed(() => (phoneFiltering.value || assetFiltering.value ? '没有符合筛选的记录' : meta.value.empty))
const emptyHint = computed(() => {
  if (error.value) return meta.value.emptyHint
  if (phoneFiltering.value) return '换个编号、型号或状态，或点重置。'
  if (!assetFiltering.value) return meta.value.emptyHint
  return kind.value === 'live'
    ? '换个编号、类型、责任人、状态或待补关联，或点重置。'
    : '换个编号、责任人、状态或待补关联，或点重置。'
})
const assetStatusOptions = computed(() => (assetStatuses.value.length ? assetStatuses.value : fallbackStatus))
const importErrors = computed(() => (importResult.value?.errors as Row[] | undefined) || [])
const importOk = computed(() => (importResult.value?.imported as Row[] | undefined) || [])
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pageList = computed(() => {
  const end = Math.min(pageCount.value, Math.max(pageNo.value + 2, 5))
  const start = Math.max(1, end - 4)
  const list: number[] = []
  for (let i = start; i <= Math.min(pageCount.value, start + 4); i += 1) list.push(i)
  return list
})

const labels: Record<string, string> = {
  phoneNumber: '号码',
  deviceNumber: '编号',
  phoneModel: '型号',
  phoneType: '类型',
  keeperName: '保管人',
  status: '状态',
  assetCode: '编号',
  assetName: '名称',
  assetType: '类型',
  spec: '规格',
  purchaseDate: '采购日期',
  ownerName: '责任人',
  bindCount: '绑定账号数',
}

function labelOf(key: string) {
  return labels[key] || key
}

function cellTestId(key: string) {
  if (kind.value === 'phone') return undefined
  if (key === 'status') return 'corp-asset-status'
  if (key === 'bindCount') return 'corp-asset-bind-count'
  return undefined
}

function ledgerQuery(forExport = false): Record<string, string | number> {
  const query: Record<string, string | number> = {}
  const text = keyword.value.trim()
  if (text) query.keyword = text
  if (status.value) query.status = status.value
  if (ownerFilter.value === 'none') query.unassigned = 1
  else if (ownerFilter.value) query.ownerUserId = Number(ownerFilter.value)
  if (linkGapOnly.value) query.linkGap = 1
  if (!forExport) return query
  if (kind.value === 'office') query.assetType = 'OFFICE'
  else if (assetTypeFilter.value) query.assetType = assetTypeFilter.value
  else query.assetType = 'LIVE,SHOOT'
  return query
}

function statusLabel(value: string) {
  return assetStatusOptions.value.find((item) => item.value === value)?.label || value
}

function typeLabel(value: string) {
  const dict = assetTypes.value.length ? assetTypes.value : fallbackType
  return dict.find((item) => item.value === value)?.label || value
}

function eventLabel(value: string) {
  return eventLabels[value] || value
}

function bindLabel(value: string) {
  if (value === 'HOLD') return '持有'
  if (value === 'GUARANTEE') return '担保'
  if (value === 'CUSTODY') return '代管'
  return value || '—'
}

function show(row: Row, key: string) {
  const value = row[key]
  if (value === undefined || value === null || value === '') return '—'
  if (key === 'status' && kind.value === 'phone') {
    return phoneStatus.value.find((item) => item.value === value)?.label || String(value)
  }
  if (key === 'status') return statusLabel(String(value))
  if (key === 'phoneType') return phoneTypes.value.find((item) => item.value === value)?.label || String(value)
  if (key === 'assetType') return typeLabel(String(value))
  return String(value)
}

async function loadDict(dictType: string) {
  const res = await http.get('/system/dict-data/list', { params: { dictType } })
  return asList(res.data?.data)
    .filter((row) => row.status === 'ENABLED')
    .map((row) => ({ value: String(row.dictValue), label: String(row.dictLabel) }))
}

async function loadUserOptions() {
  const firstRes = await http.get('/system/user/page', { params: { pageNo: 1, pageSize: 100 } })
  const payload = firstRes.data?.data as { total?: number } | undefined
  const first = asList(payload) as unknown as UserOpt[]
  const total = typeof payload?.total === 'number' ? payload.total : first.length
  if (total <= first.length) return first
  const lastPage = Math.ceil(total / 100)
  const lastRes = await http.get('/system/user/page', { params: { pageNo: lastPage, pageSize: 100 } })
  const last = asList(lastRes.data?.data) as unknown as UserOpt[]
  const seen = new Set(first.map((user) => String(user.id)))
  return first.concat(last.filter((user) => !seen.has(String(user.id))))
}

async function preparePhone() {
  const [st, types, userPage] = await Promise.all([
    loadDict('dict_phone_status'),
    loadDict('dict_phone_type'),
    loadUserOptions(),
  ])
  phoneStatus.value = st
  phoneTypes.value = types
  users.value = userPage
}

function bizError(error: unknown) {
  if (error && typeof error === 'object' && 'code' in error) {
    const body = error as { code?: number; msg?: string }
    if (body.code && body.code !== 0) return `${body.code} ${body.msg || ''}`.trim()
  }
  return errorMessage(error)
}

async function prepareAsset() {
  const [types, statuses, userPage, personPage] = await Promise.all([
    loadDict('dict_asset_type').catch(() => fallbackType),
    loadDict('dict_asset_status').catch(() => fallbackStatus),
    loadUserOptions(),
    http.get('/corp/resource/realname/page', { params: { pageNo: 1, pageSize: 100, status: 'ENABLED' } }).catch(() => null),
  ])
  assetTypes.value = types
  assetStatuses.value = statuses
  users.value = userPage
  persons.value = personPage ? (asList(personPage.data?.data) as unknown as PersonOpt[]) : []
}

function today() {
  const date = new Date()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const query: Record<string, string | number> = { pageNo: pageNo.value, pageSize: pageSize.value }
    const text = keyword.value.trim()
    const model = phoneModel.value.trim()
    if (kind.value === 'phone' && text) {
      if (/^[A-Za-z0-9-]+$/.test(text) && !/^\d{11}$/.test(text)) query.deviceNumber = text
      else if (!model) query.phoneModel = text
    }
    if (kind.value === 'phone' && model) query.phoneModel = model
    if (kind.value === 'phone' && status.value) query.status = status.value
    if (kind.value !== 'phone') {
      Object.assign(query, ledgerQuery(false))
      if (kind.value === 'live' && assetTypeFilter.value) query.assetType = assetTypeFilter.value
    }
    const url = kind.value === 'phone' ? '/corp/device/phone/page' : `/corp/device/${kind.value}/page`
    const res = await http.get(url, { params: query })
    const data = res.data?.data as { linkGapTotal?: number } | undefined
    rows.value = asList(data)
    total.value = asTotal(data, rows.value.length)
    linkGapTotal.value = kind.value === 'phone' ? 0 : Number(data?.linkGapTotal || 0)
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
  phoneModel.value = ''
  status.value = ''
  ownerFilter.value = ''
  assetTypeFilter.value = ''
  linkGapOnly.value = false
  ledgerExportNote.value = ''
  search()
}

function showLinkGap() {
  linkGapOnly.value = true
  search()
}

async function exportLedger() {
  exporting.value = true
  ledgerExportNote.value = ''
  try {
    const res = await http.get('/asset/ledger/export', { params: { ...ledgerQuery(true), format: 'XLSX' } })
    const data = (res.data?.data || {}) as {
      downloadUrl?: string
      fileName?: string
      message?: string
      exported?: number
      empty?: boolean
    }
    const downloadUrl = String(data.downloadUrl || '')
    const fileName = String(data.fileName || 'asset_ledger.xlsx')
    if (!downloadUrl) {
      throw { code: 5005, msg: '报告生成失败，请稍后重试或联系管理员' }
    }
    const token = localStorage.getItem('ims_access')
    const fileRes = await fetch(downloadUrl, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!fileRes.ok) {
      let body: { code?: number; msg?: string } = {}
      try {
        body = await fileRes.json()
      } catch {
        body = {}
      }
      throw body.code ? body : { code: fileRes.status, msg: body.msg || '报告生成失败，请稍后重试或联系管理员' }
    }
    const blob = await fileRes.blob()
    const anchor = document.createElement('a')
    anchor.href = URL.createObjectURL(blob)
    anchor.download = fileName
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(anchor.href)
    const exportedCount = Number(data.exported ?? 0)
    const emptyLedger = Boolean(data.empty) || exportedCount === 0
    ledgerExportNote.value = emptyLedger
      ? `${data.message || '已导出空台账（当前筛选命中 0 条）'} · ${fileName}`
      : `${data.message || '台账已按当前筛选导出'} · ${fileName} · ${exportedCount} 条`
  } catch (e: unknown) {
    ledgerExportNote.value = bizError(e)
  } finally {
    exporting.value = false
  }
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

async function openDetail(row: Row) {
  detailOpen.value = true
  detail.value = null
  try {
    const res = await http.get(`/corp/device/phone/${row.id}`)
    detail.value = res.data?.data
  } catch (e: unknown) {
    detail.value = { status: errorMessage(e) }
  }
}

function openCreate() {
  form.phoneNumber = ''
  form.phoneCode = ''
  form.phoneModel = ''
  form.deviceNumber = ''
  form.keeperId = users.value[0]?.id || ''
  form.phoneType = ''
  form.status = 'IN_USE'
  formError.value = ''
  formOpen.value = true
}

async function save() {
  saving.value = true
  formError.value = ''
  try {
    await http.post('/master/phone', {
      phoneNumber: form.phoneNumber.trim(),
      phoneCode: form.phoneCode,
      phoneModel: form.phoneModel,
      deviceNumber: form.deviceNumber,
      keeperId: Number(form.keeperId),
      phoneType: form.phoneType || undefined,
      status: form.status,
    })
    formOpen.value = false
    await load()
  } catch (e: unknown) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

function closeAssetDrawers() {
  assetCreateOpen.value = false
  importOpen.value = false
  checkoutOpen.value = false
  useOpen.value = false
  returnOpen.value = false
  scrapOpen.value = false
  forwardOpen.value = false
  reverseOpen.value = false
  entryOpen.value = false
  verifyOpen.value = false
}

function money(value: unknown) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '0.00'
  const sign = number < 0 ? '-' : ''
  const [whole, frac] = Math.abs(number).toFixed(2).split('.')
  return `${sign}${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${frac}`
}

function sessionStatusLabel(status: string) {
  const labels: Record<string, string> = {
    PENDING_RISK_CHECK: '待风控',
    APPROVED: '已放行',
    LIVE: '直播中',
    ENDED: '已结束',
    CANCELLED: '已取消',
  }
  return labels[status] || status || '—'
}

function verifyTypeLabel(kind: string) {
  const labels: Record<string, string> = {
    asset_person: '资产↔实名人',
    asset_account: '资产↔账号',
    asset_session: '资产↔场次',
  }
  return labels[kind] || kind
}

function verifyTaskLabel(status: string) {
  const labels: Record<string, string> = {
    PENDING_DISPATCH: '待派发',
    REPAIRING: '修复中',
    CLOSED: '已闭环',
  }
  return labels[status] || status || '—'
}

function rateText(value: unknown) {
  if (value === undefined || value === null || value === '') return '—'
  const number = Number(value)
  if (!Number.isFinite(number)) return '—'
  return `${(number * 100).toFixed(2)}%`
}

function metricClass(value: unknown) {
  const number = Number(value)
  if (!Number.isFinite(number)) return 'hint'
  return number < 0.98 ? 'hint bad' : 'hint'
}

function deadlineText(value: unknown) {
  const text = String(value || '')
  if (!text) return '—'
  const parsed = new Date(`${text.replace(' ', 'T')}Z`)
  if (Number.isNaN(parsed.getTime())) return text.slice(0, 10)
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(parsed)
}

function importSummary(result: Row) {
  const passed = Number(result.successCount || 0)
  const failed = Number(result.failCount || 0)
  if (result.partial) return `部分成功：成功 ${passed} 条，失败 ${failed} 条`
  if (failed && !passed) return `未能入库：失败 ${failed} 条`
  return `全部成功：成功 ${passed} 条`
}

function openImport() {
  closeAssetDrawers()
  importFile.value = null
  importResult.value = null
  formError.value = ''
  importOpen.value = true
}

function onImportFile(event: Event) {
  const input = event.target as HTMLInputElement
  importFile.value = input.files && input.files[0] ? input.files[0] : null
}

async function submitImport() {
  if (!importFile.value) {
    formError.value = '请选择 CSV 文件'
    return
  }
  saving.value = true
  formError.value = ''
  try {
    const body = new FormData()
    body.append('file', importFile.value)
    const res = await http.post('/asset/ledger/import', body)
    importResult.value = (res.data?.data || null) as Row | null
    await load()
  } catch (e: unknown) {
    formError.value = bizError(e)
  } finally {
    saving.value = false
  }
}

function openAssetCreate() {
  closeAssetDrawers()
  assetForm.assetCode = ''
  assetForm.assetName = ''
  assetForm.spec = ''
  assetForm.assetType = kind.value === 'live' ? 'LIVE' : 'OFFICE'
  assetForm.purchaseDate = today()
  assetForm.realnameId = ''
  assetForm.parentAssetCode = ''
  assetForm.accountNo = ''
  assetForm.sessionCode = ''
  formError.value = ''
  assetCreateOpen.value = true
}

function openCheckout(row: Row) {
  closeAssetDrawers()
  activeAsset.value = row
  assetForm.ownerUserId = users.value[0]?.id || ''
  assetForm.purpose = ''
  formError.value = ''
  checkoutOpen.value = true
}

function openUse(row: Row) {
  closeAssetDrawers()
  activeAsset.value = row
  assetForm.remark = '现场使用'
  formError.value = ''
  useOpen.value = true
}

function openReturn(row: Row) {
  closeAssetDrawers()
  activeAsset.value = row
  assetForm.remark = '归还入库'
  formError.value = ''
  returnOpen.value = true
}

function openScrap(row: Row) {
  closeAssetDrawers()
  activeAsset.value = row
  assetForm.remark = ''
  formError.value = ''
  scrapOpen.value = true
}

async function openAssetDetail(row: Row) {
  assetDetailOpen.value = true
  assetDetail.value = null
  timeline.value = []
  try {
    const res = await http.get(`/asset/ledger/${row.id}`)
    assetDetail.value = res.data?.data
    timeline.value = (res.data?.data?.timeline || []) as Row[]
  } catch (e: unknown) {
    assetDetail.value = { assetCode: errorMessage(e), assetName: '', status: '' }
  }
}

async function saveAsset() {
  saving.value = true
  formError.value = ''
  try {
    const payload: Record<string, unknown> = {
      assetCode: assetForm.assetCode.trim(),
      assetName: assetForm.assetName.trim(),
      assetType: kind.value === 'live' ? assetForm.assetType : 'OFFICE',
      spec: assetForm.spec,
      purchaseDate: assetForm.purchaseDate || undefined,
    }
    const parent = assetForm.parentAssetCode.trim()
    if (parent) payload.parentAssetCode = parent
    else if (assetForm.realnameId) payload.realnameId = Number(assetForm.realnameId)
    if (assetForm.accountNo.trim()) payload.accountNo = assetForm.accountNo.trim()
    if (assetForm.sessionCode.trim()) payload.sessionCode = assetForm.sessionCode.trim()
    await http.post('/asset/ledger', payload)
    assetCreateOpen.value = false
    keyword.value = assetForm.assetCode.trim()
    await load()
  } catch (e: unknown) {
    formError.value = bizError(e)
  } finally {
    saving.value = false
  }
}

async function loadTrace(url: string, params?: Record<string, unknown>) {
  try {
    const res = await http.get(url, { params })
    forwardNodes.value = (res.data?.data?.nodes || []) as Row[]
    forwardError.value = ''
  } catch (e: unknown) {
    forwardNodes.value = []
    forwardError.value = bizError(e)
  }
}

function clearForwardLayers() {
  forwardSessions.value = []
  forwardFinance.value = null
  forwardSessionsLoaded.value = false
  forwardLayerError.value = ''
}

const forwardEmpty = computed(
  () => forwardNodes.value.length > 0 && forwardNodes.value.every((node) => node.layer === 'PERSON'),
)

function openForwardPerson() {
  closeAssetDrawers()
  forwardOpen.value = true
  forwardNodes.value = []
  forwardError.value = ''
  forwardHint.value = '实名人 → 资产，最多 5 层'
  forwardAssetId.value = 0
  clearForwardLayers()
  exportNote.value = ''
  forwardRealnameId.value = persons.value[0] ? String(persons.value[0].id) : ''
}

async function queryForwardPerson() {
  const id = Number(forwardRealnameId.value)
  if (!id) {
    forwardError.value = '请选择实名人'
    forwardNodes.value = []
    return
  }
  forwardHint.value = '实名人 → 资产，最多 5 层'
  forwardAssetId.value = 0
  clearForwardLayers()
  exportNote.value = ''
  await loadTrace('/asset/forward/trace/0', { realnameId: id })
}

async function loadForwardLayers(assetId: number) {
  clearForwardLayers()
  if (!assetId) return
  try {
    const res = await http.get(`/asset/forward/detail/${assetId}`, {
      params: { withSessionLayer: true, withFinanceLayer: true },
    })
    const data = (res.data?.data || {}) as { liveSessions?: Row[]; financeSummary?: Row }
    forwardSessions.value = data.liveSessions || []
    forwardFinance.value = data.financeSummary || null
    forwardSessionsLoaded.value = true
  } catch (e: unknown) {
    forwardLayerError.value = bizError(e) || '场次层加载失败'
  }
}

function retryForwardLayers() {
  if (forwardAssetId.value) void loadForwardLayers(forwardAssetId.value)
}

async function openForwardAsset(row: Row) {
  closeAssetDrawers()
  forwardOpen.value = true
  forwardNodes.value = []
  forwardError.value = ''
  forwardHint.value = `${row.assetCode || ''} 的链路（实名人 → 资产）`
  forwardRealnameId.value = ''
  forwardAssetId.value = Number(row.id)
  exportNote.value = ''
  clearForwardLayers()
  await loadTrace(`/asset/forward/trace/${row.id}`)
  if (!forwardError.value) await loadForwardLayers(Number(row.id))
}

function openVerify() {
  closeAssetDrawers()
  verifyOpen.value = true
  verifyError.value = ''
  verifySummary.value = ''
  verifyErrors.value = []
  verifyAssetCode.value = ''
  verifyCloseRemark.value = ''
  verifyBoardLoaded.value = false
  const admin = users.value.find((user) => (user.nickname || user.username) === '管理员')
  verifyOwnerId.value = String((admin || users.value[0])?.id || '')
  void loadVerifyBoard().catch((error: unknown) => {
    verifyError.value = bizError(error)
  })
}

async function loadVerifyBoard() {
  const batches = await http.get('/asset/verify/batches', { params: { pageNo: 1, pageSize: 8 } })
  const metrics = await http.get('/asset/verify/metrics')
  verifyBatches.value = ((batches.data?.data?.list || []) as Row[])
  verifyMetrics.value = (metrics.data?.data || null) as Row | null
  verifyBoardLoaded.value = true
}

async function dispatchBatch(row: Row) {
  verifyError.value = ''
  if (!verifyOwnerId.value) {
    verifyError.value = '1001 修复责任人必填'
    return
  }
  try {
    await http.put(`/asset/verify/task/${row.id}`, {
      taskStatus: 'REPAIRING',
      ownerUserId: Number(verifyOwnerId.value),
      remark: '派发修复',
    })
    await loadVerifyBoard()
  } catch (e: unknown) {
    verifyError.value = bizError(e)
  }
}

async function closeBatch(row: Row) {
  verifyError.value = ''
  const remark = verifyCloseRemark.value.trim()
  if (!remark) {
    verifyError.value = '1001 复核说明必填'
    return
  }
  try {
    await http.put(`/asset/verify/task/${row.id}`, {
      taskStatus: 'CLOSED',
      remark,
    })
    await loadVerifyBoard()
  } catch (e: unknown) {
    verifyError.value = bizError(e)
  }
}

async function runVerify() {
  verifyRunning.value = true
  verifyError.value = ''
  verifySummary.value = ''
  verifyErrors.value = []
  try {
    const res = await http.post('/asset/verify/run', {
      verifyTypes: ['asset_person', 'asset_account', 'asset_session'],
      scope: 'FULL',
    })
    const data = (res.data?.data || {}) as { batchNo?: string; errorCount?: number; relationCompleteRate?: number; consistencyRate?: number }
    const batchNo = String(data.batchNo || '')
    const complete = Math.round(Number(data.relationCompleteRate || 0) * 1000) / 10
    const consistent = Math.round(Number(data.consistencyRate || 0) * 1000) / 10
    verifySummary.value = `批次 ${batchNo} · 异常资产 ${data.errorCount || 0} 台 · 完整率 ${complete}% · 一致率 ${consistent}%`
    if (batchNo) {
      const params: Record<string, string | number> = { batchNo, pageNo: 1, pageSize: 20 }
      const code = verifyAssetCode.value.trim()
      if (code) params.assetCode = code
      const listed = await http.get('/asset/verify/errors', { params })
      verifyErrors.value = ((listed.data?.data?.list || []) as Row[])
    }
    await loadVerifyBoard()
  } catch (e: unknown) {
    verifyError.value = bizError(e)
  } finally {
    verifyRunning.value = false
  }
}

function openEntryReverse() {
  closeAssetDrawers()
  entryOpen.value = true
  entryType.value = 'ACCOUNT'
  entryAccountNo.value = ''
  entrySessionCode.value = ''
  entryUserId.value = ''
  entryRows.value = []
  entryError.value = ''
  entrySummary.value = ''
  entryQueried.value = false
  entryIncludeHistory.value = true
  exportNote.value = ''
}

function clearEntryResult() {
  entryRows.value = []
  entryError.value = ''
  entrySummary.value = ''
  entryQueried.value = false
  exportNote.value = ''
}

function toggleHistory(event: Event) {
  entryIncludeHistory.value = (event.target as HTMLInputElement).checked
  clearEntryResult()
}

function sessionCodeOrError(): string {
  const code = entrySessionCode.value.trim().toUpperCase()
  if (!code) {
    entryError.value = '请填写场次编号'
    return ''
  }
  if (!SESSION_CODE.test(code)) {
    entryError.value = '场次编号格式不正确'
    return ''
  }
  entrySessionCode.value = code
  return code
}

function pickEntry(type: 'ACCOUNT' | 'SESSION' | 'PERSON') {
  entryType.value = type
  clearEntryResult()
  if (type === 'PERSON' && !entryUserId.value && users.value.length) {
    const admin = users.value.find((user) => (user.nickname || user.username) === '管理员')
    entryUserId.value = String((admin || users.value[0]).id)
  }
}

function entrySummaryText(summary: Row) {
  return `命中 ${summary.total || 0} 条（在用 ${summary.inUse || 0} / 已归还 ${summary.returned || 0} / 已报废 ${summary.scrapped || 0}）`
}

async function queryEntry() {
  entryError.value = ''
  entryRows.value = []
  entrySummary.value = ''
  entryQueried.value = false
  try {
    let res
    if (entryType.value === 'ACCOUNT') {
      const accountNo = entryAccountNo.value.trim()
      if (!accountNo) {
        entryError.value = '请填写账号编号'
        return
      }
      res = await http.get('/asset/reverse/by-account/0', { params: { accountNo, pageNo: 1, pageSize: 20 } })
    } else if (entryType.value === 'SESSION') {
      const sessionCode = sessionCodeOrError()
      if (!sessionCode) return
      res = await http.get(`/asset/reverse/by-session/${encodeURIComponent(sessionCode)}`, { params: { pageNo: 1, pageSize: 20 } })
    } else {
      const userId = Number(entryUserId.value)
      if (!userId) {
        entryError.value = '请选择使用人'
        return
      }
      res = await http.get(`/asset/reverse/by-person/${userId}`, {
        params: { includeHistory: entryIncludeHistory.value, pageNo: 1, pageSize: 20 },
      })
    }
    const data = (res.data?.data || {}) as { list?: Row[]; summary?: Row }
    entryRows.value = data.list || []
    entrySummary.value = entrySummaryText(data.summary || {})
    entryQueried.value = true
  } catch (e: unknown) {
    entryError.value = bizError(e)
  }
}

async function downloadExport(
  path: string,
  params: Record<string, unknown>,
  filename: string,
  note: string,
  target: 'forward' | 'entry',
) {
  exporting.value = true
  exportNote.value = ''
  try {
    const res = await http.get(path, { params })
    const downloadUrl = String(res.data?.data?.downloadUrl || '')
    if (!downloadUrl) {
      throw { code: 5005, msg: '报告生成失败，请稍后重试或联系管理员' }
    }
    const token = localStorage.getItem('ims_access')
    const fileRes = await fetch(downloadUrl, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!fileRes.ok) {
      let body: { code?: number; msg?: string } = {}
      try {
        body = await fileRes.json()
      } catch {
        body = {}
      }
      throw body.code ? body : { code: fileRes.status, msg: body.msg || '报告生成失败，请稍后重试或联系管理员' }
    }
    const blob = await fileRes.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(a.href)
    if (target === 'forward') forwardError.value = ''
    else entryError.value = ''
    const empty = Boolean((res.data?.data as { empty?: boolean } | undefined)?.empty)
    if (empty && target === 'forward') exportNote.value = '已导出穿透报告 PDF（暂无资产层级）'
    else if (empty) exportNote.value = '已导出空表（命中 0 条）'
    else if (target === 'forward' && forwardSessionEmpty.value) exportNote.value = '已导出穿透报告 PDF（该资产没有关联场次）'
    else exportNote.value = note
  } catch (e: unknown) {
    exportNote.value = ''
    const text = bizError(e)
    if (target === 'forward') forwardError.value = text
    else entryError.value = text
  } finally {
    exporting.value = false
  }
}

async function exportForward() {
  const params: Record<string, unknown> = {}
  const id = forwardAssetId.value
  if (!id) {
    const person = Number(forwardRealnameId.value)
    if (!person) {
      forwardError.value = '请选择实名人'
      return
    }
    params.realnameId = person
  }
  await downloadExport(
    `/asset/forward/export/${id || 0}`,
    params,
    'asset_forward_report.pdf',
    '已导出穿透报告 PDF',
    'forward',
  )
}

async function exportEntry() {
  entryError.value = ''
  exportNote.value = ''
  const params: Record<string, string | number | boolean> = { entryType: entryType.value, entryId: 0 }
  if (entryType.value === 'ACCOUNT') {
    const accountNo = entryAccountNo.value.trim()
    if (!accountNo) {
      entryError.value = '请填写账号编号'
      return
    }
    params.accountNo = accountNo
  } else if (entryType.value === 'SESSION') {
    const sessionCode = sessionCodeOrError()
    if (!sessionCode) return
    params.sessionCode = sessionCode
  } else {
    const userId = Number(entryUserId.value)
    if (!userId) {
      entryError.value = '请选择使用人'
      return
    }
    params.entryId = userId
    params.includeHistory = entryIncludeHistory.value
  }
  await downloadExport('/asset/reverse/export', params, 'asset_reverse_report.xlsx', '已导出反查 xlsx', 'entry')
}

async function openReverse(row: Row) {
  closeAssetDrawers()
  reverseOpen.value = true
  reverseHolders.value = []
  reverseError.value = ''
  reverseHint.value = `${row.assetCode || ''} → 使用人（在用 / 已归还 / 已报废）`
  try {
    const res = await http.get(`/asset/ledger/${row.id}`)
    reverseHolders.value = (res.data?.data?.holders || []) as Row[]
  } catch (e: unknown) {
    reverseError.value = bizError(e)
  }
}

async function postAction(path: string, payload: Record<string, unknown>, close: () => void) {
  if (!activeAsset.value) return
  saving.value = true
  formError.value = ''
  try {
    await http.post(`/asset/ledger/${activeAsset.value.id}${path}`, payload)
    close()
    await load()
  } catch (e: unknown) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

function submitCheckout() {
  postAction('/checkout', { ownerUserId: Number(assetForm.ownerUserId), purpose: assetForm.purpose }, () => {
    checkoutOpen.value = false
  })
}

function submitUse() {
  postAction('/use', { remark: assetForm.remark }, () => {
    useOpen.value = false
  })
}

function submitReturn() {
  if (returnBlocked.value) return
  postAction('/return', { remark: assetForm.remark }, () => {
    returnOpen.value = false
  })
}

function submitScrap() {
  postAction('/scrap', { remark: assetForm.remark }, () => {
    scrapOpen.value = false
  })
}

watch(kind, async () => {
  keyword.value = ''
  phoneModel.value = ''
  status.value = ''
  ownerFilter.value = ''
  assetTypeFilter.value = ''
  linkGapOnly.value = false
  ledgerExportNote.value = ''
  linkGapTotal.value = 0
  pageNo.value = 1
  detailOpen.value = false
  formOpen.value = false
  closeAssetDrawers()
  assetDetailOpen.value = false
  if (kind.value === 'phone' && !phoneStatus.value.length) {
    try {
      await preparePhone()
    } catch {
      /* 列表仍可打开 */
    }
  }
  if (kind.value !== 'phone' && !users.value.length) {
    try {
      await prepareAsset()
    } catch {
      /* 列表仍可打开 */
    }
  }
  load()
})

onMounted(async () => {
  if (kind.value === 'phone') {
    try {
      await preparePhone()
    } catch {
      /* 列表仍可打开 */
    }
  } else {
    try {
      await prepareAsset()
    } catch {
      /* 列表仍可打开 */
    }
  }
  await load()
})
</script>
