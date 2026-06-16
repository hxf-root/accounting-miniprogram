module.exports = {
  id: 'fitness',
  name: '健身',
  icon: '💪',
  color: '#FF6B6B',
  version: '1.0.0',
  capabilities: ['record', 'analytics', 'history', 'goal'],
  pages: [
    { id: 'home', name: '首页', path: '/pages/fitness/index' },
    { id: 'record', name: '记录', path: '/pages/fitness/record' },
    { id: 'analytics', name: '分析', path: '/pages/fitness/analytics' },
    { id: 'history', name: '历史', path: '/pages/fitness/history' },
    { id: 'settings', name: '设置', path: '/pages/fitness/settings' }
  ]
}
