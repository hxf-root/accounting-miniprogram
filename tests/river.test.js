const assert = require('node:assert/strict')
let page
const oldPage = global.Page
global.Page = config => { page = config }
require('../pages/river/river.js')
global.Page = oldPage
page.setData = values => Object.assign(page.data, values)
assert.equal(page.data.memories.length, 4)
const before = page.data.selected.id
page.selectMemory({ currentTarget: { dataset: { index: 2 } } })
assert.equal(page.data.selected.id, 'thought')
page.selectMemory({ currentTarget: { dataset: { index: 999 } } })
assert.equal(page.data.selected.id, 'thought')
for (let i = 0; i < 30; i++) {
  const previous = page.data.selected.id
  page.discover()
  assert.notEqual(page.data.selected.id, previous)
  assert.ok(page.data.memories.some(item => item.id === page.data.selected.id))
}
assert.notEqual(before, undefined)
console.log('river page interactions: passed')
