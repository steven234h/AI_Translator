const API_BASE_URL = 'http://localhost:8000'

// API请求工具
export const request = {
  async uploadImage(filePath) {
    return new Promise((resolve, reject) => {
      uni.uploadFile({
        url: `${API_BASE_URL}/api/detect`,
        filePath: filePath,
        name: 'file',
        success: (res) => {
          try {
            const data = JSON.parse(res.data)
            resolve(data)
          } catch (e) {
            reject(e)
          }
        },
        fail: (err) => {
          reject(err)
        }
      })
    })
  }
}

// 存储工具
export const storage = {
  // 获取收藏列表
  getFavorites() {
    try {
      const favorites = uni.getStorageSync('favorites')
      return favorites ? JSON.parse(favorites) : []
    } catch (e) {
      console.error('获取收藏列表失败:', e)
      return []
    }
  },

  // 添加收藏
  addFavorite(item) {
    try {
      const favorites = this.getFavorites()
      const exists = favorites.find(fav =>
        fav.name.zh === item.name.zh
      )

      if (!exists) {
        const newItem = {
          ...item,
          id: Date.now(),
          createTime: new Date().toISOString()
        }
        favorites.push(newItem)
        uni.setStorageSync('favorites', JSON.stringify(favorites))

        // 触发存储更新事件
        uni.$emit('favoritesUpdated')
        return true
      }
      return false
    } catch (e) {
      console.error('添加收藏失败:', e)
      return false
    }
  },

  // 删除收藏
  removeFavorite(id) {
    try {
      const favorites = this.getFavorites()
      const filtered = favorites.filter(item => item.id !== id)

      // 确保实际删除了数据
      if (filtered.length < favorites.length) {
        uni.setStorageSync('favorites', JSON.stringify(filtered))

        // 清除可能的缓存
        uni.removeStorageSync('favoritesCache')

        // 触发存储更新事件
        uni.$emit('favoritesUpdated')
        return true
      }
      return false
    } catch (e) {
      console.error('删除收藏失败:', e)
      return false
    }
  },

  // 清除收藏缓存
  clearFavoritesCache() {
    try {
      uni.removeStorageSync('favoritesCache')
    } catch (e) {
      console.error('清除缓存失败:', e)
    }
  }
  ,

  // 识别历史：[{ id, image, results, descriptions, createTime }]
  getRecognitionHistory() {
    try {
      const list = uni.getStorageSync('recognitionHistory')
      return list ? JSON.parse(list) : []
    } catch (e) {
      console.error('获取识别历史失败:', e)
      return []
    }
  },

  addRecognitionHistory(entry, max = 50) {
    try {
      const list = this.getRecognitionHistory()
      const id = entry && entry.id ? entry.id : Date.now()
      const newItem = {
        id,
        image: entry?.image || '',
        results: Array.isArray(entry?.results) ? entry.results : [],
        descriptions: entry?.descriptions || {},
        createTime: entry?.createTime || new Date().toISOString()
      }
      list.unshift(newItem)
      // 去重：相同图片路径且时间接近（1s内）视为同一次
      const filtered = []
      const seen = new Set()
      for (const it of list) {
        const key = `${it.image}|${(it.createTime || '').slice(0, 18)}`
        if (!seen.has(key)) { seen.add(key); filtered.push(it) }
      }
      const trimmed = filtered.slice(0, Math.max(1, max || 50))
      uni.setStorageSync('recognitionHistory', JSON.stringify(trimmed))
      uni.$emit('recognitionHistoryUpdated')
      return true
    } catch (e) {
      console.error('添加识别历史失败:', e)
      return false
    }
  },

  removeRecognitionHistory(id) {
    try {
      const list = this.getRecognitionHistory()
      const filtered = list.filter(it => it.id !== id)
      uni.setStorageSync('recognitionHistory', JSON.stringify(filtered))
      uni.$emit('recognitionHistoryUpdated')
      return true
    } catch (e) {
      console.error('删除识别历史失败:', e)
      return false
    }
  },

  clearRecognitionHistory() {
    try {
      uni.removeStorageSync('recognitionHistory')
      uni.$emit('recognitionHistoryUpdated')
    } catch (e) {
      console.error('清空识别历史失败:', e)
    }
  }
}
