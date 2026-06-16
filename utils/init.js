// 应用初始化模块
const config = require('./config.js')
const { safeStorage } = require('./storage.js')
const { runMigrations } = require('./migrations.js')

function mergeCategories(defaults, existing = []) {
  const existingById = new Map(existing.map((item) => [item.id, item]))
  const merged = defaults.map((item) => existingById.get(item.id) || item)
  const customs = existing.filter((item) => item.isCustom)
  return [...merged, ...customs]
}

module.exports = {
  // 初始化本地存储
  initStorage() {
    try {
      const bills = safeStorage.get(config.STORAGE_KEYS.BILLS)
      const categoriesExpense = safeStorage.get(config.STORAGE_KEYS.CATEGORIES_EXPENSE)
      const categoriesIncome = safeStorage.get(config.STORAGE_KEYS.CATEGORIES_INCOME)
      
      // 如果没有数据，初始化默认数据
      if (!bills || bills.length === 0) {
        safeStorage.set(config.STORAGE_KEYS.BILLS, [])
      }
      
      if (!categoriesExpense || categoriesExpense.length === 0) {
        safeStorage.set(config.STORAGE_KEYS.CATEGORIES_EXPENSE, config.defaultExpenseCategories)
      } else {
        safeStorage.set(
          config.STORAGE_KEYS.CATEGORIES_EXPENSE,
          mergeCategories(config.defaultExpenseCategories, categoriesExpense)
        )
      }
      
      if (!categoriesIncome || categoriesIncome.length === 0) {
        safeStorage.set(config.STORAGE_KEYS.CATEGORIES_INCOME, config.defaultIncomeCategories)
      } else {
        safeStorage.set(
          config.STORAGE_KEYS.CATEGORIES_INCOME,
          mergeCategories(config.defaultIncomeCategories, categoriesIncome)
        )
      }
    } catch (error) {
      console.error('Init storage error:', error)
    }
  },
  
  // 初始化应用
  initApp() {
    console.log(`${config.APP_CONFIG.name} 启动`)
    try {
      const result = runMigrations()
      if (result.migrated) {
        console.log(`Schema migrated: v${result.from} -> v${result.to}`)
      }
      this.initStorage()
    } catch (error) {
      console.error('Init app error:', error)
    }
  }
}
