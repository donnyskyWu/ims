import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { folderEntry } from '../src/nav/folderEntry.ts'

test('账号财务 and 场次财务 open different pages', () => {
  const menu = readFileSync(new URL('../src/nav/menu.ts', import.meta.url), 'utf8')
  const router = readFileSync(new URL('../src/router/index.ts', import.meta.url), 'utf8')
  assert.match(menu, /cost: '\/ims\/cost'/)
  assert.match(menu, /finCost: '\/ims\/fin\/cost'/)
  assert.match(router, /path: 'cost', component: \(\) => import\('\.\.\/views\/cost\/index\.vue'\)/)
  assert.match(router, /path: 'fin\/cost', component: \(\) => import\('\.\.\/views\/fin\/cost\.vue'\)/)
})

test('场次财务 folder enters 成本核算 when the open page is 账号财务', () => {
  const children = ['finCost', 'finProfit', 'finDashboard']
  assert.equal(folderEntry(children, 'cost'), 'finCost')
  assert.equal(folderEntry(children, 'finProfit'), null)
  assert.equal(folderEntry([], 'cost'), null)
})
