<template>
  <view class="particle-container" :style="containerStyle">
    <!-- #ifndef H5 -->
    <canvas 
      :id="canvasId" 
      class="canvas-layer" 
      type="2d"
      :change:props="renderer.onPropsChange"
      :props="canvasProps"
    ></canvas>
    <!-- #endif -->
  </view>
</template>

<script>
export default {
  name: 'DynamicParticles',
  props: {
    fullScreen: { type: Boolean, default: true },
    particleCount: { type: Number, default: 50 },
    connectDist: { type: Number, default: 120 },
    touchRadius: { type: Number, default: 150 },
    speedScale: { type: Number, default: 1 },
    // 是否在需要时自动暂停（占位，便于外部传参，不强制使用）
    autoPause: { type: Boolean, default: false },
    // 背景配置：null(透明) | 'gradient' | 自定义颜色
    background: { type: String, default: null },
    // 渐变起始色
    gradientStart: { type: String, default: '#667eea' },
    // 渐变结束色
    gradientEnd: { type: String, default: '#764ba2' }
  },
  data() {
    return {
      canvasId: 'dp-' + Date.now() + Math.random().toString(36).slice(2),
      canvasProps: {
        ts: Date.now(),
        count: 50,
        dist: 120,
        radius: 150,
        speedScale: 1,
        fullScreen: true,
        background: null,
        gradientStart: '#667eea',
        gradientEnd: '#764ba2'
      }
    }
  },
  computed: {
    containerStyle() {
      if (this.fullScreen) {
        return {
          position: 'fixed',
          left: 0,
          top: 0,
          width: '100vw',
          height: '100vh',
          zIndex: 0,
          pointerEvents: 'none'
        }
      }
      return {
        position: 'absolute',
        left: 0,
        top: 0,
        right: 0,
        bottom: 0,
        zIndex: 0,
        pointerEvents: 'none'
      }
    }
  },
  watch: {
    particleCount() { this.updateProps() },
    connectDist() { this.updateProps() },
    touchRadius() { this.updateProps() },
    speedScale() { this.updateProps() },
    background() { this.updateProps() },
    gradientStart() { this.updateProps() },
    gradientEnd() { this.updateProps() }
  },
  mounted() {
    this.updateProps()
  },
  beforeDestroy() {
    // 通知 renderjs 进行清理，避免事件监听与动画句柄泄漏
    try {
      this.canvasProps = {
        ...this.canvasProps,
        dispose: true,
        ts: Date.now()
      }
    } catch (e) {}
  },
  methods: {
    updateProps() {
      this.canvasProps = {
        ts: Date.now(),
        count: this.particleCount,
        dist: this.connectDist,
        radius: this.touchRadius,
        speedScale: this.speedScale,
        fullScreen: this.fullScreen,
        id: this.canvasId,
        background: this.background,
        gradientStart: this.gradientStart,
        gradientEnd: this.gradientEnd
      }
    }
  }
}
</script>

<script module="renderer" lang="renderjs">
let canvas = null
let ctx = null
let particles = []
let ripples = []
let touch = { x: null, y: null }
let isRunning = false
let rafId = 0
let cfg = {}
let createdCanvas = false
let eventsBound = false
let handlers = {
  resize: null,
  move: null,
  tmove: null,
  leave: null,
  tend: null,
  down: null,
  tstart: null
}

export default {
  methods: {
    onPropsChange(val) {
      if (!val) return
      cfg = val
      // 处理销毁指令
      if (val.dispose) {
        this.dispose()
        return
      }
      
      if (!canvas) {
        this.setup()
      } else {
        this.initParticles()
      }
    },
    
    setup() {
      const el = document.getElementById(cfg.id)
      if (!el) {
        setTimeout(() => this.setup(), 100)
        return
      }
      
      if (typeof el.getContext !== 'function') {
        const parent = el.parentNode || document.body
        canvas = document.createElement('canvas')
        canvas.className = 'canvas-layer'
        canvas.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none'
        parent.appendChild(canvas)
        try { el.style.display = 'none' } catch (e) {}
        createdCanvas = true
      } else {
        canvas = el
      }
      
      const dpr = Math.min(2, window.devicePixelRatio || 1)
      const w = cfg.fullScreen ? window.innerWidth : canvas.offsetWidth
      const h = cfg.fullScreen ? window.innerHeight : canvas.offsetHeight
      
      canvas.width = w * dpr
      canvas.height = h * dpr
      canvas.style.width = w + 'px'
      canvas.style.height = h + 'px'
      
      ctx = canvas.getContext('2d')
      ctx.scale(dpr, dpr)
      
      this.bindEvents()
      this.initParticles()
      this.run()
    },
    
    initParticles() {
      const w = cfg.fullScreen ? window.innerWidth : canvas.offsetWidth
      const h = cfg.fullScreen ? window.innerHeight : canvas.offsetHeight
      const count = cfg.count || 50
      const speed = (typeof cfg.speedScale === 'number' && !isNaN(cfg.speedScale)) ? cfg.speedScale : 1
      
      particles = []
      ripples = []
      
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * 2 * speed,
          vy: (Math.random() - 0.5) * 2 * speed,
          r: Math.random() * 2 + 1
        })
      }
    },
    
    bindEvents() {
      if (eventsBound) return

      handlers.resize = () => this.setup()
      const handleMove = (e) => {
        const pt = this.getPoint(e)
        touch.x = pt.x
        touch.y = pt.y
      }
      const handleEnd = () => {
        touch.x = null
        touch.y = null
      }
      const handleTouch = (e) => {
        const pt = this.getPoint(e)
        if (pt.x !== null) {
          ripples.push({
            x: pt.x,
            y: pt.y,
            r: 0,
            max: (cfg.radius || 150) * 1.5,
            t: Date.now()
          })
        }
      }
      handlers.move = handleMove
      handlers.tmove = handleMove
      handlers.leave = handleEnd
      handlers.tend = handleEnd
      handlers.down = handleTouch
      handlers.tstart = handleTouch

      window.addEventListener('resize', handlers.resize, { passive: true })
      window.addEventListener('mousemove', handlers.move, { passive: true })
      window.addEventListener('touchmove', handlers.tmove, { passive: true })
      window.addEventListener('mouseleave', handlers.leave, { passive: true })
      window.addEventListener('touchend', handlers.tend, { passive: true })
      window.addEventListener('mousedown', handlers.down, { passive: true })
      window.addEventListener('touchstart', handlers.tstart, { passive: true })

      eventsBound = true
    },

    unbindEvents() {
      if (!eventsBound) return
      try {
        window.removeEventListener('resize', handlers.resize)
        window.removeEventListener('mousemove', handlers.move)
        window.removeEventListener('touchmove', handlers.tmove)
        window.removeEventListener('mouseleave', handlers.leave)
        window.removeEventListener('touchend', handlers.tend)
        window.removeEventListener('mousedown', handlers.down)
        window.removeEventListener('touchstart', handlers.tstart)
      } catch (e) {}
      handlers = { resize: null, move: null, tmove: null, leave: null, tend: null, down: null, tstart: null }
      eventsBound = false
    },
    
    getPoint(e) {
      if (e.touches && e.touches[0]) {
        return { x: e.touches[0].clientX, y: e.touches[0].clientY }
      }
      return { x: e.clientX, y: e.clientY }
    },
    
    run() {
      if (isRunning) return
      isRunning = true
      
      const loop = () => {
        if (!isRunning) return
        this.draw()
        rafId = requestAnimationFrame(loop)
      }
      loop()
    },
    
    draw() {
      const w = cfg.fullScreen ? window.innerWidth : canvas.offsetWidth
      const h = cfg.fullScreen ? window.innerHeight : canvas.offsetHeight
      
      // 根据配置绘制背景
      if (cfg.background === 'gradient') {
        // 绘制渐变背景
        const gradient = ctx.createLinearGradient(0, 0, w, h)
        gradient.addColorStop(0, cfg.gradientStart || '#667eea')
        gradient.addColorStop(1, cfg.gradientEnd || '#764ba2')
        ctx.fillStyle = gradient
        ctx.fillRect(0, 0, w, h)
        
        // 添加半透明遮罩产生拖尾效果
        ctx.fillStyle = 'rgba(102, 126, 234, 0.05)'
        ctx.fillRect(0, 0, w, h)
      } else if (cfg.background) {
        // 自定义纯色背景
        ctx.fillStyle = cfg.background
        ctx.fillRect(0, 0, w, h)
        
        // 添加半透明遮罩
        ctx.fillStyle = 'rgba(0, 0, 0, 0.05)'
        ctx.fillRect(0, 0, w, h)
      } else {
        // 默认背景
        const gradient = ctx.createLinearGradient(0, 0, w, h)
        gradient.addColorStop(0, '#a3bffa')
        gradient.addColorStop(1, '#b794f4')
        ctx.fillStyle = gradient
        ctx.fillRect(0, 0, w, h)
        
        // 添加半透明拖尾遮罩
        ctx.fillStyle = 'rgba(163, 191, 250, 0.05)'
        ctx.fillRect(0, 0, w, h)
      }
      
      // 更新并绘制粒子
      particles.forEach(p => {
        p.x += p.vx
        p.y += p.vy
        
        if (p.x < 0 || p.x > w) p.vx *= -1
        if (p.y < 0 || p.y > h) p.vy *= -1
        p.x = Math.max(0, Math.min(w, p.x))
        p.y = Math.max(0, Math.min(h, p.y))
        
        ctx.fillStyle = '#a3bffa'
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fill()
      })
      
      // 粒子间连线
      const maxDist = cfg.dist || 120
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x
          const dy = particles[i].y - particles[j].y
          const d = Math.sqrt(dx * dx + dy * dy)
          
          if (d < maxDist) {
            const alpha = (1 - d / maxDist) * 0.4
            ctx.strokeStyle = `rgba(255,255,255,${alpha})`
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(particles[i].x, particles[i].y)
            ctx.lineTo(particles[j].x, particles[j].y)
            ctx.stroke()
          }
        }
      }
      
      // 触摸点与粒子连线
      if (touch.x !== null) {
        const tr = cfg.radius || 150
        particles.forEach(p => {
          const dx = p.x - touch.x
          const dy = p.y - touch.y
          const d = Math.sqrt(dx * dx + dy * dy)
          
          if (d < tr) {
            const alpha = (1 - d / tr) * 0.6
            ctx.strokeStyle = `rgba(100,200,255,${alpha})`
            ctx.lineWidth = 2
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(touch.x, touch.y)
            ctx.stroke()
          }
        })
      }
      
      // 波纹效果
      const now = Date.now()
      for (let i = ripples.length - 1; i >= 0; i--) {
        const rp = ripples[i]
        const elapsed = now - rp.t
        const dur = 800
        const progress = elapsed / dur
        
        if (progress >= 1) {
          ripples.splice(i, 1)
          continue
        }
        
        rp.r = rp.max * progress * 0.3
        const alpha = (1 - progress) * 0.5
        
        ctx.strokeStyle = `rgba(150,220,255,${alpha})`
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.arc(rp.x, rp.y, rp.r, 0, Math.PI * 2)
        ctx.stroke()
        
        ctx.fillStyle = `rgba(150,220,255,${alpha * 0.15})`
        ctx.beginPath()
        ctx.arc(rp.x, rp.y, rp.r, 0, Math.PI * 2)
        ctx.fill()
      }
    }
    ,
    // 释放资源，避免跨页面卡顿
    dispose() {
      try { if (rafId) cancelAnimationFrame(rafId) } catch (e) {}
      isRunning = false
      this.unbindEvents()
      particles = []
      ripples = []
      touch = { x: null, y: null }
      try {
        if (createdCanvas && canvas && canvas.parentNode) {
          canvas.parentNode.removeChild(canvas)
        }
      } catch (e) {}
      canvas = null
      ctx = null
      createdCanvas = false
    }
  }
}
</script>

<style scoped>
.particle-container {
  overflow: hidden;
}
.canvas-layer {
  display: block;
}
</style>

<style scoped>
.particle-bg {
  pointer-events: none;
}
.particle-canvas {
  display: block;
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
}
.controls {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 10px;
  z-index: 2;
}
.btn {
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.28);
  color: #fff;
  border-radius: 18px;
  font-size: 12px;
  cursor: pointer;
}
</style>
