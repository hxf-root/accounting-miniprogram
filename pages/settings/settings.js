const api = require('../../utils/api.js')
const identity = require('../../utils/wechatIdentity.js')
const { formatDate } = require('../../utils/helpers.js')

Page({
  data: {
    statusBarHeight: 0,
    userName: '',
    hasAccount: false,
    wechatConfigured: null,
    wechatBound: null,
    autoEnabled: false,
    identityBusy: false,
    showWechatBindModal: false,
    wechatBindPassword: '',

  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({ statusBarHeight: sysInfo.statusBarHeight })
  },

  onShow() {
    const version = this.nextStateVersion()
    this.accountStateToken = null
    const user = api.getUser()
    this.setData({ userName: user.username || '私人空间', hasAccount: Boolean(api.getToken()),
      wechatConfigured: null, wechatBound: null, autoEnabled: identity.enabled() })
    return identity.restore().then(() => {
      if (version !== this.stateVersion) return
      return this.refreshAccountState(version)
    })
  },

  nextStateVersion() {
    this.stateVersion = (this.stateVersion || 0) + 1
    return this.stateVersion
  },

  async refreshAccountState(version = this.stateVersion) {
    const requestedToken = api.getToken()
    this.setData({ hasAccount: Boolean(requestedToken), autoEnabled: identity.enabled() })
    const [capabilities, account] = await Promise.allSettled([
      api.getCapabilities(), requestedToken ? api.getMe() : Promise.resolve(null),
    ])
    if (version !== this.stateVersion) return
    if (api.getToken() !== requestedToken) {
      this.setData({ hasAccount: Boolean(api.getToken()), userName: '私人空间', wechatBound: null, wechatConfigured: null })
      if (api.getToken()) return this.onShow()
      return
    }
    const cap = capabilities.status === 'fulfilled' ? capabilities.value : null
    const me = account.status === 'fulfilled' ? account.value : null
    const bound = me && typeof me.wechat_bound === 'boolean' ? me.wechat_bound : null
    this.accountStateToken = bound !== null ? requestedToken : null
    if (me && typeof me.username === 'string' && Number.isInteger(me.user_id)) {
      api.setUser({ username: me.username, user_id: me.user_id })
    }
    this.setData({ wechatConfigured: cap && typeof cap.wechat_identity_configured === 'boolean' ? cap.wechat_identity_configured : null,
      wechatBound: bound, userName: me && me.username || '私人空间', hasAccount: Boolean(api.getToken()), autoEnabled: identity.enabled() })
  },

  // ========== 数据导出 ==========

  onExport() {
    wx.showLoading({ title: '导出中...' })
    api.exportData()
      .then(data => {
        wx.hideLoading()
        const jsonStr = JSON.stringify(data, null, 2)
        // 写入文件并分享
        const fs = wx.getFileSystemManager()
        const filePath = `${wx.env.USER_DATA_PATH}/baobaoji_backup_${formatDate()}.json`
        fs.writeFile({
          filePath,
          data: jsonStr,
          encoding: 'utf-8',
          success() {
            wx.showActionSheet({
              itemList: ['保存到手机', '分享文件'],
              success(res) {
                if (res.tapIndex === 0) {
                  // 保存到相册/文件
                  wx.saveFileToDisk
                    ? wx.saveFileToDisk({ filePath })
                    : wx.saveFile({
                        tempFilePath: filePath,
                        success() { wx.showToast({ title: '已保存', icon: 'success' }) },
                        fail() { wx.showToast({ title: '保存失败', icon: 'none' }) },
                      })
                } else {
                  wx.shareFileMessage({ filePath })
                }
              },
            })
          },
          fail() {
            wx.showToast({ title: '导出失败', icon: 'none' })
          },
        })
      })
      .catch(() => {
        wx.hideLoading()
        wx.showToast({ title: '导出失败', icon: 'none' })
      })
  },

  connectAccount() {
    wx.navigateTo({ url: '/pages/login/login' })
  },

  bindWechat() {
    if (this.data.identityBusy || this.data.wechatConfigured !== true || this.data.wechatBound !== false ||
        !api.getToken() || api.getToken() !== this.accountStateToken) return
    this.setData({ showWechatBindModal: true, wechatBindPassword: '' })
  },

  setAutoEnabled() {
    if (this.data.wechatBound !== true || !api.getToken() || api.getToken() !== this.accountStateToken) return
    if (identity.enabled()) identity.stopAuto()
    else if (this.data.wechatConfigured === true) identity.startAuto()
    this.setData({ autoEnabled: identity.enabled() })
  },

  onBindPasswordInput(event) {
    this.setData({ wechatBindPassword: event.detail.value })
  },

  cancelWechatBind() {
    if (!this.data.identityBusy) this.setData({ showWechatBindModal: false, wechatBindPassword: '' })
  },

  onHide() {
    this.nextStateVersion()
    this.setData({ showWechatBindModal: false, wechatBindPassword: '' })
  },

  async confirmWechatBind() {
    if (this.data.identityBusy) return
    const password = this.data.wechatBindPassword
    if (!password) {
      wx.showToast({ title: '请输入账户密码', icon: 'none' })
      return
    }
    this.setData({ identityBusy: true, wechatBindPassword: '' })
    try {
      await identity.bind(password)
      this.setData({ wechatBound: true, autoEnabled: identity.enabled(), showWechatBindModal: false })
      wx.showToast({ title: '微信已连接', icon: 'success' })
    } catch (_) {
      wx.showToast({ title: '连接失败，请核对密码或稍后再试', icon: 'none' })
    } finally { this.setData({ identityBusy: false, wechatBindPassword: '' }) }
  },

  unbindWechat() {
    if (this.data.identityBusy || this.data.wechatConfigured !== true || this.data.wechatBound !== true ||
        !api.getToken() || api.getToken() !== this.accountStateToken) return
    wx.showModal({
      title: '解除微信连接',
      content: '解除后将退出当前账户，并关闭本机自动识别。',
      success: async result => {
        if (!result.confirm) return
        this.setData({ identityBusy: true })
        try {
          await identity.unbind()
          wx.reLaunch({ url: '/pages/main/main' })
        } catch (_) {
          wx.showToast({ title: '解除失败，请稍后再试', icon: 'none' })
        } finally { this.setData({ identityBusy: false }) }
      },
    })
  },

  // ========== 退出登录 ==========

  onLogout() {
    if (this.data.identityBusy) return
    wx.showModal({
      title: '退出登录',
      content: '退出后将关闭本机自动识别，可重新连接账户。',
      success: async res => {
        if (!res.confirm || this.data.identityBusy) return
        const token = api.getToken()
        const wasAutoEnabled = identity.enabled()
        this.setData({ identityBusy: true })
        identity.stopAuto()
        try {
          await api.logout()
          if (api.getToken() !== token) return
          api.clearAuth()
          wx.reLaunch({ url: '/pages/main/main' })
        } catch (error) {
          if (!api.getToken() && error.statusCode === 401) {
            wx.reLaunch({ url: '/pages/main/main' })
            return
          }
          if (api.getToken() !== token) return
          wx.showModal({ title: '仅退出本机？',
            content: '服务器未能确认撤销当前登录凭证。仅退出本机会清除本机登录信息，但该凭证可能仍有效。',
            confirmText: '本机退出',
            success: answer => {
              if (api.getToken() !== token) return
              if (!answer.confirm) {
                if (wasAutoEnabled) identity.startAuto()
                this.setData({ autoEnabled: identity.enabled() })
                return
              }
              api.clearAuth()
              wx.reLaunch({ url: '/pages/main/main' })
            },
          })
        } finally {
          this.setData({ identityBusy: false, autoEnabled: identity.enabled() })
        }
      },
    })
  },

  // ========== 工具方法 ==========

  formatDate() {
    const now = new Date()
    const y = now.getFullYear()
    const m = String(now.getMonth() + 1).padStart(2, '0')
    const d = String(now.getDate()).padStart(2, '0')
    return `${y}${m}${d}`
  },
})
