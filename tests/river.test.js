const assert = require('node:assert/strict')
const api = require('../utils/api.js')
let page
const oldPage = global.Page
global.Page = config => { page = config }
require('../pages/river/river.js')
global.Page = oldPage
page.setData = values => Object.assign(page.data, values)

;(async () => {
  assert.equal(page.data.mode, 'demo')
  page.selectMemory({ currentTarget: { dataset: { index: 2 } } })
  assert.equal(page.data.selected.id, 'thought')
  page.selectMemory({ currentTarget: { dataset: { index: 999 } } })
  assert.equal(page.data.selected.id, 'thought')
  for (let i = 0; i < 30; i++) {
    const previous = page.data.selected.id
    page.discover()
    assert.notEqual(page.data.selected.id, previous)
  }
  let called = false
  api.getToken = () => ''
  api.getMemories = async () => { called = true; return [] }
  await page.loadMemories()
  assert.equal(called, false)
  assert.match(page.data.status, /尚未连接私人回忆/)
  api.getToken = () => 'test-token'
  api.getMemories = async () => Array.from({length: 6}, (_, i) => ({
    id: i + 1, source: i === 5 ? 'coros' : 'manual',
    occurred_at: '2026-10-26T10:00:00+00:00', text: '测试记录 ' + i,
  }))
  await page.loadMemories()
  assert.equal(page.data.mode, 'live')
  assert.equal(page.data.memories.length, 6)
  assert.equal(page.data.countLabel, '最近 6 条')
  page.selectMemory({ currentTarget: { dataset: { index: 5 } } })
  assert.equal(page.data.selected.note, '来自高驰')
  assert.equal(page.data.stars.length, 2)
  assert.equal(page.data.stars[1].index, 5)
  api.getMemories = async () => []
  await page.loadMemories()
  assert.equal(page.data.mode, 'demo')
  assert.match(page.data.status, /没有真实回忆/)
  api.getMemories = async () => { throw new Error('offline') }
  await page.loadMemories()
  assert.equal(page.data.mode, 'demo')
  assert.match(page.data.status, /无法连接/)
  api.getMemories = async () => [{ id: 1, occurred_at: 'not a date' }]
  await page.loadMemories()
  assert.equal(page.data.mode, 'demo')
  console.log('river page: sample, data, empty, error and selection passed')
})().catch(error => { console.error(error); process.exitCode = 1 })
