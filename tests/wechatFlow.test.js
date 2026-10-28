const assert = require('node:assert/strict')
const values = new Map([['baobaoji_wechat_auto', true], ['baobaoji_token', 'expired-token']])
let memoryRequests = 0, loginCalls = 0, clientConfig, river
const fresh = 'b'.repeat(43)
global.wx = {
  getStorageSync: key => values.get(key), setStorageSync: (key, value) => values.set(key, value),
  removeStorageSync: key => values.delete(key),
  login: ({ success }) => { loginCalls++; success({ code: 'fake-code' }) },
  request: options => {
    if (options.url.includes('/api/memories')) {
      memoryRequests++
      if (memoryRequests === 1) options.success({ statusCode: 401, data: {} })
      else options.success({ statusCode: 200, data: [{ id: 1, source: 'coros', occurred_at: '2026-10-28T10:00:00Z', text: '模拟跑步' }] })
    } else if (options.url.endsWith('/api/auth/wechat/login')) {
      options.success({ statusCode: 200, data: { token: fresh } })
    } else throw Error('unexpected request')
  },
}
global.App = config => { clientConfig = config }
require('../app.js')
global.Page = config => { river = config }
require('../pages/river/river.js')
river.setData = values => Object.assign(river.data, values)
;(async () => {
  clientConfig.onLaunch()
  await river.onShow()
  assert.equal(loginCalls, 1)
  assert.equal(memoryRequests, 2)
  assert.equal(values.get('baobaoji_token'), fresh)
  assert.equal(river.data.mode, 'live')
  assert.equal(river.data.selected.text, '模拟跑步')
  console.log('wechat flow: expired session reauth and simulated memory passed')
})().catch(error => { console.error(error); process.exitCode = 1 })
