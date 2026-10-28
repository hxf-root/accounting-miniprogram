const api = require('../../utils/api.js')
const identity = require('../../utils/wechatIdentity.js')
const { formatDate } = require('../../utils/helpers.js')

Page({
  data: {
    statusBarHeight: 0,
    userName: '',
    hasAccount: false,
    wechatEnabled: false,
    identityBusy: false,

  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({ statusBarHeight: sysInfo.statusBarHeight })
  },

  onShow() {
    const user = api.getUser()
    this.setData({ userName: user.username || '私人空间', hasAccount: Boolean(api.getToken()), wechatEnabled: identity.enabled() })
    identity.restore().then(() => {
      const current = api.getUser()
      this.setData({ userName: current.username || '私人空间', hasAccount: Boolean(api.getToken()), wechatEnabled: identity.enabled() })
    })
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

  async bindWechat() {
    if (this.data.identityBusy) return
    this.setData({ identityBusy: true })
    try {
      await identity.bind()
      this.setData({ wechatEnabled: identity.enabled() })
      wx.showToast({ title: '微信已连接', icon: 'success' })
    } catch (_) {
      wx.showToast({ title: '连接失败，请稍后再试', icon: 'none' })
    } finally { this.setData({ identityBusy: false }) }
  },

  unbindWechat() {
    if (this.data.identityBusy) return
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
    wx.showModal({
      title: '退出登录',
      content: '退出后将关闭本机自动识别，可重新连接账户。',
      success(res) {
        if (res.confirm) {
          identity.stopAuto()
          api.clearAuth()
          wx.reLaunch({ url: '/pages/main/main' })
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
