const assert = require('node:assert/strict')
const values = new Map()
let received
let statusCode = 401
global.wx = {
  getStorageSync: key => values.get(key),
  setStorageSync: (key, value) => values.set(key, value),
  removeStorageSync: key => values.delete(key),
  request: options => { received = options; options.success({ statusCode, data: {} }) },
}
const api = require('../utils/api.js')
;(async () => {
  api.setToken('existing-account-token')
  await assert.rejects(api.bindWechat('invalid-code'))
  assert.equal(api.getToken(), 'existing-account-token')
  assert.deepEqual(received.data, { code: 'invalid-code' })
  assert.equal(received.header.Authorization, 'Bearer existing-account-token')
  await assert.rejects(api.getMemories())
  assert.equal(api.getToken(), undefined)
  statusCode = 200
  await api.loginWechat('fake-code')
  assert.deepEqual(received.data, { code: 'fake-code' })
  console.log('wechat api: 401 handling and credential request passed')
})().catch(error => { console.error(error); process.exitCode = 1 })
