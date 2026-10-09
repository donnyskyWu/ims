<template>
  <div class="match-scheme">
    <div class="dsec">赛事与玩法</div>
    <div class="tabs" style="margin-bottom: 8px">
      <div
        v-for="tab in tabs"
        :key="tab.id"
        class="tab"
        :class="{ on: matchType === tab.id }"
        @click="switchType(tab.id)"
      >
        {{ tab.label }}
      </div>
    </div>
    <div class="rowline" style="gap: 8px; flex-wrap: wrap; margin-bottom: 8px">
      <input v-model="draft.matchId" placeholder="matchId" style="width: 120px" />
      <input v-model="draft.homeName" placeholder="主队" style="width: 120px" />
      <input v-model="draft.awayName" placeholder="客队" style="width: 120px" />
      <button class="btn btn-sec btn-sm" type="button" @click="addMatch">添加场次</button>
    </div>
    <div v-if="!scheme.length" class="hint">尚未添加场次</div>
    <div v-for="(item, index) in scheme" :key="index" class="card" style="padding: 8px 10px; margin-bottom: 6px">
      <span>{{ item.homeName || '主' }} VS {{ item.awayName || '客' }}</span>
      <span class="csub" style="margin-left: 8px">{{ item.matchId || item.scheduleId }}</span>
      <button class="btn btn-txt btn-sm" type="button" style="margin-left: 8px" @click="removeAt(index)">移除</button>
    </div>
    <div class="rowline" style="gap: 8px; align-items: center; margin-top: 8px">
      <button class="btn btn-pri btn-sm" type="button" :disabled="!scheme.length" @click="confirmPlays">确定玩法</button>
      <span class="hint">{{ confirmed ? `已确定 ${scheme.length} 场` : '切换赛事类型会清空未确定的场次' }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

export type MatchSchemeItem = {
  matchId?: string
  scheduleId?: string
  homeName?: string
  awayName?: string
  className?: string
  matchTime?: string
  matchPlays?: unknown[]
  mainPlayMethod?: string
}

const matchType = defineModel<number>('matchType', { default: 1 })
const scheme = defineModel<MatchSchemeItem[]>('scheme', { default: () => [] })
const props = defineProps<{ seedKey?: number }>()

const tabs = [
  { id: 1, label: '竞足' },
  { id: 2, label: '传足' },
  { id: 3, label: '北单' },
  { id: 4, label: '足球' },
]

const confirmed = ref(false)
const draft = reactive({ matchId: '', homeName: '', awayName: '' })

watch(
  () => props.seedKey,
  () => {
    confirmed.value = scheme.value.length > 0
    draft.matchId = ''
    draft.homeName = ''
    draft.awayName = ''
  },
)

function switchType(id: number) {
  if (id === matchType.value) return
  if (!confirmed.value) scheme.value = []
  matchType.value = id
}

function addMatch() {
  const matchId = draft.matchId.trim()
  const homeName = draft.homeName.trim()
  const awayName = draft.awayName.trim()
  if (!matchId || !homeName || !awayName) {
    window.alert('请填写 matchId、主队、客队')
    return
  }
  scheme.value = [...scheme.value, { matchId, homeName, awayName, matchPlays: [] }]
  confirmed.value = false
  draft.matchId = ''
  draft.homeName = ''
  draft.awayName = ''
}

function removeAt(index: number) {
  scheme.value = scheme.value.filter((_, idx) => idx !== index)
  confirmed.value = false
}

function confirmPlays() {
  if (!scheme.value.length) {
    window.alert('请先添加场次')
    return
  }
  confirmed.value = true
}
</script>
