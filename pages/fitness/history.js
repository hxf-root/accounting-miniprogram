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
    historyData: [],
    isLoading: true,
    loadingMore: false,
    page: 1,
    pageSize: 50,
    hasMore: true
  },

  onLoad() {
    this.loadHistoryData(true)
  },

  onShow() {
    this.loadHistoryData(true)
  },

  onPullDownRefresh() {
    this.loadHistoryData(true).then(() => {
      wx.stopPullDownRefresh()
    })
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loadingMore) {
      this.loadHistoryData(false)
    }
  },

  async loadHistoryData(refresh) {
    if (refresh) {
      this.setData({ isLoading: true, page: 1, hasMore: true })
    } else {
      this.setData({ loadingMore: true })
    }

    try {
      const page = refresh ? 1 : this.data.page
      const records = await api.getFitnessRecords({
        page: page,
        page_size: this.data.pageSize
      })

      const flatRecords = records || []
      const hasMore = flatRecords.length >= this.data.pageSize

      const grouped = this.groupByDate(flatRecords)

      if (refresh) {
        this.setData({
          historyData: grouped,
          page: page + 1,
          hasMore,
          isLoading: false,
          loadingMore: false
        })
      } else {
        // 去重合并
        const existing = this.data.historyData
        const merged = this.mergeGroups(existing, grouped)
        this.setData({
          historyData: merged,
          page: page + 1,
          hasMore,
          loadingMore: false
        })
      }
    } catch (e) {
      console.error('加载历史记录失败', e)
      this.setData({ isLoading: false, loadingMore: false })
    }
  },

  groupByDate(records) {
    const map = {}
    records.forEach(r => {
      const date = r.date
      if (!map[date]) {
        map[date] = { date, activities: [], totalMinutes: 0, totalCalories: 0 }
      }
      const cfg = EXERCISE_TYPES[r.exercise_type] || EXERCISE_TYPES.other
      const item = {
        id: r.id,
        icon: cfg.icon,
        name: cfg.name,
        color: cfg.color,
        duration: r.duration_minutes || 0,
        calories: r.calories || 0,
        distance: r.distance || 0,
        steps: r.steps || 0,
        intensity: r.intensity || 'medium',
        remark: r.note || '',
        time: r.time || '',
        exercise_type: r.exercise_type
      }
      map[date].activities.push(item)
      map[date].totalMinutes += item.duration
      map[date].totalCalories += item.calories
    })
    return Object.values(map).sort((a, b) => b.date.localeCompare(a.date))
  },

  mergeGroups(existing, incoming) {
    const map = {}
    existing.forEach(g => { map[g.date] = g })
    incoming.forEach(g => {
      if (map[g.date]) {
        // 合并活动，按 id 去重
        const existingIds = new Set(map[g.date].activities.map(a => a.id))
        g.activities.forEach(a => {
          if (!existingIds.has(a.id)) {
            map[g.date].activities.push(a)
            map[g.date].totalMinutes += a.duration
            map[g.date].totalCalories += a.calories
          }
        })
      } else {
        map[g.date] = g
      }
    })
    return Object.values(map).sort((a, b) => b.date.localeCompare(a.date))
  },

  goToRecord() {
    wx.navigateTo({ url: '/pages/fitness/record' })
  },

  deleteRecord(e) {
    const recordId = e.currentTarget.dataset.id
    const self = this

    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条健身记录吗？',
      success(res) {
        if (res.confirm) {
          wx.showLoading({ title: '删除中...' })
          api.deleteFitnessRecord(recordId)
            .then(() => {
              wx.showToast({ title: '已删除', icon: 'success' })
              self.loadHistoryData(true)
            })
            .catch(err => {
              wx.showToast({ title: '删除失败: ' + (err.message || ''), icon: 'none' })
            })
            .finally(() => wx.hideLoading())
        }
      }
    })
  },

  goToRecordDetail(e) {
    const activity = e.currentTarget.dataset.activity
    wx.navigateTo({
      url: '/pages/fitness/record?id=' + activity.id
    })
  },

  onShareAppMessage() {
    return { title: '我的健身历史记录', path: '/pages/fitness/history' }
  }
})
