<template>
  <view class="container" @touchstart="onSwipeStart" @touchend="onSwipeEnd">
    <ParticleBackground :fullScreen="true" :particleCount="Math.round(80 * 2 / 3)" :speedScale="0.6" :autoPause="true" :mouseRadius="140" :connectDistance="110" />
    <!-- 头部标题 -->
    <view class="header">
      <text class="title">我的收藏</text>
      <text class="subtitle">{{ favorites.length }} 个词汇</text>
    </view>

    <!-- 搜索栏 -->
    <view class="search-bar">
      <input class="search-input" v-model="searchQuery" placeholder="搜索收藏（中文/英文/日文）" placeholder-class="search-placeholder" />
    </view>

    <!-- 收藏列表 -->
    <view v-if="!isLoading && favorites.length > 0" class="favorites-list">
      <view
        v-for="(item, index) in pagedFavorites"
        :key="item.id"
        class="favorite-item"
        @click="showWordDetail(item)"
      >
        <view class="item-content">
          <text class="zh-name">{{ item.name.zh }}</text>
          <text class="item-time">{{ formatTime(item.createTime) }}</text>
        </view>
      </view>
      <!-- 分页条（列表底部） -->
      <view v-if="totalPages > 1" class="pagination">
        <text
          class="page-arrow"
          :class="{ disabled: currentPage === 1 }"
          @click.stop="prevPage"
        >
          ＜
        </text>

        <block v-for="(p, idx) in displayPages" :key="idx">
          <text v-if="p === '…'" class="ellipsis">…</text>
          <text
            v-else
            class="page-item"
            :class="{ active: p === currentPage }"
            @click.stop="goToPage(p)"
          >{{ p }}</text>
        </block>

        <text
          class="page-arrow"
          :class="{ disabled: currentPage === totalPages }"
          @click.stop="nextPage"
        >
          ＞
        </text>

        <view class="jump-to">
          <text class="jump-label">跳至</text>
          <input
            class="jump-input"
            type="number"
            v-model="jumpPageInput"
            @confirm="handleJump"
            @blur="handleJump"
            placeholder=""
          />
          <text class="jump-label">页</text>
        </view>
      </view>
    </view>

    <!-- 加载状态 -->
    <view v-else-if="!isLoading && favorites.length > 0 && filteredFavorites.length === 0" class="empty-state">
      <text class="empty-text">无匹配结果</text>
      <text class="empty-subtitle">换个关键词试试~</text>
    </view>

    <view v-if="isLoading" class="loading-state">
      <text class="loading-text">加载中...</text>
    </view>

    <!-- 空状态 -->
    <view v-else-if="!isLoading && favorites.length === 0" class="empty-state">
      <image src="/static/empty-star.png" class="empty-icon" mode="aspectFit"></image>
      <text class="empty-text">还没有收藏任何词汇</text>
      <text class="empty-subtitle">去识别页面添加收藏吧</text>
      <button class="btn-goto" @click="gotoRecognition">开始识别</button>
    </view>

    <!-- 详情弹窗 -->
    <view v-if="showDetailModal" class="detail-modal-overlay" @click="closeWordDetail">
      <view class="detail-modal" @click.stop>
        <view class="modal-header">
          <text class="modal-title">{{ selectedItem && selectedItem.name ? selectedItem.name.zh : '' }}</text>
          <text class="close-btn" @click="closeWordDetail">×</text>
        </view>
        <view v-if="selectedItem" class="modal-content">
          <view class="detail-languages">
            <view class="detail-lang-item">
              <text class="detail-lang-label">中文：</text>
              <text class="detail-lang-text">{{ selectedItem.name.zh }}</text>
            </view>
            <view class="detail-lang-item">
              <text class="detail-lang-label">英文：</text>
              <text class="detail-lang-text">{{ selectedItem.name.en }}</text>
            </view>
            <view class="detail-lang-item">
              <text class="detail-lang-label">日文：</text>
              <text class="detail-lang-text">{{ selectedItem.name.jp }}</text>
            </view>
          </view>
          <view class="detail-time">
            收藏时间：{{ formatTime(selectedItem.createTime) }}
          </view>
        </view>
        <view class="modal-actions">
          <button class="btn-remove" @click="confirmDeleteFromModal">删除收藏</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { storage } from '@/utils/api.js'
import ParticleBackground from '@/components/ParticleBackground.vue'

  export default {
    components: { ParticleBackground },
    data() {
      return {
      favorites: [],
      searchQuery: '',
      selectedItem: null,
      showDetailModal: false,
      isLoading: true,
      // 分页
      pageSize: 7,
      currentPage: 1,
      jumpPageInput: '',
      // 页面左右滑动手势状态
      swipeStartX: 0,
      swipeStartY: 0,
      swipeStartTime: 0,
      swipeLocked: false
      }
    },

  onShow() {
    this.loadFavorites()
  },

  onLoad() {
    // 首次加载时立即同步获取数据，避免闪烁
    this.favorites = storage.getFavorites().sort((a, b) =>
      new Date(b.createTime) - new Date(a.createTime)
    )
    this.isLoading = false

    // 监听收藏更新事件
    uni.$on('favoritesUpdated', () => {
      this.loadFavorites()
    })
  },

  onUnload() {
    // 取消事件监听
    uni.$off('favoritesUpdated')
  },

  computed: {
    filteredFavorites() {
      const q = (this.searchQuery || '').trim()
      if (!q) return this.favorites
      const lower = q.toLowerCase()
      return this.favorites.filter(it => {
        const zh = it.name?.zh || ''
        const en = it.name?.en || ''
        const jp = it.name?.jp || ''
        return zh.includes(q) || en.toLowerCase().includes(lower) || jp.includes(q)
      })
    },
    // 总页数
    totalPages() {
      return Math.max(1, Math.ceil(this.filteredFavorites.length / this.pageSize))
    },
    // 当前页的数据
    pagedFavorites() {
      const start = (this.currentPage - 1) * this.pageSize
      return this.filteredFavorites.slice(start, start + this.pageSize)
    },
    // 要展示的页码数组，包含省略号
    displayPages() {
      const pages = []
      const total = this.totalPages
      const cur = this.currentPage

      // 总页数小于等于3，全部显示
      if (total <= 3) {
        for (let i = 1; i <= total; i++) pages.push(i)
        return pages
      }

      // 始终显示第一页
      if (cur !== 1) {
        pages.push(1)
      }

      // 显示当前页（如果不是第一页）
      if (cur > 1) {
        // 如果当前页和第一页之间有间隔，显示省略号
        if (cur > 2) {
          pages.push('…')
        }
        pages.push(cur)
      } else {
        // 当前页就是第一页
        pages.push(1)
      }

      // 显示下一页（如果存在）
      if (cur < total) {
        pages.push(cur + 1)
        // 如果下一页后面还有页面，显示省略号
        if (cur + 1 < total) {
          pages.push('…')
        }
      }

      return pages
    }
  },

  watch: {
    // 关键字变更时回到第 1 页
    searchQuery() {
      this.currentPage = 1
    },
    // 列表变化时校正当前页
    filteredFavorites() {
      if (this.currentPage > this.totalPages) {
        this.currentPage = this.totalPages
      }
    }
  },

  methods: {
    // 分页：切换、前后翻页、跳页
    goToPage(p) {
      if (typeof p !== 'number') return
      if (p < 1 || p > this.totalPages) return
      if (p === this.currentPage) return
      this.currentPage = p
      this.jumpPageInput = ''
      try { uni.pageScrollTo({ scrollTop: 0, duration: 200 }) } catch (e) {}
    },
    prevPage() {
      if (this.currentPage > 1) this.goToPage(this.currentPage - 1)
    },
    nextPage() {
      if (this.currentPage < this.totalPages) this.goToPage(this.currentPage + 1)
    },
    handleJump() {
      const v = String(this.jumpPageInput || '').trim()
      if (!v) return
      let p = parseInt(v, 10)
      if (isNaN(p)) return
      if (p < 1) p = 1
      if (p > this.totalPages) p = this.totalPages
      this.goToPage(p)
    },
    // 页面级左右滑动：向右切换回识别页
    onSwipeStart(e) {
      const t = (e && (e.touches && e.touches[0])) || (e && e.changedTouches && e.changedTouches[0]) || {}
      this.swipeStartX = t.clientX || t.pageX || t.x || 0
      this.swipeStartY = t.clientY || t.pageY || t.y || 0
      this.swipeStartTime = Date.now()
      this.swipeLocked = false
    },
    onSwipeEnd(e) {
      if (this.swipeLocked) return
      // 弹窗/加载中时禁用页面级滑动，避免冲突
      if (this.isLoading || this.showDetailModal) return
      const t = (e && (e.changedTouches && e.changedTouches[0])) || (e && e.touches && e.touches[0]) || {}
      const endX = t.clientX || t.pageX || t.x || 0
      const endY = t.clientY || t.pageY || t.y || 0
      const dx = endX - this.swipeStartX
      const dy = endY - this.swipeStartY
      const dt = Date.now() - this.swipeStartTime
      // 快速、横向为主的滑动才触发
      if (dt <= 500 && Math.abs(dx) >= 60 && Math.abs(dy) < 50) {
        if (dx > 0) { // 向右滑，从收藏页回识别页
          this.swipeLocked = true
          try {
            uni.switchTab({ url: '/pages/index/index' })
          } catch (err) {}
        }
      }
    },
    // 加载收藏列表（用于更新时刷新）
    loadFavorites() {
      // 直接更新数据，不清空避免闪烁
      const newFavorites = storage.getFavorites().sort((a, b) =>
        new Date(b.createTime) - new Date(a.createTime)
      )
      this.favorites = newFavorites
      this.isLoading = false
    },

    // 格式化时间
    formatTime(timeString) {
      const date = new Date(timeString)
      const now = new Date()
      const diff = now - date

      if (diff < 60000) { // 1分钟内
        return '刚刚'
      } else if (diff < 3600000) { // 1小时内
        return `${Math.floor(diff / 60000)}分钟前`
      } else if (diff < 86400000) { // 1天内
        return `${Math.floor(diff / 3600000)}小时前`
      } else if (diff < 2592000000) { // 30天内
        return `${Math.floor(diff / 86400000)}天前`
      } else {
        return date.toLocaleDateString()
      }
    },

    // 显示单词详情
    showWordDetail(item) {
      this.selectedItem = item
      this.showDetailModal = true
    },

    // 关闭单词详情
    closeWordDetail() {
      this.showDetailModal = false
      this.selectedItem = null
    },

    // 从弹窗中删除（保持原有逻辑）
    confirmDeleteFromModal() {
      if (!this.selectedItem) return

      uni.showModal({
        title: '确认删除',
        content: `确定要删除收藏的"${this.selectedItem.name.zh}"吗？`,
        success: (res) => {
          if (res.confirm) {
            const success = storage.removeFavorite(this.selectedItem.id)
            if (success) {
              // 立即关闭弹窗
              this.closeWordDetail()

              // 强制重新加载收藏列表
              this.loadFavorites()

              uni.showToast({
                title: '删除成功',
                icon: 'success'
              })
            } else {
              uni.showToast({
                title: '删除失败',
                icon: 'error'
              })
            }
          }
        }
      })
    },

    // 跳转到识别页面
    gotoRecognition() {
      uni.switchTab({
        url: '/pages/index/index'
      })
    }
  }
}
</script>

<style>
.container {
  padding: 20rpx;
  background: linear-gradient(135deg, var(--brand-start) 0%, var(--brand-end) 100%);
  /* 覆盖全屏高度，确保全屏手势可用 */
  box-sizing: border-box;
  height: 100%;
  min-height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
}

.header {
  text-align: center;
  margin-bottom: 40rpx;
  margin-top: 10px;
}

.title {
  font-size: 48rpx;
  font-weight: bold;
  color: #eef2ff;
  display: block;
  margin-bottom: 12rpx;
  letter-spacing: 1rpx;
  text-shadow: 0 4rpx 14rpx rgba(82, 102, 191, 0.28);
  margin-top: 75px;
}

.subtitle {
  font-size: 28rpx;
  color: #e0e7ff;
}

.favorites-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.favorite-item {
  background-color: #fff;
  border-radius: 20rpx;
  padding: 30rpx;
  box-shadow: 0 2rpx 10rpx rgba(0,0,0,0.1);
  transition: background-color 0.2s;
}

.favorite-item:active {
  background-color: #f8f8f8;
}

.item-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.zh-name {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  flex: 1;
}

.item-time {
  font-size: 22rpx;
  color: #999;
}

.detail-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.detail-modal {
  background-color: #fff;
  border-radius: 20rpx;
  padding: 40rpx;
  margin: 40rpx;
  max-height: 80vh;
  overflow-y: auto;
  width: 80%;
  max-width: 600rpx;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100rpx 40rpx;
  text-align: center;
}

.empty-icon {
  width: 120rpx;
  height: 120rpx;
  margin-bottom: 30rpx;
  opacity: 0.5;
}

.empty-text {
  font-size: 32rpx;
  color: #666;
  margin-bottom: 10rpx;
}

.empty-subtitle {
  font-size: 26rpx;
  color: #999;
  margin-bottom: 40rpx;
}

.btn-goto {
  background: linear-gradient(135deg, #a3bffa, #b794f4);
  color: white;
  padding: 20rpx 60rpx;
  border-radius: 50rpx;
  font-size: 28rpx;
  border: none;
  box-shadow: 0 4rpx 12rpx rgba(82, 102, 191, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30rpx;
  border-bottom: 1rpx solid #f0f0f0;
  padding-bottom: 20rpx;
}

.modal-title {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
}

.close-btn {
  font-size: 60rpx;
  color: #999;
  line-height: 1;
}

.modal-content {
  margin-bottom: 30rpx;
}

.detail-languages {
  margin-bottom: 30rpx;
}

.detail-lang-item {
  display: flex;
  margin-bottom: 20rpx;
  align-items: flex-start;
}

.detail-lang-label {
  font-size: 28rpx;
  color: #666;
  width: 120rpx;
  flex-shrink: 0;
}

.detail-lang-text {
  font-size: 28rpx;
  color: #333;
  flex: 1;
}


.detail-time {
  font-size: 24rpx;
  color: #999;
  text-align: center;
}

.modal-actions {
  text-align: center;
}

.btn-remove {
  background: linear-gradient(135deg, #a3bffa, #b794f4);
  color: white;
  padding: 20rpx 60rpx;
  border-radius: 50rpx;
  font-size: 28rpx;
  border: none;
  box-shadow: 0 4rpx 12rpx rgba(82, 102, 191, 0.3);
}

/* 使页面内容位于粒子背景之上 */
.header,
.favorites-list,
.loading-state,
.empty-state {
  position: relative;
  z-index: 1;
}

/* 搜索栏 */
.search-bar {
  margin: 20rpx 0 30rpx;
  padding: 16rpx;
  border-radius: 16rpx;
  background: rgba(255, 255, 255, 0.18);
  border: 1rpx solid rgba(255, 255, 255, 0.28);
  -webkit-backdrop-filter: blur(8px) saturate(120%);
  backdrop-filter: blur(8px) saturate(120%);
  box-shadow: 0 8rpx 24rpx rgba(82, 102, 191, 0.18);
  width: 80%;
  max-width: 700rpx;
  margin-left: auto;
  margin-right: auto;
  box-sizing: border-box;
  overflow: hidden; /* 防止内部白色输入框溢出圆角容器 */
}
.search-input {
  width: 100%;
  height: 72rpx;
  line-height: 72rpx;
  padding: 0 24rpx;
  border-radius: 999rpx;
  background: #fff;
  border: 2rpx solid #a5b4fc;
  font-size: 28rpx;
  color: #333;
  box-sizing: border-box; /* 计算边框进宽度，避免溢出 */
}
.search-placeholder {
  color: #98a2ff;
  font-size: 26rpx;
}

/* 收藏项交互增强 */
@media (hover:hover) {
  .favorite-item:hover {
    box-shadow: 0 6rpx 16rpx rgba(0,0,0,0.12);
    transform: translateY(-2rpx);
  }
}
.favorite-item:active {
  transform: translateY(1rpx);
}

/* 弹层毛玻璃与入场动画 */
.detail-modal-overlay {
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
}
.detail-modal {
  animation: popIn .18s ease-out;
  transform-origin: center;
}
@keyframes popIn {
  0% { transform: translateY(20rpx) scale(.98); opacity: .5; }
  100% { transform: translateY(0) scale(1); opacity: 1; }
}

/* 分页条样式 */
.pagination {
  margin: 24rpx auto 40rpx;
  padding: 16rpx 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  color: #333;
  width: 92%;
  max-width: 900rpx;
  position: relative;
  z-index: 1;
}
.page-arrow,
.page-item {
  min-width: 30rpx;
  height: 56rpx;
  line-height: 56rpx;
  text-align: center;
  padding: 0 18rpx;
  border-radius: 14rpx;
  border: 2rpx solid transparent;
  background: #fff;
  box-shadow: 0 2rpx 10rpx rgba(0,0,0,0.06);
  color: #333;
}
.page-item.active {
  color: #4f46e5;
  border-color: #6366f1;
  box-shadow: 0 0 0 4rpx rgba(99, 102, 241, 0.15);
}
.page-arrow.disabled {
  opacity: 0.35;
}
.ellipsis {
  padding: 0 10rpx;
  color: #999;
}
.jump-to {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-left: 16rpx;
}
.jump-label {
  color: #666;
  font-size: 26rpx;
}
.jump-input {
  width: 75rpx;
  height: 56rpx;
  line-height: 56rpx;
  background: #fff;
  border: 2rpx solid #e5e7eb;
  border-radius: 12rpx;
  text-align: center;
  font-size: 28rpx;
  color: #333;
}
</style>
