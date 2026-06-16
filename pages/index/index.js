// 记账首页 - 使用 API 后端
const api = require('../../utils/api.js')

Page({
  data: {
    currentYear: new Date().getFullYear(),
    currentMonth: new Date().getMonth() + 1,

    // 统计
    expenseText: '0.00',
    incomeText: '0.00',
    balanceText: '0.00',
    balanceColor: 'var(--income)',

    // 饼图
    pieChartData: [],
    pieChartStyle: '',
    hasExpenseData: false,

    // 预算
    budgetEnabled: false,
    budgetText: '未设置',
    budgetProgress: 0,
    budgetHint: '去「我的」页设置月预算',
    budgetHintClass: '',

    // 最近记录
    recentBills: [],

    // 分类缓存
    categoryMap: {},
  },

  onShow() {
    this.loadPageData()
  },

  onPullDownRefresh() {
    this.loadPageData()
    wx.stopPullDownRefresh()
  },

  async loadPageData() {
    const year = this.data.currentYear
    const month = this.data.currentMonth

    try {
      // 并行请求
      const [stats, allBills, settings] = await Promise.all([
        api.getMonthlyStats(year, month).catch(() => null),
        api.getBills({ page_size: 5 }).catch(() => []),
        api.getSettings().catch(() => ({ monthly_budget: 0 })),
      ])

      const expense = stats ? parseFloat(stats.expense || 0) : 0
      const income = stats ? parseFloat(stats.income || 0) : 0
      const balance = income - expense
      const balanceColor = balance >= 0 ? 'var(--income)' : 'var(--expense)'

      // 饼图数据
      const categoryStats = (stats && stats.category_stats) || []
      const pieChartData = this.buildPieData(categoryStats)
      const pieChartStyle = this.buildPieStyle(pieChartData)
      const hasExpenseData = expense > 0 && pieChartData.length > 0

      // 预算
      const budget = parseFloat(settings.monthly_budget || settings.monthlyBudget || 0)
      const budgetData = this.buildBudgetData(expense, budget)

      // 最近记录
      const recentBills = Array.isArray(allBills) ? allBills : (allBills.items || allBills.data || [])

      this.setData({
        expenseText: expense.toFixed(2),
        incomeText: income.toFixed(2),
        balanceText: Math.abs(balance).toFixed(2),
        balanceColor,
        pieChartData,
        pieChartStyle,
        hasExpenseData,
        recentBills: recentBills.slice(0, 5),
        ...budgetData,
      })
    } catch (err) {
      console.error('loadPageData error:', err)
    }
  },

  buildPieData(categoryStats) {
    const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#B2BEC3']
    return categoryStats.slice(0, 6).map((item, i) => ({
      name: item.category_name || item.categoryName,
      value: item.amount || 0,
      percentage: item.percentage || ((item.amount || 0) / (this.data.expenseText || 1) * 100).toFixed(1),
      color: item.color || colors[i % colors.length],
    }))
  },

  buildPieStyle(pieData) {
    if (!pieData.length) return ''
    let current = 0
    const parts = pieData.map(item => {
      const pct = parseFloat(item.percentage) || 0
      const seg = `${item.color} ${current}% ${current + pct}%`
      current += pct
      return seg
    })
    return `background: conic-gradient(${parts.join(', ')});`
  },

  buildBudgetData(expense, budget) {
    if (!budget || budget <= 0) {
      return {
        budgetEnabled: false,
        budgetText: '未设置',
        budgetProgress: 0,
        budgetHint: '去「我的」页设置月预算',
        budgetHintClass: '',
      }
    }
    const progressRaw = (expense / budget) * 100
    const progress = Math.min(100, Math.max(0, progressRaw))
    const remaining = budget - expense

    let hintClass = ''
    let hint = `剩余 ¥${Math.max(0, remaining).toFixed(2)}`
    if (progressRaw >= 100) {
      hintClass = 'over'
      hint = `已超支 ¥${Math.abs(remaining).toFixed(2)}`
    } else if (progressRaw >= 80) {
      hintClass = 'warn'
      hint = `已用 ${progress.toFixed(1)}%，还剩 ¥${Math.max(0, remaining).toFixed(2)}`
    }

    return {
      budgetEnabled: true,
      budgetText: budget.toFixed(2),
      budgetProgress: progress.toFixed(1),
      budgetHint: hint,
      budgetHintClass: hintClass,
    }
  },

  getPaymentMethodName(method) {
    const names = { wechat: '微信', alipay: '支付宝', cash: '现金', bankcard: '银行卡', credit: '信用卡', other: '其他' }
    return names[method] || method || ''
  },

  goToRecord() { wx.navigateTo({ url: '/pages/record/record' }) },
  goToHistory() { wx.navigateTo({ url: '/pages/history/history' }) },
  goToSettings() { wx.switchTab({ url: '/pages/settings/settings' }) },
})
