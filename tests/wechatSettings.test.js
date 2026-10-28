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
  identity.bind = async () => { values.set('baobaoji_wechat_auto', true) }
  identity.unbind = async () => { values.delete('baobaoji_wechat_auto'); api.clearAuth() }
  page.onLoad(); page.onShow(); await tick()
  assert.equal(page.data.hasAccount, true)
  await page.bindWechat()
  assert.equal(page.data.wechatEnabled, true)
  assert.equal(toast, '微信已连接')
  page.unbindWechat()
  assert.equal(modal.title, '解除微信连接')
  await modal.success({ confirm: true })
  assert.equal(api.getToken(), undefined)
  assert.equal(navigation, '/pages/main/main')
  api.setToken('fake-token')
  values.set('baobaoji_wechat_auto', true)
  page.onLogout()
  modal.success({ confirm: true })
  assert.equal(identity.enabled(), false)
  assert.equal(api.getToken(), undefined)
  console.log('wechat settings: bind, unbind and logout passed')
})().catch(error => { console.error(error); process.exitCode = 1 })
