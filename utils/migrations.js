const config = require('./config.js')
const { safeStorage } = require('./storage.js')

function getMeta() {
  return safeStorage.get(config.STORAGE_KEYS.APP_META, {
    schemaVersion: 1,
    migratedAt: 0
  })
}

function setMeta(schemaVersion) {
  safeStorage.set(config.STORAGE_KEYS.APP_META, {
    schemaVersion,
    migratedAt: Date.now()
  })
}

function normalizeFitnessActivities() {
  const activities = safeStorage.get(config.STORAGE_KEYS.FITNESS_ACTIVITIES, [])
  const normalized = activities.map((item) => {
    if (item.minutes === undefined && item.duration !== undefined) {
      return {
        ...item,
        minutes: item.duration
      }
    }
    return item
  })
  safeStorage.set(config.STORAGE_KEYS.FITNESS_ACTIVITIES, normalized)
}

function runMigrations() {
  const currentVersion = getMeta().schemaVersion || 1
  const targetVersion = config.SCHEMA_VERSION

  if (currentVersion >= targetVersion) {
    return { from: currentVersion, to: targetVersion, migrated: false }
  }

  for (let version = currentVersion + 1; version <= targetVersion; version++) {
    if (version === 2) {
      normalizeFitnessActivities()
    }
  }

  setMeta(targetVersion)
  return { from: currentVersion, to: targetVersion, migrated: true }
}

module.exports = {
  runMigrations
}
