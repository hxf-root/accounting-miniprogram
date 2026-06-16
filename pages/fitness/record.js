const api = require('../../utils/api.js')

Page({
  data: {
    activityTypes: [
      { id: 'running', name: '跑步', icon: '🏃', color: '#4ECDC4' },
      { id: 'cycling', name: '骑行', icon: '🚴', color: '#45B7D1' },
      { id: 'swimming', name: '游泳', icon: '🏊', color: '#96CEB4' },
      { id: 'gym', name: '力量', icon: '💪', color: '#FF6B6B' },
      { id: 'yoga', name: '瑜伽', icon: '🧘', color: '#DDA0DD' },
      { id: 'other', name: '其他', icon: '🏃', color: '#636E72' }
    ],
    formData: {
      exercise_type: 'running',
      duration_minutes: 30,
      calories: 300,
      date: '',
      time: '',
      note: ''
    },
    isEdit: false,
    editId: null
  },

  onLoad(options) {
    this.initDateTime()
    if (options.type) {
      this.setData({ 'formData.exercise_type': options.type })
      this.autoFillCalories()
    }
  },

  initDateTime() {
    const now = new Date()
    const y = now.getFullYear()
    const m = String(now.getMonth() + 1).padStart(2, '0')
    const d = String(now.getDate()).padStart(2, '0')
    const h = String(now.getHours()).padStart(2, '0')
    const min = String(now.getMinutes()).padStart(2, '0')
    this.setData({
      'formData.date': y + '-' + m + '-' + d,
      'formData.time': h + ':' + min
    })
  },

  autoFillCalories() {
    // 根据运动类型快速估算卡路里（30分钟基准）
    const calorieMap = {
      running: 300,
      cycling: 250,
      swimming: 280,
      gym: 200,
      yoga: 150,
      other: 180
    }
    const cal = calorieMap[this.data.formData.exercise_type] || 180
    this.setData({ 'formData.calories': cal })
  },

  onTypeSelect(e) {
    const type = e.currentTarget.dataset.type
    this.setData({ 'formData.exercise_type': type })
    this.autoFillCalories()
  },

  onMinutesInput(e) {
    const val = parseInt(e.detail.value) || 0
    this.setData({ 'formData.duration_minutes': val })
    // 按比例调整卡路里
    const baseCalorieMap = {
      running: 10,
      cycling: 8.3,
      swimming: 9.3,
      gym: 6.7,
      yoga: 5,
      other: 6
    }
    const rate = baseCalorieMap[this.data.formData.exercise_type] || 6
    this.setData({ 'formData.calories': Math.round(val * rate) })
  },

  onCaloriesInput(e) {
    const val = parseInt(e.detail.value) || 0
    this.setData({ 'formData.calories': val })
  },

  onRemarkInput(e) {
    this.setData({ 'formData.note': e.detail.value })
  },

  onDateChange(e) {
    this.setData({ 'formData.date': e.detail.value })
  },

  onTimeChange(e) {
    this.setData({ 'formData.time': e.detail.value })
  },

  async onSave() {
    const fd = this.data.formData

    if (!fd.exercise_type) {
      wx.showToast({ title: '请选择运动类型', icon: 'none' })
      return
    }
    if (!fd.duration_minutes || fd.duration_minutes <= 0) {
      wx.showToast({ title: '请输入运动时长', icon: 'none' })
      return
    }

    wx.showLoading({ title: '保存中...' })
    try {
      await api.createFitnessRecord({
        exercise_type: fd.exercise_type,
        duration_minutes: fd.duration_minutes,
        calories: fd.calories || 0,
        date: fd.date,
        time: fd.time,
        note: fd.note || ''
      })

      wx.showToast({ title: '记录成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1000)
    } catch (e) {
      wx.showToast({ title: '保存失败: ' + (e.message || '网络错误'), icon: 'none' })
    }
    wx.hideLoading()
  },

  onCancel() {
    wx.navigateBack()
  },

  onShareAppMessage() {
    return { title: '记录健身', path: '/pages/fitness/record' }
  }
})
