// 应用初始化模块
const { safeStorage } = require('./storage.js')
const { runMigrations } = require('./migrations.js')

module.exports = {
  // 初始化应用
  initApp() {
    console.log('抱布记 启动')
    try {
      const result = runMigrations()
      if (result.migrated) {
        console.log(`Schema migrated: v${result.from} -> v${result.to}`)
      }
    } catch (error) {
      console.error('Init app error:', error)
    }
  }
}
