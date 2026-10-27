const api = require('../../utils/api.js')

Page({
  data: {
    statusBarHeight: 0,
    userName: '',
    todayDate: '',
    greeting: '',

  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
    })
  },

  onShow() {
    this.loadPageData()
  },

  loadPageData() {
    const user = api.getUser()
    this.setData({ userName: user.username || '用户' })
    this.setGreeting()
    this.setTodayDate()
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

  goRiver() {
    wx.navigateTo({ url: '/pages/river/river' })
  },

})
