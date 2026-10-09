import raw from './catalog.json'

export type Mod = {
  no: string
  name: string
  code: string
  icon: string
  page: string
  desc: string
  parent?: string
  navParent?: boolean
}

export type SubNav = { type: 'sub'; id: string; label: string; children: string[] }

type Catalog = {
  mods: Record<string, Mod>
  groups: [string, (string | SubNav)[]][]
  icons: Record<string, string>
}

const catalog = raw as unknown as Catalog

export const mods = catalog.mods
export const groups = catalog.groups
export const icons = catalog.icons

/** 已接上现有接口的页面。其余菜单进建设中。 */
export const IMPLEMENTED: Record<string, string> = {
  home: '/ims/home',
  workbench: '/ims/workbench',
  workbenchTodos: '/ims/workbench/todos',
  workbenchMsgs: '/ims/workbench/messages',
  ipg: '/ims/ip-group',
  live: '/ims/live/sessions',
  liveAlarm: '/ims/live/alarm',
  cost: '/ims/cost',
  finCost: '/ims/fin/cost',
  finProfit: '/ims/fin/profit',
  finDashboard: '/ims/fin/dashboard',
  finProfitTrace: '/ims/fin/profit-trace',
  finShareRule: '/ims/fin/share/rule',
  finShareResult: '/ims/fin/share/result',
  finLedger: '/ims/fin/ledger',
  fin: '/ims/fin/cost',
  contentSop: '/ims/content/sop',
  contentTopic: '/ims/content/topic',
  contentPlan: '/ims/content/plan',
  contentReview: '/ims/content/review',
  contentPublish: '/ims/content/publish',
  contentWork: '/ims/content/work-task',
  contentTask: '/ims/content/task',
  contentTaskExecute: '/ims/content/task/execute',
  contentList: '/ims/content/list',
  collectTask: '/ims/collect/task',
  collectLog: '/ims/collect/log',
  collectExtAccount: '/ims/collect/external/account',
  collectExtKeyword: '/ims/collect/external/keyword',
  collectMetadata: '/ims/collect/metadata',
  collectThreshold: '/ims/collect/threshold',
  bi0Query: '/ims/bi/query',
  biList: '/ims/bi/report/list',
  biDesign: '/ims/bi/report/designer',
  bi0Report: '/ims/bi/report',
  bi0Metric: '/ims/bi/metric',
  bi0Analysis: '/ims/bi/analysis',
  biShare: '/ims/bi/report/subscribe',
  biPreview: '/ims/bi/report/preview',
  queryTool: '/ims/analysis/query-tool',
  intWork: '/ims/int/work',
  intAccount: '/ims/int/account',
  compWork: '/ims/comp/work',
  compAccount: '/ims/comp/account',
  comp: '/ims/comp/library',
  mon: '/ims/monitor/theme',
  dailyMine: '/ims/meet/daily',
  dailyTeam: '/ims/meet/daily/team',
  dailyReview: '/ims/meet/daily/review',
  dailyStat: '/ims/meet/daily/stat',
  meet: '/ims/meet/minutes',
  reportTpl: '/ims/report/template',
  reportSub: '/ims/report/submission',
  reportRate: '/ims/report/stat',
  trainMaterial: '/ims/train/material',
  trainTask: '/ims/train/task',
  airKb: '/ims/air/kb',
  airSkill: '/ims/air/skill',
  airExpert: '/ims/air/expert',
  airCfg: '/ims/air/cfg',
  perfMetric: '/ims/perf/metric',
  perfCalc: '/ims/perf/calc',
  perfMine: '/ims/perf/mine',
  perfScheme: '/ims/perf/scheme',
  perfExec: '/ims/perf/execution',
  perfResult: '/ims/perf/result',
  perfExam: '/ims/perf/exam',
  flow: '/ims/flow',
  bi0Screen: '/ims/bi/screen-config',
  trainStat: '/ims/train/stat',
  contentLayout: '/ims/content/layout',
  dc: '/ims/dc/trace',
  eff: '/ims/eff',
  effRelation: '/ims/eff?tab=relation',
  effInventory: '/ims/eff?tab=inventory',
  effBoard: '/ims/eff?tab=board',
  alertRule: '/ims/alert/rule',
  alertLive: '/ims/alert/live',
  alertStats: '/ims/alert/stats',
  alertHistory: '/ims/alert/live?tab=history',
  alertDedup: '/ims/alert/live?tab=dedup',
  airKey: '/ims/air/cfg?tab=key',
  airLog: '/ims/air/cfg?tab=audit',
  master: '/ims/master',
  asset: '/ims/corp/device/office',
  cert: '/ims/corp/resource/certificate',
  acct: '/ims/corp/account/douyin',
  'qtPub_QT-TPL-004': '/ims/fin/profit-trace',
  sysUser: '/ims/system/user',
  sysRole: '/ims/system/role',
  sysMenu: '/ims/system/menu',
  sysDict: '/ims/system/dict',
  sysParam: '/ims/system/param',
  sysLog: '/ims/system/log',
  sysNotify: '/ims/system/notify',
  authOrg: '/ims/auth/org',
  authPosition: '/ims/auth/position',
  caWechatOfficial: '/ims/corp/account/wechat-official',
  caWechatChannels: '/ims/corp/account/wechat-channels',
  caDouyin: '/ims/corp/account/douyin',
  caKuaishou: '/ims/corp/account/kuaishou',
  caXhs: '/ims/corp/account/xiaohongshu',
  crCompany: '/ims/corp/resource/company',
  crRealname: '/ims/corp/resource/realname',
  crSim: '/ims/corp/resource/sim-card',
  crCert: '/ims/corp/resource/certificate',
  cdOffice: '/ims/corp/device/office',
  cdLive: '/ims/corp/device/live',
  cdPhone: '/ims/corp/device/phone',
}

export function isSub(item: string | SubNav): item is SubNav {
  return typeof item !== 'string'
}

export function pathOf(id: string) {
  return IMPLEMENTED[id] || `/ims/wip/${id}`
}

export function modIdFromPath(path: string) {
  const matched = path.match(/^\/ims\/wip\/([^/]+)/)
  if (matched) return decodeURIComponent(matched[1])
  const found = Object.entries(IMPLEMENTED).find(([, href]) => href === path)
  return found?.[0] || ''
}

export function crumbOf(id: string) {
  const mod = mods[id]
  if (!mod) return { parent: 'IMS', page: '建设中' }
  return { parent: mod.parent || mod.name, page: mod.page || mod.name }
}

export function codeLabel(mod: Mod | undefined) {
  if (!mod) return ''
  return `${mod.no || ''} ${mod.code || ''}`.trim()
}
