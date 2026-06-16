// 卡路里计算服务
// 基于多种运动类型的科学计算公式

// 运动类型的MET值（代谢当量）
// 参考来源：美国运动医学学会(ACSM)和CDC的数据
const MET_VALUES = {
  // 跑步相关
  running: {
    low: 6.0,    // 慢跑 (5-6 km/h)
    medium: 9.8, // 中速跑 (8-9 km/h)
    high: 15.0   // 快跑 (12+ km/h)
  },
  // 游泳相关
  swimming: {
    low: 4.0,    // 慢泳
    medium: 7.0, // 中速游泳
    high: 10.0   // 快速游泳
  },
  // 健身相关
  gym: {
    low: 3.5,    // 轻度力量训练
    medium: 5.0, // 中度力量训练
    high: 8.0    // 高强度力量训练
  },
  // 瑜伽相关
  yoga: {
    low: 2.5,    // 温和瑜伽
    medium: 3.0, // 普通瑜伽
    high: 4.0    // 热瑜伽
  },
  // 骑行相关
  cycling: {
    low: 4.0,    // 慢速骑行 (10-16 km/h)
    medium: 8.0, // 中速骑行 (16-24 km/h)
    high: 12.0   // 快速骑行 (24+ km/h)
  },
  // 篮球相关
  basketball: {
    low: 5.0,    // 休闲篮球
    medium: 7.0, // 普通篮球
    high: 9.0    // 高强度篮球
  },
  // 足球相关
  football: {
    low: 5.0,    // 休闲足球
    medium: 7.0, // 普通足球
    high: 9.0    // 高强度足球
  },
  // 羽毛球相关
  badminton: {
    low: 3.5,    // 休闲羽毛球
    medium: 5.0, // 普通羽毛球
    high: 7.0    // 高强度羽毛球
  },
  // 网球相关
  tennis: {
    low: 4.0,    // 休闲网球
    medium: 6.0, // 普通网球
    high: 8.0    // 高强度网球
  },
  // 俯卧撑相关
  pushup: {
    low: 3.8,    // 慢速俯卧撑
    medium: 5.0, // 中速俯卧撑
    high: 8.0    // 快速俯卧撑
  },
  // 哑铃相关
  dumbbell: {
    low: 3.5,    // 轻度哑铃训练
    medium: 5.0, // 中度哑铃训练
    high: 7.0    // 高强度哑铃训练
  },
  // 其他运动
  other: {
    low: 3.0,    // 低强度
    medium: 5.0, // 中等强度
    high: 7.0    // 高强度
  }
};

// 计算卡路里消耗的核心公式
// 公式：卡路里 = 体重(kg) × MET值 × 时间(小时)
const calculateCalories = (weight, met, durationMinutes) => {
  // 将时间转换为小时
  const durationHours = durationMinutes / 60;
  // 计算卡路里消耗
  const calories = weight * met * durationHours;
  // 四舍五入到整数
  return Math.round(calories);
};

// 根据运动类型和强度获取MET值
const getMETValue = (activityType, intensity) => {
  return MET_VALUES[activityType]?.[intensity] || MET_VALUES.other.medium;
};

// 特定运动的额外计算逻辑
const calculateSpecificActivity = (activityType, formData, weight) => {
  switch (activityType) {
    case 'running':
      // 跑步可以根据速度调整MET值
      if (formData.distance && formData.minutes) {
        // 计算速度 (km/h)
        const speed = (formData.distance / formData.minutes) * 60;
        let met;
        if (speed < 6) {
          met = MET_VALUES.running.low;
        } else if (speed < 9) {
          met = MET_VALUES.running.medium;
        } else {
          met = MET_VALUES.running.high;
        }
        return calculateCalories(weight, met, formData.minutes);
      }
      break;
    
    case 'cycling':
      // 骑行可以根据速度调整MET值
      if (formData.distance && formData.minutes) {
        const speed = (formData.distance / formData.minutes) * 60;
        let met;
        if (speed < 16) {
          met = MET_VALUES.cycling.low;
        } else if (speed < 24) {
          met = MET_VALUES.cycling.medium;
        } else {
          met = MET_VALUES.cycling.high;
        }
        return calculateCalories(weight, met, formData.minutes);
      }
      break;
    
    case 'pushup':
      // 俯卧撑可以根据完成个数和时间调整强度
      if (formData.pushupCount && formData.pushupTime) {
        // 计算每分钟完成的俯卧撑个数
        const rate = formData.pushupCount / (formData.pushupTime / 60);
        let intensity = formData.intensity;
        if (rate > 30) {
          intensity = 'high';
        } else if (rate < 15) {
          intensity = 'low';
        }
        const met = getMETValue('pushup', intensity);
        return calculateCalories(weight, met, formData.minutes);
      }
      break;
  }
  
  // 默认计算方式
  const met = getMETValue(activityType, formData.intensity);
  return calculateCalories(weight, met, formData.minutes);
};

// 主计算函数
const calculateActivityCalories = (formData, weight) => {
  if (!weight || weight <= 0) {
    return 0;
  }
  
  if (!formData.minutes || formData.minutes <= 0) {
    return 0;
  }
  
  return calculateSpecificActivity(formData.type, formData, weight);
};

// 获取运动类型的MET值范围
const getMETRange = (activityType) => {
  const metValues = MET_VALUES[activityType] || MET_VALUES.other;
  return {
    min: Math.min(metValues.low, metValues.medium, metValues.high),
    max: Math.max(metValues.low, metValues.medium, metValues.high)
  };
};

// 计算误差范围
const getCalorieErrorRange = (calories) => {
  // 一般来说，卡路里计算的误差范围在10-20%之间
  const errorPercent = 0.15; // 15%
  const error = Math.round(calories * errorPercent);
  return {
    min: calories - error,
    max: calories + error,
    percent: errorPercent * 100
  };
};

module.exports = {
  calculateActivityCalories,
  getMETValue,
  getMETRange,
  getCalorieErrorRange,
  MET_VALUES
};