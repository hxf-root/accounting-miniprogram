const api = require('../../utils/api.js')

Page({
  data: {
    statusBarHeight: 0,
    userName: '',
    todayDate: '',
    greeting: '',
    loading: true,
    refreshing: false,
    monthly: {
      expense: 0,
      income: 0,
      count: 0,
      categories: [],
    },
    today: {
      expense: 0,
      income: 0,
      fitness_minutes: 0,
      fitness_calories: 0,
    },
  },

  onLoad() {
    // 获取状态栏高度
    const sysInfo = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
    })
  },

  onShow() {
    this.loadPageData()
  },

  // 下拉刷新
  onRefresh() {
    this.setData({ refreshing: true })
    this.loadPageData()
  },

  loadPageData() {
    // 获取用户信息
    const user = api.getUser()
    this.setData({
      userName: user.username || '用户',
    })

    // 构建问候语
    this.setGreeting()

    // 构建日期
    this.setTodayDate()

    // 并行加载月度和今日统计
    const now = new Date()
    const year = now.getFullYear()
    const month = now.getMonth() + 1

    Promise.all([
      api.getMonthlyStats(year, month),
      api.getTodayStats(),
    ])
      .then(([monthlyData, todayData]) => {
        this.setData({
          monthly: {
            expense: this.formatAmount(monthlyData.expense || 0),
            income: this.formatAmount(monthlyData.income || 0),
            count: monthlyData.bill_count || 0,
            categories: (monthlyData.category_stats || []).slice(0, 4),
          },
          today: {
            expense: this.formatAmount(todayData.expense || 0),
            income: this.formatAmount(todayData.income || 0),
            fitness_minutes: todayData.fitness_minutes || 0,
            fitness_calories: todayData.fitness_calories || 0,
          },
          loading: false,
          refreshing: false,
        })
      })
      .catch(err => {
        wx.showToast({ title: '数据加载失败', icon: 'none' })
        this.setData({ loading: false, refreshing: false })
      })
  },

  setGreeting() {
    const hour = new Date().getHours()
    let greeting = ''
    if (hour < 6) greeting = '夜深了'
    else if (hour < 9) greeting = '早上好 ☀️'
    else if (hour < 12) greeting = '上午好 🌤️'
    else if (hour < 14) greeting = '中午好 🌞'
    else if (hour < 18) greeting = '下午好 🌤️'
    else greeting = '晚上好 🌙'

    this.setData({ greeting })
  },

  setTodayDate() {
    const now = new Date()
    const y = now.getFullYear()
    const m = String(now.getMonth() + 1).padStart(2, '0')
    const d = String(now.getDate()).padStart(2, '0')

    const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    const wd = weekdays[now.getDay()]

    this.setData({ todayDate: `${y}年${m}月${d}日 ${wd}` })
  },

  // 金额格式化：保留两位小数
  formatAmount(val) {
    if (val === undefined || val === null) return '0.00'
    return Number(val).toFixed(2)
  },

  // 跳转到记账模块
  goAccounting() {
    wx.switchTab({ url: '/pages/index/index' })
  },

  // 跳转到健身模块
  goFitness() {
    wx.switchTab({ url: '/pages/fitness/index' })
  },
})
