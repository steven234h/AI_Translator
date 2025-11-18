/*
  Minimal particles.js-compatible renderer for H5/App webview
  Exposes global function: particlesJS(id, config)
  Note: Lightweight implementation optimized for mobile performance.
*/
(function (window) {
  function rnd(min, max) { return Math.random() * (max - min) + min }
  function pick(arr) { return arr[Math.floor(Math.random() * arr.length)] }
  function hexToRgba(hex, alpha) {
    if (!hex) return 'rgba(255,255,255,' + (alpha || 1) + ')'
    if (hex[0] === '#') hex = hex.slice(1)
    if (hex.length === 3) hex = hex.split('').map(function (c) { return c + c }).join('')
    var bigint = parseInt(hex, 16)
    var r = (bigint >> 16) & 255
    var g = (bigint >> 8) & 255
    var b = bigint & 255
    return 'rgba(' + r + ',' + g + ',' + b + ',' + (alpha == null ? 1 : alpha) + ')'
  }

  function particlesJS(tagId, config) {
    var el = document.getElementById(tagId)
    if (!el) return

    // Create canvas
    var canvas = el.querySelector('canvas')
    if (!canvas) {
      canvas = document.createElement('canvas')
      canvas.style.width = '100%'
      canvas.style.height = '100%'
      canvas.style.display = 'block'
      el.appendChild(canvas)
    }
    var ctx = canvas.getContext('2d')

    var dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1))
    function resize() {
      var w = el.clientWidth || el.offsetWidth || window.innerWidth
      var h = el.clientHeight || el.offsetHeight || window.innerHeight
      canvas.width = Math.max(1, Math.floor(w * dpr))
      canvas.height = Math.max(1, Math.floor(h * dpr))
      canvas.style.width = w + 'px'
      canvas.style.height = h + 'px'
    }
    resize()
    window.addEventListener('resize', resize)

    // Defaults
    var p = (config && config.particles) || {}
    var number = (p.number && p.number.value) || 30
    var colors = Array.isArray(p.color && p.color.value) ? p.color.value : [ (p.color && p.color.value) || '#ffffff' ]
    var sizeBase = (p.size && p.size.value) || 3
    var sizeRandom = !!(p.size && p.size.random)
    var opacity = (p.opacity && p.opacity.value) || 0.5
    var link = (p.line_linked && p.line_linked.enable) ? {
      enable: true,
      distance: (p.line_linked.distance || 120) * dpr,
      color: (p.line_linked.color || '#cccccc'),
      opacity: (p.line_linked.opacity == null ? 0.4 : p.line_linked.opacity),
      width: Math.max(1, p.line_linked.width || 1) * dpr
    } : { enable: false }
    var moveSpeed = (p.move && p.move.speed) || 1
    var outMode = (p.move && p.move.out_mode) || 'out'

    // Init particles
    var particles = []
    function makeParticle() {
      var w = canvas.width, h = canvas.height
      var r = sizeRandom ? rnd(0.6 * sizeBase, 1.4 * sizeBase) : sizeBase
      return {
        x: rnd(0, w), y: rnd(0, h),
        vx: rnd(-moveSpeed, moveSpeed) * dpr, vy: rnd(-moveSpeed, moveSpeed) * dpr,
        r: r * dpr, color: pick(colors), o: opacity
      }
    }
    for (var i = 0; i < number; i++) particles.push(makeParticle())

    var rafId = 0, running = true
    function step() {
      if (!running) return
      rafId = window.requestAnimationFrame(step)
      var w = canvas.width, h = canvas.height
      ctx.clearRect(0, 0, w, h)

      // Move & draw
      for (var i = 0; i < particles.length; i++) {
        var pt = particles[i]
        pt.x += pt.vx
        pt.y += pt.vy
        if (outMode === 'out') {
          if (pt.x < -50) pt.x = w + 50
          if (pt.x > w + 50) pt.x = -50
          if (pt.y < -50) pt.y = h + 50
          if (pt.y > h + 50) pt.y = -50
        } else { // bounce
          if (pt.x - pt.r < 0 || pt.x + pt.r > w) pt.vx *= -1
          if (pt.y - pt.r < 0 || pt.y + pt.r > h) pt.vy *= -1
        }

        ctx.beginPath()
        ctx.fillStyle = hexToRgba(pt.color, pt.o)
        ctx.arc(pt.x, pt.y, pt.r, 0, Math.PI * 2)
        ctx.fill()
      }

      // Links (O(n^2) with low n, OK for mobile)
      if (link.enable) {
        ctx.lineWidth = link.width
        for (var i = 0; i < particles.length; i++) {
          for (var j = i + 1; j < particles.length; j++) {
            var a = particles[i], b = particles[j]
            var dx = a.x - b.x, dy = a.y - b.y
            var dist2 = dx * dx + dy * dy
            if (dist2 < link.distance * link.distance) {
              var alpha = link.opacity * (1 - Math.sqrt(dist2) / link.distance)
              ctx.strokeStyle = hexToRgba(link.color, Math.max(0, alpha))
              ctx.beginPath()
              ctx.moveTo(a.x, a.y)
              ctx.lineTo(b.x, b.y)
              ctx.stroke()
            }
          }
        }
      }
    }
    step()

    var instance = {
      el: el,
      canvas: canvas,
      destroy: function () {
        running = false
        if (rafId) window.cancelAnimationFrame(rafId)
        window.removeEventListener('resize', resize)
        try { el && canvas && el.contains(canvas) && el.removeChild(canvas) } catch (e) {}
      }
    }
    window.pJSDom = window.pJSDom || []
    window.pJSDom.push({ pJS: instance })
    return instance
  }

  // UMD-ish global export only (sufficient for uni-app H5/App webview)
  window.particlesJS = particlesJS
})(typeof window !== 'undefined' ? window : this)

