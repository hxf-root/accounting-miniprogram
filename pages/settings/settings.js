const api = require('../../utils/api.js')
const { formatDate } = require('../../utils/helpers.js')

Page({
  data: {
    statusBarHeight: 0,
    userName: '',
    hasAccount: false,

  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({ statusBarHeight: sysInfo.statusBarHeight })
  },

  onShow() {
    const user = api.getUser()
    this.setData({ userName: user.username || '私人空间', hasAccount: Boolean(api.getToken()) })
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

  // ========== 退出登录 ==========

  onLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出当前账号吗？',
      success(res) {
        if (res.confirm) {
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
