<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>知识库</h1>
        <div class="sub" data-testid="air-kb-note">仅文件管理，本期不含检索</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="air-kb-create" @click="openCreate">新增知识库</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="air-kb-cat" @click="openCategory">分类管理</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="air-kb-upload" @click="openUpload">上传资料</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="air-kb-transfer" @click="openTransfer">从系统转入</button>
      </div>
    </div>

    <p v-if="toast" class="hint" data-testid="air-kb-toast">{{ toast }}</p>

    <div style="display: grid; grid-template-columns: 228px 1fr; gap: 16px; align-items: start">
      <div class="card" style="padding: 12px" data-testid="air-kb-tree">
        <div style="font-weight: 600; margin-bottom: 8px">知识目录</div>
        <div v-if="!tree.length" class="hint">加载目录…</div>
        <ul v-else style="list-style: none; padding: 0; margin: 0; font-size: 13px">
          <li v-for="kb in tree" :key="kb.id" style="margin-bottom: 6px">
            <div
              style="padding: 4px 6px; cursor: pointer; border-radius: 6px; display: flex; justify-content: space-between; gap: 6px"
              :style="{ background: selectedKbId === kb.id && !selectedCateId ? 'var(--blue-bg)' : '' }"
              :data-testid="'air-kb-node-' + kb.id"
              @click="selectKb(kb.id)"
            >
              <span>{{ kb.kbName }} · {{ kb.docCount }}</span>
              <span class="tag" :data-secret="kb.secretLevel">{{ kb.secretLabel || secretLabel(kb.secretLevel) }}</span>
            </div>
            <div
              v-for="c1 in kb.children || []"
              :key="c1.id"
            >
              <div
                style="padding: 3px 6px 3px 16px; cursor: pointer; border-radius: 6px"
                :style="{ background: selectedCateId === c1.id ? 'var(--blue-bg)' : '' }"
                @click="selectCate(kb.id, c1.id)"
              >
                {{ c1.categoryName }} · {{ c1.docCount }}
              </div>
              <div
                v-for="c2 in c1.children || []"
                :key="c2.id"
                style="padding: 2px 6px 2px 28px; cursor: pointer; border-radius: 6px; color: var(--text2)"
                :style="{ background: selectedCateId === c2.id ? 'var(--blue-bg)' : '' }"
                @click="selectCate(kb.id, c2.id)"
              >
                {{ c2.categoryName }} · {{ c2.docCount }}
              </div>
            </div>
          </li>
        </ul>
      </div>

      <div>
        <form class="qbar" @submit.prevent="reload">
          <input v-model="filters.keyword" placeholder="库编号/名称" style="width: 140px" data-testid="air-kb-keyword" />
          <select v-model="filters.secretLevel" style="width: 110px" data-testid="air-kb-secret-filter">
            <option value="">全部密级</option>
            <option v-for="item in secretOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
          <select v-model="filters.status" style="width: 130px" data-testid="air-kb-status-filter">
            <option value="">全部状态</option>
            <option value="PUBLISHED">已发布</option>
            <option value="PENDING">入库审批中</option>
            <option value="DRAFT">草稿</option>
          </select>
          <span class="sp"></span>
          <button class="btn btn-pri btn-sm" type="submit">查询</button>
        </form>

        <div v-if="selectedCateId" class="tbl-block">
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>标题</th>
                  <th>密级</th>
                  <th>来源</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading"><td colspan="5"><div class="empty"><div class="et">加载中</div></div></td></tr>
                <tr v-else-if="!docs.length"><td colspan="5"><div class="empty"><div class="et">该分类下暂无资料</div></div></td></tr>
                <tr v-for="row in docs" v-else :key="row.id">
                  <td style="font-weight: 500">{{ row.title }}</td>
                  <td>{{ row.secretLabel || '—' }}</td>
                  <td>{{ row.sourceLabel || row.sourceType }}</td>
                  <td>{{ docStatusLabel(row.auditStatus) }}</td>
                  <td>
                    <button class="btn btn-sec btn-sm" type="button" @click="openDoc(row)">详情</button>
                    <button v-if="row.auditStatus === 'PUBLISHED'" class="btn btn-sec btn-sm" type="button" @click="downloadDoc(row.id)">下载</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-else class="tbl-block">
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>库编号</th>
                  <th>知识库名称</th>
                  <th>密级</th>
                  <th>文档数</th>
                  <th>大小</th>
                  <th>状态</th>
                  <th>责任人</th>
                  <th>更新时间</th>
                  <th>授权</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading"><td colspan="10"><div class="empty"><div class="et">加载中</div></div></td></tr>
                <tr v-else-if="!rows.length"><td colspan="10"><div class="empty"><div class="et">{{ error || '暂无知识库' }}</div></div></td></tr>
                <tr v-for="row in rows" v-else :key="row.id" data-testid="air-kb-row">
                  <td class="mono" style="color: var(--blue); cursor: pointer" @click="openDetail(row.id)">{{ row.kbNo }}</td>
                  <td style="font-weight: 500">{{ row.kbName }}</td>
                  <td>
                    {{ row.secretLabel }}
                    <div v-if="row.grantsLimit" class="hint">{{ row.grantsLimit }}</div>
                  </td>
                  <td class="num">{{ row.docCount }}</td>
                  <td class="num">{{ row.sizeLabel }}</td>
                  <td>{{ row.statusLabel }}</td>
                  <td>{{ row.ownerName }}</td>
                  <td>{{ row.updatedAt }}</td>
                  <td class="num">{{ row.grantCount }}</td>
                  <td>
                    <button v-if="row.status === 'PENDING'" class="btn btn-pri btn-sm" type="button" data-testid="air-kb-audit" @click="openAudit(row)">审批</button>
                    <button class="btn btn-sec btn-sm" type="button" data-testid="air-kb-detail" @click="openDetail(row.id)">详情</button>
                    <button v-if="row.status === 'PUBLISHED'" class="btn btn-sec btn-sm" type="button" data-testid="air-kb-grant" @click="openGrant(row)">授权</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showCreate" class="modal-mask" @click.self="showCreate = false">
      <div class="card" style="width: 520px; padding: 20px" data-testid="air-kb-create-form">
        <h3 style="margin: 0 0 12px">新增知识库</h3>
        <label class="fld">知识库名称 <i class="req">*</i></label>
        <input v-model="createForm.kbName" class="fld-in" data-testid="air-kb-name" />
        <p v-if="createErrors.kbName" class="hint bad">{{ createErrors.kbName }}</p>
        <label class="fld">密级 <i class="req">*</i></label>
        <select v-model="createForm.secretLevel" class="fld-in" data-testid="air-kb-secret">
          <option value="">请选择</option>
          <option v-for="item in secretOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <p v-if="createErrors.secretLevel" class="hint bad">{{ createErrors.secretLevel }}</p>
        <label class="fld">底座 Provider</label>
        <input class="fld-in" value="LOCAL（IMS 本地对象存储）" disabled />
        <label class="fld">责任人 <i class="req">*</i></label>
        <select v-model="createForm.ownerUserId" class="fld-in" data-testid="air-kb-owner">
          <option value="">请选择</option>
          <option v-for="user in users" :key="user.id" :value="String(user.id)">{{ user.label }}</option>
        </select>
        <p v-if="createErrors.ownerUserId" class="hint bad">{{ createErrors.ownerUserId }}</p>
        <label class="fld">描述</label>
        <textarea v-model="createForm.desc" class="fld-in" rows="3" />
        <p v-if="createErrors.form" class="hint bad">{{ createErrors.form }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showCreate = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-kb-create-save" @click="submitCreate">创建</button>
        </div>
      </div>
    </div>

    <div v-if="showCategory" class="modal-mask" @click.self="showCategory = false">
      <div class="card" style="width: 520px; padding: 20px; max-height: 86vh; overflow: auto" data-testid="air-kb-cat-form">
        <h3 style="margin: 0 0 12px">分类管理</h3>
        <label class="fld">目标知识库</label>
        <select v-model="catKbId" class="fld-in" @change="loadCategoryNodes">
          <option v-for="kb in tree" :key="kb.id" :value="String(kb.id)">{{ kb.kbName }}（{{ kb.kbNo }}）</option>
        </select>
        <div class="hint" style="margin: 8px 0">当前分类</div>
        <div v-if="!flatCats.length" class="hint">暂无分类，请在下方新增</div>
        <div v-for="item in flatCats" :key="item.id" style="display: flex; justify-content: space-between; gap: 8px; padding: 4px 0">
          <span>{{ item.depth ? '└ ' : '' }}{{ item.categoryName }} · {{ item.docCount }}</span>
          <span>
            <button class="btn btn-sec btn-sm" type="button" @click="startRename(item)">重命名</button>
            <button class="btn btn-sec btn-sm" type="button" @click="askDeleteCat(item)">删除</button>
          </span>
        </div>
        <div v-if="renameId" style="margin-top: 8px">
          <label class="fld">重命名为</label>
          <input v-model="renameName" class="fld-in" />
          <button class="btn btn-pri btn-sm" type="button" style="margin-top: 6px" @click="submitRename">保存名称</button>
        </div>
        <label class="fld">父级</label>
        <select v-model="catParentId" class="fld-in">
          <option value="">（根）</option>
          <option v-for="item in flatCats.filter((row) => row.depth === 0)" :key="item.id" :value="String(item.id)">{{ item.categoryName }}</option>
        </select>
        <label class="fld">分类名称 <i class="req">*</i></label>
        <input v-model="catName" class="fld-in" data-testid="air-kb-cat-name" />
        <p v-if="catError" class="hint bad">{{ catError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showCategory = false">关闭</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-kb-cat-save" @click="submitCategory">新增分类</button>
        </div>
      </div>
    </div>

    <div v-if="deleteCat" class="modal-mask">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 8px">删除分类</h3>
        <p>分类「{{ deleteCat.categoryName }}」下含知识条目时，删除后条目将改挂根分类。</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="deleteCat = null">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="confirmDeleteCat">确认删除</button>
        </div>
      </div>
    </div>

    <div v-if="showUpload" class="modal-mask" @click.self="showUpload = false">
      <div class="card" style="width: 560px; padding: 20px; max-height: 86vh; overflow: auto" data-testid="air-kb-upload-form">
        <h3 style="margin: 0 0 12px">上传资料到知识库</h3>
        <div style="font-weight: 600; margin-bottom: 8px">上传方式</div>
        <div style="display: flex; gap: 8px">
          <button class="btn btn-sm" :class="upload.mode === 'file' ? 'btn-pri' : 'btn-sec'" type="button" data-testid="air-kb-upload-mode-file" @click="upload.mode = 'file'">文件上传</button>
          <button class="btn btn-sm" :class="upload.mode === 'url' ? 'btn-pri' : 'btn-sec'" type="button" data-testid="air-kb-upload-mode-url" @click="upload.mode = 'url'">URL 导入</button>
          <button class="btn btn-sm" :class="upload.mode === 'text' ? 'btn-pri' : 'btn-sec'" type="button" data-testid="air-kb-upload-mode-text" @click="upload.mode = 'text'">粘贴文本</button>
        </div>
        <div style="font-weight: 600; margin: 12px 0 8px">入库信息</div>
        <label class="fld">目标知识库 <i class="req">*</i></label>
        <select v-model="upload.kbId" class="fld-in" data-testid="air-kb-upload-kb">
          <option value="">请选择</option>
          <option v-for="kb in tree" :key="kb.id" :value="String(kb.id)">{{ kb.kbNo }} {{ kb.kbName }}（{{ kb.secretLabel }}）</option>
        </select>
        <p v-if="uploadErrors.kbId" class="hint bad">{{ uploadErrors.kbId }}</p>
        <label class="fld">目标分类</label>
        <select v-model="upload.categoryId" class="fld-in">
          <option value="">（根）</option>
          <option v-for="item in uploadCats" :key="item.id" :value="String(item.id)">{{ item.categoryName }}</option>
        </select>
        <label class="fld">密级</label>
        <select v-model="upload.secretLevel" class="fld-in" data-testid="air-kb-upload-secret">
          <option value="">继承库密级</option>
          <option v-for="item in secretOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <p class="hint">不得低于库密级。上传后进入入库审批。</p>
        <div style="font-weight: 600; margin: 12px 0 8px">内容</div>
        <template v-if="upload.mode === 'file'">
          <label class="fld">选择文件 <i class="req">*</i></label>
          <input class="fld-in" type="file" accept=".pdf,.doc,.docx,.md,.html,.htm,.xls,.xlsx,.txt,.csv" data-testid="air-kb-upload-file" @change="onUploadFile" />
          <p v-if="upload.fileName" class="hint">{{ upload.fileName }}</p>
          <p v-if="uploadErrors.file" class="hint bad" data-testid="air-kb-upload-error">{{ uploadErrors.file }}</p>
        </template>
        <template v-else-if="upload.mode === 'url'">
          <label class="fld">URL 地址 <i class="req">*</i></label>
          <textarea v-model="upload.urls" class="fld-in" rows="4" placeholder="每行一个 URL（http/https）" data-testid="air-kb-upload-urls" />
          <p v-if="uploadErrors.urls" class="hint bad" data-testid="air-kb-upload-error">{{ uploadErrors.urls }}</p>
        </template>
        <template v-else>
          <label class="fld">标题 <i class="req">*</i></label>
          <input v-model="upload.title" class="fld-in" maxlength="128" placeholder="≤128 字" data-testid="air-kb-upload-title" />
          <p v-if="uploadErrors.title" class="hint bad">{{ uploadErrors.title }}</p>
          <label class="fld">正文 <i class="req">*</i></label>
          <textarea v-model="upload.content" class="fld-in" rows="5" placeholder="粘贴纯文本 / Markdown 内容" data-testid="air-kb-upload-content" />
          <p v-if="uploadErrors.content" class="hint bad" data-testid="air-kb-upload-error">{{ uploadErrors.content }}</p>
        </template>
        <p class="hint">三种方式统一写入目标知识库并进入「入库审批中」。仅文件管理，不含解析、向量化与检索。</p>
        <p v-if="uploadErrors.form" class="hint bad" data-testid="air-kb-upload-error">{{ uploadErrors.form }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showUpload = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-kb-upload-save" @click="submitUpload">提交入库</button>
        </div>
      </div>
    </div>

    <div v-if="showTransfer" class="modal-mask" @click.self="showTransfer = false">
      <div class="card" style="width: 720px; padding: 20px; max-height: 86vh; overflow: auto" data-testid="air-kb-transfer-form">
        <h3 style="margin: 0 0 12px">从系统转入知识库</h3>
        <div class="hint">步骤 {{ transfer.step + 1 }} / 4 · {{ ['选择来源', '勾选条目', '目标设置', '提交'][transfer.step] }}</div>
        <div v-if="transfer.step === 0" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 12px">
          <button
            v-for="item in transferSources"
            :key="item.value"
            class="btn btn-sm"
            :class="transfer.source === item.value ? 'btn-pri' : 'btn-sec'"
            type="button"
            @click="transfer.source = item.value"
          >
            {{ item.label }}
          </button>
        </div>
        <div v-else-if="transfer.step === 1" style="margin-top: 12px">
          <p class="hint">已勾选 {{ transfer.picked.length }} 条</p>
          <div v-if="!transfer.items.length" class="hint">该来源暂无条目</div>
          <label v-for="item in transfer.items" :key="item.id" style="display: flex; gap: 8px; padding: 4px 0">
            <input type="checkbox" :checked="transfer.picked.includes(item.id)" @change="togglePicked(item.id)" />
            <span>{{ item.title }} <span v-if="item.imported" class="hint">已转入</span></span>
          </label>
        </div>
        <div v-else-if="transfer.step === 2" style="margin-top: 12px">
          <label class="fld">目标知识库 <i class="req">*</i></label>
          <select v-model="transfer.kbId" class="fld-in">
            <option value="">请选择</option>
            <option v-for="kb in tree" :key="kb.id" :value="String(kb.id)">{{ kb.kbNo }} {{ kb.kbName }}（{{ kb.secretLabel }}）</option>
          </select>
          <p v-if="transfer.error" class="hint bad">{{ transfer.error }}</p>
          <label class="fld">目标分类</label>
          <select v-model="transfer.categoryId" class="fld-in">
            <option value="">（根）</option>
            <option v-for="item in transferCats" :key="item.id" :value="String(item.id)">{{ item.categoryName }}</option>
          </select>
          <label class="fld">密级</label>
          <select v-model="transfer.secretLevel" class="fld-in">
            <option value="">取源资料密级</option>
            <option v-for="item in secretOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
        <div v-else style="margin-top: 12px">
          <p>来源 {{ transferSourceLabel }} · {{ transfer.picked.length }} 条 → {{ transferKbLabel }}</p>
        </div>
        <p v-if="transfer.error && transfer.step !== 2" class="hint bad">{{ transfer.error }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="transferBack">{{ transfer.step === 0 ? '取消' : '上一步' }}</button>
          <button v-if="transfer.step < 3" class="btn btn-pri btn-sm" type="button" data-testid="air-kb-transfer-next" @click="transferNext">下一步</button>
          <button v-else class="btn btn-pri btn-sm" type="button" data-testid="air-kb-transfer-save" @click="submitTransfer">提交入库</button>
        </div>
      </div>
    </div>

    <div v-if="auditKb" class="modal-mask" @click.self="auditKb = null">
      <div class="card" style="width: 480px; padding: 20px" data-testid="air-kb-audit-form">
        <h3 style="margin: 0 0 8px">入库审批 · {{ auditKb.kbName }}</h3>
        <p>密级 {{ auditKb.secretLabel }} · 责任人 {{ auditKb.ownerName }}</p>
        <label class="fld">意见（驳回时必填）</label>
        <textarea v-model="auditNote" class="fld-in" rows="3" data-testid="air-kb-audit-note" />
        <p v-if="auditError" class="hint bad">{{ auditError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="submitAudit(false)">驳回</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-kb-audit-ok" @click="submitAudit(true)">审批通过</button>
        </div>
      </div>
    </div>

    <div v-if="detail" class="modal-mask" @click.self="detail = null">
      <div class="card" style="width: 560px; padding: 20px; max-height: 86vh; overflow: auto" data-testid="air-kb-detail-drawer">
        <h3 style="margin: 0 0 8px">知识库详情 · {{ detail.kbName }}</h3>
        <p>密级 {{ detail.secretLabel }} · 责任人 {{ detail.ownerName }}</p>
        <p>共 {{ detail.docCount }} 份文档，总大小 {{ detail.sizeLabel }}。正文可浏览 / 下载 / 归入分类。</p>
        <div v-for="doc in detail.docs || []" :key="doc.id" style="border-top: 1px solid var(--line); padding: 8px 0">
          <b>{{ doc.title }}</b>
          <div class="hint">{{ docStatusLabel(doc.auditStatus) }} · {{ doc.secretLabel || '继承库密级' }} · {{ doc.sourceLabel }}</div>
          <button class="btn btn-sec btn-sm" type="button" @click="browseDoc = doc">浏览</button>
          <button v-if="doc.auditStatus === 'PUBLISHED'" class="btn btn-sec btn-sm" type="button" @click="downloadDoc(doc.id)">下载</button>
        </div>
        <p v-if="browseDoc" class="hint" data-testid="air-kb-browse">{{ browseDoc.body || browseDoc.fileKey || '暂无正文' }}</p>
        <p class="hint">仅文件管理：本页不含知识检索与向量化。</p>
        <button class="btn btn-sec btn-sm" type="button" @click="detail = null">关闭</button>
      </div>
    </div>

    <div v-if="grantKb" class="modal-mask" @click.self="grantKb = null">
      <div class="card" style="width: 480px; padding: 20px" data-testid="air-kb-grant-form">
        <h3 style="margin: 0 0 8px">知识库授权 · {{ grantKb.kbName }}</h3>
        <p v-if="grantKb.grantsLimit" class="hint">{{ grantKb.grantsLimit }}</p>
        <label class="fld">授权类型</label>
        <select v-model="grantForm.grantType" class="fld-in" @change="onGrantType">
          <option value="PERSON">按人员</option>
          <option value="ROLE">按角色</option>
          <option value="DEPT">按部门</option>
        </select>
        <template v-if="grantForm.grantType === 'PERSON'">
          <label class="fld">人员</label>
          <div style="display: flex; gap: 8px">
            <input v-model="userKeyword" class="fld-in" placeholder="用户名" />
            <button class="btn btn-sec btn-sm" type="button" @click="searchUsers">查找</button>
          </div>
        </template>
        <label class="fld">授权对象 <i class="req">*</i></label>
        <select v-model="grantForm.grantId" class="fld-in" data-testid="air-kb-grant-target">
          <option value="">请选择</option>
          <option v-for="opt in grantOptions" :key="opt.id" :value="opt.id">{{ opt.label }}</option>
        </select>
        <label class="fld">授权有效期</label>
        <input v-model="grantForm.expireAt" class="fld-in" type="date" />
        <p v-if="grantError" class="hint bad" data-testid="air-kb-grant-error">{{ grantError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="grantKb = null">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-kb-grant-save" @click="submitGrant">确认授权</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

type CatNode = { id: number; categoryName: string; docCount: number; children?: CatNode[] }
type TreeKb = {
  id: number
  kbNo: string
  kbName: string
  secretLevel: string
  secretLabel: string
  docCount: number
  children: CatNode[]
}
type KbRow = {
  id: number
  kbNo: string
  kbName: string
  secretLevel: string
  secretLabel: string
  grantsLimit: string
  docCount: number
  sizeLabel: string
  status: string
  statusLabel: string
  ownerName: string
  updatedAt: string
  grantCount: number
}
type DocRow = {
  id: number
  title: string
  fileKey: string
  body: string
  auditStatus: string
  secretLabel: string
  sourceType: string
  sourceLabel: string
}
type UserOpt = { id: string; label: string }
type FlatCat = { id: number; categoryName: string; docCount: number; depth: number }

const secretOptions = [
  { value: 'PUBLIC', label: '公开' },
  { value: 'INTERNAL', label: '内部' },
  { value: 'CONFIDENTIAL', label: '机密' },
  { value: 'TOP_SECRET', label: '绝密' },
]
const transferSources = [
  { value: 'TRAIN', label: '培训资料' },
  { value: 'PERF', label: '绩效考核模板' },
  { value: 'CONTENT', label: '内容记录' },
]

const tree = ref<TreeKb[]>([])
const rows = ref<KbRow[]>([])
const docs = ref<DocRow[]>([])
const users = ref<UserOpt[]>([])
const selectedKbId = ref(0)
const selectedCateId = ref(0)
const loading = ref(false)
const error = ref('')
const toast = ref('')
const filters = reactive({ keyword: '', secretLevel: '', status: '' })

const showCreate = ref(false)
const createForm = reactive({ kbName: '', secretLevel: '', ownerUserId: '', desc: '' })
const createErrors = reactive({ kbName: '', secretLevel: '', ownerUserId: '', form: '' })

const showCategory = ref(false)
const catKbId = ref('')
const catParentId = ref('')
const catName = ref('')
const catError = ref('')
const categoryNodes = ref<CatNode[]>([])
const renameId = ref(0)
const renameName = ref('')
const deleteCat = ref<FlatCat | null>(null)

const FILE_EXTS = ['pdf', 'doc', 'docx', 'md', 'html', 'htm', 'xls', 'xlsx', 'txt', 'csv']
const showUpload = ref(false)
const upload = reactive({
  mode: 'file' as 'file' | 'url' | 'text',
  kbId: '',
  categoryId: '',
  secretLevel: '',
  fileName: '',
  fileSize: 0,
  contentType: '',
  urls: '',
  title: '',
  content: '',
})
const uploadErrors = reactive({ kbId: '', file: '', urls: '', title: '', content: '', form: '' })

const showTransfer = ref(false)
const transfer = reactive({
  step: 0,
  source: '',
  items: [] as Array<{ id: number; title: string; imported?: boolean }>,
  picked: [] as number[],
  kbId: '',
  categoryId: '',
  secretLevel: '',
  error: '',
})

const auditKb = ref<KbRow | null>(null)
const auditNote = ref('')
const auditError = ref('')
const detail = ref<(KbRow & { docs?: DocRow[] }) | null>(null)
const browseDoc = ref<DocRow | null>(null)
const grantKb = ref<KbRow | null>(null)
const grantForm = reactive({ grantType: 'PERSON', grantId: '', expireAt: '' })
const grantOptions = ref<UserOpt[]>([])
const grantError = ref('')
const userKeyword = ref('')

const flatCats = computed(() => {
  const list: FlatCat[] = []
  for (const node of categoryNodes.value) {
    list.push({ id: node.id, categoryName: node.categoryName, docCount: node.docCount, depth: 0 })
    for (const child of node.children || []) {
      list.push({ id: child.id, categoryName: child.categoryName, docCount: child.docCount, depth: 1 })
    }
  }
  return list
})

const transferCats = computed(() => {
  const kb = tree.value.find((item) => String(item.id) === transfer.kbId)
  const list: FlatCat[] = []
  for (const node of kb?.children || []) {
    list.push({ id: node.id, categoryName: node.categoryName, docCount: node.docCount, depth: 0 })
    for (const child of node.children || []) {
      list.push({ id: child.id, categoryName: `${node.categoryName} / ${child.categoryName}`, docCount: child.docCount, depth: 1 })
    }
  }
  return list
})

const uploadCats = computed(() => {
  const kb = tree.value.find((item) => String(item.id) === upload.kbId)
  const list: FlatCat[] = []
  for (const node of kb?.children || []) {
    list.push({ id: node.id, categoryName: node.categoryName, docCount: node.docCount, depth: 0 })
    for (const child of node.children || []) {
      list.push({ id: child.id, categoryName: `${node.categoryName} / ${child.categoryName}`, docCount: child.docCount, depth: 1 })
    }
  }
  return list
})

const transferSourceLabel = computed(() => transferSources.find((item) => item.value === transfer.source)?.label || '')
const transferKbLabel = computed(() => tree.value.find((item) => String(item.id) === transfer.kbId)?.kbName || '—')

function secretLabel(value: string) {
  return secretOptions.find((item) => item.value === value)?.label || value
}

function docStatusLabel(status: string) {
  return ({ PENDING: '入库审批中', PUBLISHED: '已发布', DRAFT: '草稿' } as Record<string, string>)[status] || status
}

function say(message: string) {
  toast.value = message
}

async function loadUsers() {
  const res = await http.get('/system/user/page', { params: { pageNo: 1, pageSize: 50 } })
  const list = res.data.data?.list || []
  users.value = list.map((item: { id: string | number; username: string; nickname?: string }) => ({
    id: String(item.id),
    label: item.nickname ? `${item.nickname}（${item.username}）` : item.username,
  }))
}

async function loadTree() {
  const res = await http.get('/air/kb/tree')
  if (res.data.code === 0) tree.value = res.data.data || []
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/air/kb/page', {
      params: {
        pageNo: 1,
        pageSize: 20,
        keyword: filters.keyword || undefined,
        kbId: selectedKbId.value || undefined,
        secretLevel: filters.secretLevel || undefined,
        status: filters.status || undefined,
      },
    })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data?.list || []
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

async function loadDocs() {
  loading.value = true
  try {
    const res = await http.get('/air/kb/doc/page', {
      params: {
        pageNo: 1,
        pageSize: 50,
        kbId: selectedKbId.value || undefined,
        categoryId: selectedCateId.value || undefined,
      },
    })
    docs.value = res.data.code === 0 ? res.data.data?.list || [] : []
  } catch (err) {
    docs.value = []
    say(errorMessage(err))
  } finally {
    loading.value = false
  }
}

async function reload() {
  await loadTree()
  if (selectedCateId.value) await loadDocs()
  else await loadList()
}

function selectKb(id: number) {
  selectedKbId.value = id
  selectedCateId.value = 0
  loadList()
  say(`已定位知识库`)
}

function selectCate(kbId: number, cateId: number) {
  selectedKbId.value = kbId
  selectedCateId.value = cateId
  loadDocs()
  say('已按分类过滤')
}

function openCreate() {
  createForm.kbName = ''
  createForm.secretLevel = ''
  createForm.ownerUserId = ''
  createForm.desc = ''
  createErrors.kbName = ''
  createErrors.secretLevel = ''
  createErrors.ownerUserId = ''
  createErrors.form = ''
  showCreate.value = true
  if (!users.value.length) loadUsers().catch(() => undefined)
}

async function submitCreate() {
  createErrors.kbName = createForm.kbName.trim() ? '' : '必填项，请填写'
  createErrors.secretLevel = createForm.secretLevel ? '' : '必填项，请填写'
  createErrors.ownerUserId = createForm.ownerUserId ? '' : '必填项，请填写'
  createErrors.form = ''
  if (createErrors.kbName || createErrors.secretLevel || createErrors.ownerUserId) return
  try {
    await http.post('/air/kb', {
      kbName: createForm.kbName.trim(),
      secretLevel: createForm.secretLevel,
      ownerUserId: Number(createForm.ownerUserId),
      desc: createForm.desc.trim(),
    })
    showCreate.value = false
    say('知识库已创建')
    await reload()
  } catch (err) {
    createErrors.form = errorMessage(err)
  }
}

async function loadCategoryNodes() {
  if (!catKbId.value) {
    categoryNodes.value = []
    return
  }
  const res = await http.get('/air/kb/category/tree', { params: { kbId: Number(catKbId.value) } })
  categoryNodes.value = res.data.code === 0 ? res.data.data || [] : []
}

function openCategory() {
  catError.value = ''
  catName.value = ''
  catParentId.value = ''
  renameId.value = 0
  catKbId.value = String(selectedKbId.value || tree.value[0]?.id || '')
  showCategory.value = true
  loadCategoryNodes()
}

async function submitCategory() {
  catError.value = ''
  if (!catName.value.trim()) {
    catError.value = '必填项，请填写'
    return
  }
  try {
    await http.post('/air/kb/category', {
      kbId: Number(catKbId.value),
      parentId: catParentId.value ? Number(catParentId.value) : undefined,
      categoryName: catName.value.trim(),
    })
    catName.value = ''
    say('已新增分类')
    await loadCategoryNodes()
    await loadTree()
  } catch (err) {
    catError.value = errorMessage(err)
  }
}

function startRename(item: FlatCat) {
  renameId.value = item.id
  renameName.value = item.categoryName
}

async function submitRename() {
  if (!renameName.value.trim()) {
    catError.value = '必填项，请填写'
    return
  }
  try {
    await http.put(`/air/kb/category/${renameId.value}`, {
      kbId: Number(catKbId.value),
      categoryName: renameName.value.trim(),
    })
    renameId.value = 0
    say('分类已重命名')
    await loadCategoryNodes()
    await loadTree()
  } catch (err) {
    catError.value = errorMessage(err)
  }
}

function askDeleteCat(item: FlatCat) {
  if (item.docCount > 0) {
    deleteCat.value = item
    return
  }
  removeCategory(item.id, false)
}

async function confirmDeleteCat() {
  if (!deleteCat.value) return
  const id = deleteCat.value.id
  deleteCat.value = null
  await removeCategory(id, true)
}

async function removeCategory(id: number, moveToRoot: boolean) {
  try {
    await http.delete(`/air/kb/category/${id}`, {
      params: { kbId: Number(catKbId.value), moveToRoot },
    })
    say(moveToRoot ? '已删除分类，条目已改挂根分类' : '已删除空分类')
    await loadCategoryNodes()
    await loadTree()
  } catch (err) {
    catError.value = errorMessage(err)
  }
}

function clearUploadErrors() {
  uploadErrors.kbId = ''
  uploadErrors.file = ''
  uploadErrors.urls = ''
  uploadErrors.title = ''
  uploadErrors.content = ''
  uploadErrors.form = ''
}

function openUpload() {
  upload.mode = 'file'
  upload.kbId = selectedKbId.value ? String(selectedKbId.value) : ''
  upload.categoryId = selectedCateId.value ? String(selectedCateId.value) : ''
  upload.secretLevel = ''
  upload.fileName = ''
  upload.fileSize = 0
  upload.contentType = ''
  upload.urls = ''
  upload.title = ''
  upload.content = ''
  clearUploadErrors()
  showUpload.value = true
}

function onUploadFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  upload.fileName = file?.name || ''
  upload.fileSize = file?.size || 0
  upload.contentType = file?.type || 'application/octet-stream'
  uploadErrors.file = ''
}

async function submitUpload() {
  clearUploadErrors()
  if (!upload.kbId) uploadErrors.kbId = '必填项，请填写'
  if (upload.mode === 'file') {
    if (!upload.fileName) uploadErrors.file = '必填项，请填写'
    else {
      const ext = upload.fileName.includes('.') ? upload.fileName.split('.').pop()?.toLowerCase() || '' : ''
      if (!FILE_EXTS.includes(ext)) uploadErrors.file = '不支持的文件类型'
    }
  } else if (upload.mode === 'url') {
    const lines = upload.urls.split(/\n+/).map((item) => item.trim()).filter(Boolean)
    if (!lines.length) uploadErrors.urls = '必填项，请填写'
    else if (lines.some((item) => !item.startsWith('http://') && !item.startsWith('https://'))) {
      uploadErrors.urls = 'URL 须以 http:// 或 https:// 开头'
    }
  } else {
    if (!upload.title.trim()) uploadErrors.title = '必填项，请填写'
    if (!upload.content.trim()) uploadErrors.content = '必填项，请填写'
  }
  if (uploadErrors.kbId || uploadErrors.file || uploadErrors.urls || uploadErrors.title || uploadErrors.content) return
  const modeName = upload.mode === 'file' ? '文件' : upload.mode === 'url' ? 'URL' : '文本'
  try {
    const kbId = Number(upload.kbId)
    const categoryId = upload.categoryId ? Number(upload.categoryId) : undefined
    const secretLevel = upload.secretLevel || undefined
    if (upload.mode === 'file') {
      await http.post('/air/kb/doc/upload', {
        kbId,
        categoryId,
        fileName: upload.fileName,
        fileSize: upload.fileSize,
        contentType: upload.contentType || 'application/octet-stream',
        secretLevel,
      })
    } else if (upload.mode === 'url') {
      const urls = upload.urls.split(/\n+/).map((item) => item.trim()).filter(Boolean)
      await http.post('/air/kb/doc/import-url', { kbId, categoryId, urls, secretLevel })
    } else {
      await http.post('/air/kb/doc/import-text', {
        kbId,
        categoryId,
        title: upload.title.trim(),
        content: upload.content.trim(),
        secretLevel,
      })
    }
    showUpload.value = false
    say(`已提交 ${modeName}入库`)
    await reload()
  } catch (err) {
    uploadErrors.form = errorMessage(err)
  }
}

function openTransfer() {
  transfer.step = 0
  transfer.source = ''
  transfer.items = []
  transfer.picked = []
  transfer.kbId = String(selectedKbId.value || '')
  transfer.categoryId = ''
  transfer.secretLevel = ''
  transfer.error = ''
  showTransfer.value = true
}

function togglePicked(id: number) {
  transfer.picked = transfer.picked.includes(id) ? transfer.picked.filter((item) => item !== id) : [...transfer.picked, id]
}

async function transferNext() {
  transfer.error = ''
  if (transfer.step === 0) {
    if (!transfer.source) {
      transfer.error = '请先选择来源模块'
      return
    }
    const res = await http.get('/air/kb/transfer-source', { params: { sourceType: transfer.source, pageNo: 1, pageSize: 50 } })
    transfer.items = res.data.code === 0 ? res.data.data?.list || [] : []
    transfer.picked = []
  }
  if (transfer.step === 1 && !transfer.picked.length) {
    transfer.error = '请至少勾选 1 条来源条目'
    return
  }
  if (transfer.step === 2 && !transfer.kbId) {
    transfer.error = '必填项，请填写'
    return
  }
  transfer.step += 1
}

function transferBack() {
  transfer.error = ''
  if (transfer.step === 0) {
    showTransfer.value = false
    return
  }
  transfer.step -= 1
}

async function submitTransfer() {
  try {
    const res = await http.post('/air/kb/doc/import-from', {
      sourceType: transfer.source,
      sourceIds: transfer.picked,
      targetKbId: Number(transfer.kbId),
      targetCategoryId: transfer.categoryId ? Number(transfer.categoryId) : undefined,
      secretLevel: transfer.secretLevel || undefined,
    })
    const count = res.data.data?.docIds?.length || transfer.picked.length
    showTransfer.value = false
    say(`已提交 ${count} 条转入，进入入库审批`)
    await reload()
  } catch (err) {
    transfer.error = errorMessage(err)
  }
}

function openAudit(row: KbRow) {
  auditKb.value = row
  auditNote.value = ''
  auditError.value = ''
}

async function submitAudit(approve: boolean) {
  if (!auditKb.value) return
  auditError.value = ''
  if (!approve && !auditNote.value.trim()) {
    auditError.value = '必填项，请填写'
    return
  }
  try {
    await http.post('/air/kb/audit', {
      kbId: auditKb.value.id,
      approve,
      auditNote: auditNote.value.trim(),
    })
    auditKb.value = null
    say(approve ? '审批通过，知识库已发布' : '已驳回，知识库退回草稿')
    await reload()
  } catch (err) {
    auditError.value = errorMessage(err)
  }
}

async function openDetail(id: number) {
  browseDoc.value = null
  const res = await http.get(`/air/kb/${id}`)
  if (res.data.code === 0) detail.value = res.data.data
}

function openDoc(row: DocRow) {
  browseDoc.value = row
  detail.value = {
    id: 0,
    kbNo: '',
    kbName: row.title,
    secretLevel: '',
    secretLabel: row.secretLabel,
    grantsLimit: '',
    docCount: 1,
    sizeLabel: '—',
    status: row.auditStatus,
    statusLabel: docStatusLabel(row.auditStatus),
    ownerName: '',
    updatedAt: '',
    grantCount: 0,
    docs: [row],
  }
}

async function downloadDoc(id: number) {
  try {
    const res = await http.get(`/air/kb/doc/${id}/download`)
    say(`可下载：${res.data.data.fileKey}`)
  } catch (err) {
    say(errorMessage(err))
  }
}

function openGrant(row: KbRow) {
  grantKb.value = row
  grantForm.grantType = 'PERSON'
  grantForm.grantId = ''
  grantForm.expireAt = ''
  grantError.value = ''
  grantOptions.value = []
  userKeyword.value = ''
}

async function onGrantType() {
  grantForm.grantId = ''
  grantOptions.value = []
  if (grantForm.grantType === 'ROLE') {
    const res = await http.get('/system/role/list')
    const list = Array.isArray(res.data.data) ? res.data.data : []
    grantOptions.value = list.map((item: { id: number; roleName: string }) => ({ id: String(item.id), label: item.roleName }))
  }
}

async function searchUsers() {
  const res = await http.get('/system/user/page', {
    params: { pageNo: 1, pageSize: 20, username: userKeyword.value.trim() || undefined },
  })
  const list = res.data.data?.list || []
  grantOptions.value = list.map((item: { id: string | number; username: string; nickname?: string }) => ({
    id: String(item.id),
    label: item.nickname ? `${item.nickname}（${item.username}）` : item.username,
  }))
}

async function submitGrant() {
  if (!grantKb.value) return
  grantError.value = ''
  if (!grantForm.grantId) {
    grantError.value = '必填项，请填写'
    return
  }
  try {
    await http.post('/air/kb/grant', {
      kbId: grantKb.value.id,
      grantType: grantForm.grantType,
      grantId: Number(grantForm.grantId),
      expireAt: grantForm.expireAt,
    })
    say('授权成功')
    grantKb.value = null
    await reload()
  } catch (err) {
    grantError.value = errorMessage(err)
  }
}

onMounted(async () => {
  await loadTree()
  await loadList()
  loadUsers().catch(() => undefined)
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
.hint.bad {
  color: var(--red);
}
</style>
