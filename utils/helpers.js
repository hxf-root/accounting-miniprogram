// 通用工具函数

/**
 * 格式化日期为 YYYY-MM-DD
 */
function formatDate(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/**
 * 格式化金额（保留两位小数）
 */
function formatAmount(num) {
  if (num === undefined || num === null) return '0.00'
  return Number(num).toFixed(2)
}

/**
 * 支付方式中文映射
 */
const PAYMENT_NAMES = {
  wechat: '微信',
  alipay: '支付宝',
  cash: '现金',
  bankcard: '银行卡',
  credit: '信用卡',
  other: '其他',
}

function getPaymentName(method) {
  return PAYMENT_NAMES[method] || method || ''
}

/**
 * 按日期分组账单
 */
function groupByDate(bills) {
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
    }))
    .sort((a, b) => b.date.localeCompare(a.date))
}

/**
 * 计算预算百分比
 */
function calcBudgetPercent(budget, expense) {
  if (!budget || budget <= 0 || !expense || expense <= 0) return 0
  return Math.min(100, Math.round((expense / budget) * 100))
}

/**
 * 计算统计（账单列表 → 统计对象）
 */
function calcStats(bills) {
  let totalExpense = 0
  let totalIncome = 0
  for (const bill of bills) {
    const amount = Number(bill.amount) || 0
    if (bill.type === 'expense') totalExpense += amount
    else if (bill.type === 'income') totalIncome += amount
  }
  return {
    totalCount: bills.length,
    totalExpense: totalExpense.toFixed(2),
    totalIncome: totalIncome.toFixed(2),
    totalExpenseNum: totalExpense,
    totalIncomeNum: totalIncome,
  }
}

module.exports = {
  formatDate,
  formatAmount,
  getPaymentName,
  groupByDate,
  calcBudgetPercent,
  calcStats,
}
