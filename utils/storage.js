// 数据存储服务 - 基于 wx.setStorageSync
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
  // 获取所有账单
  getAllBills() {
    return safeStorage.get(STORAGE_KEYS.BILLS, [])
  },

  // 添加账单
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

  // 更新账单
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

  // 删除账单
  deleteBill(id) {
    const bills = this.getAllBills()
    const filtered = bills.filter(b => b.id !== id)
    safeStorage.set(STORAGE_KEYS.BILLS, filtered)
    return filtered.length !== bills.length
  },

  // 获取账单详情
  getBillById(id) {
    const bills = this.getAllBills()
    return bills.find(b => b.id === id)
  },

  // 获取本月账单统计
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

  // 按分类统计
  getCategoryStats(year, month, type = 'expense') {
    const bills = this.getAllBills()
    const targetMonth = `${year}-${String(month).padStart(2, '0')}`
    
    const monthBills = bills.filter(b => 
      b.date.startsWith(targetMonth) && b.type === type
    )

    const stats = {}
    monthBills.forEach(bill => {
      if (!stats[bill.categoryId]) {
        stats[bill.categoryId] = {
          categoryId: bill.categoryId,
          categoryName: bill.categoryName,
          categoryIcon: bill.categoryIcon,
          amount: 0,
          count: 0
        }
      }
      stats[bill.categoryId].amount += bill.amount
      stats[bill.categoryId].count += 1
    })

    return Object.values(stats)
      .map(s => ({ ...s, amount: parseFloat(s.amount.toFixed(2)) }))
      .sort((a, b) => b.amount - a.amount)
  },

  // 按支付方式统计
  getPaymentMethodStats(year, month) {
    const bills = this.getAllBills()
    const targetMonth = `${year}-${String(month).padStart(2, '0')}`
    
    const monthBills = bills.filter(b => 
      b.date.startsWith(targetMonth) && b.type === 'expense'
    )

    const stats = {}
    monthBills.forEach(bill => {
      if (!stats[bill.paymentMethod]) {
        stats[bill.paymentMethod] = {
          method: bill.paymentMethod,
          amount: 0,
          count: 0
        }
      }
      stats[bill.paymentMethod].amount += bill.amount
      stats[bill.paymentMethod].count += 1
    })

    return Object.values(stats)
      .map(s => ({ ...s, amount: parseFloat(s.amount.toFixed(2)) }))
      .sort((a, b) => b.amount - a.amount)
  },

  // 获取最近记录
  getRecentBills(limit = 5) {
    const bills = this.getAllBills()
    return bills.slice(0, limit)
  },

  // 筛选账单
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

  // 按日期分组
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
  // 获取支出分类
  getExpenseCategories() {
    return safeStorage.get(STORAGE_KEYS.CATEGORIES_EXPENSE, [])
  },

  // 获取收入分类
  getIncomeCategories() {
    return safeStorage.get(STORAGE_KEYS.CATEGORIES_INCOME, [])
  },

  // 根据类型获取分类
  getCategoriesByType(type) {
    return type === 'expense' 
      ? this.getExpenseCategories() 
      : this.getIncomeCategories()
  },

  // 添加分类
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

  // 删除分类
  deleteCategory(type, id) {
    const key = type === 'expense' 
      ? STORAGE_KEYS.CATEGORIES_EXPENSE 
      : STORAGE_KEYS.CATEGORIES_INCOME
    
    const categories = safeStorage.get(key, [])
    const filtered = categories.filter(c => c.id !== id)
    safeStorage.set(key, filtered)
    return filtered.length !== categories.length
  },

  // 更新分类
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
  // 获取设置
  getSettings() {
    return safeStorage.get(STORAGE_KEYS.SETTINGS, {
      monthlyBudget: 0,
      currency: '¥',
      enableReminder: false,
      reminderTime: '20:00'
    })
  },

  // 更新设置
  updateSettings(updates) {
    const settings = this.getSettings()
    const newSettings = { ...settings, ...updates }
    safeStorage.set(STORAGE_KEYS.SETTINGS, newSettings)
    return newSettings
  }
}

// 数据导出/导入
const dataService = {
  // 导出所有数据
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

  // 导入数据（会覆盖现有数据）
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

  // 清空所有数据
  clearAllData() {
    safeStorage.set(STORAGE_KEYS.BILLS, [])
    safeStorage.set(STORAGE_KEYS.CATEGORIES_EXPENSE, [])
    safeStorage.set(STORAGE_KEYS.CATEGORIES_INCOME, [])
    safeStorage.set(STORAGE_KEYS.SETTINGS, {})
    safeStorage.set(STORAGE_KEYS.FITNESS_ACTIVITIES, [])
    safeStorage.set(STORAGE_KEYS.FITNESS_GOALS, {})
  }
}

// 健身相关操作
const fitnessService = {
  // 获取所有健身活动
  getAllActivities() {
    return safeStorage.get(STORAGE_KEYS.FITNESS_ACTIVITIES, [])
  },

  // 添加健身活动
  addActivity(activity) {
    const activities = this.getAllActivities()
    const newActivity = {
      ...activity,
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      createdAt: Date.now(),
      date: activity.date || new Date().toISOString().split('T')[0]
    }
    activities.unshift(newActivity)
    safeStorage.set(STORAGE_KEYS.FITNESS_ACTIVITIES, activities)
    return newActivity
  },

  // 获取今日统计数据
  getTodayStats() {
    const activities = this.getAllActivities()
    const today = new Date().toISOString().split('T')[0]
    const todayActivities = activities.filter(a => a.date === today)
    
    const totalMinutes = todayActivities.reduce((sum, a) => sum + (a.minutes || 0), 0)
    const totalCalories = todayActivities.reduce((sum, a) => sum + (a.calories || 0), 0)
    
    return {
      totalMinutes,
      totalCalories,
      activityCount: todayActivities.length
    }
  },

  // 获取最近活动
  getRecentActivities(limit = 5) {
    const activities = this.getAllActivities()
    return activities.slice(0, limit)
  },

  // 获取每日目标
  getDailyGoal() {
    const goals = safeStorage.get(STORAGE_KEYS.FITNESS_GOALS, {})
    return goals.daily || null
  },

  // 设置每日目标
  setDailyGoal(goal) {
    const goals = safeStorage.get(STORAGE_KEYS.FITNESS_GOALS, {})
    goals.daily = goal
    safeStorage.set(STORAGE_KEYS.FITNESS_GOALS, goals)
    return goal
  },

  // 获取历史记录（按日期分组）
  getHistoryByDate() {
    const activities = this.getAllActivities()
    const groups = {}
    
    activities.forEach(activity => {
      if (!groups[activity.date]) {
        groups[activity.date] = {
          date: activity.date,
          activities: [],
          totalMinutes: 0,
          totalCalories: 0
        }
      }
      groups[activity.date].activities.push(activity)
      groups[activity.date].totalMinutes += activity.minutes || 0
      groups[activity.date].totalCalories += activity.calories || 0
    })
    
    return Object.values(groups)
      .sort((a, b) => b.date.localeCompare(a.date))
  },

  // 获取指定时间范围的活动
  getActivitiesByDateRange(startDate, endDate) {
    const activities = this.getAllActivities()
    return activities.filter(a => a.date >= startDate && a.date <= endDate)
  },

  // 按运动类型统计
  getActivityTypeStats(startDate, endDate) {
    const activities = this.getActivitiesByDateRange(startDate, endDate)
    const stats = {}
    
    activities.forEach(activity => {
      if (!stats[activity.type]) {
        stats[activity.type] = {
          type: activity.type,
          name: activity.name,
          icon: activity.icon,
          totalMinutes: 0,
          totalCalories: 0,
          count: 0
        }
      }
      stats[activity.type].totalMinutes += activity.minutes || activity.duration || 0
      stats[activity.type].totalCalories += activity.calories || 0
      stats[activity.type].count += 1
    })
    
    return Object.values(stats)
      .sort((a, b) => b.totalMinutes - a.totalMinutes)
  },

  // 根据ID获取活动
  getActivityById(id) {
    const activities = this.getAllActivities()
    return activities.find(a => a.id === id)
  },

  // 更新活动
  updateActivity(id, updates) {
    const activities = this.getAllActivities()
    const index = activities.findIndex(a => a.id === id)
    if (index !== -1) {
      activities[index] = {
        ...activities[index],
        ...updates,
        updatedAt: Date.now()
      }
      safeStorage.set(STORAGE_KEYS.FITNESS_ACTIVITIES, activities)
      return activities[index]
    }
    return null
  },

  // 根据时间范围获取统计数据
  getStatsByRange(range) {
    const now = new Date()
    let startDate
    
    switch (range) {
      case 'week':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        break
      case 'month':
        startDate = new Date(now.getFullYear(), now.getMonth(), 1)
        break
      case 'year':
        startDate = new Date(now.getFullYear(), 0, 1)
        break
      default:
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
    }
    
    const startDateStr = startDate.toISOString().split('T')[0]
    const endDateStr = now.toISOString().split('T')[0]
    
    const activities = this.getActivitiesByDateRange(startDateStr, endDateStr)
    
    const totalMinutes = activities.reduce((sum, a) => sum + (a.minutes || 0), 0)
    const totalCalories = activities.reduce((sum, a) => sum + (a.calories || 0), 0)
    const totalActivities = activities.length
    const averageMinutes = totalActivities > 0 ? totalMinutes / totalActivities : 0
    
    return {
      totalMinutes,
      totalCalories,
      totalActivities,
      averageMinutes: parseFloat(averageMinutes.toFixed(1))
    }
  },

  // 获取活动分布
  getActivityDistribution(range) {
    const now = new Date()
    let startDate
    
    switch (range) {
      case 'week':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        break
      case 'month':
        startDate = new Date(now.getFullYear(), now.getMonth(), 1)
        break
      case 'year':
        startDate = new Date(now.getFullYear(), 0, 1)
        break
      default:
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
    }
    
    const startDateStr = startDate.toISOString().split('T')[0]
    const endDateStr = now.toISOString().split('T')[0]
    
    return this.getActivityTypeStats(startDateStr, endDateStr)
  },

  // 获取趋势数据
  getTrendData(range) {
    const now = new Date()
    let startDate
    let format
    
    switch (range) {
      case 'week':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        format = 'day'
        break
      case 'month':
        startDate = new Date(now.getFullYear(), now.getMonth(), 1)
        format = 'day'
        break
      case 'year':
        startDate = new Date(now.getFullYear(), 0, 1)
        format = 'month'
        break
      default:
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        format = 'day'
    }
    
    const startDateStr = startDate.toISOString().split('T')[0]
    const endDateStr = now.toISOString().split('T')[0]
    
    const activities = this.getActivitiesByDateRange(startDateStr, endDateStr)
    const groups = {}
    
    activities.forEach(activity => {
      let key
      if (format === 'day') {
        key = activity.date
      } else {
        key = activity.date.substring(0, 7) // YYYY-MM
      }
      
      if (!groups[key]) {
        groups[key] = {
          date: key,
          minutes: 0,
          calories: 0
        }
      }
      groups[key].minutes += activity.minutes || 0
      groups[key].calories += activity.calories || 0
    })
    
    return Object.values(groups)
      .sort((a, b) => a.date.localeCompare(b.date))
  }
}

module.exports = {
  billService,
  categoryService,
  settingsService,
  dataService,
  fitnessService,
  safeStorage,
  STORAGE_KEYS
}
