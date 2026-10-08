<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>知识库</h1>
        <div class="sub">AIR · 分类树 + 入库审批（无检索）· 20 AIR</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="toggleAudit">
          {{ showAudit ? '全部文档' : '待审批' }}
        </button>
        <button class="btn btn-pri btn-sm" type="button" @click="openUpload">上传文件</button>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 220px 1fr; gap: 16px; align-items: start">
      <div class="card" style="padding: 12px">
        <div style="font-weight: 600; margin-bottom: 8px">知识目录</div>
        <div v-if="!tree.length" class="hint">加载目录…</div>
        <ul v-else style="list-style: none; padding: 0; margin: 0; font-size: 13px">
          <li
            style="padding: 4px 6px; cursor: pointer; border-radius: 6px"
            :style="{ background: selectedCateId === 0 ? 'var(--blue-bg)' : '' }"
            @click="selectCate(0)"
          >
            全部 · {{ tree[0]?.docCount ?? 0 }}
          </li>
          <template v-for="c1 in tree[0]?.children || []" :key="c1.id">
            <li
              style="padding: 4px 6px 4px 10px; cursor: pointer; border-radius: 6px"
              :style="{ background: selectedCateId === c1.id ? 'var(--blue-bg)' : '' }"
              @click="selectCate(c1.id)"
            >
              {{ c1.categoryName }} · {{ c1.docCount }}
            </li>
            <li
              v-for="c2 in c1.children || []"
              :key="c2.id"
              style="padding: 2px 6px 2px 22px; cursor: pointer; border-radius: 6px; color: var(--text2)"
              :style="{ background: selectedCateId === c2.id ? 'var(--blue-bg)' : '', color: selectedCateId === c2.id ? 'inherit' : '' }"
              @click="selectCate(c2.id)"
            >
              {{ c2.categoryName }} · {{ c2.docCount }}
            </li>
          </template>
        </ul>
      </div>

      <div>
        <form class="qbar" @submit.prevent="loadList">
          <input v-model="filters.title" placeholder="文档标题" style="width: 160px" />
          <span class="sp"></span>
          <button class="btn btn-pri btn-sm" type="submit">查询</button>
        </form>

        <div class="tbl-block">
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>标题</th>
                  <th>状态</th>
                  <th>上传人</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading">
                  <td colspan="5"><div class="empty"><div class="et">加载中</div></div></td>
                </tr>
                <tr v-else-if="!rows.length">
                  <td colspan="5"><div class="empty"><div class="et">{{ error || '暂无文档' }}</div></div></td>
                </tr>
                <tr v-for="row in rows" v-else :key="row.id">
                  <td class="mono">{{ row.id }}</td>
                  <td style="font-weight: 500">{{ row.title }}</td>
                  <td>{{ row.auditStatus }}</td>
                  <td>{{ row.uploaderName }}</td>
                  <td>
                    <button
                      v-if="row.auditStatus === 'PENDING'"
                      class="btn btn-pri btn-sm"
                      type="button"
                      @click="auditDoc(row.id, true)"
                    >
                      通过
                    </button>
                    <button
                      v-if="row.auditStatus === 'PENDING'"
                      class="btn btn-sec btn-sm"
                      type="button"
                      @click="auditDoc(row.id, false)"
                    >
                      驳回
                    </button>
                    <button
                      v-if="row.auditStatus === 'PUBLISHED'"
                      class="btn btn-sec btn-sm"
                      type="button"
                      @click="downloadStub(row.id)"
                    >
                      下载
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 400px; padding: 20px">
        <h3 style="margin: 0 0 12px">上传入库（审批 PENDING）</h3>
        <label class="fld">标题</label>
        <input v-model="form.title" class="fld-in" />
        <label class="fld">fileKey（相对路径）</label>
        <input v-model="form.fileKey" class="fld-in" placeholder="kb/2026/demo.pdf" />
        <label class="fld">分类 ID（可选）</label>
        <input v-model.number="form.cateId" class="fld-in" type="number" />
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitUpload">提交</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type TreeKb = {
  id: number
  kbName: string
  docCount: number
  children: {
    id: number
    categoryName: string
    docCount: number
    children?: { id: number; categoryName: string; docCount: number }[]
  }[]
}

type Row = {
  id: number
  title: string
  fileKey: string
  auditStatus: string
  uploaderName: string
}

const tree = ref<TreeKb[]>([])
const kbId = ref(0)
const selectedCateId = ref(0)
const showAudit = ref(false)
const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const formError = ref('')
const filters = reactive({ title: '' })
const form = reactive({ title: '', fileKey: '', cateId: 0 })

async function loadTree() {
  try {
    const res = await http.get('/air/kb/tree')
    if (res.data.code === 0) {
      tree.value = res.data.data || []
      kbId.value = tree.value[0]?.id || 0
    }
  } catch {
    /* ignore */
  }
}

function selectCate(id: number) {
  selectedCateId.value = id
  loadList()
}

function toggleAudit() {
  showAudit.value = !showAudit.value
  loadList()
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/air/kb/page', {
      params: {
        pageNo: 1,
        pageSize: 20,
        kbId: kbId.value || undefined,
        categoryId: selectedCateId.value || undefined,
        title: filters.title || undefined,
        docStatus: showAudit.value ? 'PENDING' : undefined,
      },
    })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data?.list || []
  } catch {
    error.value = '网络错误'
  } finally {
    loading.value = false
  }
}

function openUpload() {
  form.title = ''
  form.fileKey = ''
  form.cateId = selectedCateId.value || 0
  formError.value = ''
  showForm.value = true
}

async function submitUpload() {
  formError.value = ''
  try {
    const res = await http.post('/air/kb/doc/upload', {
      ...form,
      kbId: kbId.value,
    })
    if (res.data.code !== 0) {
      formError.value = res.data.msg || '上传失败'
      return
    }
    showForm.value = false
    await loadTree()
    await loadList()
  } catch {
    formError.value = '网络错误'
  }
}

async function auditDoc(docId: number, approve: boolean) {
  let auditNote = ''
  if (!approve) {
    auditNote = window.prompt('驳回原因（必填）') || ''
    if (!auditNote.trim()) return
  }
  try {
    const res = await http.post('/air/kb/doc/audit', { docId, approve, auditNote })
    if (res.data.code === 0) {
      await loadTree()
      await loadList()
    }
  } catch {
    /* ignore */
  }
}

async function downloadStub(id: number) {
  try {
    const res = await http.get(`/air/kb/doc/${id}/download`)
    if (res.data.code === 0) {
      window.alert(`下载桩：${res.data.data.downloadUrl}`)
    } else {
      window.alert(res.data.msg || '不可下载')
    }
  } catch {
    /* ignore */
  }
}

onMounted(async () => {
  await loadTree()
  await loadList()
})
</script>
