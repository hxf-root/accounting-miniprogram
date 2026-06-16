const api = require('../../utils/api.js')

const EXERCISE_TYPES = {
  running: { name: '跑步', icon: '🏃', color: '#4ECDC4' },
  cycling: { name: '骑行', icon: '🚴', color: '#45B7D1' },
  swimming: { name: '游泳', icon: '🏊', color: '#96CEB4' },
  gym: { name: '力量', icon: '💪', color: '#FF6B6B' },
  yoga: { name: '瑜伽', icon: '🧘', color: '#DDA0DD' },
  other: { name: '其他', icon: '🏃', color: '#636E72' }
}

Page({
  data: {
    timeRange: 'week',
    stats: {
      totalMinutes: 0,
      totalCalories: 0,
      totalActivities: 0,
      averageMinutes: 0
    },
    activityDistribution: [],
    trendData: [],
    isLoading: true
  },

  onLoad() {
    this.loadData()
  },

  onTimeRangeChange(e) {
    const range = e.currentTarget.dataset.range
    if (range === this.data.timeRange) return
    this.setData({ timeRange: range, isLoading: true })
    this.loadData()
  },

  formatDate(date) {
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    return y + '-' + m + '-' + d
  },

  getRangeDates() {
    const end = new Date()
    let start
    const range = this.data.timeRange

    if (range === 'year') {
      start = new Date(end.getFullYear(), 0, 1)
    } else if (range === 'month') {
      start = new Date(end.getFullYear(), end.getMonth(), 1)
    } else {
      start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000)
    }
    return {
      startDate: this.formatDate(start),
      endDate: this.formatDate(end)
    }
  },

  async loadData() {
    wx.showLoading({ title: '加载中...' })
    try {
      const { startDate, endDate } = this.getRangeDates()
      const records = await api.getFitnessRecords({
        date_from: startDate,
        date_to: endDate,
        page_size: 999
      })

      this.calculateStats(records || [])
      this.calculateDistribution(records || [])
      this.calculateTrend(records || [])
    } catch (e) {
      console.error('加载分析数据失败', e)
      wx.showToast({ title: '数据加载失败', icon: 'none' })
    }
    wx.hideLoading()
    this.setData({ isLoading: false })
  },

  calculateStats(records) {
    const totalMinutes = records.reduce((s, r) => s + (r.duration_minutes || 0), 0)
    const totalCalories = records.reduce((s, r) => s + (r.calories || 0), 0)
    const totalActivities = records.length
    const days = this.getDaysInRange()
    const averageMinutes = days > 0 ? Math.round(totalMinutes / days) : 0

    this.setData({
      stats: {
        totalMinutes,
        totalCalories,
        totalActivities,
        averageMinutes
      }
    })
  },

  getDaysInRange() {
    const { startDate, endDate } = this.getRangeDates()
    const s = new Date(startDate)
    const e = new Date(endDate)
    return Math.max(1, Math.round((e - s) / (24 * 60 * 60 * 1000)) + 1)
  },

  calculateDistribution(records) {
    const grouped = {}
    records.forEach(r => {
      const type = r.exercise_type || 'other'
      if (!grouped[type]) grouped[type] = 0
      grouped[type] += r.duration_minutes || 0
    })

    const totalMin = Object.values(grouped).reduce((s, v) => s + v, 0) || 1
    const distribution = Object.entries(grouped).map(([type, minutes]) => {
      const cfg = EXERCISE_TYPES[type] || EXERCISE_TYPES.other
      return {
        name: cfg.name,
        icon: cfg.icon,
        color: cfg.color,
        minutes,
        percentage: Math.round((minutes / totalMin) * 100)
      }
    }).sort((a, b) => b.minutes - a.minutes)

    this.setData({ activityDistribution: distribution })
  },

  calculateTrend(records) {
    const grouped = {}
    records.forEach(r => {
      const date = r.date
      if (!grouped[date]) grouped[date] = { minutes: 0, calories: 0 }
      grouped[date].minutes += r.duration_minutes || 0
      grouped[date].calories += r.calories || 0
    })

    const trendData = Object.entries(grouped)
      .map(([date, val]) => ({
        date: date.slice(5), // MM-DD
        minutes: val.minutes,
        calories: val.calories
      }))
      .sort((a, b) => a.date.localeCompare(b.date))
      .slice(-14) // 最多显示14天

    this.setData({ trendData })
  },

  onExportData() {
    const { startDate, endDate } = this.getRangeDates()
    api.getFitnessRecords({ date_from: startDate, date_to: endDate, page_size: 999 })
      .then(records => {
        const csv = this.convertToCSV(records || [])
        wx.setClipboardData({
          data: csv,
          success: () => {
            wx.showModal({
              title: '导出成功',
              content: '数据已复制到剪贴板，可粘贴到 Excel 等软件查看',
              showCancel: false
            })
          }
        })
      })
      .catch(() => {
        wx.showToast({ title: '导出失败', icon: 'none' })
      })
  },

  convertToCSV(data) {
    const headers = ['日期', '时间', '运动类型', '时长(分钟)', '热量(卡路里)', '备注']
    const rows = data.map(r => [
      r.date,
      r.time,
      r.exercise_type,
      r.duration_minutes,
      r.calories,
      (r.note || '').replace(/,/g, '，')
    ])
    return [headers, ...rows].map(row => row.join(',')).join('\n')
  },

  onShareAppMessage() {
    const s = this.data.stats
    return {
      title: '健身统计：' + s.totalMinutes + '分钟，消耗' + s.totalCalories + '卡路里',
      path: '/pages/fitness/analytics'
    }
  },

  navigateBack() {
    wx.navigateBack()
  }
})
