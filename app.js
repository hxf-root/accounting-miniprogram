// 抱布记：无账户可浏览示例，已绑定时尝试自动恢复私人会话。
const identity = require('./utils/wechatIdentity.js')

App({
  onLaunch() { this.restoreIdentity() },
  restoreIdentity() { return identity.restore() },
})
