<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>培训资料库</h1>
        <div class="sub">TRAIN-001 · DOC/VIDEO/LINK · 02 TRAIN</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">上传资料</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">岗位分类树只读展示；资料按分类维护，支持发布/下架。</p>
    <div class="g2" style="margin-bottom: 12px; align-items: flex-start">
      <div class="card" style="padding: 12px; max-height: 280px; overflow: auto">
        <div style="font-weight: 600; margin-bottom: 8px">分类树</div>
        <ul v-if="cates.length" class="tree">
          <li v-for="root in cates" :key="root.id">
            <span>{{ root.cateName }} <small>({{ root.positionCode }})</small></span>
            <ul>
              <li v-for="child in root.children" :key="child.id">
                <button type="button" class="linkish" @click="pickCate(child)">
                  {{ child.cateName }} · {{ child.materialCount }}
                </button>
              </li>
            </ul>
          </li>
        </ul>
        <div v-else class="empty"><div class="et">加载分类…</div></div>
      </div>
      <div style="flex: 1">
        <form class="qbar" @submit.prevent="loadList">
          <input v-model="filters.title" placeholder="标题" style="width: 140px" />
          <select v-model="filters.materialType" style="width: 100px">
            <option value="">全部类型</option>
            <option value="DOC">文档</option>
            <option value="VIDEO">视频</option>
            <option value="LINK">链接</option>
          </select>
          <select v-model="filters.status" style="width: 100px">
            <option value="">全部状态</option>
            <option value="DRAFT">草稿</option>
            <option value="PUBLISHED">已发布</option>
            <option value="OFFLINE">已下架</option>
          </select>
          <span class="sp"></span>
          <button class="btn btn-pri btn-sm" type="submit">查询</button>
        </form>
        <div class="tbl-block">
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>编号</th>
                  <th>标题</th>
                  <th>类型</th>
                  <th>状态</th>
                  <th>上传人</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading">
                  <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
                </tr>
                <tr v-else-if="!rows.length">
                  <td colspan="6"><div class="empty"><div class="et">{{ error || '暂无资料' }}</div></div></td>
                </tr>
                <tr v-for="row in rows" v-else :key="row.id">
                  <td class="mono">{{ row.materialNo }}</td>
                  <td style="font-weight: 500">{{ row.title }}</td>
                  <td>{{ row.materialType }}</td>
                  <td>{{ row.status }}</td>
                  <td>{{ row.uploaderName }}</td>
                  <td>
                    <button
                      v-if="row.status !== 'OFFLINE'"
                      class="btn btn-sec btn-sm"
                      type="button"
                      @click="offline(row)"
                    >
                      下架
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
        <h3 style="margin: 0 0 12px">上传资料</h3>
        <label class="fld">分类 ID</label>
        <input v-model.number="form.cateId" type="number" class="fld-in" />
        <label class="fld">标题</label>
        <input v-model="form.title" class="fld-in" />
        <label class="fld">类型</label>
        <select v-model="form.materialType" class="fld-in">
          <option value="DOC">DOC</option>
          <option value="VIDEO">VIDEO</option>
          <option value="LINK">LINK</option>
        </select>
        <label v-if="form.materialType === 'LINK'" class="fld">外链</label>
        <input v-if="form.materialType === 'LINK'" v-model="form.linkUrl" class="fld-in" />
        <template v-else>
          <label class="fld">fileKey</label>
          <input v-model="form.fileKey" class="fld-in" placeholder="直传回执 key" />
        </template>
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-sec btn-sm" type="button" @click="submit(false)">草稿</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submit(true)">发布</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type Cate = {
  id: number
  cateName: string
  positionCode?: string
  materialCount: number
  children: Cate[]
}

type Row = {
  id: number
  materialNo: string
  title: string
  materialType: string
  status: string
  uploaderName: string
}

const cates = ref<Cate[]>([])
const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const formError = ref('')
const filters = reactive({ title: '', materialType: '', status: '', cateId: 0 })
const form = reactive({
  cateId: 0,
  title: '',
  materialType: 'DOC',
  fileKey: 'demo/file.pdf',
  linkUrl: '',
})

async function loadCates() {
  const res = await http.get('/train/material/cates')
  if (res.data.code === 0) cates.value = res.data.data || []
}

function pickCate(child: Cate) {
  filters.cateId = child.id
  form.cateId = child.id
  loadList()
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 30 }
    if (filters.title) params.title = filters.title
    if (filters.materialType) params.materialType = filters.materialType
    if (filters.status) params.status = filters.status
    if (filters.cateId) params.cateId = filters.cateId
    const res = await http.get('/train/material/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data.list || []
  } catch {
    error.value = '网络错误'
    rows.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.title = ''
  form.materialType = 'DOC'
  form.fileKey = 'demo/file.pdf'
  form.linkUrl = ''
  if (!form.cateId && cates.value[0]?.children?.[0]) {
    form.cateId = cates.value[0].children[0].id
  }
  formError.value = ''
  showForm.value = true
}

async function submit(publish: boolean) {
  formError.value = ''
  if (!form.title.trim() || !form.cateId) {
    formError.value = '标题与分类必填'
    return
  }
  const body: Record<string, unknown> = {
    title: form.title.trim(),
    cateId: form.cateId,
    materialType: form.materialType,
    positionCodes: [],
    publish,
  }
  if (form.materialType === 'LINK') body.linkUrl = form.linkUrl
  else body.fileKey = form.fileKey
  const res = await http.post('/train/material', body)
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showForm.value = false
  await loadCates()
  await loadList()
}

async function offline(row: Row) {
  if (!confirm(`下架「${row.title}」？`)) return
  const res = await http.delete(`/train/material/${row.id}`)
  if (res.data.code === 0) await loadList()
}

onMounted(async () => {
  await loadCates()
  await loadList()
})
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.tree {
  list-style: none;
  padding-left: 0;
  font-size: 13px;
}
.tree ul {
  padding-left: 16px;
}
.linkish {
  background: none;
  border: none;
  color: var(--blue);
  cursor: pointer;
  padding: 0;
  font-size: 13px;
}
.fld {
  display: block;
  font-size: 12px;
  color: var(--text2);
  margin: 8px 0 4px;
}
.fld-in {
  width: 100%;
  box-sizing: border-box;
}
.g2 {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 12px;
}
</style>
