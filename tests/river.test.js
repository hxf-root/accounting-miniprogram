const assert = require('node:assert/strict')
const api = require('../utils/api.js')
const identity = require('../utils/wechatIdentity.js')
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
  assert.equal(page.data.countLabel, '已加载 6 条')
  page.selectMemory({ currentTarget: { dataset: { index: 5 } } })
  assert.equal(page.data.selected.note, '来自高驰')
  assert.equal(page.data.stars.length, 2)
  assert.equal(page.data.stars[1].index, 5)
  const batch = offset => Array.from({length: 50}, (_, i) => ({ id: offset + i + 1, source: 'manual', occurred_at: '2026-10-26T10:00:00Z', text: '记录' }))
  api.getMemories = async cursor => cursor ? batch(50).slice(0, 3) : batch(0)
  await page.loadMemories()
  assert.equal(page.data.hasMore, true)
  await page.loadMore()
  assert.equal(page.data.memories.length, 53)
  assert.equal(page.data.hasMore, false)
  assert.equal(page.data.countLabel, '已加载 53 条')
  api.getMemories = async cursor => { if (cursor) throw new Error('offline'); return batch(0) }
  await page.loadMemories()
  await page.loadMore()
  assert.equal(page.data.memories.length, 50)
  assert.equal(page.data.hasMore, true)
  assert.match(page.data.loadMoreError, /重试/)
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

  // Two refreshes with the same token can resolve in the opposite order.
  let oldResolve, newResolve
  api.getMemories = () => new Promise(resolve => { oldResolve = resolve })
  const older = page.loadMemories()
  api.getMemories = () => new Promise(resolve => { newResolve = resolve })
  const newer = page.loadMemories()
  newResolve(batch(50).slice(0, 1)); await newer
  oldResolve(batch(0).slice(0, 1)); await older
  assert.equal(page.data.selected.id, '51')

  // A selected local calendar day is sent as an exclusive UTC range.
  let dateRange
  api.getMemories = async (cursor, range) => { dateRange = range; return batch(0).slice(0, 1) }
  await page.chooseDate({ detail: { value: '2026-10-26' } })
  assert.equal(page.data.selectedDate, '2026-10-26')
  assert.equal(new Date(dateRange.start).getDate(), 26)
  assert.equal(new Date(dateRange.end).getDate(), 27)
  if (process.env.TZ === 'America/New_York') {
    await page.chooseDate({ detail: { value: '2026-03-08' } })
    assert.equal((new Date(dateRange.end) - new Date(dateRange.start)) / 3600000, 23)
    await page.chooseDate({ detail: { value: '2026-11-01' } })
    assert.equal((new Date(dateRange.end) - new Date(dateRange.start)) / 3600000, 25)
  }
  await page.clearDate()
  assert.equal(dateRange, null)
  // Changing date invalidates the previous request and hides the previous results immediately.
  let earlierDate
  api.getMemories = () => new Promise(resolve => { earlierDate = resolve })
  const olderDate = page.chooseDate({ detail: { value: '2026-10-25' } })
  assert.equal(page.data.mode, 'demo')
  api.getMemories = async () => []
  await page.chooseDate({ detail: { value: '2026-10-26' } })
  earlierDate(batch(0)); await olderDate
  assert.match(page.data.status, /所选日期没有真实回忆/)
  await page.clearDate()

  // A result outside the loaded page can be shown without changing the pagination cursor.
  api.getMemories = async () => batch(0)
  await page.loadMemories()
  const cursor = page.data.nextCursor
  api.discoverMemory = async () => batch(500).slice(0, 1)[0]
  await page.discover()
  assert.equal(page.data.selected.id, '501')
  assert.equal(page.data.activeIndex, -1)
  assert.equal(page.data.memories.length, 50)
  assert.equal(page.data.nextCursor, cursor)
  // A manual selection wins over an outstanding discovery.
  let discoverResolve
  api.discoverMemory = () => new Promise(resolve => { discoverResolve = resolve })
  const discovery = page.discover()
  page.selectMemory({ currentTarget: { dataset: { index: 2 } } })
  discoverResolve(batch(600)[0]); await discovery
  assert.equal(page.data.selected.id, '3')
  api.discoverMemory = async () => { throw new Error('offline') }
  await page.discover()
  assert.match(page.data.discoverError, /重试/)
  let firstDiscover, secondDiscover
  api.discoverMemory = () => new Promise(resolve => { firstDiscover = resolve })
  const firstDiscovery = page.discover()
  api.discoverMemory = () => new Promise(resolve => { secondDiscover = resolve })
  const secondDiscovery = page.discover()
  secondDiscover(batch(800)[0]); await secondDiscovery
  firstDiscover(batch(900)[0]); await firstDiscovery
  assert.equal(page.data.selected.id, '801')

  // Refresh invalidates an outstanding pagination request as well.
  api.getMemories = async () => batch(0)
  await page.loadMemories()
  let pageResolve
  api.getMemories = () => new Promise(resolve => { pageResolve = resolve })
  const oldPageRequest = page.loadMore()
  api.getMemories = async () => batch(100).slice(0, 1)
  await page.loadMemories()
  pageResolve(batch(50)); await oldPageRequest
  assert.equal(page.data.memories.length, 1)
  assert.equal(page.data.selected.id, '101')

  // A 401 clears private content before any session recovery.
  let token = 'test-token'
  api.getToken = () => token
  identity.enabled = () => false
  api.getMemories = async () => batch(0)
  await page.loadMemories()
  api.getMemories = async () => { token = ''; throw new Error('401') }
  await page.loadMore()
  assert.equal(page.data.mode, 'demo')
  assert.equal(page.data.loadingMore, false)
  assert.ok(!page.data.memories.some(item => item.id === '1'))

  // Hidden pages cannot be repopulated by a late response.
  token = 'test-token'
  let hiddenResolve
  api.getMemories = () => new Promise(resolve => { hiddenResolve = resolve })
  const pending = page.loadMemories()
  page.onHide()
  hiddenResolve(batch(0)); await pending
  assert.equal(page.data.mode, 'demo')
  api.getMemories = async () => batch(0)
  await page.loadMemories()
  api.discoverMemory = () => new Promise(resolve => { discoverResolve = resolve })
  const hiddenDiscovery = page.discover()
  page.onHide()
  discoverResolve(batch(700)[0]); await hiddenDiscovery
  assert.equal(page.data.mode, 'demo')
  assert.notEqual(page.data.selected.id, '701')
  await page.loadMemories()
  api.discoverMemory = () => new Promise(resolve => { discoverResolve = resolve })
  const switchedDiscovery = page.discover()
  token = ''
  discoverResolve(batch(700)[0]); await switchedDiscovery
  assert.equal(page.data.mode, 'demo')
  assert.notEqual(page.data.selected.id, '701')
  console.log('river page: sample, data, empty, error and selection passed')
})().catch(error => { console.error(error); process.exitCode = 1 })
