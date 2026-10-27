const api = require('../../utils/api.js')

// 体验版：这些内容是虚构的示例，不代表用户的真实记录。
const EXAMPLES = [
  { id: 'morning', date: '2025.04.12', category: '一个清晨', title: '风从窗边经过', text: '早上出门时，发现路边的树又绿了。', note: '一条普通日子的示例', symbol: '✦' },
  { id: 'road', date: '2025.07.06', category: '在路上', title: '沿着光走了一会儿', text: '傍晚的路很安静，走着走着，天就暗了。', note: '一段旅途的示例', symbol: '◌' },
  { id: 'thought', date: '2025.11.23', category: '随手一想', title: '留一点空白', text: '有些问题可以慢一点回答，有些日子可以只用来生活。', note: '一句想法的示例', symbol: '✧' },
  { id: 'run', date: '2026.02.15', category: '一次跑步', title: '跟着呼吸向前', text: '跑到后来，脚步和呼吸慢慢找到了同一个节奏。', note: '一条运动记录的示例', symbol: '≈' },
]

function toMemory(item) {
  if (!item || !item.id || !item.occurred_at) throw new Error('回忆数据格式无效')
  const date = new Date(item.occurred_at)
  if (!Number.isFinite(date.getTime())) {
    throw new Error('回忆数据格式无效')
  }
  const pad = value => String(value).padStart(2, '0')
  const dateText = `${date.getFullYear()}.${pad(date.getMonth() + 1)}.${pad(date.getDate())}`
  const fromCoros = item.source === 'coros'
  return {
    id: String(item.id), date: dateText,
    category: fromCoros ? '运动记录' : '生活记录',
    title: fromCoros ? '一次运动' : '一条记录',
    text: item.text || '这一天留下了一条记录。',
    note: fromCoros ? '来自高驰' : '私人记录',
    symbol: fromCoros ? '≈' : '✦',
  }
}

function starsFor(memories, activeIndex) {
  const start = Math.floor(activeIndex / 4) * 4
  return memories.slice(start, start + 4).map((item, offset) => ({ ...item, index: start + offset }))
}

Page({
  data: {
    memories: EXAMPLES,
    stars: starsFor(EXAMPLES, 0),
    selected: EXAMPLES[0],
    activeIndex: 0,
    mode: 'demo',
    countLabel: `示例 ${EXAMPLES.length} 条`,
    status: '正在寻找你的回忆 · 以下内容为示例',
  },

  onShow() {
    this.loadMemories()
  },

  loadMemories() {
    this.setData({ status: '正在寻找你的回忆 · 以下内容为示例' })
    return api.getMemories().then(items => {
      if (!Array.isArray(items)) throw new Error('回忆数据格式无效')
      if (!items.length) {
        this.setMemories(EXAMPLES, 'demo', '还没有真实回忆 · 以下内容为示例')
        return
      }
      const memories = items.map(toMemory)
      this.setMemories(memories, 'live', '你的私人回忆')
    }).catch(() => {
      this.setMemories(EXAMPLES, 'demo', '暂时无法连接回忆 · 以下内容为示例')
    })
  },

  setMemories(memories, mode, status) {
    this.setData({ memories, stars: starsFor(memories, 0), selected: memories[0], activeIndex: 0, mode, status, countLabel: `${mode === 'demo' ? '示例' : '最近'} ${memories.length} 条` })
  },

  selectMemory(event) {
    const index = Number(event.currentTarget.dataset.index)
    if (!Number.isInteger(index) || index < 0 || index >= this.data.memories.length) return
    this.setData({ activeIndex: index, selected: this.data.memories[index], stars: starsFor(this.data.memories, index) })
  },

  discover() {
    const length = this.data.memories.length
    if (length < 2) return
    const step = 1 + Math.floor(Math.random() * (length - 1))
    const index = (this.data.activeIndex + step) % length
    this.setData({ activeIndex: index, selected: this.data.memories[index], stars: starsFor(this.data.memories, index) })
  },
})
