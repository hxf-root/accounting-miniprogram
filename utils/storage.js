// 数据存储服务 - 基于 wx.setStorageSync
// 只保留记账相关，健身数据全走云端 API
const config = require('./config.js')

const STORAGE_KEYS = config.STORAGE_KEYS

// 安全的存储操作封装
const safeStorage = {
  get(key, defaultValue = []) {
    try {
      const value = wx.getStorageSync(key)
      return value !== undefined ? value : defaultValue
    } catch (error) {
      console.error(`Get storage error for ${key}:`, error)
      return defaultValue
    }
  },

  set(key, value) {
    try {
      wx.setStorageSync(key, value)
      return true
    } catch (error) {
      console.error(`Set storage error for ${key}:`, error)
      return false
    }
  }
}

// 账单相关操作
const billService = {
  getAllBills() {
    return safeStorage.get(STORAGE_KEYS.BILLS, [])
  },

  addBill(bill) {
    const bills = this.getAllBills()
    const newBill = {
      ...bill,
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
    bills.unshift(newBill)
    safeStorage.set(STORAGE_KEYS.BILLS, bills)
    return newBill
  },

  updateBill(id, updates) {
    const bills = this.getAllBills()
    const index = bills.findIndex(b => b.id === id)
    if (index !== -1) {
      bills[index] = {
        ...bills[index],
        ...updates,
        updatedAt: Date.now()
      }
      safeStorage.set(STORAGE_KEYS.BILLS, bills)
      return bills[index]
    }
    return null
  },

  deleteBill(id) {
    const bills = this.getAllBills()
    const filtered = bills.filter(b => b.id !== id)
    safeStorage.set(STORAGE_KEYS.BILLS, filtered)
    return filtered.length !== bills.length
  },

  getBillById(id) {
    const bills = this.getAllBills()
    return bills.find(b => b.id === id)
  },

  getMonthStats(year, month) {
    const bills = this.getAllBills()
    const targetMonth = `${year}-${String(month).padStart(2, '0')}`

    const monthBills = bills.filter(b => b.date.startsWith(targetMonth))

    const expense = monthBills
      .filter(b => b.type === 'expense')
      .reduce((sum, b) => sum + b.amount, 0)

    const income = monthBills
      .filter(b => b.type === 'income')
      .reduce((sum, b) => sum + b.amount, 0)

    return {
      expense: parseFloat(expense.toFixed(2)),
      income: parseFloat(income.toFixed(2)),
      balance: parseFloat((income - expense).toFixed(2))
    }
  },

  filterBills(filters = {}) {
    let bills = this.getAllBills()

    if (filters.type) {
      bills = bills.filter(b => b.type === filters.type)
    }

    if (filters.categoryId) {
      bills = bills.filter(b => b.categoryId === filters.categoryId)
    }

    if (filters.paymentMethod) {
      bills = bills.filter(b => b.paymentMethod === filters.paymentMethod)
    }

    if (filters.startDate && filters.endDate) {
      bills = bills.filter(b =>
        b.date >= filters.startDate && b.date <= filters.endDate
      )
    }

    if (filters.keyword) {
      bills = bills.filter(b =>
        b.remark && b.remark.includes(filters.keyword)
      )
    }

    return bills
  },

  getBillsGroupedByDate(filters = {}) {
    const bills = this.filterBills(filters)
    const groups = {}

    bills.forEach(bill => {
      if (!groups[bill.date]) {
        groups[bill.date] = {
          date: bill.date,
          bills: [],
          expense: 0,
          income: 0
        }
      }
      groups[bill.date].bills.push(bill)
      if (bill.type === 'expense') {
        groups[bill.date].expense += bill.amount
      } else {
        groups[bill.date].income += bill.amount
      }
    })

    return Object.values(groups)
      .map(g => ({
        ...g,
        expense: parseFloat(g.expense.toFixed(2)),
        income: parseFloat(g.income.toFixed(2))
      }))
      .sort((a, b) => b.date.localeCompare(a.date))
  }
}

// 分类相关操作
const categoryService = {
  getExpenseCategories() {
    return safeStorage.get(STORAGE_KEYS.CATEGORIES_EXPENSE, [])
  },

  getIncomeCategories() {
    return safeStorage.get(STORAGE_KEYS.CATEGORIES_INCOME, [])
  },

  getCategoriesByType(type) {
    return type === 'expense'
      ? this.getExpenseCategories()
      : this.getIncomeCategories()
  },

  addCategory(type, category) {
    const key = type === 'expense'
      ? STORAGE_KEYS.CATEGORIES_EXPENSE
      : STORAGE_KEYS.CATEGORIES_INCOME

    const categories = safeStorage.get(key, [])
    const newCategory = {
      ...category,
      id: `custom_${Date.now()}`,
      isCustom: true
    }
    categories.push(newCategory)
    safeStorage.set(key, categories)
    return newCategory
  },

  deleteCategory(type, id) {
    const key = type === 'expense'
      ? STORAGE_KEYS.CATEGORIES_EXPENSE
      : STORAGE_KEYS.CATEGORIES_INCOME

    const categories = safeStorage.get(key, [])
    const filtered = categories.filter(c => c.id !== id)
    safeStorage.set(key, filtered)
    return filtered.length !== categories.length
  },

  updateCategory(type, id, updates) {
    const key = type === 'expense'
      ? STORAGE_KEYS.CATEGORIES_EXPENSE
      : STORAGE_KEYS.CATEGORIES_INCOME

    const categories = safeStorage.get(key, [])
    const index = categories.findIndex(c => c.id === id)

    if (index !== -1) {
      categories[index] = { ...categories[index], ...updates }
      safeStorage.set(key, categories)
      return categories[index]
    }
    return null
  }
}

// 设置相关操作
const settingsService = {
  getSettings() {
    return safeStorage.get(STORAGE_KEYS.SETTINGS, {
      monthlyBudget: 0,
      currency: '¥',
      enableReminder: false,
      reminderTime: '20:00'
    })
  },

  updateSettings(updates) {
    const settings = this.getSettings()
    const newSettings = { ...settings, ...updates }
    safeStorage.set(STORAGE_KEYS.SETTINGS, newSettings)
    return newSettings
  }
}

// 数据导出/导入
const dataService = {
  exportData() {
    return {
      exportTime: new Date().toISOString(),
      appVersion: '1.0.0',
      data: {
        bills: billService.getAllBills(),
        categories_expense: categoryService.getExpenseCategories(),
        categories_income: categoryService.getIncomeCategories(),
        settings: settingsService.getSettings()
      }
    }
  },

  importData(data) {
    if (data.data) {
      if (data.data.bills) {
        safeStorage.set(STORAGE_KEYS.BILLS, data.data.bills)
      }
      if (data.data.categories_expense) {
        safeStorage.set(STORAGE_KEYS.CATEGORIES_EXPENSE, data.data.categories_expense)
      }
      if (data.data.categories_income) {
        safeStorage.set(STORAGE_KEYS.CATEGORIES_INCOME, data.data.categories_income)
      }
      if (data.data.settings) {
        safeStorage.set(STORAGE_KEYS.SETTINGS, data.data.settings)
      }
      return true
    }
    return false
  },

  clearAllData() {
    safeStorage.set(STORAGE_KEYS.BILLS, [])
    safeStorage.set(STORAGE_KEYS.CATEGORIES_EXPENSE, [])
    safeStorage.set(STORAGE_KEYS.CATEGORIES_INCOME, [])
    safeStorage.set(STORAGE_KEYS.SETTINGS, {})
  }
}

module.exports = {
  billService,
  categoryService,
  settingsService,
  dataService,
  safeStorage,
  STORAGE_KEYS
}
