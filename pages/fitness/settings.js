const api = require('../../utils/api.js')

Page({
  data: {
    dailyGoal: {
      minutes: 30,
      calories: 300
    }
  },

  onLoad() {
    this.loadSettings()
  },

  onShow() {
    this.loadSettings()
  },

  async loadSettings() {
    try {
      const settings = await api.getSettings()
      this.setData({
        dailyGoal: {
          minutes: settings.fitness_daily_goal_minutes || 30,
          calories: settings.fitness_daily_goal_calories || 300
        }
      })
    } catch (e) {
      console.error('加载设置失败', e)
    }
  },

  onMinutesChange(e) {
    const val = parseInt(e.detail.value) || 0
    this.setData({ 'dailyGoal.minutes': val })
  },

  onCaloriesChange(e) {
    const val = parseInt(e.detail.value) || 0
    this.setData({ 'dailyGoal.calories': val })
  },

  async onSaveGoal() {
    const goal = this.data.dailyGoal

    if (goal.minutes <= 0 && goal.calories <= 0) {
      wx.showToast({ title: '请设置有效的目标值', icon: 'none' })
      return
    }

    wx.showLoading({ title: '保存中...' })
    try {
      await api.updateSettings({
        fitness_daily_goal_minutes: goal.minutes,
        fitness_daily_goal_calories: goal.calories
      })

      wx.showToast({ title: '保存成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1500)
    } catch (e) {
      wx.showToast({ title: '保存失败: ' + (e.message || ''), icon: 'none' })
    }
    wx.hideLoading()
  },

  onCancel() {
    wx.navigateBack()
  },

  onShareAppMessage() {
    return { title: '健身目标设置', path: '/pages/fitness/settings' }
  }
})
