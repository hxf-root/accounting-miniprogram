// 抱布记 - 应用入口
const api = require('./utils/api.js')

App({
  onLaunch() {
    // 检查登录状态
    const user = api.getUser()
    const token = api.getToken()
    if (!token || !user.user_id) {
      // 未登录，跳转登录页
      wx.reLaunch({ url: '/pages/login/login' })
    }
  },

  globalData: {
    user: null,
    categories: { expense: [], income: [] },
  }
})
