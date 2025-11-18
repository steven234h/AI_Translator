<template>
  <view class="container" @touchstart="onSwipeStart" @touchend="onSwipeEnd">
    <ParticleBackground :fullScreen="true" :particleCount="Math.round(80 * 2 / 3)" :speedScale="0.6" :autoPause="true" :mouseRadius="140" :connectDistance="110" />
    <!-- 右上角功能按钮：历史、分享 -->
    <view class="header-actions absolute">
      <view class="action-btn" @click="openHistory" :aria-label="'查看历史识别记录'">
        <text class="action-icon">🕘</text>
      </view>
      <view class="action-btn" :class="{ disabled: !shareEnabled }" @click="onShareClick" :aria-label="'分享识别结果'">
        <text class="action-icon">🔗</text>
      </view>
    </view>
    <!-- 头部标题 -->
    <view class="header">
      <text class="title">物体识别</text>
      <text class="subtitle">拍照或选择图片识别物体</text>
    </view>

    <!-- 图片上传区域 -->
    <view class="upload-section">
      <view v-if="!selectedImage" class="upload-placeholder" @click="showImageOptions">
        <image src="/static/camera-icon.png" class="upload-icon" mode="aspectFit"></image>
        <text class="upload-text">点击上传图片...</text>
        <text class="upload-subtext">支持拍照/相册，画面清晰、正面更易识别</text>
        <view class="upload-badges">
          <text class="badge">PNG</text>
          <text class="badge">JPG</text>
          <text class="badge">JPEG</text>
        </view>
      </view>

      <view v-else class="image-container">
        <view class="selected-image-frame">
          <image :src="selectedImage" class="selected-image" mode="aspectFit"></image>
        </view>
        <view class="image-actions">
          <button class="btn-secondary" @click="showImageOptions" :disabled="loading">重新选择</button>
          <button class="btn-primary" @click="openCropper" :disabled="loading">
            {{ loading ? '处理中...' : '选取物体' }}
          </button>
          <button
            class="btn-primary"
            @click="analyzeImage"
            :disabled="loading || !cropPreviewImage"
          >
            {{ loading ? '识别中...' : '开始识别' }}
          </button>
        </view>
        <view v-if="cropPreviewImage" class="crop-hint">已选取物体区域，下方为截取预览</view>
        <view v-if="cropPreviewImage" class="crop-preview">
          <text class="crop-preview-title">选取预览</text>
          <view class="crop-preview-frame">
            <image :src="cropPreviewImage" class="crop-preview-image" mode="aspectFit"></image>
            <!-- 仅在选取预览框内显示的加载遮罩 -->
            <view
              v-if="loading"
              class="preview-loading-overlay"
              catchtouchmove="true"
              @touchmove.stop.prevent
              @touchstart.stop.prevent
              @touchend.stop.prevent
              @click.stop
            >
              <view class="loading-card compact">
                <view class="spinner-ring small"></view>
                <text class="loading-title">识别中</text>
                <view class="loading-dots">
                  <view class="dot"></view>
                  <view class="dot"></view>
                  <view class="dot"></view>
                </view>
              </view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 加载骨架屏 -->
    <view v-if="loading" class="skeleton-section">
      <view class="skeleton-card"></view>
      <view class="skeleton-card"></view>
      <view class="skeleton-card short"></view>
    </view>

    <!-- 识别结果展示 -->
    <view v-if="recognitionResults.length > 0" class="results-section">
      <view class="section-header">
        <text class="section-title">识别结果</text>
        <text class="count-badge">{{ recognitionResults.length }}</text>
      </view>

      <!-- Canvas绘制区域 -->
      <view class="results-container">
        <view class="result-canvas-frame">
          <canvas
            canvas-id="imageCanvas"
            class="result-canvas"
            :style="{width: canvasWidth + 'px', height: canvasHeight + 'px'}"
          ></canvas>
        </view>
      </view>

      <!-- 识别结果三语言列表 -->
      <view class="objects-list">
        <view class="list-title">识别结果详情：</view>
        <view
          v-for="(obj, index) in recognitionResults"
          :key="index"
          class="object-detail-item"
          
        >
          <view class="object-number">{{ index + 1 }}</view>
          <view class="object-content">
            <view class="language-row">
              <text class="lang-prefix">中文：</text>
              <text class="lang-text zh">{{ obj.names ? obj.names.zh : (obj.keyword || '') }}</text>
            </view>
            <view class="language-row">
              <text class="lang-prefix">英文：</text>
              <text class="lang-text en">{{ obj.names ? obj.names.en : 'Loading...' }}</text>
            </view>
            <view class="language-row">
              <text class="lang-prefix">日文：</text>
              <text class="lang-text jp">{{ obj.names ? (obj.names.ja || obj.names.jp) : 'Loading...' }}</text>
            </view>
          </view>
          <view class="object-actions">
            <text class="icon-button icon-copy" @click.stop="copyItem(obj)">📋</text>
            <image class="icon-button icon-star" :src="(obj._favorited || isItemFavorited(obj)) ? '/static/stars-active.png' : '/static/stars.png'" mode="aspectFit" @click.stop="addFavoriteFromList(obj)" />
          </view>
        </view>

        <!-- 描述信息（三语），展示在识别结果详情底部 -->
        <view v-if="hasDescriptions" class="descriptions-block">
          <view class="blank-line"></view>
          <text class="desc-title">图像描述: (点击可切换语言)</text>
          <view class="blank-line"></view>
          <view class="desc-card" @click="openDescLangPicker">
            <view class="language-row">
              <text class="lang-prefix">{{ activeDescLabel }}：</text>
              <view class="lang-text" :class="activeDescLang">
                <text
                  v-for="(seg, idx) in activeDescSegments"
                  :key="'active-'+idx"
                  :class="['desc-seg', seg.highlight ? 'hl-word hl-' + seg.colorIndex : '']"
                >{{ seg.text }}</text>
              </view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 选择图片来源弹窗 -->
    <view v-if="showImageSourceModal" class="image-source-modal" @click="closeImageSourcePopup">
      <view class="image-source-options" @click.stop>
        <view class="option-item" @click="takePhoto">
          <text class="option-text">拍照</text>
        </view>
        <view class="option-item" @click="chooseFromAlbum">
          <text class="option-text">从相册选择</text>
        </view>
        <view class="option-item cancel" @click="closeImageSourcePopup">
          <text class="option-text">取消</text>
        </view>
      </view>
    </view>

    <!-- 描述语言切换弹窗 -->
    <view v-if="showDescLangPicker" class="image-source-modal" @click="showDescLangPicker = false">
      <view class="image-source-options" @click.stop>
        <view
          v-if="activeDescLang !== 'zh'"
          class="option-item"
          @click="setDescLang('zh')"
        >
          <text class="option-text">切换为中文</text>
        </view>
        <view
          v-if="activeDescLang !== 'en'"
          class="option-item"
          @click="setDescLang('en')"
        >
          <text class="option-text">Switch to English</text>
        </view>
        <view
          v-if="activeDescLang !== 'ja'"
          class="option-item"
          @click="setDescLang('ja')"
        >
          <text class="option-text">日本語に切り替え</text>
        </view>
        <view class="option-item cancel" @click="showDescLangPicker = false">
          <text class="option-text">取消</text>
        </view>
      </view>
    </view>

    <!-- 物体区域裁剪弹窗 -->
    <view v-if="showCropModal" class="cropper-modal" @click="closeCropperModal">
      <view class="cropper-container" @click.stop>
        <view class="cropper-header">
          <text class="cropper-title">选取物体区域</text>
          <text class="close-btn" @click="closeCropperModal">×</text>
        </view>
        <view class="cropper-tip">
          <text class="tip-line">拖动手指绘制选区，再次点选选区可拖动调整，重置后可重新框选。</text>
          <text class="tip-line">画布会按屏幕自适应缩放，不影响最终识别的清晰度。</text>
        </view>
        <view class="cropper-canvas-wrapper">
          <canvas
            canvas-id="cropCanvas"
            class="crop-canvas"
            :style="{ width: cropCanvasWidth + 'px', height: cropCanvasHeight + 'px' }"
            disable-scroll="true"
            @touchstart="onCropTouchStart"
            @touchmove="onCropTouchMove"
            @touchend="onCropTouchEnd"
            @touchcancel="onCropTouchEnd"
          ></canvas>
        </view>
        <view class="cropper-actions">
          <button class="btn-secondary" @click="resetCropSelection">重置</button>
          <button class="btn-primary" @click="confirmCropSelection">完成选取</button>
        </view>
      </view>
    </view>
    
    <!-- 历史记录弹窗 -->
    <view v-if="showHistoryModal" class="history-overlay" @click="closeHistory">
      <view class="history-panel" @click.stop>
        <view class="history-header">
          <text class="history-title">历史识别</text>
          <text class="close-btn" @click="closeHistory">×</text>
        </view>
        <view v-if="historyList.length > 0" class="history-grid">
          <view v-for="item in historyList" :key="item.id" class="history-item" @click="selectHistoryItem(item)">
            <image :src="item.image" mode="aspectFill" class="history-thumb" />
            <view class="history-time">{{ formatTime(item.createTime) }}</view>
            <text class="history-del" @click.stop="confirmDeleteItem(item)">×</text>
          </view>
        </view>
        <view v-else class="history-empty">
          <text class="empty-text">暂无历史记录</text>
        </view>
      </view>
    </view>

    <!-- 离屏合成分享用画布（隐藏） -->
    <canvas
      canvas-id="shareCanvas"
      class="share-canvas"
      :style="{ width: shareCanvasWidth + 'px', height: shareCanvasHeight + 'px' }"
    ></canvas>

  </view>
</template>

<script>
import { request, storage } from '@/utils/api.js'
import ParticleBackground from '@/components/ParticleBackground.vue'


  export default {
    components: { ParticleBackground },
    data() {
      return {
      selectedImage: '',
      originalImage: '',
      croppedImage: '',
      cropPreviewImage: '',
      recognitionResults: [],
      // 新增：多语言描述（与后端字段 descriptions 对齐）
      descriptions: { zh: '', en: '', ja: '' },
      loading: false,
      canvasWidth: 0,
      canvasHeight: 0,
      canvasDrawWidth: 0,
      canvasDrawHeight: 0,
      canvasDrawOffsetX: 0,
      canvasDrawOffsetY: 0,
      imageWidth: 0,
      imageHeight: 0,
      cropImageWidth: 0,
      cropImageHeight: 0,
      cropCanvasWidth: 0,
      cropCanvasHeight: 0,
      cropStartPoint: null,
      cropRect: null,
      isCropping: false,
      cropScaleX: 1,
      cropScaleY: 1,
      cropMode: 'idle',
      cropMoveStart: null,
      cropMoveRect: null,
      lastCropRatio: null,
      showImageSourceModal: false,
      showCropModal: false,
      // 页面左右滑动手势状态
      swipeStartX: 0,
      swipeStartY: 0,
      swipeStartTime: 0,
      swipeLocked: false,
      // 描述语言切换
      activeDescLang: 'zh',
      showDescLangPicker: false,
      // 历史/分享
      showHistoryModal: false,
      historyList: [],
      lastSharePath: '',
      shareCanvasWidth: 10,
      shareCanvasHeight: 10,
      showClearConfirm: false
      }
    },
    // 离屏合成：将图片、标注、文字绘制到隐藏画布，导出稳定图片
    

  

  computed: {
    resultDisplayImage() {
      return this.croppedImage || this.cropPreviewImage || this.selectedImage || ''
    }
    ,
    // 分享按钮是否可用：有识别结果或正在查看历史
    shareEnabled() {
      return (this.recognitionResults && this.recognitionResults.length > 0) || this.showHistoryModal
    }
    ,
    hasDescriptions() {
      const d = this.descriptions || {}
      return !!(d.zh || d.en || d.ja || d.jp)
    },
    // 描述高亮（按识别结果为每种语言生成最多7个高亮词，颜色按红橙黄绿青蓝紫）
    highlightedDescriptions() {
      const d = this.descriptions || {}
      const textZh = d.zh || ''
      const textEn = d.en || ''
      const textJa = d.ja || d.jp || ''

      const tokens = this.getHighlightTokens()
      return {
        zh: this.highlightSegments(textZh, tokens.zh, 'zh'),
        en: this.highlightSegments(textEn, tokens.en, 'en'),
        ja: this.highlightSegments(textJa, tokens.ja, 'ja')
      }
    },
    // 当前展示语言的分片与标签
    activeDescSegments() {
      const lang = this.activeDescLang || 'zh'
      const map = this.highlightedDescriptions || {}
      const segs = (map[lang] && map[lang].length ? map[lang] : [])
      if (segs.length > 0) return segs
      // 若当前语言为空，则回退中文/英文/日文
      return map.zh && map.zh.length ? map.zh : (map.en && map.en.length ? map.en : (map.ja || []))
    },
    activeDescLabel() {
      const l = (this.activeDescLang || 'zh')
      return l === 'en' ? '英文' : (l === 'ja' ? '日文' : '中文')
    }
  },

  methods: {
    // 删除单条历史
    confirmDeleteItem(item) {
      if (!item) return
      uni.showModal({
        title: '删除历史',
        content: '是否要删除该条历史记录？',
        cancelText: '否',
        confirmText: '是',
        success: (res) => {
          if (res.confirm) {
            storage.removeRecognitionHistory(item.id)
            this.historyList = this.historyList.filter(it => it.id !== item.id)
            uni.showToast({ title: '已删除', icon: 'success' })
          }
        }
      })
    },
    // 打开历史面板
    openHistory() {
      if (this.loading) return
      this.historyList = storage.getRecognitionHistory().sort((a,b) => new Date(b.createTime) - new Date(a.createTime))
      this.showHistoryModal = true
    },
    closeHistory() {
      this.showHistoryModal = false
    },
    // 选择一条历史记录，切换到该图片与结果
    selectHistoryItem(item) {
      if (!item) return
      this.selectedImage = item.image || ''
      this.originalImage = item.image || ''
      this.croppedImage = item.image || ''
      this.cropPreviewImage = item.image || ''
      this.recognitionResults = this.formatRecognitionObjects(item.results || [])
      this.descriptions = item.descriptions || {}
      this.activeDescLang = 'zh'
      this.showHistoryModal = false
      // 绘制识别框
      this.$nextTick(() => {
        setTimeout(() => this.drawImageWithBounds(), 120)
      })
      uni.showToast({ title: '已回溯', icon: 'success' })
    },
    // 保存识别结果到历史
    async saveRecognitionToHistory() {
      try {
        let finalPath = this.croppedImage
        // 尝试持久化保存临时文件，避免被系统清理
        if (finalPath && typeof uni.saveFile === 'function') {
          await new Promise((resolve) => {
            uni.saveFile({ tempFilePath: finalPath, success: (r)=>{ finalPath = r.savedFilePath || finalPath; resolve(); }, fail: ()=> resolve() })
          })
        }
        storage.addRecognitionHistory({
          image: finalPath || this.resultDisplayImage,
          results: this.recognitionResults,
          descriptions: this.descriptions
        })
      } catch (e) {
        console.warn('保存识别历史失败:', e)
      }
    },
    // 点击右上角分享
    onShareClick() {
      if (!this.shareEnabled) { uni.showToast({ title: '暂无可分享内容，请先识别或从历史选择', icon: 'none' }); return }
      // 若暂无结果，给予提示
      if (!this.recognitionResults || this.recognitionResults.length === 0) {
        uni.showToast({ title: '请选择一条历史图片', icon: 'none' })
        return
      }
      uni.showToast({ title: '正在生成分享图...', icon: 'none', duration: 1000 })
      this.shareResultsSection()
    },
    // 生成卡其色三语词汇分享卡（不再拼接原图与框）
    shareResultsSection() {
      const results = Array.isArray(this.recognitionResults) ? this.recognitionResults : []
      const d = this.descriptions || {}
      const zhSentence = d.zh || ''
      const enSentence = d.en || ''
      const jaSentence = d.ja || d.jp || ''

      const boardW = 1080
      const outerPad = 40
      const cardW = boardW - outerPad * 2
      const innerPad = 48
      const radius = 24

      const count = Math.max(1, results.length)
      const titleFont = count <= 3 ? 48 : (count <= 6 ? 44 : 40)
      const zhWordFont = count <= 3 ? 48 : (count <= 6 ? 42 : 36)
      const enWordFont = count <= 3 ? 36 : (count <= 6 ? 32 : 28)
      const jaWordFont = count <= 3 ? 36 : (count <= 6 ? 32 : 28)
      const sentenceFont = count <= 3 ? 34 : (count <= 6 ? 32 : 30)
      const lineGap = count > 6 ? 6 : 8
      const itemGap = count > 6 ? 22 : 32

      const maxTextWidth = cardW - innerPad * 2

      const estimateWidth = (str, fontSize) => {
        let w = 0
        const s = String(str || '')
        for (let i = 0; i < s.length; i++) {
          const ch = s.charCodeAt(i)
          if (ch >= 0x4e00 && ch <= 0x9fff) w += fontSize * 0.9
          else if (ch > 255) w += fontSize * 0.9
          else if (s[i] === ' ' || s[i] === '\t') w += fontSize * 0.33
          else w += fontSize * 0.55
        }
        return w
      }
      const wrapText = (text, maxWidth, fontSize) => {
        const lines = []
        const chars = Array.from(String(text || ''))
        let line = ''
        for (const ch of chars) {
          const test = line + ch
          if (estimateWidth(test, fontSize) <= maxWidth) {
            line = test
          } else {
            if (line) lines.push(line)
            line = ch
          }
        }
        if (line) lines.push(line)
        return lines.length ? lines : ['']
      }
      const roundRectPath = (ctx2, x, y, w, h, r) => {
        const rr = Math.max(0, Math.min(r, Math.min(w, h) / 2))
        ctx2.beginPath()
        ctx2.moveTo(x + rr, y)
        ctx2.lineTo(x + w - rr, y)
        ctx2.quadraticCurveTo(x + w, y, x + w, y + rr)
        ctx2.lineTo(x + w, y + h - rr)
        ctx2.quadraticCurveTo(x + w, y + h, x + w - rr, y + h)
        ctx2.lineTo(x + rr, y + h)
        ctx2.quadraticCurveTo(x, y + h, x, y + h - rr)
        ctx2.lineTo(x, y + rr)
        ctx2.quadraticCurveTo(x, y, x + rr, y)
        ctx2.closePath()
      }

      // 预排版以计算高度
      let cursor = innerPad + (titleFont + 8) + 16
      const wordBlocks = results.map(obj => {
        const zh = (obj && obj.names && obj.names.zh) || obj.keyword || ''
        const en = (obj && obj.names && obj.names.en) || ''
        const ja = (obj && obj.names && (obj.names.ja || obj.names.jp)) || ''
        const zhLines = wrapText(zh, maxTextWidth - 60, zhWordFont)
        const enLines = wrapText(en, maxTextWidth - 60, enWordFont)
        const jaLines = wrapText(ja, maxTextWidth - 60, jaWordFont)
        const blockH = zhLines.length * (zhWordFont + lineGap) +
                       enLines.length * (enWordFont + lineGap) +
                       jaLines.length * (jaWordFont + lineGap) + 8
        cursor += blockH + itemGap
        return { zhLines, enLines, jaLines }
      })

      const sentenceBlocks = []
      if (zhSentence) sentenceBlocks.push({ label: '中文', text: zhSentence })
      if (enSentence) sentenceBlocks.push({ label: '英文', text: enSentence })
      if (jaSentence) sentenceBlocks.push({ label: '日文', text: jaSentence })
      sentenceBlocks.forEach(b => {
        const lines = wrapText(b.text, maxTextWidth - 72, sentenceFont)
        b.lines = lines
        cursor += 34 + 12 /* label + gap */
        cursor += lines.length * (sentenceFont + 8) + 12
      })

      const cardH = cursor + innerPad
      const boardH = cardH + outerPad * 2

      this.shareCanvasWidth = boardW
      this.shareCanvasHeight = boardH

      // 等待尺寸应用后再绘制，避免首次分享空白
      this.$nextTick(() => {
        setTimeout(() => {
          const ctx = uni.createCanvasContext('shareCanvas', this)

          // 绘制背景与卡片
          ctx.setFillStyle('#f7f4ec')
          ctx.fillRect(0, 0, boardW, boardH)

          const cardX = outerPad
          const cardY = outerPad
          // 阴影
          ctx.setFillStyle('rgba(0,0,0,0.08)')
          roundRectPath(ctx, cardX + 4, cardY + 6, cardW, cardH, radius)
          ctx.fill()
          // 卡其色卡面
          ctx.setFillStyle('#f0e6d2')
          roundRectPath(ctx, cardX, cardY, cardW, cardH, radius)
          ctx.fill()

          // 标题
          let y = cardY + innerPad
          ctx.setFillStyle('#5a503b')
          ctx.setFontSize(titleFont)
          ctx.setTextAlign('left')
          ctx.setTextBaseline('top')
          ctx.fillText('三语词汇卡', cardX + innerPad, y)
          y += (titleFont + 8) + 16

          // 单词三语列表
          const chipR = Math.max(12, Math.min(22, Math.round(zhWordFont * 0.45)))
          results.forEach((obj, idx) => {
            const block = wordBlocks[idx]
            const leftX = cardX + innerPad
            const circleY = y + Math.max(zhWordFont, 28) / 2
            ctx.beginPath(); ctx.arc(leftX + chipR, circleY, chipR, 0, 2 * Math.PI)
            ctx.setFillStyle('#d4b483'); ctx.fill()
            ctx.setFillStyle('#ffffff'); ctx.setFontSize(20); ctx.setTextAlign('center'); ctx.setTextBaseline('middle')
            ctx.fillText(String(idx + 1), leftX + chipR, circleY)
            ctx.setTextAlign('left'); ctx.setTextBaseline('top')

            let tx = leftX + chipR * 2 + 16
            let ty = y
            ctx.setFillStyle('#2f2a1f'); ctx.setFontSize(zhWordFont)
            block.zhLines.forEach(line => { ctx.fillText(line, tx, ty); ty += zhWordFont + lineGap })
            ctx.setFillStyle('#5a503b'); ctx.setFontSize(enWordFont)
            block.enLines.forEach(line => { ctx.fillText(line, tx, ty); ty += enWordFont + lineGap })
            ctx.setFillStyle('#5a503b'); ctx.setFontSize(jaWordFont)
            block.jaLines.forEach(line => { ctx.fillText(line, tx, ty); ty += jaWordFont + lineGap })
            y = ty + itemGap
          })

          if (sentenceBlocks.length > 0) {
            // 分割线
            ctx.setFillStyle('rgba(90,80,59,0.25)')
            ctx.fillRect(cardX + innerPad, y, cardW - innerPad * 2, 2)
            y += 22

            // 三语句子标题
            const subTitleFont = Math.max(30, titleFont - 10)
            ctx.setFillStyle('#5a503b'); ctx.setFontSize(subTitleFont); ctx.setTextBaseline('top')
            ctx.fillText('三语句子', cardX + innerPad, y)
            y += subTitleFont + 18

            // 句子块
            sentenceBlocks.forEach(b => {
              const labelText = b.label
              const labelFont = 24
              const labelPadX = 14
              const labelH = 30
              const labelW = estimateWidth(labelText, labelFont) + labelPadX * 2
              // 标签底
              ctx.setFillStyle('#e2d3ad')
              roundRectPath(ctx, cardX + innerPad, y, labelW, labelH, 12)
              ctx.fill()
              // 标签字
              ctx.setFillStyle('#5a503b'); ctx.setFontSize(labelFont); ctx.setTextBaseline('top')
              ctx.fillText(labelText, cardX + innerPad + labelPadX, y + 4)
              y += labelH + 10
              // 文本
              ctx.setFillStyle('#2f2a1f'); ctx.setFontSize(sentenceFont)
              const lines = b.lines || []
              lines.forEach(line => { ctx.fillText(line, cardX + innerPad, y); y += sentenceFont + 8 })
              y += 8
            })
          }

          ctx.draw(false, () => {
            setTimeout(() => {
              uni.canvasToTempFilePath({
                canvasId: 'shareCanvas',
                destWidth: boardW,
                destHeight: boardH,
                fileType: 'png',
                success: (r) => {
                  const path = r.tempFilePath
                  // #ifdef APP-PLUS
                  try { plus.share.sendWithSystem({ type: 'image', pictures: [path] }) } catch (e) { uni.showToast({ title: '分享失败', icon: 'none' }) }
                  // #endif
                  // #ifndef APP-PLUS
                  uni.saveImageToPhotosAlbum({ filePath: path, success: () => uni.showToast({ title: '已保存图片，可前往系统分享', icon: 'none' }) })
                  // #endif
                },
                fail: () => this.shareCanvasFallback()
              })
            }, 60)
          })
        }, 60)
      })
    },
    // 回退：导出画布(只含图片与框)，仍可分享
    shareCanvasFallback() {
      try {
        uni.canvasToTempFilePath({
          canvasId: 'imageCanvas',
          success: (r) => {
            const path = r.tempFilePath
            // H5/小程序调用通用分享（能力受限），App 走系统分享
            // #ifdef APP-PLUS
            try { plus.share.sendWithSystem({ type: 'image', pictures: [path] }) } catch (_) {}
            // #endif
            // 其他平台：保存到相册，提示用户再手动分享
            // #ifndef APP-PLUS
            uni.saveImageToPhotosAlbum({ filePath: path, success: () => uni.showToast({ title: '已保存图片，可前往系统分享', icon: 'none' }) })
            // #endif
          },
          fail: (err) => {
            console.error('导出分享图片失败:', err)
            uni.showToast({ title: '分享失败', icon: 'none' })
          }
        })
      } catch (e) {
        console.error('分享回退异常:', e)
      }
    },
    // 时间格式化（用于历史列表）
    formatTime(isoStr) {
      if (!isoStr) return ''
      try {
        const d = new Date(isoStr)
        const p = (n) => (n < 10 ? '0' + n : '' + n)
        return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
      } catch (_) {
        return isoStr
      }
    },
    // 打开描述语言切换
    openDescLangPicker() {
      if (this.loading) return
      this.showDescLangPicker = true
    },
    // 设置描述语言
    setDescLang(lang) {
      this.activeDescLang = lang || 'zh'
      this.showDescLangPicker = false
    },
    // 生成每种语言需要高亮的词（按识别结果顺序，最多7个）
    getHighlightTokens() {
      const max = 7
      const list = Array.isArray(this.recognitionResults) ? this.recognitionResults : []
      const zhSet = new Set()
      const enSet = new Set()
      const jaSet = new Set()

      const zh = []
      const en = []
      const ja = []

      for (const obj of list) {
        if (zh.length < max) {
          const v = (obj && obj.names && obj.names.zh) || (obj && obj.keyword) || ''
          const key = this.normalizeLangToken(v, 'zh')
          if (key && !zhSet.has(key)) { zhSet.add(key); zh.push(v) }
        }
        if (en.length < max) {
          const v = (obj && obj.names && obj.names.en) || ''
          const key = this.normalizeLangToken(v, 'en')
          if (key && !enSet.has(key)) { enSet.add(key); en.push(v) }
        }
        if (ja.length < max) {
          const v = (obj && obj.names && (obj.names.ja || obj.names.jp)) || ''
          const key = this.normalizeLangToken(v, 'ja')
          if (key && !jaSet.has(key)) { jaSet.add(key); ja.push(v) }
        }
        if (zh.length >= max && en.length >= max && ja.length >= max) break
      }
      // 截断，确保不超过7
      return {
        zh: zh.slice(0, max),
        en: en.slice(0, max),
        ja: ja.slice(0, max)
      }
    },

    // 将 text 分割为若干片段，匹配到的词带有 highlight 与颜色索引（1..7）
    highlightSegments(text, tokens, lang) {
      const segments = []
      if (!text || !Array.isArray(tokens) || tokens.length === 0) {
        return [{ text: text || '', highlight: false }]
      }

      // 收集所有命中范围
      const matches = []
      const maxColors = 7
      const limited = tokens.slice(0, maxColors)

      for (let i = 0; i < limited.length; i++) {
        const raw = limited[i]
        const token = (raw || '').toString().trim()
        if (!token) continue
        try {
          const regex = this.createLangRegex(token, lang)
          let m
          while ((m = regex.exec(text)) !== null) {
            const start = m.index
            const end = m.index + m[0].length
            matches.push({ start, end, colorIndex: i + 1 })
            if (!regex.global) break
            if (m.index === regex.lastIndex) regex.lastIndex++
          }
        } catch (_) {}
      }

      if (matches.length === 0) return [{ text, highlight: false }]

      // 按起点排序并去重重叠（保留最先出现的）
      matches.sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start))
      const selected = []
      let cursor = 0
      for (const m of matches) {
        if (m.start >= cursor) {
          selected.push(m)
          cursor = m.end
        }
      }

      // 生成片段
      let pos = 0
      for (const m of selected) {
        if (m.start > pos) {
          segments.push({ text: text.slice(pos, m.start), highlight: false })
        }
        segments.push({ text: text.slice(m.start, m.end), highlight: true, colorIndex: m.colorIndex })
        pos = m.end
      }
      if (pos < text.length) {
        segments.push({ text: text.slice(pos), highlight: false })
      }
      return segments
    },

    // 针对不同语言的匹配规则：英文使用单词边界，其他语言使用子串匹配
    createLangRegex(token, lang) {
      const escaped = this.escapeRegExp(token)
      if (lang === 'en') {
        return new RegExp(`\\b${escaped}\\b`, 'gi')
      }
      return new RegExp(escaped, 'g')
    },
    // 归一化用于集合去重
    normalizeLangToken(token, lang) {
      if (!token) return ''
      const s = String(token).trim()
      return lang === 'en' ? s.toLowerCase() : s
    },
    // 正则转义
    escapeRegExp(str) {
      return String(str).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    },
    // 页面级左右滑动：向左切换到收藏页
    onSwipeStart(e) {
      const t = (e && (e.touches && e.touches[0])) || (e && e.changedTouches && e.changedTouches[0]) || {}
      this.swipeStartX = t.clientX || t.pageX || t.x || 0
      this.swipeStartY = t.clientY || t.pageY || t.y || 0
      this.swipeStartTime = Date.now()
      this.swipeLocked = false
    },
    onSwipeEnd(e) {
      if (this.swipeLocked) return
      // 弹窗/裁剪/加载中时禁用页面级滑动，避免冲突
      if (this.loading || this.showImageSourceModal || this.showCropModal ) return
      const t = (e && (e.changedTouches && e.changedTouches[0])) || (e && e.touches && e.touches[0]) || {}
      const endX = t.clientX || t.pageX || t.x || 0
      const endY = t.clientY || t.pageY || t.y || 0
      const dx = endX - this.swipeStartX
      const dy = endY - this.swipeStartY
      const dt = Date.now() - this.swipeStartTime
      // 快速、横向为主的滑动才触发
      if (dt <= 500 && Math.abs(dx) >= 60 && Math.abs(dy) < 50) {
        if (dx < 0) { // 向左滑，从识别页到收藏页
          this.swipeLocked = true
          try {
            uni.switchTab({ url: '/pages/favorites/favorites' })
          } catch (err) {}
        }
      }
    },
    // 显示图片来源选择（识别期间禁止）
    showImageOptions() {
      if (this.loading) return
      this.showImageSourceModal = true
    },

    closeImageSourcePopup() {
      this.showImageSourceModal = false
    },

    // 拍照
    takePhoto() {
      this.closeImageSourcePopup()

      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['camera'],
        success: (res) => {
          const fileObj = (res && res.tempFiles && res.tempFiles[0]) || null
          const imagePath = (res && res.tempFilePaths && res.tempFilePaths[0])
            || (fileObj && (fileObj.path || (typeof URL !== 'undefined' && URL.createObjectURL(fileObj))))
            || ''
          const size = fileObj && fileObj.size
          this.handleImageSelect(imagePath, size)
        },
        fail: (err) => {
          console.error('拍照失败:', err)
          let errorMsg = '拍照失败'
          if (err.errMsg) {
            if (err.errMsg.includes('cancel')) {
              errorMsg = '用户取消拍照'
            } else if (err.errMsg.includes('camera')) {
              errorMsg = '相机不可用'
            }
          }
          uni.showToast({
            title: errorMsg,
            icon: 'none',
            duration: 2000
          })
        }
      })
    },

    // 从相册选择
    chooseFromAlbum() {
      this.closeImageSourcePopup()

      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album'],
        success: (res) => {
          const fileObj = (res && res.tempFiles && res.tempFiles[0]) || null
          const imagePath = (res && res.tempFilePaths && res.tempFilePaths[0])
            || (fileObj && (fileObj.path || (typeof URL !== 'undefined' && URL.createObjectURL(fileObj))))
            || ''
          const size = fileObj && fileObj.size
          this.handleImageSelect(imagePath, size)
        },
        fail: (err) => {
          console.error('选择图片失败:', err)
          let errorMsg = '选择图片失败'
          if (err.errMsg && err.errMsg.includes('cancel')) {
            errorMsg = '用户取消选择'
          }
          uni.showToast({
            title: errorMsg,
            icon: 'none',
            duration: 2000
          })
        }
      })
    },

    // 处理图片选择（优先使用 chooseImage 返回的 size，失败再退回 getFileInfo）
    async handleImageSelect(imagePath, fileSize) {
      const proceed = async () => {
        // 统一在最早时机做路径标准化，并校验可读性，必要时通过压缩生成稳定本地临时文件
        try {
          const fixed = await this.coerceLoadablePath(imagePath)
          this.originalImage = fixed || imagePath
          this.selectedImage = fixed || imagePath
        } catch (_) {
          this.originalImage = imagePath
          this.selectedImage = imagePath
        }
        this.croppedImage = ''
        this.cropPreviewImage = ''
        this.cropRect = null
        this.cropStartPoint = null
        this.isCropping = false
        this.cropMode = 'idle'
        this.cropMoveStart = null
        this.cropMoveRect = null
        this.lastCropRatio = null
        this.recognitionResults = []
      }

      // 已知大小且合规，直接继续，减少一次 I/O
      if (typeof fileSize === 'number' && fileSize >= 0) {
        if (fileSize > 10 * 1024 * 1024) {
          uni.showToast({ title: '图片大小不能超过10MB', icon: 'error' })
          return
        }
        await proceed()
        return
      }

      // 未提供大小时，尽量通过 getFileInfo 获取；失败则放行但提示
      uni.getFileInfo({
        filePath: imagePath,
        success: async (res) => {
          if (res.size > 10 * 1024 * 1024) {
            uni.showToast({ title: '图片大小不能超过10MB', icon: 'error' })
            return
          }
          await proceed()
        },
        fail: async () => {
          // 某些平台路径（如 blob:/content://）可能不被 getFileInfo 支持
          // 为了不阻塞用户流程，放行并提示
          uni.showToast({ title: '已选择图片（大小未知）', icon: 'none' })
          await proceed()
        }
      })
    },

    formatRecognitionObjects(objects = []) {
      return objects.map(obj => {
        const normalizedImage = this.normalizeResultImage(obj)
        const resultImage = this.resultDisplayImage || normalizedImage
        return {
          ...obj,
          displayImage: resultImage || normalizedImage || ''
        }
      })
    },

    normalizeResultImage(obj) {
      if (!obj || typeof obj !== 'object') return ''
      const candidates = [
        obj.displayImage,
        obj.imageUrl,
        obj.image,
        obj.url,
        obj.thumbnail,
        obj.previewImage,
        obj.image_path,
        obj.base64,
        obj.base64Image
      ]
      if (obj.media) {
        if (typeof obj.media === 'string') {
          candidates.push(obj.media)
        } else if (typeof obj.media === 'object') {
          candidates.push(obj.media.url, obj.media.image, obj.media.preview)
        }
      }
      for (const candidate of candidates) {
        if (!candidate || typeof candidate !== 'string') continue
        const trimmed = candidate.trim()
        if (!trimmed) continue
        if (
          trimmed.startsWith('data:image') ||
          trimmed.startsWith('http://') ||
          trimmed.startsWith('https://') ||
          trimmed.startsWith('file://') ||
          trimmed.startsWith('blob:')
        ) {
          return trimmed
        }
        if (/^[A-Za-z0-9+/=]+$/.test(trimmed) && trimmed.length > 50) {
          return `data:image/jpeg;base64,${trimmed}`
        }
      }
      return ''
    },

    // 将可能的 blob:// 或其他不兼容路径转换为可被 getImageInfo/Canvas 使用的路径
    async ensureImageLoadable(src) {
      if (!src || typeof src !== 'string') return src
      const trimmed = src.trim()
      if (!trimmed) return trimmed

      // 直接可用的几类
      if (
        trimmed.startsWith('data:image') ||
        trimmed.startsWith('http://') ||
        trimmed.startsWith('https://') ||
        trimmed.startsWith('file://') ||
        trimmed.startsWith('wxfile://') ||
        trimmed.startsWith('/storage/') ||
        trimmed.startsWith('/_doc/')
      ) {
        return trimmed
      }

      // Android 原生内容路径：尝试解析为本地可用路径
      if (trimmed.startsWith('content://')) {
        try {
          if (typeof plus !== 'undefined' && plus.io && (plus.io.resolveLocalFileSystemURL || plus.io.convertLocalFileSystemURL)) {
            // 优先 resolve 成 Entry，再取 toLocalURL；失败则退回 convertLocalFileSystemURL
            const local = await new Promise((resolve) => {
              try {
                if (plus.io.resolveLocalFileSystemURL) {
                  plus.io.resolveLocalFileSystemURL(trimmed, (entry) => {
                    try {
                      const url = (entry && entry.toLocalURL && entry.toLocalURL()) || (plus.io.convertLocalFileSystemURL && plus.io.convertLocalFileSystemURL(trimmed))
                      resolve(url || trimmed)
                    } catch (e) { resolve(trimmed) }
                  }, () => {
                    try {
                      const url = plus.io.convertLocalFileSystemURL && plus.io.convertLocalFileSystemURL(trimmed)
                      resolve(url || trimmed)
                    } catch (e) { resolve(trimmed) }
                  })
                } else {
                  const url = plus.io.convertLocalFileSystemURL && plus.io.convertLocalFileSystemURL(trimmed)
                  resolve(url || trimmed)
                }
              } catch (e) { resolve(trimmed) }
            })
            if (local) return local
          }
        } catch (_) {}
      }

      // H5 blob: 需转 dataURL
      if (trimmed.startsWith('blob:')) {
        try {
          if (typeof fetch === 'function' && typeof FileReader !== 'undefined') {
            const resp = await fetch(trimmed)
            const blob = await resp.blob()
            const dataUrl = await new Promise((resolve, reject) => {
              const reader = new FileReader()
              reader.onload = () => resolve(reader.result)
              reader.onerror = reject
              reader.readAsDataURL(blob)
            })
            return dataUrl
          }
        } catch (err) {
          console.warn('blob 转换 dataURL 失败:', err)
        }
      }

      // APP-PLUS 场景：尝试转系统绝对路径
      try {
        if (typeof plus !== 'undefined' && plus.io && plus.io.convertLocalFileSystemURL) {
          const local = plus.io.convertLocalFileSystemURL(trimmed)
          if (local) return local
        }
      } catch (_) {}

      return trimmed
    },

    // 校验图片路径可读；若失败，尝试通过 compressImage 生成新的临时路径以规避 content://、EXIF 方向等兼容问题
    async coerceLoadablePath(src) {
      if (!src) return src
      const normalized = await this.ensureImageLoadable(src)
      const ok = await this.verifyImageReadable(normalized)
      if (ok) return normalized
      // 若读取失败，尝试压缩一次生成临时文件，通常可修复 content:// 与某些竖图的加载问题
      try {
        const temp = await this.createLocalTempFromImage(normalized)
        const ok2 = await this.verifyImageReadable(temp)
        return ok2 ? temp : (normalized || src)
      } catch (e) {
        console.warn('coerceLoadablePath fallback 失败:', e)
        return normalized || src
      }
    },

    // 使用 getImageInfo 验证路径可读取
    verifyImageReadable(path) {
      return new Promise((resolve) => {
        if (!path) { resolve(false); return }
        try {
          uni.getImageInfo({
            src: path,
            success: () => resolve(true),
            fail: () => resolve(false)
          })
        } catch (_) { resolve(false) }
      })
    },

    // 通过 compressImage 生成本地可访问的临时文件（并清除可能的 EXIF 造成的方向/元数据干扰）
    createLocalTempFromImage(src) {
      return new Promise((resolve, reject) => {
        if (!src) { reject(new Error('empty src')); return }
        try {
          uni.compressImage({
            src,
            quality: 100,
            success: (r) => {
              // HBuilderX/uni-app 各版本字段名可能为 tempFilePath 或 tempFilePaths
              const out = (r && (r.tempFilePath || (Array.isArray(r.tempFilePaths) && r.tempFilePaths[0]))) || ''
              if (out) resolve(out); else reject(new Error('no tempFilePath'))
            },
            fail: (err) => reject(err)
          })
        } catch (e) {
          reject(e)
        }
      })
    },

    // 打开裁剪弹窗
    openCropper() {
      const candidate = this.croppedImage || this.cropPreviewImage || this.selectedImage || this.originalImage
      if (!candidate) {
        uni.showToast({
          title: '请先上传图片',
          icon: 'none'
        })
        return
      }
      this.originalImage = candidate
      this.showCropModal = true
      this.cropRect = null
      this.cropStartPoint = null
      this.isCropping = false
      this.cropScaleX = 1
      this.cropScaleY = 1
      this.cropMode = 'idle'
      this.cropMoveStart = null
      this.cropMoveRect = null
      this.$nextTick(() => {
        this.prepareCropCanvas()
      })
    },

    closeCropperModal() {
      this.showCropModal = false
      this.isCropping = false
      this.cropStartPoint = null
      this.cropMode = 'idle'
      this.cropMoveStart = null
      this.cropMoveRect = null
    },

    async prepareCropCanvas() {
      // 在进入裁剪前也做一层强制纠正，避免二次选择部分竖图在 getImageInfo 阶段失败
      const loadable = await this.coerceLoadablePath(this.originalImage)
      this.originalImage = loadable || this.originalImage

      uni.getImageInfo({
        src: this.originalImage,
        success: (res) => {
          this.cropImageWidth = res.width
          this.cropImageHeight = res.height

          const systemInfo = uni.getSystemInfoSync()
          const maxWidth = systemInfo.windowWidth - 40
          const maxHeight = 400

          let canvasWidth = res.width
          let canvasHeight = res.height

          if (canvasWidth > maxWidth) {
            canvasHeight = canvasHeight * maxWidth / canvasWidth
            canvasWidth = maxWidth
          }

          if (canvasHeight > maxHeight) {
            canvasWidth = canvasWidth * maxHeight / canvasHeight
            canvasHeight = maxHeight
          }

          this.cropCanvasWidth = canvasWidth
          this.cropCanvasHeight = canvasHeight
          const safeCanvasWidth = canvasWidth || 1
          const safeCanvasHeight = canvasHeight || 1
          this.cropScaleX = res.width / safeCanvasWidth
          this.cropScaleY = res.height / safeCanvasHeight

          if (this.lastCropRatio) {
            this.cropRect = {
              x: this.lastCropRatio.x * canvasWidth,
              y: this.lastCropRatio.y * canvasHeight,
              width: this.lastCropRatio.width * canvasWidth,
              height: this.lastCropRatio.height * canvasHeight
            }
          }

          this.$nextTick(() => {
            this.drawCropCanvas()
          })
        },
        fail: async (err) => {
          console.error('初始化裁剪画布失败，尝试 fallback:', err)
          try {
            const temp = await this.createLocalTempFromImage(this.originalImage)
            this.originalImage = temp
            uni.getImageInfo({
              src: this.originalImage,
              success: (res2) => {
                this.cropImageWidth = res2.width
                this.cropImageHeight = res2.height

                const systemInfo = uni.getSystemInfoSync()
                const maxWidth = systemInfo.windowWidth - 40
                const maxHeight = 400

                let canvasWidth = res2.width
                let canvasHeight = res2.height
                if (canvasWidth > maxWidth) { canvasHeight = canvasHeight * maxWidth / canvasWidth; canvasWidth = maxWidth }
                if (canvasHeight > maxHeight) { canvasWidth = canvasWidth * maxHeight / canvasHeight; canvasHeight = maxHeight }

                this.cropCanvasWidth = canvasWidth
                this.cropCanvasHeight = canvasHeight
                const safeCanvasWidth = canvasWidth || 1
                const safeCanvasHeight = canvasHeight || 1
                this.cropScaleX = res2.width / safeCanvasWidth
                this.cropScaleY = res2.height / safeCanvasHeight

                this.$nextTick(() => { this.drawCropCanvas() })
              },
              fail: () => {
                uni.showToast({ title: '无法加载图片', icon: 'error' })
                this.closeCropperModal()
              }
            })
          } catch (e) {
            uni.showToast({ title: '无法加载图片', icon: 'error' })
            this.closeCropperModal()
          }
        }
      })
    },

    drawCropCanvas() {
      if (!this.showCropModal) return
      const ctx = uni.createCanvasContext('cropCanvas', this)
      ctx.clearRect(0, 0, this.cropCanvasWidth, this.cropCanvasHeight)
      ctx.drawImage(this.originalImage, 0, 0, this.cropCanvasWidth, this.cropCanvasHeight)

      if (this.cropRect && this.cropRect.width > 0 && this.cropRect.height > 0) {
        ctx.setFillStyle('rgba(82, 102, 191, 0.2)')
        ctx.fillRect(this.cropRect.x, this.cropRect.y, this.cropRect.width, this.cropRect.height)
        ctx.setStrokeStyle('#7c8ae5')
        ctx.setLineWidth(2)
        ctx.strokeRect(this.cropRect.x, this.cropRect.y, this.cropRect.width, this.cropRect.height)
      }

      ctx.draw()
    },

    onCropTouchStart(e) {
      const touch = e.touches[0]
      const point = {
        x: this.clamp(touch.x, 0, this.cropCanvasWidth),
        y: this.clamp(touch.y, 0, this.cropCanvasHeight)
      }

      if (this.cropRect && this.isPointInRect(point, this.cropRect)) {
        this.cropMode = 'move'
        this.cropMoveStart = point
        this.cropMoveRect = { ...this.cropRect }
      } else {
        this.cropMode = 'draw'
        this.cropStartPoint = point
        this.cropRect = {
          x: point.x,
          y: point.y,
          width: 0,
          height: 0
        }
      }

      this.isCropping = true
      this.drawCropCanvas()
    },

    onCropTouchMove(e) {
      if (!this.isCropping || !this.cropRect) return
      const touch = e.touches[0]
      const point = {
        x: this.clamp(touch.x, 0, this.cropCanvasWidth),
        y: this.clamp(touch.y, 0, this.cropCanvasHeight)
      }

      if (this.cropMode === 'move' && this.cropMoveStart && this.cropMoveRect) {
        const deltaX = point.x - this.cropMoveStart.x
        const deltaY = point.y - this.cropMoveStart.y
        const newX = this.clamp(
          this.cropMoveRect.x + deltaX,
          0,
          this.cropCanvasWidth - this.cropRect.width
        )
        const newY = this.clamp(
          this.cropMoveRect.y + deltaY,
          0,
          this.cropCanvasHeight - this.cropRect.height
        )
        this.cropRect = {
          ...this.cropRect,
          x: newX,
          y: newY
        }
      } else if (this.cropMode === 'draw' && this.cropStartPoint) {
        const startX = this.cropStartPoint.x
        const startY = this.cropStartPoint.y

        const rectX = Math.min(startX, point.x)
        const rectY = Math.min(startY, point.y)
        const rectWidth = Math.abs(point.x - startX)
        const rectHeight = Math.abs(point.y - startY)

        this.cropRect = {
          x: rectX,
          y: rectY,
          width: rectWidth,
          height: rectHeight
        }
      }

      this.drawCropCanvas()
    },

    onCropTouchEnd() {
      this.isCropping = false
      this.cropMode = 'idle'
      this.cropMoveStart = null
      this.cropMoveRect = null
    },

    resetCropSelection() {
      this.cropRect = null
      this.cropMode = 'idle'
      this.cropMoveStart = null
      this.cropMoveRect = null
      this.cropStartPoint = null
      this.drawCropCanvas()
    },

    isPointInRect(point, rect) {
      return (
        point.x >= rect.x &&
        point.x <= rect.x + rect.width &&
        point.y >= rect.y &&
        point.y <= rect.y + rect.height
      )
    },

    clamp(value, min, max) {
      if (value < min) return min
      if (value > max) return max
      return value
    },

    confirmCropSelection() {
      if (!this.cropRect || this.cropRect.width < 10 || this.cropRect.height < 10) {
        uni.showToast({
          title: '请框选物体区域',
          icon: 'none'
        })
        return
      }

      uni.canvasToTempFilePath({
        canvasId: 'cropCanvas',
        x: this.cropRect.x,
        y: this.cropRect.y,
        width: this.cropRect.width,
        height: this.cropRect.height,
        destWidth: Math.max(1, Math.round(this.cropRect.width * this.cropScaleX)),
        destHeight: Math.max(1, Math.round(this.cropRect.height * this.cropScaleY)),
        quality: 1,
        success: (res) => {
          this.croppedImage = res.tempFilePath
          this.cropPreviewImage = res.tempFilePath
          this.lastCropRatio = this.cropCanvasWidth > 0 && this.cropCanvasHeight > 0 ? {
            x: this.cropRect.x / this.cropCanvasWidth,
            y: this.cropRect.y / this.cropCanvasHeight,
            width: this.cropRect.width / this.cropCanvasWidth,
            height: this.cropRect.height / this.cropCanvasHeight
          } : null
          this.recognitionResults = []
          this.closeCropperModal()
          uni.showToast({
            title: '已选取物体',
            icon: 'success'
          })
        },
        fail: (err) => {
          console.error('截取物体失败:', err)
          uni.showToast({
            title: '截取失败，请重试',
            icon: 'error'
          })
        }
      })
    },

    // 分析图片
    async analyzeImage() {
      if (!this.selectedImage) return
      if (!this.croppedImage) {
        uni.showToast({
          title: '请先选取物体区域',
          icon: 'none'
        })
        return
      }

      this.loading = true
      /* uni.showLoading({
        title: '识别中...'
      })*/

      try {
        const result = await request.uploadImage(this.croppedImage)
        this.recognitionResults = this.formatRecognitionObjects(result.objects || [])
        this.descriptions = (result.descriptions || {})
        // 识别完成后，默认回到中文展示
        this.activeDescLang = 'zh'

        if (this.recognitionResults.length > 0) {
          // 使用 $nextTick 确保 DOM 更新完成后再绘制Canvas
          this.$nextTick(() => {
            setTimeout(() => {
              this.drawImageWithBounds()
            }, 100)
          })
          uni.showToast({
            title: `识别到 ${this.recognitionResults.length} 个物体`,
            icon: 'success'
          })
        } else {
          uni.showToast({
            title: '未识别到物体',
            icon: 'none'
          })
        }
        // 保存本次识别到历史
        this.saveRecognitionToHistory()
      } catch (error) {
        console.error('识别失败:', error)
        uni.showToast({
          title: '识别失败，请重试',
          icon: 'error'
        })
      } finally {
        this.loading = false
        /* uni.hideLoading() */
      }
    },

    // 在画布上绘制图片
    drawImageWithBounds() {
      // 确保Canvas在DOM中已经渲染
      this.$nextTick(() => {
        const targetImage = this.resultDisplayImage
        if (!targetImage) {
          console.warn('暂无可绘制的图片资源')
          return
        }
        // 获取图片信息
        uni.getImageInfo({
          src: targetImage,
          success: (res) => {
            this.imageWidth = res.width
            this.imageHeight = res.height

            // 计算画布尺寸，固定为更扁平的16:9区域
            const systemInfo = uni.getSystemInfoSync()
            const availableWidth = Math.max(80, systemInfo.windowWidth - 80)
            const limitedWidth = Math.min(availableWidth, 640)
            const canvasWidth = Math.max(80, Math.floor(limitedWidth))
            const canvasHeight = Math.max(100, Math.floor(canvasWidth * 9 / 16))

            this.canvasWidth = canvasWidth
            this.canvasHeight = canvasHeight

            const safeImageWidth = Math.max(1, this.imageWidth)
            const safeImageHeight = Math.max(1, this.imageHeight)

            const drawScale = Math.min(
              canvasWidth / safeImageWidth,
              canvasHeight / safeImageHeight
            )
            const drawWidth = safeImageWidth * drawScale
            const drawHeight = safeImageHeight * drawScale
            const offsetX = (canvasWidth - drawWidth) / 2
            const offsetY = (canvasHeight - drawHeight) / 2

            this.canvasDrawWidth = drawWidth
            this.canvasDrawHeight = drawHeight
            this.canvasDrawOffsetX = offsetX
            this.canvasDrawOffsetY = offsetY

            // 等待Canvas尺寸更新完成后再绘制
            this.$nextTick(() => {
              setTimeout(() => {
                this.drawOnCanvas()
              }, 300) // 增加延迟确保Canvas完全准备好
            })
          },
          fail: (err) => {
            console.error('获取图片信息失败:', err)
            // 如果Canvas失败，仍然显示识别结果列表
            this.showRecognitionList()
          }
        })
      })
    },

    // 分离Canvas绘制逻辑
    drawOnCanvas() {
      try {
        const ctx = uni.createCanvasContext('imageCanvas', this)

        if (!ctx) {
          console.error('Canvas上下文创建失败')
          return
        }

        // 清空画布
        ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight)

        const drawWidth = this.canvasDrawWidth || this.canvasWidth
        const drawHeight = this.canvasDrawHeight || this.canvasHeight
        const offsetX = this.canvasDrawOffsetX || 0
        const offsetY = this.canvasDrawOffsetY || 0

        const sourceImage = this.resultDisplayImage
        if (!sourceImage) {
          console.warn('未找到绘制所需的图片资源')
          return
        }
        // 绘制图片，增加错误处理
        ctx.drawImage(sourceImage, offsetX, offsetY, drawWidth, drawHeight)

        // 绘制边界框和角标
        const safeImageWidth = Math.max(1, this.imageWidth)
        const safeImageHeight = Math.max(1, this.imageHeight)
        const scaleX = drawWidth / safeImageWidth
        const scaleY = drawHeight / safeImageHeight

        this.recognitionResults.forEach((obj, index) => {
          const location = obj.location || { left: 0, top: 0, width: 100, height: 100 }
          const left = Math.max(0, Number(location.left) || 0)
          const top = Math.max(0, Number(location.top) || 0)
          const boxWidth = Math.max(1, Number(location.width) || 0)
          const boxHeight = Math.max(1, Number(location.height) || 0)

          const x = offsetX + left * scaleX
          const y = offsetY + top * scaleY
          const width = Math.max(
            10,
            Math.min(drawWidth - (x - offsetX), boxWidth * scaleX)
          )
          const height = Math.max(
            10,
            Math.min(drawHeight - (y - offsetY), boxHeight * scaleY)
          )

          // 只绘制角标，不绘制边界框
          const labelNumber = index + 1
          const circleX = x + 10
          const circleY = y + 10
          const radius = 10

          // 绘制白色圆圈背景
          ctx.setFillStyle('rgba(255,255,255,0)')
          ctx.beginPath()
          ctx.arc(circleX, circleY, radius, 0, 2 * Math.PI)
          ctx.fill()

          // 绘制红色圆圈边框
          ctx.setStrokeStyle('rgba(255,0,0,0.4)')
          ctx.setLineWidth(2)
          ctx.beginPath()
          ctx.arc(circleX, circleY, radius, 0, 2 * Math.PI)
          ctx.stroke()

          // 绘制角标数字
          ctx.setFillStyle('#ff0000')
          ctx.setFontSize(16)
          ctx.setTextAlign('center')
          ctx.setTextBaseline('middle')
          ctx.fillText(labelNumber.toString(), circleX, circleY)
        })

        // 执行绘制并添加回调确认
        ctx.draw(false, () => {
          console.log('Canvas绘制完成')
        })

      } catch (error) {
        console.error('Canvas绘制错误:', error)
        this.showRecognitionList()
      }
    },

    // 显示识别结果列表（Canvas的备用方案）
    showRecognitionList() {
      // 这里可以显示一个简单的列表而不是Canvas
      console.log('识别结果:', this.recognitionResults)
    },

    // 处理画布点击
    onCanvasTouch(e) {
      const touch =
        (e.changedTouches && e.changedTouches[0]) ||
        (e.touches && e.touches[0])

      if (!touch) return
      const offsetX = this.canvasDrawOffsetX || 0
      const offsetY = this.canvasDrawOffsetY || 0
      const drawWidth = this.canvasDrawWidth || this.canvasWidth
      const drawHeight = this.canvasDrawHeight || this.canvasHeight

      const withinX = touch.x >= offsetX && touch.x <= offsetX + drawWidth
      const withinY = touch.y >= offsetY && touch.y <= offsetY + drawHeight

      if (!withinX || !withinY) return

      const scaleX = this.imageWidth / Math.max(1, drawWidth)
      const scaleY = this.imageHeight / Math.max(1, drawHeight)

      const clickX = (touch.x - offsetX) * scaleX
      const clickY = (touch.y - offsetY) * scaleY

      // 检查是否点击在物体边界框内
      let clickedOnObject = false

      // 查找点击的物体
      for (let obj of this.recognitionResults) {
        const location = obj.location
        if (!location) continue
        const left = Math.max(0, Number(location.left) || 0)
        const top = Math.max(0, Number(location.top) || 0)
        const width = Math.max(1, Number(location.width) || 0)
        const height = Math.max(1, Number(location.height) || 0)
        if (
          clickX >= left &&
          clickX <= left + width &&
          clickY >= top &&
          clickY <= top + height
        ) {
          clickedOnObject = true
          break
        }
      }

      // 如果没有点击在物体上，则显示图片预览
      if (!clickedOnObject) return
    },

    // 列表：判断是否已收藏
    isItemFavorited(obj) {
      const zh = (obj && obj.names && obj.names.zh) || (obj && obj.keyword) || ''
      const favorites = storage.getFavorites()
      return favorites.some(f => f && f.name && f.name.zh === zh)
    },

      // 列表：添加收藏
    addFavoriteFromList(obj) {
  if (!obj) return
  const zh = (obj.names && obj.names.zh) || obj.keyword || ''
  const en = (obj.names && obj.names.en) || 'Unknown Object'
  const jp = (obj.names && (obj.names.ja || obj.names.jp)) || '不明な物体'
  const favorites = storage.getFavorites()
  const exist = favorites.find(f => f && f.name && f.name.zh === zh)
  if (exist) {
    const ok = storage.removeFavorite(exist.id)
    if (ok) {
      if (this.$set) this.$set(obj, '_favorited', false); else obj._favorited = false
      uni.showToast({ title: '已取消收藏', icon: 'none' })
    } else {
      uni.showToast({ title: '取消失败', icon: 'none' })
    }
    return
  }
  const success = storage.addFavorite({ name: { zh, en, jp } })
  if (success) {
    if (this.$set) this.$set(obj, '_favorited', true); else obj._favorited = true
    uni.showToast({ title: '已收藏', icon: 'success' })
  } else {
    uni.showToast({ title: '已收藏过', icon: 'none' })
  }
},

    // 列表：复制三语
    copyItem(obj) {
      if (!obj) return
      const zh = (obj.names && obj.names.zh) || obj.keyword || ''
      const en = (obj.names && obj.names.en) || ''
      const jp = (obj.names && (obj.names.ja || obj.names.jp)) || ''
      const text = `中文：${zh}\n英文：${en}\n日文：${jp}`
      uni.setClipboardData({
        data: text,
        success: () => { uni.showToast({ title: '已复制', icon: 'success' }) },
        fail: () => { uni.showToast({ title: '复制失败', icon: 'none' }) }
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

.header-actions.absolute {
  position: absolute;
  top: 100rpx;
  right: 26rpx;
  display: flex;
  gap: 16rpx;
  z-index: 10;
}
.action-btn {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  background: rgba(255,255,255,0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6rpx 14rpx rgba(0,0,0,0.12);
}
.action-btn.disabled { opacity: 0.45; }
.action-icon { font-size: 50rpx; }

/* 历史记录弹窗 */
.history-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}
.history-panel {
  width: 86vw;
  max-width: 700rpx;
  max-height: 70vh;
  background: rgba(255,255,255,0.92);
  border-radius: 16rpx;
  overflow: hidden;
  box-shadow: 0 10rpx 30rpx rgba(0,0,0,0.18);
}
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20rpx 24rpx;
  border-bottom: 1rpx solid rgba(0,0,0,0.06);
}
.history-title { font-size: 32rpx; font-weight: 700; }
.history-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12rpx;
  padding: 16rpx;
  overflow-y: auto;
  max-height: 58vh;
}
.history-item {
  position: relative;
  border-radius: 12rpx;
  overflow: hidden;
  border: 1rpx solid rgba(0,0,0,0.06);
}
.history-thumb { width: 100%; height: 200rpx; }
.history-time {
  position: absolute;
  left: 8rpx;
  bottom: 8rpx;
  background: rgba(0,0,0,0.45);
  color: #fff;
  font-size: 22rpx;
  padding: 2rpx 6rpx;
  border-radius: 6rpx;
}
.history-del {
  position: absolute;
  top: 6rpx;
  right: 6rpx;
  width: 36rpx;
  height: 36rpx;
  border-radius: 18rpx;
  background: rgba(0,0,0,0.5);
  color: #fff;
  font-size: 28rpx;
  line-height: 36rpx;
  text-align: center;
}
.history-empty { padding: 40rpx; text-align: center; color: #666; }

/* 离屏画布（隐藏用于分享合成） */
.share-canvas {
  position: absolute;
  left: -9999px;
  top: -9999px;
  opacity: 0;
  pointer-events: none;
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
  font-size: 32rpx;
  color: #e0e7ff;
  margin-top: 25px;
  line-height: 1.3;
  letter-spacing: 0.5rpx;
  text-shadow: 0 3rpx 12rpx rgba(82, 102, 191, 0.35);
}

.upload-section {
  background: transparent;
  border-radius: 20rpx;
  padding: 40rpx;
  margin-bottom: 40rpx;
  margin-top: 40px;
  box-shadow: none;
  border: none;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400rpx;
  border: 2rpx dashed rgba(165, 180, 252, 0.6);
  border-radius: 20rpx;
  background: transparent;
  position: relative;
  overflow: hidden;
  transition: border-color .2s ease, transform .12s ease, box-shadow .2s ease;
  -webkit-backdrop-filter: blur(8px) saturate(120%);
  backdrop-filter: blur(8px) saturate(120%);
  box-shadow: 0 12rpx 36rpx rgba(82, 102, 191, 0.30), 0 0 40rpx rgba(165, 180, 252, 0.25);
  outline: 1px solid rgba(255, 255, 255, 0.18);
  outline-offset: -1px;
}
.upload-placeholder::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(800rpx 400rpx at 30% 20%, rgba(180, 200, 255, 0.18), transparent 60%);
  pointer-events: none;
}
.upload-placeholder::after {
  content: '';
  position: absolute;
  inset: 1px;
  border-radius: 18rpx;
  background: linear-gradient(180deg, rgba(255,255,255,0.22), rgba(255,255,255,0.04));
  pointer-events: none;
}
@media (hover:hover) {
  .upload-placeholder:hover {
    border-color: rgba(165, 180, 252, 0.85);
    transform: translateY(-2rpx);
    box-shadow: 0 20rpx 48rpx rgba(82, 102, 191, 0.35), 0 0 54rpx rgba(165, 180, 252, 0.3);
  }
}
.upload-placeholder:active {
  transform: scale(.995);
}

.upload-icon {
  width: 80rpx;
  height: 80rpx;
  margin-bottom: 20rpx;
  opacity: .95;
  filter: drop-shadow(0 8rpx 20rpx rgba(82, 102, 191, 0.45));
}

.upload-text {
  font-size: 40rpx;
  color: #eef2ff;
  font-weight: 800;
  text-align: center;
  margin-top: -40px;
  text-shadow: 0 3rpx 12rpx rgba(82, 102, 191, 0.35);
}

.image-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20rpx;
}

.selected-image-frame {
  position: relative;
  width: 100%;
  max-width: 640rpx;
  border-radius: 16rpx;
  overflow: hidden;
  background: linear-gradient(135deg, #f5f7ff, #f0eaff);
  box-shadow: 0 6rpx 18rpx rgba(82, 102, 191, 0.15);
  margin-bottom: 16rpx;
}

.selected-image-frame::before {
  content: '';
  display: block;
  padding-top: 56.25%;
}

.selected-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.image-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 20rpx;
  justify-content: center;
  margin-top: 20rpx;
}

.crop-hint {
  margin-top: 16rpx;
  font-size: 26rpx;
  color: #6b7ae6;
  text-align: center;
}

.crop-preview {
  width: 100%;
  max-width: 640rpx;
  background: linear-gradient(135deg, #eef2ff, #ede9fe);
  border-radius: 16rpx;
  padding: 24rpx;
  box-shadow: 0 4rpx 12rpx rgba(82, 102, 191, 0.15);
}

.crop-preview-title {
  display: block;
  font-size: 28rpx;
  color: #6b7ae6;
  margin-bottom: 16rpx;
  text-align: center;
}

.crop-preview-frame {
  position: relative;
  width: 100%;
  border-radius: 12rpx;
  overflow: hidden;
  background: #fff7e6;
}

.crop-preview-frame::before {
  content: '';
  display: block;
  padding-top: 56.25%;
}

.crop-preview-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.btn-primary, .btn-secondary {
  padding: 20rpx 40rpx;
  border-radius: 10rpx;
  font-size: 28rpx;
  border: none;
}

.btn-primary {
  background: linear-gradient(135deg, #a3bffa, #b794f4);
  color: white;
  box-shadow: 0 4rpx 12rpx rgba(82, 102, 191, 0.3);
}

/* 禁用态：统一弱化并禁止交互 */
button[disabled], .btn-primary[disabled], .btn-secondary[disabled] {
  opacity: 0.6;
  filter: grayscale(20%);
  pointer-events: none;
}

.btn-secondary {
  background-color: #fff;
  color: #6b7ae6;
  border: 2rpx solid #a5b4fc;
}

.results-section {
  background: linear-gradient(135deg, #eef2ff, #ede9fe);
  border-radius: 20rpx;
  padding: 40rpx;
  box-shadow: 0 4rpx 16rpx rgba(82, 102, 191, 0.2);
  border: 2rpx solid #a5b4fc;
}

.section-title {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 30rpx;
}

.results-container {
  display: flex;
  justify-content: center;
  width: 100%;
}

.result-canvas-frame {
  padding: 16rpx;
  border-radius: 20rpx;
  background: linear-gradient(135deg, #f5f7ff, #f0eaff);
  box-shadow: 0 6rpx 18rpx rgba(82, 102, 191, 0.15);
  max-width: 100%;
  box-sizing: border-box;
}

.result-canvas {
  border: 1rpx solid #ddd;
  border-radius: 12rpx;
}

.objects-list {
  margin-top: 30rpx;
}

.descriptions-block {
  margin-top: 20rpx; /* 与物体识别详情项间距保持一致 */
  padding-top: 0;
  border-top: none;
}

.desc-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 20rpx;
}

/* 描述内容外框美化 */
.desc-card {
  margin-bottom: 20rpx;
  display: flex;
  align-items: flex-start; 
  gap: 20rpx;
  background: linear-gradient(135deg, #f5f7ff, #f0eaff);
  border: 1rpx solid #a5b4fc;
  border-radius: 15rpx; 
  box-shadow: 0 4rpx 12rpx rgba(82, 102, 191, 0.15);
  padding: 25rpx;
  transition: transform .12s ease, box-shadow .2s ease, background .2s ease;
}
.desc-card:active {
  transform: scale(0.98); 
  background: linear-gradient(135deg, #eaefff, #f3efff);
}
.desc-card .language-row { margin-bottom: 0; }

.list-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 20rpx;
}

.object-detail-item {
  background: linear-gradient(135deg, #f5f7ff, #f0eaff);
  border-radius: 15rpx;
  margin-bottom: 20rpx;
  box-shadow: 0 4rpx 12rpx rgba(82, 102, 191, 0.15);
  display: flex;
  padding: 25rpx;
  align-items: flex-start;
  border: 1rpx solid #a5b4fc;
  gap: 20rpx;
}

.object-detail-item:active {
  background: linear-gradient(135deg, #eaefff, #f3efff);
  transform: scale(0.98);
}

.object-number {
  width: 60rpx;
  height: 60rpx;
  background: linear-gradient(135deg, #a3bffa, #b794f4);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
  font-weight: bold;
  flex-shrink: 0;
  box-shadow: 0 2rpx 8rpx rgba(82, 102, 191, 0.3);
}

.object-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.language-row {
  display: flex;
  align-items: center;
  margin-bottom: 8rpx;
}

.lang-prefix {
  font-size: 24rpx;
  color: #666;
  width: 80rpx;
  flex-shrink: 0;
}

.lang-text {
  font-size: 26rpx;
  flex: 1;
}

.lang-text.zh {
  color: #333;
}

.lang-text.en {
  color: #333;
}

.lang-text.jp {
  color: #333;
}

.close-btn {
  font-size: 60rpx;
  color: #999;
  line-height: 1;
}

.language-item {
  display: flex;
  margin-bottom: 20rpx;
  align-items: flex-start;
}

.language-label {
  font-size: 28rpx;
  color: #666;
  width: 120rpx;
  flex-shrink: 0;
}

.language-text {
  font-size: 28rpx;
  color: #333;
  flex: 1;
}

.detail-actions {
  margin-top: 40rpx;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 20rpx;
}

.btn-favorite {
  background: linear-gradient(135deg, #a3bffa, #b794f4);
  color: white;
  padding: 20rpx 60rpx;
  border-radius: 50rpx;
  font-size: 28rpx;
  border: none;
  box-shadow: 0 4rpx 12rpx rgba(82, 102, 191, 0.3);
}

.image-source-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 999;
  display: flex;
  align-items: flex-end;
}

.image-source-options {
  background-color: #fff;
  border-radius: 20rpx 20rpx 0 0;
  width: 100%;
}

.option-item {
  padding: 40rpx;
  text-align: center;
  border-bottom: 1rpx solid #f0f0f0;
}

.option-item:last-child {
  border-bottom: none;
}

.option-item.cancel {
  color: #ff6b6b;
}

.option-text {
  font-size: 32rpx;
  color: #333;
}

.image-preview-container {
  background: linear-gradient(135deg, #eef2ff, #ede9fe);
  border-radius: 20rpx;
  width: 90%;
  max-width: 600rpx;
  max-height: 80%;
  overflow: hidden;
  border: 2rpx solid #a5b4fc;
  box-shadow: 0 8rpx 32rpx rgba(82, 102, 191, 0.3);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 30rpx;
  background: linear-gradient(135deg, #a3bffa, #b794f4);
  color: white;
}

.preview-title {
  font-size: 36rpx;
  font-weight: bold;
}

.preview-content {
  padding: 20rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  max-height: 400rpx;
  overflow: hidden;
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  border-radius: 10rpx;
}

.preview-actions {
  padding: 30rpx;
  text-align: center;
  background: linear-gradient(135deg, #eef2ff, #ede9fe);
}

.btn-preview {
  background: linear-gradient(135deg, #a3bffa, #b794f4);
  color: white;
  padding: 20rpx 60rpx;
  border-radius: 50rpx;
  font-size: 28rpx;
  border: none;
  box-shadow: 0 4rpx 12rpx rgba(82, 102, 191, 0.3);
}

.detail-image-wrapper {
  width: 100%;
  border-radius: 16rpx;
  overflow: hidden;
  margin-bottom: 24rpx;
  position: relative;
  background: #f5f7ff;
}

.detail-image-wrapper::before {
  content: '';
  display: block;
  padding-top: 56.25%;
}

.detail-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.cropper-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  z-index: 1001;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx;
}

.cropper-container {
  background: #fff;
  border-radius: 20rpx;
  width: 100%;
  max-width: 700rpx;
  overflow: hidden;
  box-shadow: 0 8rpx 32rpx rgba(0, 0, 0, 0.2);
}

.cropper-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 30rpx;
  background: linear-gradient(135deg, #a3bffa, #b794f4);
  color: #fff;
}

.cropper-tip {
  padding: 20rpx 30rpx 0;
  font-size: 26rpx;
  color: #666;
  line-height: 1.6;
}

.tip-line {
  display: block;
  margin-bottom: 8rpx;
}

.cropper-title {
  font-size: 32rpx;
  font-weight: bold;
}

.cropper-canvas-wrapper {
  padding: 30rpx;
  display: flex;
  justify-content: center;
  align-items: center;
}

.crop-canvas {
  background-color: #f4f4f4;
  border-radius: 12rpx;
}

.cropper-actions {
  display: flex;
  justify-content: flex-end;
  gap: 20rpx;
  padding: 20rpx 30rpx 30rpx;
}
/* 使页面内容位于粒子背景之上 */
.header,
.favorites-list,
.loading-state,
.empty-state,
.detail-modal-overlay,
.upload-section,
.results-section{
  position: relative;
  z-index: 1;
}

/* 辅助文案与类型徽章 */
.upload-subtext {
  font-size: 26rpx;
  color: #e0e7ff;
  margin-top: 12rpx;
}
.upload-badges {
  margin-top: 16rpx;
  display: flex;
  gap: 12rpx;
}
.badge {
  font-size: 22rpx;
  color: #eef2ff;
  background: rgba(255, 255, 255, 0.12);
  border: 1rpx solid rgba(255, 255, 255, 0.35);
  border-radius: 999rpx;
  padding: 8rpx 16rpx;
}

/* 识别结果计数徽标与标题容器 */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 30rpx;
}
.count-badge {
  font-size: 24rpx;
  color: #6b7ae6;
  background: #fff;
  border: 2rpx solid #a5b4fc;
  border-radius: 999rpx;
  padding: 6rpx 16rpx;
  line-height: 1;
}

/* 加载骨架屏 */
.skeleton-section {
  margin: 30rpx 0 40rpx;
}
.skeleton-card {
  height: 84rpx;
  border-radius: 14rpx;
  background: linear-gradient(90deg,
    rgba(255,255,255,0.15) 25%,
    rgba(255,255,255,0.25) 37%,
    rgba(255,255,255,0.15) 63%
  );
  background-size: 400% 100%;
  animation: shimmer 1.2s ease-in-out infinite;
  margin-bottom: 18rpx;
}
.skeleton-card.short { width: 70%; }
@keyframes shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}

/* 按钮禁用与按压态 */
.btn-primary[disabled], .btn-secondary[disabled], .is-disabled {
  opacity: .6;
  filter: grayscale(.1);
}
.btn-primary:active, .btn-secondary:active {
  transform: translateY(1rpx);
}

/* 弹层毛玻璃与入场动画 */
.image-source-modal,
.cropper-modal {
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
}

@keyframes popIn {
  0% { transform: translateY(20rpx) scale(.98); opacity: .5; }
  100% { transform: translateY(0) scale(1); opacity: 1; }
}

/* 加载时全局点击拦截遮罩 */
.global-click-blocker {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 2000; /* 高于各类弹层 */
  background: rgba(0,0,0,0); /* 透明，不影响视觉 */
  pointer-events: auto; /* 确保可拦截点击 */
}

/* 识别结果项右侧操作区 */
.object-actions {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-left: 10rpx;
}
.icon-button {
  width: 88rpx;
  height: 88rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 56rpx;
  color: #6b7ae6;
}
.icon-star {
  width: 88rpx;
  height: 88rpx;
}
.icon-copy {
  width: 88rpx;
  height: 88rpx;
}
/* 现代加载遮罩（毛玻璃 + 圆环 + 三点跳动）*/
.modern-loading-overlay {
  position: fixed;
  top: 0; right: 0; bottom: 0; left: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(10, 15, 35, 0.45);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}
.loading-card {
  width: 560rpx;
  max-width: 86vw;
  padding: 48rpx 40rpx;
  border-radius: 28rpx;
  background: linear-gradient(180deg, rgba(255,255,255,0.14), rgba(255,255,255,0.08));
  border: 1rpx solid rgba(255,255,255,0.28);
  box-shadow: 0 12rpx 60rpx rgba(0,0,0,0.35), inset 0 1rpx 0 rgba(255,255,255,0.12);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16rpx;
  position: relative;
  overflow: hidden;
}
.loading-card::before {
  content: '';
  position: absolute;
  inset: -40rpx;
  background:
    radial-gradient(120rpx 120rpx at 20% 10%, rgba(120,130,255,0.35), transparent 60%),
    radial-gradient(160rpx 160rpx at 80% 90%, rgba(67,230,255,0.25), transparent 60%);
  filter: blur(12rpx);
  z-index: 0;
}
.spinner-ring {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  border: 10rpx solid rgba(255,255,255,0.18);
  border-top-color: #a5b4fc;
  border-right-color: #60a5fa;
  animation: spin 1s linear infinite;
  box-shadow: inset 0 0 0 1rpx rgba(255,255,255,0.06);
}
@keyframes spin { to { transform: rotate(360deg); } }

.loading-title {
  margin-top: 12rpx;
  font-size: 36rpx;
  font-weight: 600;
  letter-spacing: 1rpx;
  color: #ffffff;
  z-index: 1;
}
.loading-dots {
  display: inline-flex;
  gap: 12rpx;
  margin: 4rpx 0 6rpx;
  z-index: 1;
}
.loading-dots .dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 999rpx;
  background: linear-gradient(90deg, #a5b4fc, #60a5fa);
  animation: dotBounce 1.2s ease-in-out infinite;
}
.loading-dots .dot:nth-child(2) { animation-delay: 0.15s; }
.loading-dots .dot:nth-child(3) { animation-delay: 0.30s; }
@keyframes dotBounce {
  0%, 80%, 100% { transform: translateY(0); opacity: .6; }
  40% { transform: translateY(-10rpx); opacity: 1; }
}
.loading-sub {
  font-size: 24rpx;
  color: rgba(255,255,255,0.85);
  z-index: 1;
}

/* 选取预览内的局部加载遮罩 */
.preview-loading-overlay {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(10, 15, 35, 0.25);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  z-index: 2;
}
.loading-card.compact {
  width: 70%;
  max-width: 420rpx;
  padding: 28rpx 24rpx;
  border-radius: 20rpx;
}
.spinner-ring.small {
  width: 72rpx;
  height: 72rpx;
  border-width: 8rpx;
}
/* 描述高亮：与页面视觉保持一致 */
.desc-seg { display: inline; }
.hl-word {
  font-weight: 700;
  padding: 0 6rpx;
  border-radius: 6rpx;
  background: rgba(255, 255, 255, 0.22);
  box-shadow: inset 0 1rpx 0 rgba(255,255,255,0.35);
}
.hl-1 { color: #ff4d4f; } /* 红 */
.hl-2 { color: #fa8c16; } /* 橙 */
.hl-3 { color: #fadb14; } /* 黄 */
.hl-4 { color: #52c41a; } /* 绿 */
.hl-5 { color: #13c2c2; } /* 青 */
.hl-6 { color: #1890ff; } /* 蓝 */
.hl-7 { color: #722ed1; } /* 紫 */

.blank-line {
  height: 20rpx; /* 控制空白高度 */
}
</style>
