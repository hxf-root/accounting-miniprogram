// 明细页 - 使用 API 后端
const api = require('../../utils/api.js')

Page({
  data: {
    billGroups: [],
    loading: false,
    refreshing: false,

    // 统计
    totalExpense: 0,
    totalIncome: 0,
    balance: 0,
    balanceColor: 'var(--income)',

    // 筛选
    showFilter: false,
    filterType: '',
    filterTypeText: '',
    filterPayment: '',
    filterPaymentName: '',
    filterDateRange: 'all',
    dateRangeText: '',
    startDate: '',
    endDate: '',
    hasFilter: false,
  },

  onLoad() {
    this.initDates()
  },

  onShow() {
    this.loadBills()
  },

  initDates() {
    const now = new Date()
    const end = this._fmtDate(now)
    const start = this._fmtDate(new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000))
    this.setData({ startDate: start, endDate: end })
  },

  _fmtDate(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  },

  onRefresh() {
    this.setData({ refreshing: true })
    this.loadBills()
  },

  async loadBills() {
    this.setData({ loading: true })
    try {
      const params = {}
      if (this.data.filterType) params.type = this.data.filterType
      if (this.data.filterPayment) params.payment = this.data.filterPayment

      // 时间范围
      if (this.data.filterDateRange === 'week') {
        const now = new Date()
        params.date_from = this._fmtDate(new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000))
        params.date_to = this._fmtDate(now)
      } else if (this.data.filterDateRange === 'month') {
        const now = new Date()
        params.date_from = this._fmtDate(new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000))
        params.date_to = this._fmtDate(now)
      } else if (this.data.filterDateRange === 'custom' && this.data.startDate && this.data.endDate) {
        params.date_from = this.data.startDate
        params.date_to = this.data.endDate
      }

      params.page_size = 500

      const res = await api.getBills(params)
      const bills = Array.isArray(res) ? res : (res.items || res.data || [])

      // 按日期分组（后端返回已是倒序，API层处理）
      const groups = this._groupByDate(bills)

      // 统计
      let totalExpense = 0
      let totalIncome = 0
      groups.forEach(g => {
        totalExpense += g.expense
        totalIncome += g.income
      })
      const balance = totalIncome - totalExpense
      const balanceColor = balance >= 0 ? 'var(--income)' : 'var(--expense)'

      this.setData({
        billGroups: groups,
        totalExpense: parseFloat(totalExpense.toFixed(2)),
        totalIncome: parseFloat(totalIncome.toFixed(2)),
        balance: parseFloat(balance.toFixed(2)),
        balanceColor,
        loading: false,
        refreshing: false,
      })
    } catch (err) {
      console.error('loadBills error:', err)
      this.setData({ loading: false, refreshing: false })
    }
  },

  _groupByDate(bills) {
    const map = {}
    ;(bills || []).forEach(b => {
      const d = b.date || ''
      if (!map[d]) {
        map[d] = { date: d, bills: [], expense: 0, income: 0 }
      }
      const amt = parseFloat(b.amount) || 0
      map[d].bills.push(b)
      if (b.type === 'expense') map[d].expense += amt
      else map[d].income += amt
    })
    return Object.values(map)
      .map(g => ({
        ...g,
        expense: parseFloat(g.expense.toFixed(2)),
        income: parseFloat(g.income.toFixed(2)),
        expenseText: g.expense.toFixed(2),
        incomeText: g.income.toFixed(2),
      }))
      .sort((a, b) => b.date.localeCompare(a.date))
  },

  // ---- 筛选 ----
  onShowFilter() { this.setData({ showFilter: true }) },
  onHideFilter() { this.setData({ showFilter: false }) },
  stopPropagation() {},

  onFilterTypeChange(e) {
    const type = e.currentTarget.dataset.type
    const names = { expense: '支出', income: '收入' }
    this.setData({
      filterType: type,
      filterTypeText: names[type] || '',
    }, () => this.loadBills())
  },

  onFilterPaymentChange(e) {
    const names = { wechat: '微信', alipay: '支付宝', cash: '现金', bankcard: '银行卡', credit: '信用卡' }
    const payment = e.currentTarget.dataset.payment
    this.setData({
      filterPayment: payment,
      filterPaymentName: names[payment] || '',
    }, () => this.loadBills())
  },

  onDateRangeChange(e) {
    const range = e.currentTarget.dataset.range
    const labels = { all: '', week: '近7天', month: '近30天', custom: '自定义' }
    this.setData({
      filterDateRange: range,
      dateRangeText: labels[range] || '',
    }, () => {
      if (range !== 'custom') this.loadBills()
    })
  },

  onStartDateChange(e) {
    this.setData({ startDate: e.detail.value, filterDateRange: 'custom', dateRangeText: '自定义' }, () => this.loadBills())
  },

  onEndDateChange(e) {
    this.setData({ endDate: e.detail.value, filterDateRange: 'custom', dateRangeText: '自定义' }, () => this.loadBills())
  },

  onResetFilter() {
    this.setData({
      filterType: '',
      filterTypeText: '',
      filterPayment: '',
      filterPaymentName: '',
      filterDateRange: 'all',
      dateRangeText: '',
    })
    this.initDates()
    this.loadBills()
  },

  clearFilterType() {
    this.setData({ filterType: '', filterTypeText: '' }, () => this.loadBills())
  },
  clearFilterPayment() {
    this.setData({ filterPayment: '', filterPaymentName: '' }, () => this.loadBills())
  },
  clearDateRange() {
    this.setData({ filterDateRange: 'all', dateRangeText: '' }, () => this.loadBills())
  },

  // ---- 操作 ----
  onEditBill(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/record/record?id=${id}` })
  },

  onDeleteBill(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认删除',
      content: '删除后不可恢复，确定吗？',
      confirmColor: '#e86a6a',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.deleteBill(id)
            wx.showToast({ title: '已删除', icon: 'success' })
            this.loadBills()
          } catch (err) {
            wx.showToast({ title: err.message || '删除失败', icon: 'none' })
          }
        }
      },
    })
  },

  getPaymentMethodName(m) {
    const names = { wechat: '微信', alipay: '支付宝', cash: '现金', bankcard: '银行卡', credit: '信用卡', other: '其他' }
    return names[m] || m || ''
  },

  formatDateDisplay(dateStr) {
    if (!dateStr) return ''
    const today = this._fmtDate(new Date())
    const yesterday = this._fmtDate(new Date(Date.now() - 86400000))
    if (dateStr === today) return '今天'
    if (dateStr === yesterday) return '昨天'
    const d = new Date(dateStr)
    const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    return `${d.getMonth() + 1}月${d.getDate()}日 ${weekDays[d.getDay()]}`
  },

  goToRecord() {
    wx.navigateTo({ url: '/pages/record/record' })
  },
})
