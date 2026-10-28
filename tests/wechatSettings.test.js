const assert = require('node:assert/strict')
const values = new Map()
let page, modal, toast, navigation
const api = require('../utils/api.js')
const identity = require('../utils/wechatIdentity.js')
global.wx = {
  getStorageSync: key => values.get(key), setStorageSync: (key, value) => values.set(key, value),
  removeStorageSync: key => values.delete(key), getSystemInfoSync: () => ({ statusBarHeight: 24 }),
  showModal: options => { modal = options }, showToast: options => { toast = options.title },
  reLaunch: options => { navigation = options.url },
}
global.Page = config => { page = config }
require('../pages/settings/settings.js')
page.setData = update => Object.assign(page.data, update)
const tick = () => new Promise(resolve => setImmediate(resolve))
;(async () => {
  api.setToken('fake-token')
  api.getCapabilities = async () => ({ wechat_identity_configured: true })
  api.getMe = async () => ({ user_id: 1, username: 'fictional-user', wechat_bound: false })
  api.logout = async () => ({ ok: true })
  identity.bind = async () => { values.set('baobaoji_wechat_auto', true) }
  identity.unbind = async () => { values.delete('baobaoji_wechat_auto'); api.clearAuth() }
  page.onLoad(); page.onShow(); await tick()
  assert.equal(page.data.hasAccount, true)
  page.bindWechat()
  assert.equal(page.data.showWechatBindModal, true)
  page.onBindPasswordInput({ detail: { value: 'discarded-password' } })
  page.cancelWechatBind()
  assert.equal(page.data.wechatBindPassword, '')
  assert.equal(page.data.showWechatBindModal, false)
  page.bindWechat()
  page.onBindPasswordInput({ detail: { value: 'hidden-password' } })
  page.onHide()
  assert.equal(page.data.wechatBindPassword, '')
  page.bindWechat()
  page.onBindPasswordInput({ detail: { value: 'fake-password' } })
  await page.confirmWechatBind()
  assert.equal(page.data.wechatBindPassword, '')
  assert.equal(page.data.showWechatBindModal, false)
  assert.equal(page.data.wechatBound, true)
  assert.equal(page.data.autoEnabled, true)
  assert.equal(toast, '微信已连接')
  page.setAutoEnabled()
  assert.equal(page.data.wechatBound, true)
  assert.equal(page.data.autoEnabled, false)
  page.setAutoEnabled()
  assert.equal(page.data.autoEnabled, true)
  page.unbindWechat()
  assert.equal(modal.title, '解除微信连接')
  await modal.success({ confirm: true })
  assert.equal(api.getToken(), undefined)
  assert.equal(navigation, '/pages/main/main')
  api.setToken('fake-token')
  values.set('baobaoji_wechat_auto', true)
  page.onLogout()
  await modal.success({ confirm: true })
  assert.equal(identity.enabled(), false)
  assert.equal(api.getToken(), undefined)

  // A bound identity is server state even if the local preference is off.
  api.setToken('new-token')
  api.getMe = async () => ({ user_id: 2, username: 'fictional-user-2', wechat_bound: true })
  await page.onShow()
  assert.equal(page.data.wechatBound, true)
  assert.equal(page.data.autoEnabled, false)
  assert.equal(page.data.userName, 'fictional-user-2')

  // An old server cannot report its binding state: do not infer it locally.
  api.getCapabilities = async () => { throw new Error('404') }
  api.getMe = async () => { throw new Error('404') }
  await page.onShow()
  assert.equal(page.data.wechatConfigured, null)
  assert.equal(page.data.wechatBound, null)

  // A failed revoke only offers local logout; cancellation retains the token.
  api.logout = async () => { const e = new Error('legacy'); e.statusCode = 409; throw e }
  page.onLogout()
  await modal.success({ confirm: true })
  assert.equal(modal.title, '仅退出本机？')
  modal.success({ confirm: false })
  assert.equal(api.getToken(), 'new-token')
  modal.success({ confirm: true })
  assert.equal(api.getToken(), undefined)

  // Stale account lookups must not overwrite a switched account.
  api.setToken('old-account')
  api.getCapabilities = async () => ({ wechat_identity_configured: true })
  let resolveOld
  api.getMe = () => new Promise(resolve => { resolveOld = resolve })
  const pending = page.onShow()
  await tick()
  api.setToken('different-account')
  api.getMe = async () => ({ user_id: 3, username: 'new-account', wechat_bound: false })
  resolveOld({ user_id: 2, username: 'old-account', wechat_bound: true })
  await pending
  assert.equal(page.data.userName, 'new-account')
  assert.equal(page.data.wechatBound, false)

  // A delayed logout must never clear a newer manually signed-in account.
  let finishLogout
  api.logout = () => new Promise(resolve => { finishLogout = resolve })
  page.onLogout()
  const logoutPending = modal.success({ confirm: true })
  api.setToken('latest-account')
  finishLogout({ ok: true })
  await logoutPending
  assert.equal(api.getToken(), 'latest-account')
  console.log('wechat settings: bind, unbind and logout passed')
})().catch(error => { console.error(error); process.exitCode = 1 })
