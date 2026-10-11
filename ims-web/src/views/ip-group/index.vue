<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>IP 组运营</h1>
        <div class="sub">大组小组、成员岗位、作者与账号绑定 · 19a IPG</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec" type="button" disabled>导出</button>
      </div>
    </div>
    <p v-if="msg" class="hint" data-testid="ipg-toast" style="margin-bottom: 10px">{{ msg }}</p>
    <div class="ipg-split">
      <div class="ipg-tree-panel card">
        <div class="ipg-tree-hd">
          <span>IP 组结构</span>
          <button class="btn-txt btn" type="button" @click="openCreate('BIG')">+ 新建大组</button>
        </div>
        <div class="ipg-tree-search">
          <div class="ico">
            <input v-model="treeKeyword" placeholder="搜索组名" />
          </div>
        </div>
        <div class="ipg-tree-body">
          <div v-if="!treeReady" class="ipg-empty-detail">加载中…</div>
          <div v-else-if="!flatNodes.length" class="ipg-empty-detail">暂无 IP 组，请新建大组</div>
          <template v-else>
            <div
              v-for="node in flatNodes"
              :key="node.id"
              class="ipg-node"
              :class="{ on: selectedId === node.id, child: node.depth > 0 }"
              :style="{ marginLeft: `${node.depth * 14}px` }"
              @click="selectGroup(node.id)"
            >
              <span class="exp ph"></span>
              <span class="nm">
                {{ node.groupName }}
                <span class="cnt">({{ node.memberCount }}/{{ node.accountCount }}/{{ node.anchorCount }})</span>
                <span v-if="node.level" class="lv">{{ levelText(node.level) }}</span>
              </span>
            </div>
          </template>
        </div>
      </div>
      <div class="ipg-detail-panel card">
        <div v-if="!selectedId" class="ipg-empty-detail">请从左侧选择 IP 组</div>
        <template v-else-if="detail">
          <div class="ipg-detail-hd">
            <div class="rowline" style="justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px">
              <div>
                <div class="rowline" style="gap: 8px; flex-wrap: wrap">
                  <span class="tag" style="background: rgba(90, 200, 250, 0.12); color: #0e7fb8">
                    <span class="dot"></span>{{ detail.groupType === 'BIG' ? '大组' : '小组' }}
                  </span>
                  <span v-if="detail.level" class="tag" style="background: rgba(0, 113, 227, 0.12); color: #0071e3">
                    <span class="dot"></span>{{ levelText(detail.level) }}
                  </span>
                </div>
                <h2>{{ detail.groupName }}</h2>
                <div class="ipg-detail-meta" data-testid="ipg-meta">
                  <span>组长：{{ detail.leaderUserName || '—' }}</span>
                  <span>上级：{{ parentName || '—' }}</span>
                  <span>创建于 {{ detail.createdAt || '—' }}</span>
                </div>
              </div>
              <div class="acts">
                <button v-if="detail.groupType === 'BIG'" class="btn btn-sec btn-sm" type="button" @click="openCreate('SMALL', detail.id)">
                  + 新建小组
                </button>
                <button class="btn btn-sec btn-sm" type="button" data-testid="ipg-edit" @click="openEdit">编辑</button>
                <button class="btn btn-sec btn-sm" type="button" data-testid="ipg-toggle" @click="toggleStatus">
                  {{ detail.status === 1 ? '停用' : '启用' }}
                </button>
                <button class="btn btn-sec btn-sm" type="button" data-testid="ipg-delete" @click="askRemove">删除</button>
              </div>
            </div>
          </div>
          <div class="ipg-detail-body">
            <div class="tabs">
              <div v-for="t in tabs" :key="t" class="tab" :class="{ on: tab === t }" @click="tab = t">{{ t }}</div>
            </div>
            <table v-if="tab === '基本信息'" class="ipg-info-grid" data-testid="ipg-basic">
              <tbody>
                <tr>
                  <td class="lbl">组名</td><td>{{ detail.groupName }}</td>
                  <td class="lbl">组类型</td><td>{{ detail.groupType === 'BIG' ? '大组' : '小组' }}</td>
                </tr>
                <tr>
                  <td class="lbl">上级组</td><td>{{ parentName || '—' }}</td>
                  <td class="lbl">组长</td><td>{{ detail.leaderUserName || '—' }}</td>
                </tr>
                <tr>
                  <td class="lbl">等级</td><td>{{ levelText(detail.level) }}</td>
                  <td class="lbl">状态</td><td data-testid="ipg-status">{{ detail.status === 1 ? '启用' : '停用' }}</td>
                </tr>
                <tr>
                  <td class="lbl">排序</td><td data-testid="ipg-sort">{{ detail.sortOrder ?? 0 }}</td>
                  <td class="lbl">备注</td><td data-testid="ipg-remark">{{ detail.remark || '—' }}</td>
                </tr>
                <tr>
                  <td class="lbl">创建时间</td><td data-testid="ipg-created">{{ detail.createdAt || '—' }}</td>
                  <td class="lbl">更新时间</td><td data-testid="ipg-updated">{{ detail.updatedAt || '—' }}</td>
                </tr>
              </tbody>
            </table>
            <div v-else-if="tab === '成员管理'" class="tbl-block">
              <div class="acts" style="margin: 12px 0">
                <button class="btn btn-pri btn-sm" type="button" data-testid="ipg-add-member" @click="openAddMember">+ 添加成员</button>
              </div>
              <div class="tbl-wrap">
                <table>
                  <thead>
                    <tr><th>姓名</th><th>岗位</th><th>主/兼</th><th>组长</th><th>操作</th></tr>
                  </thead>
                  <tbody>
                    <tr v-if="!members.length"><td colspan="5"><div class="empty"><div class="et">暂无成员</div></div></td></tr>
                    <tr v-for="m in members" :key="m.id" data-testid="ipg-member-row">
                      <td>{{ m.userName }}</td>
                      <td>{{ m.position }}</td>
                      <td>{{ m.relationType }}</td>
                      <td>{{ m.isLeader ? '是' : '否' }}</td>
                      <td>
                        <button class="btn-txt btn" type="button" data-testid="ipg-member-edit" @click="openEditMember(m)">编辑</button>
                        <button class="btn-txt btn" type="button" data-testid="ipg-member-remove" @click="askRemoveMember(m)">移除</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div v-else-if="tab === '账号绑定'">
              <div v-if="detail.groupType === 'BIG'" class="hint" style="margin: 12px 0">
                大组不可直接绑定平台账号（业务码 1203）。请选择小组节点。
              </div>
              <template v-else>
                <div class="acts" style="margin: 12px 0">
                  <input v-model.number="bindAccountId" placeholder="平台账号 id" style="width: 140px; height: 34px" />
                  <button class="btn btn-pri btn-sm" type="button" @click="bindAccount">关联账号</button>
                </div>
                <div class="tbl-wrap">
                  <table>
                    <thead>
                      <tr><th>账号</th><th>平台</th><th>状态</th></tr>
                    </thead>
                    <tbody>
                      <tr v-if="!accounts.length"><td colspan="3"><div class="empty"><div class="et">暂无绑定账号</div></div></td></tr>
                      <tr v-for="a in accounts" :key="a.id">
                        <td>{{ a.accountName }}</td>
                        <td>{{ a.platformType }}</td>
                        <td>{{ a.status }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>
            </div>
            <div v-else-if="tab === '关联作者'">
              <div class="acts" style="margin: 12px 0">
                <input v-model.number="bindAuthorId" placeholder="作者 id" style="width: 120px; height: 34px" />
                <button class="btn btn-pri btn-sm" type="button" @click="bindAuthor">绑定作者</button>
              </div>
              <div class="tbl-wrap">
                <table>
                  <thead>
                    <tr><th>作者</th><th>类型</th><th>主作者</th></tr>
                  </thead>
                  <tbody>
                    <tr v-if="!anchors.length"><td colspan="3"><div class="empty"><div class="et">暂无关联作者</div></div></td></tr>
                    <tr v-for="a in anchors" :key="a.id">
                      <td>{{ a.authorName }}</td>
                      <td>{{ a.anchorType || '—' }}</td>
                      <td>{{ a.isPrimary ? '是' : '否' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div v-else class="g4" style="margin-top: 12px">
              <div class="card stat"><span class="l">粉丝</span><div class="n">{{ stats.followerCount ?? 0 }}</div></div>
              <div class="card stat"><span class="l">作品</span><div class="n">{{ stats.contentCount ?? 0 }}</div></div>
              <div class="card stat"><span class="l">账号</span><div class="n">{{ stats.accountCount ?? 0 }}</div></div>
              <div class="card stat"><span class="l">ROI</span><div class="n">{{ stats.roiAvg ?? 0 }}</div></div>
            </div>
          </div>
        </template>
      </div>
    </div>
    <div v-if="creating" class="drawer on" data-testid="ipg-group-drawer">
      <div class="drawer-h">
        <b>{{ drawerTitle }}</b>
      </div>
      <div class="drawer-b">
        <div class="formrow one">
          <div class="fld">
            <label>IP 组名称<i class="req">*</i></label>
            <input v-model="createForm.groupName" data-testid="ipg-name" :class="{ err: formErrors.groupName }" />
            <div v-if="formErrors.groupName" class="ferr" data-testid="ipg-name-err">{{ formErrors.groupName }}</div>
          </div>
        </div>
        <div class="formrow one">
          <div class="fld">
            <label>组类型</label>
            <div class="pills" data-testid="ipg-type">
              <label class="pill">
                <input v-model="createType" type="radio" value="BIG" :disabled="groupMode === 'edit' || createType !== 'BIG'" />
                <span>大组</span>
              </label>
              <label class="pill">
                <input v-model="createType" type="radio" value="SMALL" :disabled="groupMode === 'edit' || createType !== 'SMALL'" />
                <span>小组</span>
              </label>
            </div>
          </div>
        </div>
        <div class="formrow one">
          <div class="fld">
            <label>上级 IP 组<i v-if="createType === 'SMALL'" class="req">*</i></label>
            <select
              v-model="createForm.parentId"
              data-testid="ipg-parent"
              :disabled="createType === 'BIG'"
              :class="{ err: formErrors.parentId }"
            >
              <option value="">{{ createType === 'BIG' ? '大组无上级' : '请选择大组' }}</option>
              <option v-for="group in bigGroups" :key="group.id" :value="String(group.id)">{{ group.groupName }}</option>
            </select>
            <div class="hint">小组须选择大组</div>
            <div v-if="formErrors.parentId" class="ferr" data-testid="ipg-parent-err">{{ formErrors.parentId }}</div>
          </div>
        </div>
        <div class="formrow one">
          <div class="fld">
            <label>组长</label>
            <input v-model="leaderKeyword" data-testid="ipg-leader-search" placeholder="搜索姓名" />
            <select v-model="createForm.leaderUserId" data-testid="ipg-leader" style="margin-top: 8px">
              <option value="">请选择（可空）</option>
              <option v-for="user in filteredUsers" :key="user.id" :value="String(user.id)">
                {{ user.nickname || user.username }}
              </option>
            </select>
          </div>
        </div>
        <div class="formrow one">
          <div class="fld">
            <label>等级</label>
            <select v-model="createForm.level" data-testid="ipg-level">
              <option value="">未分级</option>
              <option v-for="item in levels" :key="item.dictValue" :value="item.dictValue">{{ item.dictLabel }}</option>
            </select>
          </div>
        </div>
        <div class="formrow one">
          <div class="fld">
            <label>描述</label>
            <textarea v-model="createForm.description" data-testid="ipg-desc" rows="3" :class="{ err: formErrors.description }" />
            <div v-if="formErrors.description" class="ferr" data-testid="ipg-desc-err">{{ formErrors.description }}</div>
          </div>
        </div>
        <div v-if="groupMode === 'edit'" class="formrow one">
          <div class="fld">
            <label>排序</label>
            <input v-model="createForm.sortOrder" data-testid="ipg-sort-input" />
          </div>
        </div>
      </div>
      <div class="drawer-f">
        <button class="btn btn-sec" type="button" @click="creating = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="ipg-group-submit" @click="submitGroup">确认</button>
      </div>
    </div>
    <div v-if="memberOpen" class="drawer on" data-testid="ipg-member-drawer">
      <div class="drawer-h"><b>{{ memberMode === 'edit' ? '编辑成员' : '添加成员' }}</b></div>
      <div class="drawer-b">
        <div class="formrow one">
          <div class="fld">
            <label>用户<i class="req">*</i></label>
            <input v-model="memberKeyword" data-testid="ipg-member-user-search" placeholder="搜索姓名" :disabled="memberMode === 'edit'" />
            <select
              v-model="memberForm.userId"
              data-testid="ipg-member-user"
              style="margin-top: 8px"
              :disabled="memberMode === 'edit'"
              :class="{ err: memberErrors.userId }"
            >
              <option value="">请按姓名选择</option>
              <option v-for="user in filteredMemberUsers" :key="user.id" :value="String(user.id)">
                {{ user.nickname || user.username }}
              </option>
            </select>
            <div v-if="memberErrors.userId" class="ferr" data-testid="ipg-member-user-err">{{ memberErrors.userId }}</div>
          </div>
        </div>
        <div class="formrow one">
          <div class="fld">
            <label>岗位<i class="req">*</i></label>
            <select v-model="memberForm.position" data-testid="ipg-member-position" :class="{ err: memberErrors.position }">
              <option value="">请选择</option>
              <option v-for="item in positions" :key="item.dictValue" :value="item.dictValue">{{ item.dictLabel }}</option>
            </select>
            <div v-if="memberErrors.position" class="ferr" data-testid="ipg-member-position-err">{{ memberErrors.position }}</div>
          </div>
        </div>
        <div class="formrow one">
          <div class="fld">
            <label>主/兼</label>
            <select v-model="memberForm.relationType" data-testid="ipg-member-relation">
              <option value="PRIMARY">主职</option>
              <option value="PART_TIME">兼职</option>
            </select>
          </div>
        </div>
      </div>
      <div class="drawer-f">
        <button class="btn btn-sec" type="button" @click="memberOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="ipg-member-submit" @click="submitMember">确认</button>
      </div>
    </div>
    <div v-if="confirming" class="cfwrap on" data-testid="ipg-confirm">
      <div class="cfmask" @click="confirming = null"></div>
      <div class="cfcard danger">
        <div class="cf-t">{{ confirming.title }}</div>
        <div class="cf-m" data-testid="ipg-confirm-text">{{ confirming.message }}</div>
        <div class="cf-f">
          <button class="btn btn-sec" type="button" data-testid="ipg-confirm-cancel" @click="confirming = null">取消</button>
          <button class="btn btn-red" type="button" data-testid="ipg-confirm-ok" @click="confirming.run()">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { http, errorMessage } from '../../api/http'

type TreeNode = {
  id: number
  groupName: string
  groupType: string
  parentId: number | null
  leaderUserName?: string
  memberCount: number
  accountCount: number
  anchorCount: number
  leaderUserId?: number | null
  level?: string
  sortOrder?: number
  status?: number
  remark?: string
  createdAt?: string
  updatedAt?: string
  children?: TreeNode[]
}

const msg = ref('')
const treeReady = ref(false)
const tree = ref<TreeNode[]>([])
const treeKeyword = ref('')
const selectedId = ref<number | null>(null)
const tab = ref('基本信息')
const tabs = ['基本信息', '成员管理', '账号绑定', '关联作者', '统计']
const members = ref<any[]>([])
const accounts = ref<any[]>([])
const anchors = ref<any[]>([])
const stats = ref<Record<string, number>>({})
const confirming = ref<{ title: string; message: string; run: () => void } | null>(null)
const bindAccountId = ref<number | undefined>()
const bindAuthorId = ref<number | undefined>()
const creating = ref(false)
const groupMode = ref<'create' | 'edit'>('create')
const createType = ref<'BIG' | 'SMALL'>('BIG')
const createForm = ref({ groupName: '', parentId: '', leaderUserId: '', level: '', description: '', sortOrder: '0' })
const drawerTitle = computed(() => {
  if (groupMode.value === 'edit') return '编辑 IP 组'
  return createType.value === 'BIG' ? '新建大组' : '新建小组'
})
const formErrors = ref<Record<string, string>>({})
const leaderKeyword = ref('')
const users = ref<{ id: number; nickname: string; username: string }[]>([])
const levels = ref<{ dictValue: string; dictLabel: string }[]>([])
const positions = ref<{ dictValue: string; dictLabel: string }[]>([])
const memberOpen = ref(false)
const memberMode = ref<'add' | 'edit'>('add')
const editingMemberId = ref<number | null>(null)
const memberKeyword = ref('')
const memberForm = ref({ userId: '', position: '', relationType: 'PRIMARY' })
const memberErrors = ref<Record<string, string>>({})

const nodeMap = computed(() => {
  const map = new Map<number, TreeNode>()
  const walk = (nodes: TreeNode[]) => {
    for (const n of nodes) {
      map.set(n.id, n)
      if (n.children?.length) walk(n.children)
    }
  }
  walk(tree.value)
  return map
})

const flatNodes = computed(() => {
  const key = treeKeyword.value.trim().toLowerCase()
  const out: (TreeNode & { depth: number })[] = []
  const walk = (nodes: TreeNode[], depth: number) => {
    for (const n of nodes) {
      if (!key || n.groupName.toLowerCase().includes(key)) {
        out.push({ ...n, depth })
      }
      if (n.children?.length) walk(n.children, depth + 1)
    }
  }
  walk(tree.value, 0)
  return out
})

const bigGroups = computed(() => {
  const out: TreeNode[] = []
  const walk = (nodes: TreeNode[]) => {
    for (const node of nodes) {
      if (node.groupType === 'BIG') out.push(node)
      if (node.children?.length) walk(node.children)
    }
  }
  walk(tree.value)
  return out
})
const filteredUsers = computed(() => filterUsers(leaderKeyword.value))
const filteredMemberUsers = computed(() => filterUsers(memberKeyword.value))

function filterUsers(keyword: string) {
  const key = keyword.trim().toLowerCase()
  if (!key) return users.value
  return users.value.filter((user) => `${user.nickname} ${user.username}`.toLowerCase().includes(key))
}
function levelText(level?: string) {
  if (!level) return '未分级'
  const found = levels.value.find((item) => item.dictValue === level)
  return found?.dictLabel || `${level}级`
}

const detail = computed(() => (selectedId.value ? nodeMap.value.get(selectedId.value) : null))
const parentName = computed(() => {
  if (!detail.value?.parentId) return ''
  return nodeMap.value.get(detail.value.parentId)?.groupName || String(detail.value.parentId)
})

async function loadTree() {
  treeReady.value = false
  try {
    const res = await http.get('/ip-group/tree')
    tree.value = res.data.data || []
    if (!selectedId.value && flatNodes.value.length) {
      selectedId.value = flatNodes.value[0].id
    }
  } catch (e) {
    msg.value = apiError(e)
  } finally {
    treeReady.value = true
  }
}

async function loadDetailTabs() {
  if (!selectedId.value) return
  const id = selectedId.value
  try {
    const [m, a, an, s] = await Promise.all([
      http.get(`/ip-group/${id}/members`),
      http.get(`/ip-group/${id}/accounts`),
      http.get(`/ip-group/${id}/anchors`),
      http.get(`/ip-group/${id}/stats`),
    ])
    members.value = m.data.data || []
    accounts.value = a.data.data || []
    anchors.value = an.data.data || []
    stats.value = s.data.data || {}
  } catch (e) {
    msg.value = apiError(e)
  }
}

function apiError(error: unknown) {
  if (error && typeof error === 'object' && 'code' in error) {
    const body = error as { code?: number; msg?: string }
    if (body.code) return `${body.code} ${body.msg || ''}`.trim()
  }
  return errorMessage(error)
}

function selectGroup(id: number) {
  selectedId.value = id
}

async function toggleStatus() {
  if (!selectedId.value || !detail.value) return
  const next = detail.value.status === 1 ? 0 : 1
  const label = next === 1 ? '启用' : '停用'
  try {
    await http.put('/ip-group/update', { id: selectedId.value, status: next })
    msg.value = `状态已更新为「${label}」`
    const current = selectedId.value
    await loadTree()
    selectedId.value = current
  } catch (e) {
    msg.value = apiError(e)
  }
}

async function loadUsers() {
  try {
    const res = await http.get('/system/user/page', { params: { pageNo: 1, pageSize: 100, status: 'ENABLED' } })
    const list = (res.data.data?.list || []) as { id: string | number; nickname?: string; username?: string }[]
    users.value = list.map((user) => ({
      id: Number(user.id),
      nickname: user.nickname || '',
      username: user.username || '',
    }))
  } catch (e) {
    msg.value = apiError(e)
  }
}

async function loadDict(dictType: string) {
  const res = await http.get('/system/dict-data/list', { params: { dictType } })
  const list = (res.data.data || []) as { dictValue: string; dictLabel: string; status: string }[]
  return list.filter((item) => item.status === 'ENABLED')
}

async function loadLevels() {
  try {
    levels.value = await loadDict('dict_ip_group_level')
  } catch {
    levels.value = [
      { dictValue: 'S', dictLabel: 'S级' },
      { dictValue: 'A', dictLabel: 'A级' },
      { dictValue: 'B', dictLabel: 'B级' },
      { dictValue: 'C', dictLabel: 'C级' },
    ]
  }
}

async function loadPositions() {
  try {
    positions.value = await loadDict('dict_position')
  } catch {
    positions.value = []
  }
}

function openCreate(type: 'BIG' | 'SMALL', parentId?: number) {
  groupMode.value = 'create'
  createType.value = type
  createForm.value = {
    groupName: '',
    parentId: parentId ? String(parentId) : '',
    leaderUserId: '',
    level: '',
    description: '',
    sortOrder: '0',
  }
  formErrors.value = {}
  leaderKeyword.value = ''
  creating.value = true
  loadUsers()
}

function openEdit() {
  if (!detail.value) return
  groupMode.value = 'edit'
  createType.value = detail.value.groupType === 'BIG' ? 'BIG' : 'SMALL'
  createForm.value = {
    groupName: detail.value.groupName,
    parentId: detail.value.parentId ? String(detail.value.parentId) : '',
    leaderUserId: detail.value.leaderUserId ? String(detail.value.leaderUserId) : '',
    level: detail.value.level || '',
    description: detail.value.remark || '',
    sortOrder: String(detail.value.sortOrder ?? 0),
  }
  formErrors.value = {}
  leaderKeyword.value = ''
  creating.value = true
  loadUsers()
}

function validateCreate() {
  const errors: Record<string, string> = {}
  const name = createForm.value.groupName.trim()
  if (!name) errors.groupName = '必填项，请填写'
  else if (name.length > 50) errors.groupName = '名称长度 1-50 字符'
  if (createType.value === 'SMALL' && !createForm.value.parentId) errors.parentId = '必填项，请填写'
  if (createForm.value.description.trim().length > 200) errors.description = '描述长度 0-200 字符'
  formErrors.value = errors
  return Object.keys(errors).length === 0
}

async function submitGroup() {
  if (!validateCreate()) return
  const leader = createForm.value.leaderUserId ? Number(createForm.value.leaderUserId) : null
  const payload = {
    groupName: createForm.value.groupName.trim(),
    parentId: createType.value === 'SMALL' ? Number(createForm.value.parentId) : null,
    leaderUserId: leader,
    level: createForm.value.level,
    description: createForm.value.description.trim(),
    sortOrder: Number(createForm.value.sortOrder || 0),
  }
  try {
    if (groupMode.value === 'edit' && selectedId.value) {
      await http.put('/ip-group/update', { id: selectedId.value, ...payload })
      creating.value = false
      msg.value = '已保存'
      const current = selectedId.value
      await loadTree()
      selectedId.value = current
      return
    }
    const res = await http.post('/ip-group/create', {
      ...payload,
      groupType: createType.value,
      status: 1,
    })
    creating.value = false
    msg.value = '已创建 IP 组'
    await loadTree()
    selectedId.value = Number(res.data.data)
  } catch (e) {
    msg.value = apiError(e)
  }
}

function openAddMember() {
  memberMode.value = 'add'
  editingMemberId.value = null
  memberForm.value = { userId: '', position: '', relationType: 'PRIMARY' }
  memberErrors.value = {}
  memberKeyword.value = ''
  memberOpen.value = true
  loadUsers()
}

function openEditMember(member: { id: number; userId: number; position: string; relationType: string }) {
  memberMode.value = 'edit'
  editingMemberId.value = member.id
  memberForm.value = {
    userId: String(member.userId),
    position: member.position || '',
    relationType: member.relationType || 'PRIMARY',
  }
  memberErrors.value = {}
  memberKeyword.value = ''
  memberOpen.value = true
  loadUsers()
}

function validateMember() {
  const errors: Record<string, string> = {}
  if (!memberForm.value.userId) errors.userId = '必填项，请填写'
  if (!memberForm.value.position) errors.position = '必填项，请填写'
  memberErrors.value = errors
  return Object.keys(errors).length === 0
}

async function refreshMembers() {
  const current = selectedId.value
  await loadTree()
  selectedId.value = current
  await loadDetailTabs()
}

async function submitMember() {
  if (!selectedId.value || !validateMember()) return
  try {
    if (memberMode.value === 'edit' && editingMemberId.value) {
      await http.put(`/ip-group/${selectedId.value}/members/${editingMemberId.value}`, {
        position: memberForm.value.position,
        relationType: memberForm.value.relationType || 'PRIMARY',
      })
      msg.value = '成员已保存'
    } else {
      await http.post(`/ip-group/${selectedId.value}/members`, {
        userId: Number(memberForm.value.userId),
        position: memberForm.value.position,
        relationType: memberForm.value.relationType || 'PRIMARY',
      })
      msg.value = '已添加成员'
    }
    memberOpen.value = false
    await refreshMembers()
  } catch (e) {
    msg.value = apiError(e)
  }
}

function askRemoveMember(member: { id: number; userName: string }) {
  if (!selectedId.value) return
  const groupId = selectedId.value
  confirming.value = {
    title: '移除成员',
    message: `确认移除成员「${member.userName || ''}」？`,
    run: () => {
      confirming.value = null
      removeMember(groupId, member.id)
    },
  }
}

async function removeMember(groupId: number, memberId: number) {
  try {
    await http.delete(`/ip-group/${groupId}/members/${memberId}`)
    msg.value = '成员已移除'
    await refreshMembers()
  } catch (e) {
    msg.value = apiError(e)
  }
}

async function bindAccount() {
  if (!selectedId.value || !bindAccountId.value) return
  try {
    await http.post(`/ip-group/${selectedId.value}/accounts`, { accountIds: [bindAccountId.value] })
    msg.value = '账号已关联'
    bindAccountId.value = undefined
    await loadDetailTabs()
    await loadTree()
  } catch (e) {
    msg.value = apiError(e)
  }
}

async function bindAuthor() {
  if (!selectedId.value || !bindAuthorId.value) return
  try {
    await http.post(`/ip-group/${selectedId.value}/anchors`, {
      anchorUserIds: [bindAuthorId.value],
      isPrimary: true,
    })
    msg.value = '作者已绑定'
    bindAuthorId.value = undefined
    await loadDetailTabs()
    await loadTree()
  } catch (e) {
    msg.value = apiError(e)
  }
}

function askRemove() {
  if (!selectedId.value || !detail.value) return
  const id = selectedId.value
  const name = detail.value.groupName
  confirming.value = {
    title: '删除确认',
    message: `确认删除 IP 组「${name}」？`,
    run: () => {
      confirming.value = null
      removeGroup(id)
    },
  }
}

async function removeGroup(id: number) {
  try {
    await http.delete('/ip-group/delete', { params: { id } })
    msg.value = 'IP 组已删除'
    if (selectedId.value === id) selectedId.value = null
    await loadTree()
  } catch (e) {
    msg.value = apiError(e)
  }
}

watch(selectedId, () => {
  loadDetailTabs()
})

onMounted(async () => {
  await Promise.all([loadTree(), loadLevels(), loadPositions()])
  await loadDetailTabs()
})
</script>
