const assert = require('node:assert/strict')
const api = require('../utils/api.js')
const identity = require('../utils/wechatIdentity.js')
let page, calls = 0, toast = ''
global.Page = config => { page = config }
global.wx = { showToast: result => { toast = result.title }, reLaunch: () => {} }
require('../pages/login/login.js')
page.setData = values => Object.assign(page.data, values)
api.login = async () => { calls++; throw new Error('synthetic') }
api.register = async () => { throw new Error('unexpected registration') }

;(async () => {
  page.setData({ username: 'legacy', password: '1234', isRegister: false })
  page.onLogin()
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(calls, 1, 'existing short passwords must reach the server')
  page.setData({ username: 'new', password: '1234', isRegister: true })
  page.onLogin()
  assert.equal(toast, '密码至少6位')
  let stopped = 0
  identity.stopAuto = () => { stopped++ }
  api.login = async () => ({ token: 'fictional-token', username: 'new-account', user_id: 2 })
  api.setToken = () => {}
  api.setUser = () => {}
  page.setData({ username: 'new-account', password: '1234', isRegister: false })
  page.onLogin()
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(stopped, 1, 'manual login must cancel previous auto-identity restoration')
  console.log('login: existing short password supported; new short password rejected')
})().catch(error => { console.error(error); process.exitCode = 1 })
