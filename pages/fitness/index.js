const api = require('../../utils/api.js')

const EXERCISE_TYPES = {
  running: { id: 'running', name: '跑步', icon: '🏃', color: '#4ECDC4' },
  swimming: { id: 'swimming', name: '游泳', icon: '🏊', color: '#45B7D1' },
  gym: { id: 'gym', name: '力量', icon: '💪', color: '#FF6B6B' },
  yoga: { id: 'yoga', name: '瑜伽', icon: '🧘', color: '#96CEB4' },
  cycling: { id: 'cycling', name: '骑行', icon: '🚴', color: '#FFEAA7' },
  basketball: { id: 'basketball', name: '球类', icon: '🏀', color: '#DDA0DD' },
  other: { id: 'other', name: '其他', icon: '🏃', color: '#636E72' }
}

Page({
  data: {
    currentDate: '',
    todayStats: {
      totalMinutes: 0,
      totalCalories: 0,
      activityCount: 0
    },
    recentActivities: [],
    quickActivities: Object.values(EXERCISE_TYPES),
    goalProgress: 0,
    goalText: '今日目标未设置',
    goalEnabled: false,
    goalStatusText: '',
    goalStatusClass: 'safe',
    dailyGoalMinutes: 0,
    dailyGoalCalories: 0
  },

  onLoad() {
    this.setData({
      currentDate: this.formatDate(new Date())
    })
    this.loadAll()
  },

  onShow() {
    this.loadAll()
  },

  formatDate(date) {
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return month + '-' + day
  },

  formatISO(date) {
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    return y + '-' + m + '-' + d
  },

  async loadAll() {
    wx.showLoading({ title: '加载中...' })
    try {
      await Promise.all([
        this.loadTodayStats(),
        this.loadRecentActivities(),
        this.loadGoalSettings()
      ])
    } catch (e) {
      console.error('加载健身首页失败', e)
    }
    wx.hideLoading()
  },

  async loadTodayStats() {
    try {
      const stats = await api.getTodayStats()
      this.setData({
        todayStats: {
          totalMinutes: stats.fitness_minutes || 0,
          totalCalories: stats.fitness_calories || 0,
          activityCount: stats.fitness_count || 0
        }
      })
      this.updateGoalProgress()
    } catch (e) {
      console.error('加载今日统计失败', e)
    }
  },

  async loadRecentActivities() {
    try {
      const records = await api.getFitnessRecords({ page_size: 5 })
      const activities = (records || []).map(r => {
        const typeConfig = EXERCISE_TYPES[r.exercise_type] || EXERCISE_TYPES.other
        return {
          id: r.id,
          name: typeConfig.name,
          icon: typeConfig.icon,
          color: typeConfig.color,
          minutes: r.duration_minutes,
          calories: r.calories,
          date: r.date,
          time: r.time,
          note: r.note
        }
      })
      this.setData({ recentActivities: activities })
    } catch (e) {
      console.error('加载最近记录失败', e)
    }
  },

  async loadGoalSettings() {
    try {
      const settings = await api.getSettings()
      const minutes = settings.fitness_daily_goal_minutes || 0
      const calories = settings.fitness_daily_goal_calories || 0
      this.setData({
        dailyGoalMinutes: minutes,
        dailyGoalCalories: calories
      })
      this.updateGoalProgress()
    } catch (e) {
      console.error('加载目标设置失败', e)
    }
  },

  updateGoalProgress() {
    const goalMin = this.data.dailyGoalMinutes
    const goalCal = this.data.dailyGoalCalories
    const today = this.data.todayStats

    if (goalMin > 0) {
      const progressRaw = (today.totalMinutes / goalMin) * 100
      const progress = Math.min(100, Math.round(progressRaw))
      const remaining = Math.max(0, goalMin - today.totalMinutes)

      let goalStatusText = '还差 ' + remaining + ' 分钟达标'
      let goalStatusClass = 'safe'
      if (remaining <= 0) {
        goalStatusText = '今日目标已完成，继续保持！'
        goalStatusClass = 'done'
      } else if (progressRaw >= 80) {
        goalStatusText = '快达标了，还差 ' + remaining + ' 分钟'
        goalStatusClass = 'warn'
      }

      this.setData({
        goalEnabled: true,
        goalProgress: progress,
        goalText: '今日目标: ' + goalMin + ' 分钟 / ' + goalCal + ' 卡路里',
        goalStatusText: goalStatusText,
        goalStatusClass: goalStatusClass
      })
    } else {
      this.setData({
        goalEnabled: false,
        goalProgress: 0,
        goalText: '今日目标未设置',
        goalStatusText: '去「目标设置」里设置每日目标',
        goalStatusClass: 'safe'
      })
    }
  },

  onQuickActivity(e) {
    const activity = e.currentTarget.dataset.activity
    wx.navigateTo({
      url: '/pages/fitness/record?type=' + activity.id + '&name=' + encodeURIComponent(activity.name) + '&icon=' + encodeURIComponent(activity.icon) + '&color=' + encodeURIComponent(activity.color)
    })
  },

  goToRecord() {
    wx.navigateTo({ url: '/pages/fitness/record' })
  },

  goToAnalytics() {
    wx.navigateTo({ url: '/pages/fitness/analytics' })
  },

  goToHistory() {
    wx.navigateTo({ url: '/pages/fitness/history' })
  },

  goToSettings() {
    wx.navigateTo({ url: '/pages/fitness/settings' })
  },

  onShareAppMessage() {
    const s = this.data.todayStats
    return {
      title: '今日健身 ' + s.totalMinutes + ' 分钟，消耗 ' + s.totalCalories + ' 卡路里',
      path: '/pages/fitness/index'
    }
  }
})
