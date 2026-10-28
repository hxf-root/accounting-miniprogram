const assert = require('node:assert/strict')
const api = require('../utils/api.js')
const state = new Map()
let nextLogin = () => Promise.resolve('fake-code')
global.wx = {
  getStorageSync: key => state.get(key),
  setStorageSync: (key, value) => state.set(key, value),
  removeStorageSync: key => state.delete(key),
  login: ({ success, fail }) => nextLogin().then(code => success({ code }), fail),
}
const identity = require('../utils/wechatIdentity.js')
const token = 'a'.repeat(43)

;(async () => {
  assert.equal(await identity.restore(), false)
  await assert.rejects(identity.bind('fake-password'), /连接已有账户/)
  api.setToken('existing-account-token')
  let calls = []
  api.bindWechat = async (code, password) => { calls.push([code, password]) }
  await identity.bind('fake-password')
  assert.equal(identity.enabled(), true)
  assert.deepEqual(calls, [['fake-code', 'fake-password']])
  api.clearAuth()
  let loginCount = 0
  api.loginWechat = async () => { loginCount++; return { token } }
  const [first, second] = await Promise.all([identity.restore(), identity.restore()])
  assert.equal(first, true); assert.equal(second, true); assert.equal(loginCount, 1)
  assert.equal(api.getToken(), token)
  api.clearAuth()
  api.loginWechat = async () => ({ token: 'bad-token' })
  assert.equal(await identity.restore(), false)
  assert.equal(api.getToken(), undefined)
  assert.equal(identity.enabled(), true) // Temporary failure does not silently unlink.
  let resolveCode
  nextLogin = () => new Promise(resolve => { resolveCode = resolve })
  const pending = identity.restore()
  identity.stopAuto()
  resolveCode('fake-code')
  assert.equal(await pending, false)
  assert.equal(api.getToken(), undefined)
  assert.equal(identity.enabled(), false)
  let resolveBindingCode, bindingCalls = 0
  nextLogin = () => new Promise(resolve => { resolveBindingCode = resolve })
  api.setToken('first-account')
  api.bindWechat = async () => { bindingCalls++ }
  const binding = identity.bind('fake-password')
  api.setToken('different-account')
  resolveBindingCode('fake-code')
  await assert.rejects(binding, /操作已取消/)
  assert.equal(bindingCalls, 0)
  nextLogin = () => Promise.resolve('fake-code')
  api.setToken('existing-account-token')
  await identity.bind('fake-password')
  api.unbindWechat = async () => ({ ok: true })
  await identity.unbind()
  assert.equal(identity.enabled(), false)
  assert.equal(api.getToken(), undefined)
  console.log('wechat identity: binding, dedup, failures, cancellation and unbind passed')
})().catch(error => { console.error(error); process.exitCode = 1 })
