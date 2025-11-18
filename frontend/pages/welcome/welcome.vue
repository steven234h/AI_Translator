<template>
  <view class="welcome-page" @touchstart="onTouchStart" @touchmove="onTouchMove">
    <!-- 渐变网格背景 -->
    <view class="mesh-gradient" :style="{ transform: meshTransform }"></view>
    
    <!-- 浮动装饰元素 -->
    <view class="floating-shapes">
      <view class="shape shape-1"></view>
      <view class="shape shape-2"></view>
      <view class="shape shape-3"></view>
    </view>

    <!-- 跟随鼠标/触摸的光标效果 -->
    <view class="cursor-glow" :style="{ left: cursorX + 'px', top: cursorY + 'px' }"></view>

    <!-- 粒子效果 -->
    <view class="particles">
      <view 
        v-for="(particle, index) in particles" 
        :key="index"
        class="particle"
        :style="{ 
          left: particle.x + 'px', 
          top: particle.y + 'px',
          animationDelay: particle.delay + 's',
          animationDuration: particle.duration + 's'
        }"
      ></view>
    </view>

    <view class="content">
      <view class="brand-section" @click="onLogoClick">
        <view class="logo-wrapper" :class="{ bounce: logoBounce }">
          <text class="logo-icon">✦</text>
        </view>
        <text class="brand-title">AI翻译官</text>
        <text class="brand-subtitle">智能识别 · 即时翻译</text>
        <text class="easter-egg" v-if="showEasterEgg">{{ easterEggText }}</text>
      </view>

      <view class="action-section">
        <view 
          class="action-card primary"
          :class="{ pressed: activeTarget === 'index' }"
          @touchstart="onPress('index')"
          @touchend="onRelease"
          @touchcancel="onRelease"
          @click="goIndex"
        >
          <view class="card-icon">📷</view>
          <text class="card-title">开始识别</text>
          <text class="card-desc">拍照即可翻译</text>
        </view>

        <view 
          class="action-card secondary"
          :class="{ pressed: activeTarget === 'favorites' }"
          @touchstart="onPress('favorites')"
          @touchend="onRelease"
          @touchcancel="onRelease"
          @click="goFavorites"
        >
          <view class="card-icon">⭐</view>
          <text class="card-title">我的收藏</text>
          <text class="card-desc">查看历史记录</text>
        </view>

        <view 
          class="action-card tertiary"
          :class="{ pressed: activeTarget === 'contact' }"
          @touchstart="onPress('contact')"
          @touchend="onRelease"
          @touchcancel="onRelease"
          @click="contactUs"
        >
          <view class="card-icon">📧</view>
          <text class="card-title">联系我们</text>
          <text class="card-desc">反馈与建议</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  name: 'ModernWelcomePage',
  data() {
    return {
      activeTarget: '',
      cursorX: 0,
      cursorY: 0,
      meshTransform: '',
      particles: [],
      logoBounce: false,
      clickCount: 0,
      showEasterEgg: false,
      easterEggText: '',
      // 统一的屏幕尺寸，避免非 H5 环境下 window 未定义
      screenWidth: 375,
      screenHeight: 667
    }
  },
  mounted() {
    // 初始化屏幕尺寸（优先使用 uni API，H5 回退 window）
    try {
      if (typeof uni !== 'undefined' && uni.getSystemInfoSync) {
        const sys = uni.getSystemInfoSync()
        if (sys) {
          this.screenWidth = sys.windowWidth || sys.screenWidth || this.screenWidth
          this.screenHeight = sys.windowHeight || sys.screenHeight || this.screenHeight
        }
      }
    } catch (err) {}

    if (typeof window !== 'undefined') {
      this.screenWidth = window.innerWidth || this.screenWidth
      this.screenHeight = window.innerHeight || this.screenHeight
    }

    this.initParticles()
    // 监听鼠标移动（PC端）
    if (typeof window !== 'undefined') {
      window.addEventListener('mousemove', this.onMouseMove)
      window.addEventListener('resize', this.onResize)
    }
  },
  beforeDestroy() {
    if (typeof window !== 'undefined') {
      window.removeEventListener('mousemove', this.onMouseMove)
      window.removeEventListener('resize', this.onResize)
    }
  },
  methods: {
    onResize() {
      if (typeof window !== 'undefined') {
        this.screenWidth = window.innerWidth || this.screenWidth
        this.screenHeight = window.innerHeight || this.screenHeight
      }
    },
    onPress(target) {
      this.activeTarget = target
    },
    onRelease() {
      this.activeTarget = ''
    },
    goIndex() {
      uni.switchTab({ url: '/pages/index/index' })
    },
    goFavorites() {
      uni.switchTab({ url: '/pages/favorites/favorites' })
    },
    contactUs() {
      // 直接打开邮件客户端
      plus.runtime.openURL('mailto:stevensbw000@gmail.com', function(res) {
        // 打开成功
      }, function(e) {
        // 打开失败，提示用户
        uni.showModal({
          title: '提示',
          content: '无法打开邮件应用，请手动发送邮件至：stevensbw000@gmail.com',
          showCancel: true,
          confirmText: '复制邮箱',
          success: (res) => {
            if (res.confirm) {
              uni.setClipboardData({
                data: 'stevensbw000@gmail.com',
                success: () => {
                  uni.showToast({
                    title: '邮箱已复制',
                    icon: 'success'
                  })
                }
              })
            }
          }
        })
      })
    },
    // 鼠标移动事件（PC端）
    onMouseMove(e) {
      this.cursorX = e.clientX
      this.cursorY = e.clientY
      
      // 背景跟随移动（使用统一屏幕尺寸，兼容非 H5 环境）
      const width = this.screenWidth || (typeof window !== 'undefined' ? window.innerWidth : 375)
      const height = this.screenHeight || (typeof window !== 'undefined' ? window.innerHeight : 667)
      const moveX = (e.clientX / width - 0.5) * 20
      const moveY = (e.clientY / height - 0.5) * 20
      this.meshTransform = `translate(${moveX}px, ${moveY}px)`
    },
    // 触摸移动时更新光标位置和背景
    onTouchMove(e) {
      if (e.touches && e.touches[0]) {
        this.cursorX = e.touches[0].clientX
        this.cursorY = e.touches[0].clientY
        
        // 背景跟随移动（使用统一屏幕尺寸，兼容非 H5 环境）
        const width = this.screenWidth || (typeof window !== 'undefined' ? window.innerWidth : 375)
        const height = this.screenHeight || (typeof window !== 'undefined' ? window.innerHeight : 667)
        const moveX = (e.touches[0].clientX / width - 0.5) * 20
        const moveY = (e.touches[0].clientY / height - 0.5) * 20
        this.meshTransform = `translate(${moveX}px, ${moveY}px)`
      }
    },
    // 触摸开始时也更新一次，确保单击（轻点）能移动高光
    onTouchStart(e) {
      if (e.touches && e.touches[0]) {
        this.cursorX = e.touches[0].clientX
        this.cursorY = e.touches[0].clientY

        const width = this.screenWidth || (typeof window !== 'undefined' ? window.innerWidth : 375)
        const height = this.screenHeight || (typeof window !== 'undefined' ? window.innerHeight : 667)
        const moveX = (e.touches[0].clientX / width - 0.5) * 20
        const moveY = (e.touches[0].clientY / height - 0.5) * 20
        this.meshTransform = `translate(${moveX}px, ${moveY}px)`
      }
    },
    // 初始化粒子
    initParticles() {
      const width = this.screenWidth || (typeof window !== 'undefined' ? window.innerWidth : 375)
      const height = this.screenHeight || (typeof window !== 'undefined' ? window.innerHeight : 667)
      
      for (let i = 0; i < 20; i++) {
        this.particles.push({
          x: Math.random() * width,
          y: height + Math.random() * 200,
          delay: Math.random() * 5,
          duration: 3 + Math.random() * 4
        })
      }
    },
    // 创建涟漪效果
    createRipple(e) {
      // 可以在这里添加点击涟漪效果
    },
    // Logo点击彩蛋
    onLogoClick() {
      this.logoBounce = true
      this.clickCount++
      
      setTimeout(() => {
        this.logoBounce = false
      }, 600)
      
      if (this.clickCount === 5) {
        this.showEasterEgg = true
        const messages = ['🎉 恭喜你发现了隐藏彩蛋！', '✨ 前面的区域以后再来探索吧', '🌟 关注作者谢谢喵']
        this.easterEggText = messages[Math.floor(Math.random() * messages.length)]
        
        setTimeout(() => {
          this.showEasterEgg = false
          this.clickCount = 0
        }, 3000)
      }
    }
  }
}
</script>

<style scoped>
.welcome-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* 渐变网格动画背景 */
.mesh-gradient {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: 
    radial-gradient(circle at 20% 50%, rgba(138, 43, 226, 0.3) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(30, 144, 255, 0.3) 0%, transparent 50%),
    radial-gradient(circle at 40% 20%, rgba(255, 105, 180, 0.25) 0%, transparent 50%),
    radial-gradient(circle at 60% 90%, rgba(0, 206, 209, 0.25) 0%, transparent 50%);
  animation: mesh-move 20s ease-in-out infinite;
  filter: blur(60rpx);
  transition: transform 0.3s ease-out;
}

@keyframes mesh-move {
  0%, 100% {
    transform: translate(0, 0) rotate(0deg);
  }
  33% {
    transform: translate(30rpx, -30rpx) rotate(5deg);
  }
  66% {
    transform: translate(-20rpx, 20rpx) rotate(-5deg);
  }
}

/* 浮动装饰形状 */
.floating-shapes {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.shape {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10rpx);
  animation: float-up 15s ease-in-out infinite;
}

.shape-1 {
  width: 200rpx;
  height: 200rpx;
  top: 15%;
  left: 10%;
  animation-delay: 0s;
  animation-duration: 20s;
}

.shape-2 {
  width: 150rpx;
  height: 150rpx;
  top: 85%;
  right: 15%;
  animation-delay: 5s;
  animation-duration: 18s;
}

.shape-3 {
  width: 120rpx;
  height: 120rpx;
  bottom: 60%;
  left: 70%;
  animation-delay: 10s;
  animation-duration: 22s;
}

@keyframes float-up {
  0%, 100% {
    transform: translateY(0) scale(1);
    opacity: 0.6;
  }
  50% {
    transform: translateY(-50rpx) scale(1.1);
    opacity: 0.3;
  }
}

/* 光标跟随效果 */
.cursor-glow {
  position: absolute;
  width: 300rpx;
  height: 300rpx;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.2) 0%, transparent 70%);
  pointer-events: none;
  transform: translate(-50%, -50%);
  transition: all 0.15s ease-out;
  z-index: 1;
  mix-blend-mode: overlay;
}

/* 粒子效果 */
.particles {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: hidden;
}

.particle {
  position: absolute;
  width: 6rpx;
  height: 6rpx;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 50%;
  animation: particle-float infinite ease-in-out;
  box-shadow: 0 0 10rpx rgba(255, 255, 255, 0.5);
}

@keyframes particle-float {
  0% {
    transform: translateY(0) translateX(0);
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    transform: translateY(-100vh) translateX(50rpx);
    opacity: 0;
  }
}

/* 内容区域 */
.content {
  position: relative;
  z-index: 10;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 60rpx;
}

/* 品牌区域 */
.brand-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 100rpx;
  animation: fade-in 0.8s ease-out;
}

@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(-30rpx);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.logo-wrapper {
  width: 140rpx;
  height: 140rpx;
  border-radius: 40rpx;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(20rpx);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 40rpx;
  box-shadow: 0 20rpx 60rpx rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  cursor: pointer;
}

.logo-wrapper:active {
  transform: scale(0.95);
}

.logo-wrapper.bounce {
  animation: logo-bounce 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

@keyframes logo-bounce {
  0%, 100% { transform: scale(1); }
  25% { transform: scale(1.2) rotate(10deg); }
  50% { transform: scale(0.9) rotate(-10deg); }
  75% { transform: scale(1.1) rotate(5deg); }
}

.logo-icon {
  font-size: 80rpx;
  color: #ffffff;
  animation: rotate-sparkle 4s linear infinite;
}

@keyframes rotate-sparkle {
  0%, 100% { transform: rotate(0deg) scale(1); }
  50% { transform: rotate(180deg) scale(1.1); }
}

.brand-title {
  font-size: 64rpx;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 16rpx;
  letter-spacing: 2rpx;
  text-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.2);
}

.brand-subtitle {
  font-size: 28rpx;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 4rpx;
}

.easter-egg {
  margin-top: 30rpx;
  font-size: 30rpx;
  color: #fff;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10rpx);
  padding: 20rpx 40rpx;
  border-radius: 50rpx;
  animation: easter-egg-appear 0.5s ease-out;
}

@keyframes easter-egg-appear {
  0% {
    opacity: 0;
    transform: scale(0.5) translateY(-20rpx);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* 操作卡片区域 */
.action-section {
  display: flex;
  flex-direction: column;
  gap: 32rpx;
  width: 100%;
  max-width: 600rpx;
}

.action-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20rpx);
  border-radius: 32rpx;
  padding: 48rpx 40rpx;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-shadow: 
    0 20rpx 60rpx rgba(0, 0, 0, 0.15),
    0 0 0 1rpx rgba(255, 255, 255, 0.5) inset;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.action-card.pressed {
  transform: scale(0.97);
  box-shadow: 
    0 10rpx 30rpx rgba(0, 0, 0, 0.2),
    0 0 0 1rpx rgba(255, 255, 255, 0.5) inset;
}

.card-icon {
  font-size: 56rpx;
  margin-right: 32rpx;
  filter: grayscale(0.2);
  transition: all 0.3s ease;
}

.action-card:active .card-icon {
  transform: scale(1.2) rotate(10deg);
}

.card-title {
  font-size: 36rpx;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 8rpx;
  flex: 1;
}

.card-desc {
  position: absolute;
  right: 40rpx;
  font-size: 24rpx;
  color: #7f8c8d;
  font-weight: 400;
}

.action-card.primary {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(240, 248, 255, 0.98) 100%);
}

.action-card.secondary {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 250, 240, 0.95) 100%);
}

.action-card.tertiary {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(245, 250, 255, 0.95) 100%);
}

@media (hover: hover) {
  .action-card:hover {
    transform: translateY(-4rpx);
    box-shadow: 
      0 30rpx 80rpx rgba(0, 0, 0, 0.2),
      0 0 0 1rpx rgba(255, 255, 255, 0.6) inset;
  }
}

@media (max-width: 480px) {
  .brand-title { font-size: 56rpx; }
  .brand-subtitle { font-size: 26rpx; }
  .action-card { padding: 40rpx 32rpx; }
  .card-title { font-size: 32rpx; }
  .card-desc { font-size: 22rpx; }
}
</style>