// 抱布记 API 客户端
const BASE_URL = 'http://81.70.209.199:8089'

// Token 管理
const TOKEN_KEY = 'baobaoji_token'
const USER_KEY = 'baobaoji_user'

function getToken() {
  try { return wx.getStorageSync(TOKEN_KEY) } catch (e) { return '' }
}

function setToken(token) {
  wx.setStorageSync(TOKEN_KEY, token)
}

function getUser() {
  try { return wx.getStorageSync(USER_KEY) || {} } catch (e) { return {} }
}

function setUser(user) {
  wx.setStorageSync(USER_KEY, user)
}

function clearAuth() {
  try {
    wx.removeStorageSync(TOKEN_KEY)
    wx.removeStorageSync(USER_KEY)
  } catch (e) {}
}

// 通用请求
function request(method, path, data) {
  return new Promise((resolve, reject) => {
    const token = getToken()
    const header = { 'Content-Type': 'application/json' }
    if (token) header['Authorization'] = `Bearer ${token}`

    wx.request({
      url: BASE_URL + path,
      method,
      header,
      data,
      success(res) {
        if (res.statusCode === 401) {
          // Token 过期，跳转登录
          clearAuth()
          wx.reLaunch({ url: '/pages/login/login' })
          reject(new Error('登录已过期'))
          return
        }
        if (res.statusCode >= 400) {
          reject(new Error(res.data?.detail || '请求失败'))
          return
        }
        resolve(res.data)
      },
      fail(err) {
        reject(new Error('网络错误: ' + err.errMsg))
      }
    })
  })
}

module.exports = {
  // 认证
  login: (username, password) =>
    request('POST', '/api/auth/login', { username, password }),
  register: (username, password) =>
    request('POST', '/api/auth/register', { username, password }),

  // 账单
  getBills: (params) => request('GET', '/api/bills?' + obj2query(params)),
  createBill: (data) => request('POST', '/api/bills', data),
  updateBill: (id, data) => request('PUT', '/api/bills/' + id, data),
  deleteBill: (id) => request('DELETE', '/api/bills/' + id),

  // 分类
  getCategories: (type) => request('GET', '/api/categories' + (type ? '?type=' + type : '')),
  createCategory: (data) => request('POST', '/api/categories', data),
  deleteCategory: (id) => request('DELETE', '/api/categories/' + id),

  // 健身
  getFitnessRecords: (params) => request('GET', '/api/fitness/records?' + obj2query(params)),
  createFitnessRecord: (data) => request('POST', '/api/fitness/records', data),
  deleteFitnessRecord: (id) => request('DELETE', '/api/fitness/records/' + id),

  // 统计
  getMonthlyStats: (year, month) => request('GET', `/api/stats/monthly?year=${year}&month=${month}`),
  getTodayStats: () => request('GET', '/api/stats/today'),

  // 设置
  getSettings: () => request('GET', '/api/settings'),
  updateSettings: (data) => request('PUT', '/api/settings', data),

  // 数据导入导出
  exportData: () => request('GET', '/api/data/export'),
  importData: (data) => request('POST', '/api/data/import', data),

  // Token 管理
  getToken,
  setToken,
  getUser,
  setUser,
  clearAuth,
}

function obj2query(obj) {
  if (!obj) return ''
  return Object.entries(obj)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => k + '=' + encodeURIComponent(v))
    .join('&')
}
