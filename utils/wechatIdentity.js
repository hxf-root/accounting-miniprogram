// 微信身份客户端适配器。只保存自动识别偏好和短期服务端令牌，不保存 code 或密钥。
const api = require('./api.js')
const AUTO_KEY = 'baobaoji_wechat_auto'
let generation = 0
let pending = null

function enabled() {
  try { return wx.getStorageSync(AUTO_KEY) === true } catch (_) { return false }
}

function getCode() {
  return new Promise((resolve, reject) => {
    wx.login({
      success(result) { result && result.code ? resolve(result.code) : reject(new Error('微信凭证不可用')) },
      fail() { reject(new Error('微信凭证不可用')) },
    })
  })
}

async function bind(password) {
  if (typeof password !== 'string' || !password) throw new Error('请输入账户密码')
  const originalToken = api.getToken()
  if (!originalToken) throw new Error('请先连接已有账户')
  const version = generation
  const code = await getCode()
  if (version !== generation || api.getToken() !== originalToken) throw new Error('操作已取消')
  await api.bindWechat(code, password)
  if (version !== generation || api.getToken() !== originalToken) throw new Error('操作已取消')
  wx.setStorageSync(AUTO_KEY, true)
}

function stopAuto() {
  generation += 1
  pending = null
  try { wx.removeStorageSync(AUTO_KEY) } catch (_) {}
}

function restore() {
  if (!enabled()) return Promise.resolve(false)
  if (api.getToken()) return Promise.resolve(true)
  if (pending) return pending
  const version = generation
  const work = getCode().then(code => api.loginWechat(code)).then(result => {
    if (version !== generation || !enabled()) return false
    if (api.getToken()) return true // Never overwrite a manual login completed in the meantime.
    if (!result || typeof result.token !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(result.token)) return false
    api.setToken(result.token)
    return true
  }).catch(() => false)
  pending = work
  work.finally(() => { if (pending === work) pending = null })
  return work
}

async function unbind() {
  await api.unbindWechat()
  stopAuto()
  api.clearAuth()
}

module.exports = { enabled, bind, restore, unbind, stopAuto }
