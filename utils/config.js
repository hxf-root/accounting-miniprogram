// 应用配置模块

module.exports = {
  // 默认支出分类
  defaultExpenseCategories: [
    { id: 'food', name: '餐饮', icon: '🍔', color: '#FF6B6B', isCustom: false },
    { id: 'transport', name: '交通', icon: '🚗', color: '#4ECDC4', isCustom: false },
    { id: 'shopping', name: '购物', icon: '🛍️', color: '#45B7D1', isCustom: false },
    { id: 'entertainment', name: '娱乐', icon: '🎬', color: '#96CEB4', isCustom: false },
    { id: 'housing', name: '居住', icon: '🏠', color: '#FFEAA7', isCustom: false },
    { id: 'medical', name: '医疗', icon: '🏥', color: '#DDA0DD', isCustom: false },
    { id: 'education', name: '教育', icon: '📚', color: '#98D8C8', isCustom: false },
    { id: 'other', name: '其他', icon: '📦', color: '#B2BEC3', isCustom: false }
  ],
  
  // 默认收入分类
  defaultIncomeCategories: [
    { id: 'salary', name: '工资', icon: '💰', color: '#00B894', isCustom: false },
    { id: 'bonus', name: '奖金', icon: '🎁', color: '#00CEC9', isCustom: false },
    { id: 'investment', name: '理财', icon: '📈', color: '#0984E3', isCustom: false },
    { id: 'parttime', name: '兼职', icon: '⏰', color: '#6C5CE7', isCustom: false },
    { id: 'gift', name: '礼金', icon: '✉️', color: '#FD79A8', isCustom: false },
    { id: 'other_income', name: '其他', icon: '📦', color: '#B2BEC3', isCustom: false }
  ],
  
  // 存储键名
  STORAGE_KEYS: {
    BILLS: 'bills',
    CATEGORIES_EXPENSE: 'categories_expense',
    CATEGORIES_INCOME: 'categories_income',
    SETTINGS: 'settings',
    FITNESS_ACTIVITIES: 'fitness_activities',
    FITNESS_GOALS: 'fitness_goals',
    APP_META: 'app_meta'
  },
  
  // 应用配置
  APP_CONFIG: {
    version: '1.0.0',
    name: '抱布记',
    description: '一款简洁、清爽的个人管理工具'
  },

  // 数据结构版本
  SCHEMA_VERSION: 2
}
