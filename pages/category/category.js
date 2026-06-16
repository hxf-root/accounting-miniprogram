// 分类管理页 - 使用 API 后端
const api = require('../../utils/api.js')

Page({
  data: {
    currentType: 'expense',
    categories: [],
    loading: false,

    // 表单
    showForm: false,
    formName: '',
    formIcon: '📦',
    formColor: '#5cb8a0',
    saving: false,

    // 预设
    iconOptions: ['🍔', '🚗', '🛍️', '🎬', '🏠', '🏥', '📚', '☕', '🎮', '🐱', '💄', '📱', '🏋️', '✈️', '🎁', '💊', '📖', '🎵', '🌿', '🧹', '🔧', '💡', '👕', '🍎', '🧋', '📦', '🎂', '🍷'],
    colorOptions: ['#5cb8a0', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8',
                   '#F0A500', '#E17055', '#00B894', '#0984E3', '#6C5CE7', '#FD79A8', '#00CEC9', '#FDCB6E'],
  },

  onShow() {
    this.loadCategories()
  },

  async loadCategories() {
    this.setData({ loading: true })
    try {
      const cats = await api.getCategories(this.data.currentType)
      this.setData({
        categories: Array.isArray(cats) ? cats : [],
        loading: false,
      })
    } catch (err) {
      console.error('loadCategories error:', err)
      this.setData({ loading: false })
    }
  },

  switchType(e) {
    const type = e.currentTarget.dataset.type
    this.setData({ currentType: type }, () => this.loadCategories())
  },

  // ---- 表单 ----
  onShowAddForm() {
    this.setData({
      showForm: true,
      formName: '',
      formIcon: '📦',
      formColor: '#5cb8a0',
    })
  },

  onHideForm() {
    this.setData({ showForm: false })
  },

  stopPropagation() {},

  onFormNameInput(e) {
    this.setData({ formName: e.detail.value })
  },

  onIconSelect(e) {
    this.setData({ formIcon: e.currentTarget.dataset.icon })
  },

  onColorSelect(e) {
    this.setData({ formColor: e.currentTarget.dataset.color })
  },

  async onSubmitCategory() {
    const { formName, formIcon, formColor, currentType } = this.data

    if (!formName || !formName.trim()) {
      wx.showToast({ title: '请输入分类名称', icon: 'none' })
      return
    }

    this.setData({ saving: true })
    try {
      await api.createCategory({
        type: currentType,
        name: formName.trim(),
        icon: formIcon,
        color: formColor,
      })
      wx.showToast({ title: '添加成功', icon: 'success' })
      this.setData({ showForm: false, saving: false })
      this.loadCategories()
    } catch (err) {
      wx.showToast({ title: err.message || '添加失败', icon: 'none' })
      this.setData({ saving: false })
    }
  },

  async onDeleteCategory(e) {
    const id = e.currentTarget.dataset.id

    wx.showModal({
      title: '确认删除',
      content: '删除后无法恢复，确定删除此分类？',
      confirmColor: '#e86a6a',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.deleteCategory(id)
            wx.showToast({ title: '已删除', icon: 'success' })
            this.loadCategories()
          } catch (err) {
            wx.showToast({ title: err.message || '删除失败', icon: 'none' })
          }
        }
      },
    })
  },
})
