const api = require('../../utils/api.js')

Page({
  data: {
    statusBarHeight: 0,
    userName: '',
    loading: true,
    refreshing: false,
    // 统计
    stats: {
      totalCount: 0,
      totalExpense: '0.00',
      totalIncome: '0.00',
      totalExpenseNum: 0,
      totalIncomeNum: 0,
    },
    // 预算
    budget: 0,
    budgetEditValue: '',
    budgetPercent: 0,
    // 弹窗
    showClearModal: false,
    showBudgetModal: false,
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({ statusBarHeight: sysInfo.statusBarHeight })
  },

  onShow() {
    this.loadPageData()
  },

  onRefresh() {
    this.setData({ refreshing: true })
    this.loadPageData()
  },

  loadPageData() {
    // 用户信息
    const user = api.getUser()
    this.setData({ userName: user.username || '用户' })

    // 并行加载设置 + 全部账单
    Promise.all([
      api.getSettings(),
      api.getBills({ page: 1, page_size: 999 }),
    ])
      .then(([settings, billsData]) => {
        const budget = settings.monthly_budget || 0
        const bills = Array.isArray(billsData) ? billsData : (billsData.items || billsData.records || [])
        const stats = this.calcStats(bills)

        this.setData({
          budget,
          budgetEditValue: budget > 0 ? String(budget) : '',
          stats,
          budgetPercent: this.calcBudgetPercent(budget, stats.totalExpenseNum),
          loading: false,
          refreshing: false,
        })
      })
      .catch(err => {
        wx.showToast({ title: '数据加载失败', icon: 'none' })
        this.setData({ loading: false, refreshing: false })
      })
  },

  /**
   * 统计所有账单
   */
  calcStats(bills) {
    let totalExpense = 0
    let totalIncome = 0
    let count = 0
    for (const bill of bills) {
      const amount = Number(bill.amount) || 0
      if (bill.type === 'expense' || bill.type === 0) {
        totalExpense += amount
      } else if (bill.type === 'income' || bill.type === 1) {
        totalIncome += amount
      }
      count++
    }
    return {
      totalCount: count,
      totalExpense: totalExpense.toFixed(2),
      totalIncome: totalIncome.toFixed(2),
      totalExpenseNum: totalExpense,
      totalIncomeNum: totalIncome,
    }
  },

  /**
   * 计算预算百分比
   */
  calcBudgetPercent(budget, expense) {
    if (!budget || budget <= 0 || !expense || expense <= 0) return 0
    const pct = Math.min(100, Math.round((expense / budget) * 100))
    return pct
  },

  // ========== 预算相关 ==========

  onBudgetInput(e) {
    // 实时输入不保存，只记录值
    this.setData({ budgetEditValue: e.detail.value })
  },

  onBudgetBlur(e) {
    // 失焦时保存预算
    const val = parseFloat(e.detail.value) || 0
    this.saveBudget(val)
  },

  onBudgetEditInput(e) {
    this.setData({ budgetEditValue: e.detail.value })
  },

  showBudgetModal() {
    this.setData({
      showBudgetModal: true,
      budgetEditValue: this.data.budget > 0 ? String(this.data.budget) : '',
    })
  },

  hideBudgetModal() {
    this.setData({ showBudgetModal: false })
  },

  confirmBudget() {
    const val = parseFloat(this.data.budgetEditValue) || 0
    this.saveBudget(val)
    this.hideBudgetModal()
  },

  saveBudget(val) {
    const budget = Math.max(0, val)
    api.updateSettings({ monthly_budget: budget })
      .then(() => {
        this.setData({
          budget,
          budgetEditValue: budget > 0 ? String(budget) : '',
          budgetPercent: this.calcBudgetPercent(budget, this.data.stats.totalExpenseNum),
        })
        wx.showToast({ title: budget > 0 ? '预算已设置' : '预算已取消', icon: 'success' })
      })
      .catch(() => {
        wx.showToast({ title: '保存失败', icon: 'none' })
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
        const filePath = `${wx.env.USER_DATA_PATH}/baobaoji_backup_${this.formatDate()}.json`
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

  // ========== 导入跳转 ==========

  goImport() {
    wx.navigateTo({ url: '/pages/import-bill/import-bill' })
  },

  // ========== 清空数据 ==========

  onClearData() {
    this.setData({ showClearModal: true })
  },

  hideClearModal() {
    this.setData({ showClearModal: false })
  },

  confirmClearData() {
    this.hideClearModal()
    wx.showLoading({ title: '清空中...', mask: true })
    // 清空：先获取全部数据，导入空数据覆盖
    api.exportData()
      .then(() => {
        return api.importData({ bills: [], fitness: [], settings: {} })
      })
      .then(() => {
        wx.hideLoading()
        wx.showToast({ title: '已清空所有数据', icon: 'success' })
        this.loadPageData()
      })
      .catch(() => {
        wx.hideLoading()
        wx.showToast({ title: '清空失败', icon: 'none' })
      })
  },

  // ========== 退出登录 ==========

  onLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出当前账号吗？',
      success(res) {
        if (res.confirm) {
          api.clearAuth()
          wx.reLaunch({ url: '/pages/login/login' })
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
