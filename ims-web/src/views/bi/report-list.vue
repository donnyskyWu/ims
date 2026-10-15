<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>报表管理</h1>
        <div class="sub">
          报表/大屏统一目录 · /ims/bi/report/list · BI-001 首片 · 列表按 BR-212 行级过滤（创建者 ∩ 查看者）
        </div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-import" @click="openImport">导入模板</button>
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建报表</button>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/subscribe">订阅与分享</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/preview">预览与下钻</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report">报表中心</router-link>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 220px 1fr; gap: 12px; align-items: start">
      <div class="card" style="padding: 12px">
        <div class="rowline" style="justify-content: space-between">
          <b>分类</b>
          <button class="btn btn-sec btn-sm" type="button" data-testid="bi-cat-manage" @click="openCats">分类管理</button>
        </div>
        <div
          class="csub"
          data-testid="bi-cat-node"
          data-name="全部"
          style="margin-top: 10px; cursor: pointer"
          :style="{ fontWeight: filters.category ? 400 : 700 }"
          @click="selectCat('')"
        >
          全部
        </div>
        <template v-for="node in categories" :key="node.id">
          <div
            data-testid="bi-cat-node"
            :data-name="node.name"
            style="margin-top: 8px; cursor: pointer"
            :style="{ fontWeight: filters.category === node.name ? 700 : 400 }"
            @click="selectCat(node.name)"
          >
            {{ node.name }}
          </div>
          <div
            v-for="child in node.children"
            :key="child.id"
            data-testid="bi-cat-node"
            :data-name="child.name"
            class="csub"
            style="margin: 4px 0 0 14px; cursor: pointer"
            :style="{ fontWeight: filters.category === child.name ? 700 : 400 }"
            @click="selectCat(child.name)"
          >
            {{ child.name }}
          </div>
        </template>
        <p class="csub" data-testid="bi-cat-hint" style="margin-top: 12px">当前分类：{{ filters.category || '全部' }} · {{ total }}</p>
      </div>

      <div>
        <div class="qbar">
          <input v-model="filters.keyword" data-testid="bi-report-keyword" placeholder="名称/编号" style="width: 140px" />
          <select v-model="filters.reportType" data-testid="bi-filter-type" style="width: 110px">
            <option value="">全部类型</option>
            <option value="REPORT">报表</option>
            <option value="DASHBOARD">大屏</option>
          </select>
          <select v-model="filters.shareScope" data-testid="bi-filter-scope" style="width: 120px">
            <option value="">全部可见范围</option>
            <option value="PRIVATE">私有</option>
            <option value="SPECIFIED">指定人</option>
            <option value="ALL">全员</option>
          </select>
          <select v-model="filters.status" data-testid="bi-filter-status" style="width: 110px">
            <option value="">全部状态</option>
            <option value="DRAFT">草稿</option>
            <option value="PUBLISHED">已发布</option>
          </select>
          <span class="sp"></span>
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-report-search" @click="loadList">查询</button>
          <button class="btn btn-sec btn-sm" type="button" @click="viewMode = viewMode === 'card' ? 'table' : 'card'">
            {{ viewMode === 'card' ? '列表' : '卡片' }}
          </button>
        </div>

        <p v-if="highlightMiss" class="hint" data-testid="bi-highlight-miss" style="color: var(--red)">{{ highlightMiss }}</p>
        <div v-if="viewMode === 'card'" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 12px">
          <div
            v-for="row in rows"
            :key="row.id"
            class="card hov"
            :data-testid="isHighlight(row) ? 'bi-report-highlight' : undefined"
            :style="isHighlight(row) ? { outline: '2px solid var(--blue)' } : undefined"
          >
            <div class="rowline" style="justify-content: space-between">
              <b>{{ row.reportName }}</b>
              <span class="tag tag-info">{{ row.reportType === 'DASHBOARD' ? '大屏' : '报表' }}</span>
            </div>
            <div class="csub" style="margin-top: 6px">{{ row.category }} / {{ row.subCategory || '—' }}</div>
            <div class="csub mono" style="margin-top: 4px">{{ row.reportNo }} · {{ statusText(row.status) }} · v{{ row.version || 1 }}</div>
            <div class="csub" style="margin-top: 4px">{{ formatShanghai(row.updatedAt) }} · {{ scopeText(row.shareScope) }} · {{ opText(row.opPerm) }} · {{ rowPermText(row.rowPerm) }}</div>
            <div class="rowline" style="margin-top: 10px; gap: 8px; flex-wrap: wrap">
              <button v-if="row.canPublish !== false && editAllowed" v-perm="'bi:report:edit'" class="btn btn-sec btn-sm" type="button" data-testid="bi-card-publish" @click="openListPublish(row)">📤 发布</button>
              <button v-if="row.canEdit !== false && editAllowed" v-perm="'bi:report:edit'" class="btn btn-sec btn-sm" type="button" data-testid="bi-card-edit" @click="openDesigner(row.id)">编辑设计</button>
              <button class="btn btn-sec btn-sm" type="button" data-testid="bi-more" @click="openMore(row)">更多</button>
            </div>
          </div>
          <div v-if="!loading && !rows.length" class="card" style="grid-column: 1 / -1">
            <div class="empty" data-testid="bi-report-list-empty"><div class="et">{{ emptyText }}</div></div>
          </div>
        </div>

        <div v-else class="tbl-block" style="margin-top: 12px">
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>编号</th>
                  <th>名称</th>
                  <th>类型</th>
                  <th>分类</th>
                  <th>可见范围</th>
              <th>状态</th>
              <th>版本</th>
              <th>更新</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading"><td colspan="9"><div class="empty"><div class="et">加载中</div></div></td></tr>
                <tr v-else-if="!rows.length"><td colspan="9"><div class="empty" data-testid="bi-report-list-empty"><div class="et">{{ emptyText }}</div></div></td></tr>
                <tr v-for="row in rows" v-else :key="row.id" :data-testid="isHighlight(row) ? 'bi-report-highlight' : undefined">
                  <td class="mono">{{ row.reportNo }}</td>
                  <td>{{ row.reportName }}</td>
                  <td>{{ row.reportType === 'DASHBOARD' ? '大屏' : '报表' }}</td>
                  <td>{{ row.category }}</td>
                  <td>{{ scopeText(row.shareScope) }}</td>
              <td>{{ statusText(row.status) }}</td>
              <td>v{{ row.version || 1 }}</td>
              <td class="csub">{{ formatShanghai(row.updatedAt) }}</td>
                  <td>
                    <button v-if="row.canPublish !== false && editAllowed" v-perm="'bi:report:edit'" class="btn btn-sec btn-sm" type="button" data-testid="bi-card-publish" @click="openListPublish(row)">📤 发布</button>
                    <button v-if="row.canEdit !== false && editAllowed" v-perm="'bi:report:edit'" class="btn btn-sec btn-sm" type="button" @click="openDesigner(row.id)">编辑</button>
                    <button class="btn btn-sec btn-sm" type="button" data-testid="bi-more" @click="openMore(row)">更多</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div v-if="deleteTarget" class="modal-mask" data-testid="bi-delete-confirm" @click.self="deleteTarget = null">
      <div class="card" style="width: 380px; padding: 18px">
        <h3 style="margin: 0 0 8px">删除报表</h3>
        <p>确认删除「{{ deleteTarget.reportName }}」？</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="deleteTarget = null">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-delete-ok" @click="confirmDelete">删除</button>
        </div>
      </div>
    </div>

    <div v-if="moreRow" class="modal-mask" data-testid="bi-more-drawer" @click.self="moreRow = null">
      <div class="card" data-testid="bi-more-menu" style="width: 600px; padding: 18px">
        <h3 style="margin: 0 0 8px">报表操作 · {{ moreRow.reportName }}</h3>
        <p class="csub">报表「{{ moreRow.reportName }}」· {{ moreRow.reportNo }} · 当前 v{{ moreRow.version || 1 }}</p>
        <div style="display: grid; grid-template-columns: 88px 1fr; gap: 8px 12px; margin-top: 12px">
          <span class="csub">类型</span>
          <span data-testid="bi-more-type">{{ moreRow.reportType === 'DASHBOARD' ? '数据大屏' : '普通报表' }}</span>
          <span class="csub">可见范围</span>
          <span data-testid="bi-more-scope">{{ drawerScopeText(moreRow.shareScope) }}</span>
          <span class="csub">数据源</span>
          <span data-testid="bi-more-dataset">{{ moreRow.dataset || '—' }}</span>
          <span class="csub">状态</span>
          <span data-testid="bi-more-status">{{ drawerStatus(moreRow) }}</span>
          <span class="csub">组件数</span>
          <span data-testid="bi-more-count">{{ moreRow.compCount ?? 0 }} 个</span>
          <span class="csub">标签</span>
          <span data-testid="bi-more-tags">{{ (moreRow.tags || []).join('、') || '—' }}</span>
        </div>
        <div style="margin: 14px 0 8px; font-weight: 600">可执行操作</div>
        <div class="rowline" style="gap: 8px; flex-wrap: wrap">
          <button v-if="moreRow.canEdit !== false && editAllowed" v-perm="'bi:report:edit'" class="btn btn-sec btn-sm" type="button" data-testid="bi-more-design" @click="openDesigner(moreRow.id)">编辑设计器</button>
          <button class="btn btn-sec btn-sm" type="button" data-testid="bi-more-preview" @click="openPreview(moreRow)">预览</button>
          <button v-if="moreRow.canPublish !== false && editAllowed" v-perm="'bi:report:edit'" class="btn btn-sec btn-sm" type="button" data-testid="bi-more-publish" @click="openPublishManage(moreRow)">发布管理</button>
          <button class="btn btn-sec btn-sm" type="button" data-testid="bi-more-share" @click="openShare(moreRow)">分享设置</button>
          <button v-if="moreRow.canCopy !== false && editAllowed" v-perm="'bi:report:edit'" class="btn btn-sec btn-sm" type="button" data-testid="bi-more-copy" @click="copyReport(moreRow)">复制</button>
          <button v-if="moreRow.canExport !== false" class="btn btn-sec btn-sm" type="button" data-testid="bi-more-export" @click="exportTemplate(moreRow)">导出模板 JSON</button>
          <button v-if="moreRow.canDelete !== false && editAllowed" v-perm="'bi:report:edit'" class="btn btn-sec btn-sm" type="button" data-testid="bi-more-delete" @click="askDelete(moreRow)">删除</button>
        </div>
        <div class="acts" style="margin-top: 14px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="moreRow = null">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="publishManage" class="modal-mask" data-testid="bi-publish-manage" @click.self="publishManage = null">
      <div class="card" style="width: 560px; padding: 18px; max-height: 80vh; overflow: auto">
        <h3 style="margin: 0 0 8px">发布管理 · {{ publishManage.reportName }} · v{{ publishManage.version || 1 }}</h3>
        <p v-if="!publishRows.length" class="csub">尚未发布。可在下方填写发布配置。</p>
        <div v-for="item in publishRows" :key="item.publishId" class="csub" style="margin-top: 8px" data-testid="bi-publish-row">
          {{ destText(item.dest) }} · {{ accessText(item.accessType) }} · {{ scopeText(item.shareScope) }} · {{ opText(item.opPerm) }} · {{ rowPermText(item.rowPerm) }}
          · 有效期 {{ item.expireDays || 7 }} 天 · 密码 {{ item.hasPassword ? '••••••' : '无' }} · 快照 v{{ item.snapshotVersion }}
          <span v-if="item.menuName"> · 菜单 {{ item.menuName }}</span>
          <button v-if="item.shareUrl" class="btn btn-sec btn-sm" type="button" style="margin-left: 8px" data-testid="bi-publish-copy-link" @click="copyPublishLink(item)">复制链接</button>
        </div>
        <p v-if="copyToast" class="hint" data-testid="bi-copy-link-toast">{{ copyToast }}</p>
        <div v-if="publishManage.canPublish !== false" style="margin-top: 14px" data-testid="bi-list-publish">
          <label class="fld">发布去向</label>
          <label class="csub" style="display: block; margin-top: 6px"><input v-model="listPublish.dests" type="checkbox" value="CENTER" /> 发布到报表中心</label>
          <label class="csub" style="display: block; margin-top: 6px"><input v-model="listPublish.dests" type="checkbox" value="MENU" /> 单独发布为菜单</label>
          <template v-if="listPublish.dests.includes('MENU')">
            <label class="fld">菜单名称</label>
            <input v-model="listPublish.menuName" class="fld-in" data-testid="bi-list-menu" placeholder="侧栏显示名" />
          </template>
          <label class="fld">访问方式</label>
          <select v-model="listPublish.accessType" class="fld-in" data-testid="bi-list-access">
            <option value="SHARE_LINK">发布链接</option>
            <option value="SSO">站内授权</option>
          </select>
          <label class="fld">有效期（天，7~30）</label>
          <input v-model.number="listPublish.expireDays" class="fld-in" type="number" min="7" max="30" data-testid="bi-list-expire" />
          <label class="csub" style="display: flex; align-items: center; gap: 8px; margin-top: 8px">
            <input v-model="listPublish.passwordEnabled" type="checkbox" /> 访问密码
          </label>
          <input v-if="listPublish.passwordEnabled" v-model="listPublish.password" class="fld-in" type="password" placeholder="至少 8 位" />
          <label class="fld">可见范围</label>
          <select v-model="listPublish.shareScope" class="fld-in" data-testid="bi-list-scope">
            <option value="PRIVATE">私有</option>
            <option value="SPECIFIED">指定人</option>
            <option value="ALL">全员</option>
          </select>
          <template v-if="listPublish.shareScope === 'SPECIFIED'">
            <label class="fld">可见用户</label>
            <input
              v-model="viewerKeyword"
              class="fld-in"
              data-testid="bi-viewer-keyword"
              placeholder="按姓名或账号搜索，如 tc_r2"
              @input="scheduleViewers"
            />
            <select v-model="listPublish.viewerId" class="fld-in" data-testid="bi-list-viewer" style="margin-top: 6px">
              <option value="">请选择</option>
              <option v-for="person in viewers" :key="person.id" :value="String(person.id)">{{ viewerLabel(person) }}</option>
            </select>
            <p v-if="viewerError" class="hint" data-testid="bi-viewer-error" style="color: var(--red)">{{ viewerError }}</p>
          </template>
          <label class="fld">操作权限</label>
          <select v-model="listPublish.opPerm" class="fld-in">
            <option value="READONLY">只读</option>
            <option value="EXPORT">可导出</option>
            <option value="COPY">可复制</option>
          </select>
          <p v-if="publishError" class="hint" style="color: var(--red)">{{ publishError }}</p>
          <button class="btn btn-pri btn-sm" type="button" style="margin-top: 10px" data-testid="bi-list-publish-now" @click="confirmListPublish">保存并发布</button>
        </div>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="publishManage = null">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="actionMsg" class="hint" data-testid="bi-action-msg">{{ actionMsg }}</div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">新建报表</h3>
        <label class="fld">报表类型<i class="req">*</i></label>
        <div class="rowline" style="gap: 8px; margin-bottom: 10px">
          <button
            type="button"
            class="btn btn-sm"
            :class="form.reportType === 'REPORT' ? 'btn-pri' : 'btn-sec'"
            @click="form.reportType = 'REPORT'"
          >
            报表
          </button>
          <button
            type="button"
            class="btn btn-sm"
            :class="form.reportType === 'DASHBOARD' ? 'btn-pri' : 'btn-sec'"
            @click="form.reportType = 'DASHBOARD'"
          >
            大屏
          </button>
        </div>
        <p v-if="fieldErrors.reportType" class="hint" data-testid="bi-new-type-error" style="color: var(--red)">{{ fieldErrors.reportType }}</p>
        <label class="fld">报表名称<i class="req">*</i></label>
        <input v-model="form.reportName" class="fld-in" data-testid="bi-new-name" />
        <p v-if="fieldErrors.reportName" class="hint" data-testid="bi-new-name-error" style="color: var(--red)">{{ fieldErrors.reportName }}</p>
        <label class="fld">分类</label>
        <select v-model="form.category" class="fld-in" data-testid="bi-new-category">
          <option v-for="name in flatNames" :key="name" :value="name">{{ name }}</option>
        </select>
        <label class="fld">可见范围</label>
        <select v-model="form.shareScope" class="fld-in" data-testid="bi-new-scope">
          <option value="PRIVATE">私有</option>
          <option value="SPECIFIED">指定人</option>
          <option value="ALL">全员</option>
        </select>
        <label class="fld">指标口径说明</label>
        <textarea v-model="form.metricNote" class="fld-in" data-testid="bi-new-note" rows="3" />
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-new-submit" @click="submitCreate">创建并进入设计器</button>
        </div>
      </div>
    </div>

    <div v-if="showCats" class="modal-mask" data-testid="bi-cat-dialog" @click.self="showCats = false">
      <div class="card" style="width: 560px; padding: 20px">
        <h3 style="margin: 0 0 12px">分类管理</h3>
        <label class="fld">分类名称</label>
        <input v-model="catForm.name" class="fld-in" data-testid="bi-cat-name" placeholder="请填写分类名称" />
        <label class="fld">上级</label>
        <select v-model.number="catForm.parentId" class="fld-in" data-testid="bi-cat-parent">
          <option :value="0">顶级</option>
          <option v-for="node in categories" :key="node.id" :value="node.id">{{ node.name }}</option>
        </select>
        <p v-if="catError" class="hint" data-testid="bi-cat-error" style="color: var(--red)">{{ catError }}</p>
        <p v-if="catMsg" class="hint" data-testid="bi-cat-msg">{{ catMsg }}</p>
        <div class="acts" style="margin: 8px 0 12px">
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-cat-add" @click="addCategory">＋ 新增分类</button>
        </div>
        <table>
          <tbody>
            <tr v-for="node in flatNodes" :key="node.id">
              <td>{{ node.level === 2 ? '└ ' : '' }}{{ node.name }}</td>
              <td class="csub">{{ node.level === 1 ? '顶级' : '二级' }}</td>
              <td>
                <button
                  v-if="!node.system"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="bi-cat-rename"
                  @click="renameCategory(node)"
                >
                  改名
                </button>
                <button
                  v-if="!node.system"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="bi-cat-delete"
                  @click="removeCategory(node)"
                >
                  删除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showCats = false">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="showImport" class="modal-mask" data-testid="bi-import-dialog" @click.self="showImport = false">
      <div class="card" style="width: 560px; padding: 20px">
        <h3 style="margin: 0 0 12px">导入模板</h3>
        <input data-testid="bi-import-file" type="file" accept=".json,application/json" @change="onImportFile" />
        <p v-if="importError" class="hint" data-testid="bi-import-error" style="color: var(--red)">{{ importError }}</p>
        <p v-if="importPreview" class="csub" data-testid="bi-import-summary">
          文件格式正确 · 组件数量 {{ importPreview.compCount }} · 数据源引用 {{ importPreview.dsCount }}
        </p>
        <p v-for="(warn, idx) in importWarnings" :key="idx" class="hint">{{ warn }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showImport = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-import-submit" @click="submitImport">导入并进入设计器</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const route = useRoute()
const user = useUserStore()
const editAllowed = ref(false)

type Row = {
  id: number
  reportNo: string
  reportName: string
  reportType: string
  category: string
  subCategory: string
  status: string
  shareScope?: string
  version?: number
  opPerm?: string
  rowPerm?: string
  publishDest?: string
  menuName?: string
  viewerIds?: number[]
  accessType?: string
  expireDays?: number
  hasPassword?: boolean
  dataset?: string
  compCount?: number
  tags?: string[]
  canEdit?: boolean
  canCopy?: boolean
  canDelete?: boolean
  canExport?: boolean
  canPublish?: boolean
  updatedAt: string
}

type PublishRecord = {
  publishId: number
  dest: string
  shareScope: string
  opPerm: string
  rowPerm: string
  snapshotVersion: number
  menuName?: string
  accessType?: string
  expireDays?: number
  hasPassword?: boolean
  shareUrl?: string
}

type Viewer = { id: number | string; username: string; nickname?: string }

type CatNode = { id: number; name: string; system?: boolean; children: CatNode[] }
type FlatCat = { id: number; name: string; level: number; system: boolean }

const rows = ref<Row[]>([])
const categories = ref<CatNode[]>([])
const total = ref(0)
const loading = ref(false)
const viewMode = ref<'card' | 'table'>('card')
const showForm = ref(false)
const formError = ref('')
const fieldErrors = reactive({ reportName: '', reportType: '' })
const filters = reactive({ keyword: '', reportType: '', category: '', shareScope: '', status: '' })
const listFiltered = ref(false)
const emptyText = computed(() => (listFiltered.value ? '当前筛选下暂无报表' : '暂无报表，点击新建'))
const form = reactive({ reportName: '', reportType: 'REPORT', category: '未分类', shareScope: 'PRIVATE', metricNote: '' })
const showCats = ref(false)
const catError = ref('')
const catMsg = ref('')
const catForm = reactive({ name: '', parentId: 0 })
const showImport = ref(false)
const moreRow = ref<Row | null>(null)
const deleteTarget = ref<Row | null>(null)
const publishManage = ref<Row | null>(null)
const publishRows = ref<PublishRecord[]>([])
const publishError = ref('')
const copyToast = ref('')
const viewers = ref<Viewer[]>([])
const viewerKeyword = ref('')
const viewerError = ref('')
const highlightMiss = ref('')
let viewerTimer = 0
const listPublish = reactive({
  dests: ['CENTER'] as string[],
  menuName: '',
  shareScope: 'PRIVATE',
  viewerId: '',
  opPerm: 'READONLY',
  rowPerm: 'INHERIT',
  accessType: 'SHARE_LINK',
  expireDays: 7,
  passwordEnabled: false,
  password: '',
})
const actionMsg = ref('')
const importError = ref('')
const importTemplate = ref<Record<string, unknown> | null>(null)
const importPreview = ref<{ compCount: number; dsCount: number } | null>(null)
const importWarnings = ref<string[]>([])

const flatNames = computed(() => {
  const names: string[] = []
  for (const node of categories.value) {
    names.push(node.name)
    for (const child of node.children || []) names.push(child.name)
  }
  return names
})

const flatNodes = computed(() => {
  const list: FlatCat[] = []
  for (const node of categories.value) {
    list.push({ id: node.id, name: node.name, level: 1, system: Boolean(node.system) || node.name === '未分类' })
    for (const child of node.children || []) {
      list.push({ id: child.id, name: child.name, level: 2, system: Boolean(child.system) || child.name === '未分类' })
    }
  }
  return list
})

async function loadCategories() {
  const res = await http.get('/bi/report/categories')
  if (res.data.code === 0) categories.value = res.data.data.categories || []
}

async function loadList() {
  loading.value = true
  try {
    const res = await http.get('/bi/report/list', {
      params: {
        keyword: filters.keyword || undefined,
        reportType: filters.reportType || undefined,
        category: filters.category || undefined,
        shareScope: filters.shareScope || undefined,
        status: filters.status || undefined,
        pageNo: 1,
        pageSize: 50,
      },
    })
    if (res.data.code === 0) {
      rows.value = res.data.data.list || []
      total.value = Number(res.data.data.total ?? rows.value.length)
      listFiltered.value = Boolean(
        filters.keyword.trim() || filters.reportType || filters.category || filters.shareScope || filters.status,
      )
    }
    await pinHighlight()
  } finally {
    loading.value = false
  }
}

const highlightId = computed(() => {
  const raw = route.query.highlight
  const value = Array.isArray(raw) ? raw[0] : raw
  const id = Number(value)
  return Number.isFinite(id) && id > 0 ? id : 0
})

function isHighlight(row: Row) {
  return highlightId.value > 0 && Number(row.id) === highlightId.value
}

async function pinHighlight() {
  highlightMiss.value = ''
  const id = highlightId.value
  if (!id) return
  if (rows.value.some((row) => Number(row.id) === id)) return
  try {
    const res = await http.get(`/bi/report/${id}`)
    const row = res.data.data as Row
    if (row?.id) rows.value = [row, ...rows.value.filter((item) => Number(item.id) !== Number(row.id))]
  } catch (error: unknown) {
    highlightMiss.value = errorMessage(error)
  }
}

function statusText(status: string) {
  if (status === 'DRAFT') return '草稿'
  if (status === 'PUBLISHED') return '已发布'
  return status
}

function opText(value?: string) {
  if (value === 'EXPORT') return '可导出'
  if (value === 'COPY') return '可复制'
  return '只读'
}

function accessText(value?: string) {
  return value === 'SSO' ? '站内授权' : '发布链接'
}

function rowPermText(value?: string) {
  return value === 'SNAPSHOT' ? '快照' : '继承行权限'
}

function destText(value?: string) {
  const parts = String(value || 'CENTER').split(',')
  const labels = parts.map((item) => (item.trim() === 'MENU' ? '单独菜单' : '报表中心'))
  return labels.join('、')
}

function scopeText(value?: string) {
  if (value === 'ALL') return '全员'
  if (value === 'SPECIFIED') return '指定人'
  return '私有'
}

function openMore(row: Row) {
  moreRow.value = row
}

function drawerScopeText(value?: string) {
  if (value === 'ALL') return '公开（登录用户）'
  if (value === 'SPECIFIED') return '指定人 / 角色'
  return '私有（仅创建者）'
}

function drawerStatus(row: Row) {
  if (row.status === 'DRAFT') return '草稿 DRAFT'
  if (row.status === 'PUBLISHED') return '已发布 PUBLISHED'
  return row.status
}

function openPreview(row: Row) {
  moreRow.value = null
  void router.push({ path: '/ims/bi/report/preview', query: { reportId: String(row.id) } })
}

async function loadEditPerm() {
  try {
    const res = await http.get('/bi/report/edit-perm')
    const data = res.data.data as { allowed?: boolean; granted?: boolean; permCode?: string }
    editAllowed.value = Boolean(data?.allowed)
    if (data?.granted && data.permCode && !user.permCodes.includes(data.permCode)) {
      user.permCodes = [...user.permCodes, data.permCode]
    }
  } catch {
    editAllowed.value = false
  }
}

async function copyPublishLink(item: PublishRecord) {
  const raw = (item.shareUrl || '').trim()
  if (!raw) {
    copyToast.value = '尚未发布'
    return
  }
  const url = raw.startsWith('http') ? raw : `${window.location.origin}${raw}`
  try {
    await navigator.clipboard.writeText(url)
  } catch {
    const input = document.createElement('textarea')
    input.value = url
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    input.remove()
  }
  copyToast.value = '已复制链接'
}

function openShare(row: Row) {
  moreRow.value = null
  void router.push({ path: '/ims/bi/report/subscribe', query: { tab: 'share', reportId: String(row.id) } })
}

function fillListPublish(row: Row) {
  const dests = String(row.publishDest || 'CENTER')
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item === 'CENTER' || item === 'MENU')
  listPublish.dests = dests.length ? dests : ['CENTER']
  listPublish.menuName = row.menuName || ''
  listPublish.shareScope = row.shareScope || 'PRIVATE'
  listPublish.viewerId = row.viewerIds?.[0] ? String(row.viewerIds[0]) : ''
  listPublish.opPerm = row.opPerm || 'READONLY'
  listPublish.rowPerm = row.rowPerm || 'INHERIT'
  listPublish.accessType = row.accessType || 'SHARE_LINK'
  listPublish.expireDays = row.expireDays || 7
  listPublish.passwordEnabled = Boolean(row.hasPassword)
  listPublish.password = ''
}

function viewerLabel(person: Viewer) {
  const name = (person.nickname || '').trim()
  const account = (person.username || '').trim()
  if (name && account && name !== account) return `${name}（${account}）`
  return name || account || String(person.id)
}

function scheduleViewers() {
  window.clearTimeout(viewerTimer)
  viewerTimer = window.setTimeout(() => {
    void loadViewers()
  }, 200)
}

async function loadViewers() {
  viewerError.value = ''
  try {
    const res = await http.get('/bi/report/viewers', {
      params: {
        keyword: viewerKeyword.value.trim() || undefined,
        includeId: listPublish.viewerId || undefined,
        pageNo: 1,
        pageSize: 100,
      },
    })
    const list = (res.data.data?.list || []) as Viewer[]
    viewers.value = list
    if (!list.length) viewerError.value = viewerKeyword.value.trim() ? '没有匹配的人员' : '暂无可选人员'
  } catch (error: unknown) {
    viewers.value = []
    viewerError.value = errorMessage(error)
  }
}

async function openListPublish(row: Row) {
  moreRow.value = null
  publishError.value = ''
  copyToast.value = ''
  viewerKeyword.value = ''
  fillListPublish(row)
  publishManage.value = row
  publishRows.value = []
  await loadViewers()
  try {
    const res = await http.get(`/bi/report/${row.id}/publish/list`)
    publishRows.value = res.data.data?.list || []
  } catch {
    publishRows.value = []
  }
}

async function copyReport(row: Row) {
  actionMsg.value = ''
  try {
    const res = await http.post(`/bi/report/${row.id}/copy`)
    actionMsg.value = `已复制为「${res.data.data.reportName}」· v${res.data.data.version}`
    moreRow.value = null
    await loadList()
  } catch (error: unknown) {
    const body = error as { msg?: string }
    actionMsg.value = body.msg || '复制失败'
  }
}

function askDelete(row: Row) {
  deleteTarget.value = row
  moreRow.value = null
}

async function confirmDelete() {
  const row = deleteTarget.value
  if (!row) return
  try {
    await http.delete(`/bi/report/${row.id}`)
    actionMsg.value = `已删除「${row.reportName}」`
    deleteTarget.value = null
    await loadList()
  } catch (error: unknown) {
    const body = error as { msg?: string }
    actionMsg.value = body.msg || '删除失败'
  }
}

async function exportTemplate(row: Row) {
  try {
    const res = await http.get(`/bi/report/${row.id}/export`)
    const blob = new Blob([JSON.stringify(res.data.data.template, null, 2)], { type: 'application/json' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${row.reportNo || 'report'}.json`
    link.click()
    URL.revokeObjectURL(link.href)
    actionMsg.value = `已导出模板 ${row.reportNo}.json`
    moreRow.value = null
  } catch (error: unknown) {
    const body = error as { msg?: string }
    actionMsg.value = body.msg || '导出失败'
  }
}

async function openPublishManage(row: Row) {
  await openListPublish(row)
}

async function confirmListPublish() {
  const row = publishManage.value
  if (!row) return
  publishError.value = ''
  if (!listPublish.dests.length) {
    publishError.value = '请选择发布去向'
    return
  }
  if (listPublish.dests.includes('MENU') && !listPublish.menuName.trim()) {
    publishError.value = '请填写菜单名称'
    return
  }
  if (listPublish.expireDays < 7 || listPublish.expireDays > 30) {
    publishError.value = '分享有效期须为 7~30 天'
    return
  }
  if (listPublish.passwordEnabled && listPublish.password.trim().length < 8) {
    publishError.value = '密码至少 8 位'
    return
  }
  if (listPublish.shareScope === 'SPECIFIED' && !listPublish.viewerId) {
    publishError.value = '请选择可见用户'
    return
  }
  try {
    const res = await http.post(`/bi/report/${row.id}/publish`, {
      dests: listPublish.dests,
      menuName: listPublish.menuName.trim(),
      shareScope: listPublish.shareScope,
      opPerm: listPublish.opPerm,
      rowPerm: listPublish.rowPerm,
      viewerIds: listPublish.shareScope === 'SPECIFIED' ? [Number(listPublish.viewerId)] : [],
      accessType: listPublish.accessType,
      expireDays: listPublish.expireDays,
      passwordEnabled: listPublish.passwordEnabled,
      password: listPublish.password,
    })
    const data = res.data.data
    actionMsg.value = data.menuNote ? `已发布 · v${data.version} · ${data.menuNote}` : `已发布 · v${data.version}`
    publishManage.value = null
    await loadList()
  } catch (error: unknown) {
    const body = error as { msg?: string }
    publishError.value = body.msg || '发布失败'
  }
}

function formatShanghai(iso: string) {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso.replace('T', ' ').slice(0, 16)
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date)
  const pick = (type: string) => parts.find((part) => part.type === type)?.value || ''
  return `${pick('year')}-${pick('month')}-${pick('day')} ${pick('hour')}:${pick('minute')}`
}

function selectCat(name: string) {
  filters.category = name
}

function openCreate() {
  form.reportName = ''
  form.reportType = 'REPORT'
  form.category = flatNames.value.includes('未分类') ? '未分类' : flatNames.value[0] || '未分类'
  form.shareScope = 'PRIVATE'
  form.metricNote = ''
  formError.value = ''
  fieldErrors.reportName = ''
  fieldErrors.reportType = ''
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  fieldErrors.reportName = form.reportName.trim() ? '' : '必填项，请填写'
  fieldErrors.reportType = form.reportType ? '' : '必填项，请填写'
  if (fieldErrors.reportName || fieldErrors.reportType) return
  let res
  try {
    res = await http.post('/bi/report', {
      reportName: form.reportName.trim(),
      reportType: form.reportType,
      category: form.category,
      shareScope: form.shareScope,
      metricNote: form.metricNote.trim(),
    })
  } catch (err) {
    const body = err as { msg?: string }
    formError.value = body.msg || '保存失败'
    return
  }
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showForm.value = false
  const rid = res.data.data?.id
  if (rid) {
    await router.push({ path: '/ims/bi/report/designer', query: { reportId: String(rid) } })
    return
  }
  await loadList()
}

function openDesigner(id: number) {
  router.push({ path: '/ims/bi/report/designer', query: { reportId: String(id) } })
}

function openCats() {
  catForm.name = ''
  catForm.parentId = 0
  catError.value = ''
  catMsg.value = ''
  showCats.value = true
}

async function addCategory() {
  catError.value = ''
  catMsg.value = ''
  if (!catForm.name.trim()) {
    catError.value = '请填写分类名称'
    return
  }
  try {
    await http.post('/bi/report/category', {
      action: 'add',
      name: catForm.name.trim(),
      parentId: catForm.parentId || 0,
    })
    catForm.name = ''
    catMsg.value = '分类已新增'
    await loadCategories()
  } catch (err) {
    const body = err as { msg?: string }
    catError.value = body.msg || '新增失败'
  }
}

function rejectSystemCategory(node: FlatCat, action: '删除' | '改名') {
  if (!node.system && node.name !== '未分类') return false
  catError.value = action === '改名' ? '未分类不能改名' : '未分类不能删除'
  catMsg.value = ''
  return true
}

async function renameCategory(node: FlatCat) {
  catError.value = ''
  catMsg.value = ''
  if (rejectSystemCategory(node, '改名')) return
  if (!catForm.name.trim()) {
    catError.value = '请填写分类名称'
    return
  }
  try {
    await http.post('/bi/report/category', {
      action: 'rename',
      categoryId: node.id,
      name: catForm.name.trim(),
    })
    catForm.name = ''
    catMsg.value = '分类已改名'
    await loadCategories()
    await loadList()
  } catch (err) {
    const body = err as { msg?: string }
    catError.value = body.msg || '改名失败'
  }
}

async function removeCategory(node: FlatCat) {
  catError.value = ''
  catMsg.value = ''
  if (rejectSystemCategory(node, '删除')) return
  try {
    const listed = await http.get('/bi/report/list', {
      params: { category: node.name, pageNo: 1, pageSize: 1 },
    })
    const occupied = Number(listed.data.data?.total || 0)
    if (occupied > 0) {
      catError.value = `该分类下有 ${occupied} 个报表，请先移动`
      return
    }
    await http.post('/bi/report/category', { action: 'delete', categoryId: node.id })
    catMsg.value = '分类已删除'
    await loadCategories()
    await loadList()
  } catch (err) {
    const body = err as { msg?: string }
    catError.value = body.msg || '删除失败'
  }
}

function openImport() {
  importError.value = ''
  importTemplate.value = null
  importPreview.value = null
  importWarnings.value = []
  showImport.value = true
}

async function onImportFile(event: Event) {
  importError.value = ''
  importPreview.value = null
  importWarnings.value = []
  importTemplate.value = null
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.json')) {
    importError.value = '文件格式不正确'
    return
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(await file.text())
  } catch {
    importError.value = '文件格式不正确'
    return
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    importError.value = '文件格式不正确'
    return
  }
  const template = parsed as Record<string, unknown>
  const comps = (template.comps || template.components || []) as unknown[]
  const datasets = new Set(
    (Array.isArray(comps) ? comps : [])
      .map((item) => (item && typeof item === 'object' ? String((item as { dataset?: string }).dataset || '') : ''))
      .filter(Boolean),
  )
  importTemplate.value = template
  importPreview.value = { compCount: Array.isArray(comps) ? comps.length : 0, dsCount: datasets.size }
}

async function submitImport() {
  importError.value = ''
  if (!importTemplate.value) {
    importError.value = '文件格式不正确'
    return
  }
  try {
    const res = await http.post('/bi/report/import', { template: importTemplate.value })
    importWarnings.value = (res.data.data.warnings || []).map((item: { message?: string }) => item.message || '')
    const rid = res.data.data.reportId || res.data.data.id
    showImport.value = false
    if (rid) {
      await router.push({ path: '/ims/bi/report/designer', query: { reportId: String(rid) } })
    }
  } catch (err) {
    const body = err as { msg?: string }
    importError.value = body.msg || '文件格式不正确'
  }
}

watch(
  () => [filters.reportType, filters.shareScope, filters.status, filters.category],
  () => {
    void loadList()
  },
)

onMounted(async () => {
  await loadEditPerm()
  await loadCategories()
  await loadList()
})
</script>
