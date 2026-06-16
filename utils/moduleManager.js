// 模块管理服务 - 用于管理功能模块的注册和配置

class ModuleManager {
  constructor() {
    this.modules = []
    this.currentModule = null
  }

  // 注册模块
  registerModule(module) {
    const existingModule = this.modules.find(m => m.id === module.id)
    if (existingModule) {
      console.warn(`模块 ${module.id} 已存在`)
      return false
    }

    // 验证模块结构
    if (!module.id || !module.name || !Array.isArray(module.pages)) {
      console.error('模块结构不完整，需要包含 id、name 和 pages')
      return false
    }

    // 添加默认值
    const newModule = {
      id: module.id,
      name: module.name,
      icon: module.icon || '📦',
      color: module.color || '#4ECDC4',
      pages: module.pages,
      config: module.config || {},
      version: module.version || '1.0.0',
      capabilities: module.capabilities || [],
      init: module.init || function() {}
    }

    this.modules.push(newModule)
    return true
  }

  // 注销模块
  unregisterModule(moduleId) {
    const index = this.modules.findIndex(m => m.id === moduleId)
    if (index !== -1) {
      this.modules.splice(index, 1)
      if (this.currentModule === moduleId) {
        this.currentModule = this.modules.length > 0 ? this.modules[0].id : null
      }
      return true
    }
    return false
  }

  // 获取所有模块
  getAllModules() {
    return this.modules
  }

  // 获取模块
  getModule(moduleId) {
    return this.modules.find(m => m.id === moduleId)
  }

  // 设置当前模块
  setCurrentModule(moduleId) {
    const module = this.getModule(moduleId)
    if (module) {
      this.currentModule = moduleId
      // 执行模块初始化
      module.init()
      return true
    }
    return false
  }

  // 获取当前模块
  getCurrentModule() {
    return this.getModule(this.currentModule)
  }

  // 更新模块配置
  updateModuleConfig(moduleId, config) {
    const module = this.getModule(moduleId)
    if (module) {
      module.config = { ...module.config, ...config }
      return true
    }
    return false
  }

  // 检查模块是否存在
  hasModule(moduleId) {
    return this.modules.some(m => m.id === moduleId)
  }

  // 获取模块页面
  getModulePages(moduleId) {
    const module = this.getModule(moduleId)
    return module ? module.pages : []
  }

  // 添加模块页面
  addModulePage(moduleId, page) {
    const module = this.getModule(moduleId)
    if (module) {
      const existingPage = module.pages.find(p => p.id === page.id)
      if (!existingPage) {
        module.pages.push(page)
        return true
      }
      console.warn(`页面 ${page.id} 已存在`)
    }
    return false
  }

  // 移除模块页面
  removeModulePage(moduleId, pageId) {
    const module = this.getModule(moduleId)
    if (module) {
      const index = module.pages.findIndex(p => p.id === pageId)
      if (index !== -1) {
        module.pages.splice(index, 1)
        return true
      }
    }
    return false
  }
}

// 导出单例
const moduleManager = new ModuleManager()

function registerBuiltInModules() {
  const manifests = [
    require('../modules/accounting/manifest.js'),
    require('../modules/fitness/manifest.js')
  ]
  manifests.forEach((manifest) => moduleManager.registerModule(manifest))
}

registerBuiltInModules()

module.exports = moduleManager
