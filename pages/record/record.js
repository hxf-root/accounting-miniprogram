// 记账页 - 使用 API 后端
const api = require('../../utils/api.js')

Page({
  data: {
    type: 'expense',

    // 金额
    amount: '0',

    // 分类
    categories: [],
    selectedCategory: null,

    // 支付方式
    paymentMethods: [
      { id: 'wechat', name: '微信', icon: '微', color: '#07C160' },
      { id: 'alipay', name: '支付宝', icon: '支', color: '#1677FF' },
      { id: 'cash', name: '现金', icon: '现', color: '#FF9500' },
      { id: 'bankcard', name: '银行卡', icon: '卡', color: '#5856D6' },
      { id: 'credit', name: '信用卡', icon: '信', color: '#FF6B6B' },
      { id: 'other', name: '其他', icon: '其', color: '#B2BEC3' },
    ],
    selectedPayment: 'wechat',

    // 备注
    remark: '',
    showRemarkInput: false,

    // 日期时间
    date: '',
    time: '',
    showDatePicker: false,
    showTimePicker: false,

    // 快捷备注
    commonRemarks: {
      expense: ['早餐', '午餐', '晚餐', '交通', '购物', '奶茶', '外卖', '买菜', '零食', '话费'],
      income: ['工资', '奖金', '红包', '兼职', '理财', '退款'],
    },

    // 编辑
    isEdit: false,
    editId: null,
  },

  onLoad(options) {
    this.initDateTime()
    this.loadCategories()

    if (options.id) {
      this.loadBillForEdit(options.id)
    }
  },

  initDateTime() {
    const now = new Date()
    this.setData({
      date: this._fmtDate(now),
      time: this._fmtTime(now),
    })
  },

  _fmtDate(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  },
  _fmtTime(d) {
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  },

  async loadCategories() {
    try {
      const cats = await api.getCategories(this.data.type)
      const list = Array.isArray(cats) ? cats : []
      this.setData({
        categories: list,
        selectedCategory: list.length > 0 ? list[0] : null,
      })
    } catch (err) {
      console.error('loadCategories error:', err)
    }
  },

  async loadBillForEdit(id) {
    try {
      const bills = await api.getBills({ page_size: 100 })
      const all = Array.isArray(bills) ? bills : (bills.items || bills.data || [])
      const bill = all.find(b => b.id === id)
      if (!bill) return

      const cats = await api.getCategories(bill.type)
      const catList = Array.isArray(cats) ? cats : []
      const matched = catList.find(c => c.id === bill.category_id)

      this.setData({
        isEdit: true,
        editId: id,
        type: bill.type,
        amount: String(bill.amount || '0'),
        categories: catList,
        selectedCategory: matched || catList[0] || null,
        selectedPayment: bill.payment_method || 'wechat',
        remark: bill.remark || '',
        date: bill.date || this.data.date,
        time: bill.time || this.data.time,
      })
    } catch (err) {
      console.error('loadBillForEdit error:', err)
    }
  },

  onTypeChange(e) {
    const type = e.currentTarget.dataset.type
    this.setData({ type }, () => this.loadCategories())
  },

  onNumberInput(e) {
    const key = e.currentTarget.dataset.num
    let { amount } = this.data

    if (key === 'backspace') {
      amount = amount.length > 1 ? amount.slice(0, -1) : '0'
    } else if (key === '.') {
      if (!amount.includes('.')) amount += '.'
    } else {
      if (amount === '0') {
        amount = key
      } else if (amount.length < 10) {
        const parts = amount.split('.')
        if (parts.length === 2 && parts[1].length >= 2) return
        amount += key
      }
    }
    this.setData({ amount })
  },

  onCategorySelect(e) {
    const idx = e.currentTarget.dataset.index
    this.setData({ selectedCategory: this.data.categories[idx] })
  },

  onPaymentSelect(e) {
    this.setData({ selectedPayment: e.currentTarget.dataset.method })
  },

  onShowRemarkInput() { this.setData({ showRemarkInput: true }) },
  onHideRemarkInput() { this.setData({ showRemarkInput: false }) },
  stopPropagation() {},
  onRemarkInput(e) { this.setData({ remark: e.detail.value }) },

  onSelectCommonRemark(e) {
    this.setData({ remark: e.currentTarget.dataset.remark })
  },

  onShowDatePicker() {
    wx.createSelectorQuery()
      .selectAll('picker')
      .fields({ node: true, dataset: true })
      .exec(() => {
        // 直接触发 picker 隐藏组件
        this.setData({ showDatePicker: true })
      })
  },

  onDateChange(e) {
    this.setData({ date: e.detail.value, showDatePicker: false })
  },

  onShowTimePicker() {
    this.setData({ showTimePicker: true })
  },

  onTimeChange(e) {
    this.setData({ time: e.detail.value, showTimePicker: false })
  },

  async onSave() {
    const { amount, selectedCategory, selectedPayment, remark, date, time, type, isEdit, editId } = this.data

    if (amount === '0' || amount === '0.' || amount === '') {
      wx.showToast({ title: '请输入金额', icon: 'none' })
      return
    }
    if (!selectedCategory) {
      wx.showToast({ title: '请选择分类', icon: 'none' })
      return
    }

    const payload = {
      type,
      amount: parseFloat(amount),
      category_id: selectedCategory.id,
      category_name: selectedCategory.name,
      payment_method: selectedPayment,
      remark: (remark || '').trim(),
      date,
      time,
    }

    try {
      if (isEdit) {
        await api.updateBill(editId, payload)
        wx.showToast({ title: '修改成功', icon: 'success' })
      } else {
        await api.createBill(payload)
        wx.showToast({ title: '记账成功', icon: 'success' })
      }
      setTimeout(() => wx.navigateBack(), 800)
    } catch (err) {
      wx.showToast({ title: err.message || '保存失败', icon: 'none' })
    }
  },

  onCancel() {
    wx.navigateBack()
  },
})
