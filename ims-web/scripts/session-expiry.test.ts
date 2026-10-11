import assert from 'node:assert/strict'
import test from 'node:test'
import {
  createExpiryGate,
  isSessionInvalid,
  safeInternalRedirect,
  SESSION_EXPIRED_TOAST,
} from '../src/auth/sessionPolicy.ts'

test('session invalid is 会话无效, 未登录, code 401, or a bare HTTP 401', () => {
  assert.equal(isSessionInvalid(401, { code: 1002, msg: '会话无效' }), true)
  assert.equal(isSessionInvalid(401, { code: 401, msg: '未登录' }), true)
  assert.equal(isSessionInvalid(200, { code: 401, msg: '未登录' }), true)
  assert.equal(isSessionInvalid(401, undefined), true)
  assert.equal(isSessionInvalid(401, {}), true)
})

test('business HTTP 401 stays on the page', () => {
  assert.equal(isSessionInvalid(401, { code: 1002, msg: '下载链接已过期' }), false)
  assert.equal(isSessionInvalid(401, { code: 1002, msg: '签名链接已过期' }), false)
  assert.equal(isSessionInvalid(401, { code: 1002, msg: '同父级下名称重复' }), false)
  assert.equal(isSessionInvalid(401, { code: 1002, msg: 'state 无效' }), false)
  assert.equal(isSessionInvalid(401, { code: 1002, msg: '角色「运营」尚未配置权限，用户将无任何权限' }), false)
  assert.equal(isSessionInvalid(200, { code: 1006, msg: '用户名或密码错误' }), false)
  assert.equal(isSessionInvalid(403, { code: 403, msg: '无操作权限' }), false)
})

test('concurrent session failures toast and redirect once', () => {
  const events: string[] = []
  const gate = createExpiryGate({
    onLoginPage: () => false,
    currentFullPath: () => '/ims/workbench?tab=1',
    clearSession: () => events.push('clear'),
    toast: (message) => events.push(`toast:${message}`),
    redirectToLogin: (redirect) => events.push(`go:${redirect}`),
  })
  assert.equal(gate.expireFrom(401, { code: 1002, msg: '会话无效' }), true)
  assert.equal(gate.expireFrom(401, { msg: '未登录' }), true)
  assert.equal(gate.expireFrom(401, undefined), true)
  assert.deepEqual(events, [
    'clear',
    `toast:${SESSION_EXPIRED_TOAST}`,
    'go:/ims/workbench?tab=1',
  ])
  const previous = gate.generation()
  gate.reset()
  assert.equal(gate.expireFrom(401, { msg: '会话无效' }, previous), false)
  assert.equal(events.length, 3)
  gate.expireFrom(401, { msg: '会话无效' }, gate.generation())
  assert.equal(events.length, 6)
})

test('login page ignores a late 401 so a new token is kept', () => {
  const events: string[] = []
  const gate = createExpiryGate({
    onLoginPage: () => true,
    currentFullPath: () => '/login',
    clearSession: () => events.push('clear'),
    toast: () => events.push('toast'),
    redirectToLogin: () => events.push('go'),
  })
  assert.equal(gate.expireFrom(401, { msg: '会话无效' }), true)
  assert.deepEqual(events, [])
})

test('redirect target stays inside the app', () => {
  assert.equal(safeInternalRedirect('/ims/system/user'), '/ims/system/user')
  assert.equal(safeInternalRedirect('/ims/workbench?tab=1'), '/ims/workbench?tab=1')
  assert.equal(safeInternalRedirect(['/ims/home']), '/ims/home')
  assert.equal(safeInternalRedirect('//evil.example'), '')
  assert.equal(safeInternalRedirect('/login'), '')
  assert.equal(safeInternalRedirect('/login?redirect=/ims'), '')
  assert.equal(safeInternalRedirect('https://evil.example'), '')
  assert.equal(safeInternalRedirect(undefined), '')
})
