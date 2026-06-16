const api = require('../../utils/api.js')

Page({
  data: {
    statusBarHeight: 0,
    activeTab: 'json',        // 'json' | 'csv'
    // JSON 导入
    jsonText: '',
    // CSV 导入
    csvFileName: '',
    csvFileSize: '',
    csvFileData: '',
    csvPreview: '',
    // 结果弹窗
    showResultModal: false,
    importSuccess: false,
    importResultText: '',
    importError: '',
    // JSON 模板
    jsonTemplate: '',
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({ statusBarHeight: sysInfo.statusBarHeight })

    // 构建模板
    this.setData({
      jsonTemplate: `{\n  "bills": [\n    {\n      "date": "2024-01-15",\n      "type": "expense",\n      "amount": 35.00,\n      "category": "餐饮",\n      "note": "午餐"\n    }\n  ],\n  "fitness": [],\n  "settings": {}\n}`,
    })
  },

  onShow() {
    // 每次显示刷新
  },

  // ========== TAB 切换 ==========

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
  },

  // ========== 返回 ==========

  goBack() {
    wx.navigateBack()
  },

  // ========== JSON 导入 ==========

  onJsonInput(e) {
    this.setData({ jsonText: e.detail.value })
  },

  clearJson() {
    this.setData({ jsonText: '' })
  },

  importJson() {
    const text = this.data.jsonText.trim()
    if (!text) {
      wx.showToast({ title: '请粘贴 JSON 数据', icon: 'none' })
      return
    }

    let data
    try {
      data = JSON.parse(text)
    } catch (e) {
      wx.showToast({ title: 'JSON 格式错误', icon: 'none' })
      return
    }

    // 校验格式
    if (!data || typeof data !== 'object') {
      wx.showToast({ title: '无效的 JSON 对象', icon: 'none' })
      return
    }

    // 统一格式：支持 {bills, fitness, settings} 顶层结构
    const importPayload = {
      bills: Array.isArray(data.bills) ? data.bills : [],
      fitness: Array.isArray(data.fitness) ? data.fitness : [],
      settings: data.settings || {},
    }

    // 也支持直接传数组（仅账单）
    if (Array.isArray(data)) {
      importPayload.bills = data
      importPayload.fitness = []
      importPayload.settings = {}
    }

    // 也支持 {records: [...]} 结构
    if (Array.isArray(data.records)) {
      importPayload.bills = data.records
    }

    wx.showLoading({ title: '导入中...', mask: true })
    api.importData(importPayload)
      .then(result => {
        wx.hideLoading()
        const billCount = result.bills ? (result.bills.length || result.bills) : importPayload.bills.length
        const fitnessCount = result.fitness ? (result.fitness.length || result.fitness) : importPayload.fitness.length
        this.setData({
          showResultModal: true,
          importSuccess: true,
          importResultText: `导入成功！\n账单：${billCount} 条\n健身记录：${fitnessCount} 条`,
          importError: '',
        })
        this.setData({ jsonText: '' })
      })
      .catch(err => {
        wx.hideLoading()
        this.setData({
          showResultModal: true,
          importSuccess: false,
          importResultText: '导入失败',
          importError: err.message || '未知错误，请检查数据格式',
        })
      })
  },

  // ========== CSV 导入 ==========

  chooseCsv() {
    const self = this
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['csv', 'txt'],
      success(res) {
        const file = res.tempFiles[0]
        if (!file) return

        const fileName = file.name || '未命名.csv'
        const fileSize = self.formatFileSize(file.size)

        // 读取文件内容
        const fs = wx.getFileSystemManager()
        fs.readFile({
          filePath: file.path,
          encoding: 'utf-8',
          success(readRes) {
            const content = readRes.data || ''
            // 预览前3行
            const lines = content.split('\n').slice(0, 3)
            const preview = lines.join('\n')

            self.setData({
              csvFileName: fileName,
              csvFileSize: fileSize,
              csvFileData: content,
              csvPreview: preview || '（空文件）',
            })
          },
          fail() {
            wx.showToast({ title: '读取文件失败', icon: 'none' })
          },
        })
      },
      fail(err) {
        if (err.errMsg.indexOf('cancel') === -1) {
          wx.showToast({ title: '选择文件失败', icon: 'none' })
        }
      },
    })
  },

  clearCsv() {
    this.setData({
      csvFileName: '',
      csvFileSize: '',
      csvFileData: '',
      csvPreview: '',
    })
  },

  importCsv() {
    const csvData = this.data.csvFileData
    if (!csvData) {
      wx.showToast({ title: '请先选择 CSV 文件', icon: 'none' })
      return
    }

    try {
      const bills = this.parseCsv(csvData)
      if (bills.length === 0) {
        wx.showToast({ title: '未解析到有效数据', icon: 'none' })
        return
      }

      wx.showLoading({ title: `导入 ${bills.length} 条...`, mask: true })
      api.importData({ bills, fitness: [], settings: {} })
        .then(result => {
          wx.hideLoading()
          const count = result.bills ? (result.bills.length || result.bills) : bills.length
          this.setData({
            showResultModal: true,
            importSuccess: true,
            importResultText: `CSV 导入成功！\n账单：${count} 条`,
            importError: '',
          })
          this.clearCsv()
        })
        .catch(err => {
          wx.hideLoading()
          this.setData({
            showResultModal: true,
            importSuccess: false,
            importResultText: 'CSV 导入失败',
            importError: err.message || '请检查 CSV 格式',
          })
        })
    } catch (e) {
      wx.showToast({ title: 'CSV 解析失败: ' + e.message, icon: 'none' })
    }
  },

  /**
   * 解析 CSV 文本为账单数组
   */
  parseCsv(text) {
    const lines = text.split('\n').filter(line => line.trim())
    if (lines.length < 2) {
      throw new Error('CSV 至少需要表头 + 1 行数据')
    }

    // 解析表头
    const headers = this.parseCsvLine(lines[0]).map(h => h.trim().toLowerCase())
    const dateIdx = headers.indexOf('date')
    const typeIdx = headers.indexOf('type')
    const amountIdx = headers.indexOf('amount')
    const categoryIdx = headers.indexOf('category')
    const noteIdx = headers.indexOf('note')

    if (dateIdx === -1 || typeIdx === -1 || amountIdx === -1) {
      throw new Error('CSV 缺少必要列: date, type, amount')
    }

    const bills = []
    for (let i = 1; i < lines.length; i++) {
      const fields = this.parseCsvLine(lines[i])
      if (fields.length <= 1) continue

      const type = (fields[typeIdx] || '').trim().toLowerCase()
      if (type !== 'expense' && type !== 'income') continue

      const amount = parseFloat(fields[amountIdx])
      if (isNaN(amount) || amount <= 0) continue

      bills.push({
        date: (fields[dateIdx] || '').trim(),
        type,
        amount,
        category: categoryIdx >= 0 ? (fields[categoryIdx] || '').trim() : '其他',
        note: noteIdx >= 0 ? (fields[noteIdx] || '').trim() : '',
      })
    }

    return bills
  },

  /**
   * 解析 CSV 单行（支持引号包裹的字段）
   */
  parseCsvLine(line) {
    const fields = []
    let current = ''
    let inQuotes = false

    for (let i = 0; i < line.length; i++) {
      const ch = line[i]
      if (ch === '"') {
        inQuotes = !inQuotes
      } else if (ch === ',' && !inQuotes) {
        fields.push(current)
        current = ''
      } else {
        current += ch
      }
    }
    fields.push(current)
    return fields
  },

  // ========== 结果弹窗 ==========

  hideResultModal() {
    this.setData({ showResultModal: false })
  },

  // ========== 工具方法 ==========

  formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB']
    let idx = 0
    let size = bytes
    while (size >= 1024 && idx < units.length - 1) {
      size /= 1024
      idx++
    }
    return size.toFixed(1) + ' ' + units[idx]
  },
})
