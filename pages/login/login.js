const api = require('../../utils/api.js')

Page({
  data: {
    username: '',
    password: '',
    isRegister: false,
    loading: false,
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  toggleMode() {
    this.setData({ isRegister: !this.data.isRegister })
  },

  onLogin() {
    const { username, password, isRegister, loading } = this.data
    if (loading) return

    // 校验
    if (!username.trim()) {
      wx.showToast({ title: '请输入用户名', icon: 'none' })
      return
    }
    if (!password.trim()) {
      wx.showToast({ title: '请输入密码', icon: 'none' })
      return
    }
    if (password.length < 6) {
      wx.showToast({ title: '密码至少6位', icon: 'none' })
      return
    }

    this.setData({ loading: true })

    const action = isRegister ? api.register : api.login

    action(username.trim(), password)
      .then(res => {
        // 保存 Token 和用户信息
        api.setToken(res.token)
        api.setUser({
          username: res.username,
          user_id: res.user_id,
        })
        wx.showToast({ title: isRegister ? '注册成功' : '登录成功', icon: 'success' })
        // 跳转到主页面
        setTimeout(() => {
          wx.reLaunch({ url: '/pages/main/main' })
        }, 300)
      })
      .catch(err => {
        wx.showToast({ title: err.message || '操作失败', icon: 'none' })
      })
      .finally(() => {
        this.setData({ loading: false })
      })
  },
})
