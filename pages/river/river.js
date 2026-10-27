// 体验版：这些内容是虚构的示例，不代表用户的真实记录。
const EXAMPLES = [
  { id: 'morning', date: '2025.04.12', category: '一个清晨', title: '风从窗边经过', text: '早上出门时，发现路边的树又绿了。', note: '一条普通日子的示例', symbol: '✦' },
  { id: 'road', date: '2025.07.06', category: '在路上', title: '沿着光走了一会儿', text: '傍晚的路很安静，走着走着，天就暗了。', note: '一段旅途的示例', symbol: '◌' },
  { id: 'thought', date: '2025.11.23', category: '随手一想', title: '留一点空白', text: '有些问题可以慢一点回答，有些日子可以只用来生活。', note: '一句想法的示例', symbol: '✧' },
  { id: 'run', date: '2026.02.15', category: '一次跑步', title: '跟着呼吸向前', text: '跑到后来，脚步和呼吸慢慢找到了同一个节奏。', note: '一条运动记录的示例', symbol: '≈' },
]

Page({
  data: {
    memories: EXAMPLES,
    selected: EXAMPLES[0],
    activeIndex: 0,
  },

  selectMemory(event) {
    const index = Number(event.currentTarget.dataset.index)
    if (!Number.isInteger(index) || index < 0 || index >= EXAMPLES.length) return
    this.setData({ activeIndex: index, selected: EXAMPLES[index] })
  },

  discover() {
    const length = EXAMPLES.length
    if (length < 2) return
    const step = 1 + Math.floor(Math.random() * (length - 1))
    const index = (this.data.activeIndex + step) % length
    this.setData({ activeIndex: index, selected: EXAMPLES[index] })
  },
})
