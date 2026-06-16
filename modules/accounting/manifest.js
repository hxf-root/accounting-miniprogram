module.exports = {
  id: 'accounting',
  name: '记账',
  icon: '💰',
  color: '#4ECDC4',
  version: '1.0.0',
  capabilities: ['record', 'history', 'category', 'import'],
  pages: [
    { id: 'home', name: '首页', path: '/pages/index/index' },
    { id: 'record', name: '记录', path: '/pages/record/record' },
    { id: 'history', name: '明细', path: '/pages/history/history' },
    { id: 'category', name: '分类', path: '/pages/category/category' },
    { id: 'import', name: '导入', path: '/pages/import-bill/import-bill' }
  ]
}
