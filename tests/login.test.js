const assert = require('node:assert/strict')
const api = require('../utils/api.js')
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
  console.log('login: existing short password supported; new short password rejected')
})().catch(error => { console.error(error); process.exitCode = 1 })
