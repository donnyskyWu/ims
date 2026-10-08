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
    <p v-if="msg" class="hint" style="margin-bottom: 10px">{{ msg }}</p>
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
                <span v-if="node.level" class="lv">{{ node.level }}级</span>
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
                    <span class="dot"></span>{{ detail.level }}级
                  </span>
                </div>
                <h2>{{ detail.groupName }}</h2>
                <div class="ipg-detail-meta">
                  <span>组长：{{ detail.leaderUserName || '—' }}</span>
                  <span>上级：{{ parentName || '—' }}</span>
                </div>
              </div>
              <div class="acts">
                <button v-if="detail.groupType === 'BIG'" class="btn btn-sec btn-sm" type="button" @click="openCreate('SMALL', detail.id)">
                  + 新建小组
                </button>
                <button class="btn btn-sec btn-sm" type="button" @click="removeGroup">删除</button>
              </div>
            </div>
          </div>
          <div class="ipg-detail-body">
            <div class="tabs">
              <div v-for="t in tabs" :key="t" class="tab" :class="{ on: tab === t }" @click="tab = t">{{ t }}</div>
            </div>
            <table v-if="tab === '基本信息'" class="ipg-info-grid">
              <tbody>
                <tr><td class="lbl">组名</td><td>{{ detail.groupName }}</td></tr>
                <tr><td class="lbl">组类型</td><td>{{ detail.groupType === 'BIG' ? '大组' : '小组' }}</td></tr>
                <tr><td class="lbl">等级</td><td>{{ detail.level || '—' }}</td></tr>
                <tr><td class="lbl">状态</td><td>{{ detail.status === 1 ? '启用' : '停用' }}</td></tr>
                <tr><td class="lbl">备注</td><td>{{ detail.remark || '—' }}</td></tr>
              </tbody>
            </table>
            <div v-else-if="tab === '成员管理'" class="tbl-block">
              <div class="acts" style="margin: 12px 0">
                <button class="btn btn-pri btn-sm" type="button" @click="addMember">+ 添加成员（管理员 id=1）</button>
              </div>
              <div class="tbl-wrap">
                <table>
                  <thead>
                    <tr><th>姓名</th><th>岗位</th><th>主/兼</th><th>组长</th></tr>
                  </thead>
                  <tbody>
                    <tr v-if="!members.length"><td colspan="4"><div class="empty"><div class="et">暂无成员</div></div></td></tr>
                    <tr v-for="m in members" :key="m.id">
                      <td>{{ m.userName }}</td>
                      <td>{{ m.position }}</td>
                      <td>{{ m.relationType }}</td>
                      <td>{{ m.isLeader ? '是' : '否' }}</td>
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
    <div v-if="creating" class="drawer on">
      <div class="drawer-mask" @click="creating = false"></div>
      <div class="drawer-panel">
        <h3>{{ createType === 'BIG' ? '新建大组' : '新建小组' }}</h3>
        <div class="formrow one">
          <div class="fld"><label>组名</label><input v-model="createForm.groupName" /></div>
        </div>
        <div v-if="createType === 'SMALL'" class="formrow one">
          <div class="fld"><label>上级大组 id</label><input v-model.number="createForm.parentId" /></div>
        </div>
        <div class="formrow one">
          <div class="fld"><label>等级</label><input v-model="createForm.level" placeholder="S/A/B/C" /></div>
        </div>
        <div class="acts" style="margin-top: 16px">
          <button class="btn btn-pri" type="button" @click="submitCreate">确定</button>
          <button class="btn btn-sec" type="button" @click="creating = false">取消</button>
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
  level?: string
  status?: number
  remark?: string
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
const bindAccountId = ref<number | undefined>()
const bindAuthorId = ref<number | undefined>()
const creating = ref(false)
const createType = ref<'BIG' | 'SMALL'>('BIG')
const createForm = ref({ groupName: '', parentId: undefined as number | undefined, level: '' })

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
    msg.value = errorMessage(e)
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
    msg.value = errorMessage(e)
  }
}

function selectGroup(id: number) {
  selectedId.value = id
}

function openCreate(type: 'BIG' | 'SMALL', parentId?: number) {
  createType.value = type
  createForm.value = { groupName: '', parentId, level: '' }
  creating.value = true
}

async function submitCreate() {
  try {
    await http.post('/ip-group/create', {
      groupName: createForm.value.groupName,
      groupType: createType.value,
      parentId: createType.value === 'SMALL' ? createForm.value.parentId : null,
      leaderUserId: 1,
      level: createForm.value.level,
      status: 1,
    })
    creating.value = false
    msg.value = '已创建 IP 组'
    await loadTree()
  } catch (e) {
    msg.value = errorMessage(e)
  }
}

async function addMember() {
  if (!selectedId.value) return
  try {
    await http.post(`/ip-group/${selectedId.value}/members`, {
      userId: 1,
      position: 'OPERATOR',
      relationType: 'PRIMARY',
    })
    msg.value = '已添加成员'
    await loadDetailTabs()
    await loadTree()
  } catch (e) {
    msg.value = errorMessage(e)
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
    msg.value = errorMessage(e)
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
    msg.value = errorMessage(e)
  }
}

async function removeGroup() {
  if (!selectedId.value) return
  try {
    await http.delete('/ip-group/delete', { params: { id: selectedId.value } })
    msg.value = '已删除'
    selectedId.value = null
    await loadTree()
  } catch (e) {
    msg.value = errorMessage(e)
  }
}

watch(selectedId, () => {
  loadDetailTabs()
})

onMounted(async () => {
  await loadTree()
  await loadDetailTabs()
})
</script>
