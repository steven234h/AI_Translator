# AI识图学习APP

AI识图学习APP 是一个结合 uni-app 与 FastAPI 的多模态识图学习项目，支持相册/拍照上传图片，由后台调用 ModelScope Qwen 系列模型输出中文/英文/日文释义，并可收藏生词方便复习。

## 核心功能

- 图片采集：相册与拍照双入口，单张图片最大 10MB，支持 jpg/png/bmp。
- 多语言识别：后端统一调用模型，输出中文/英文/日文名称、释义与推荐类别。
- 标注展示：前端使用 Canvas 根据 `left/top/width/height` 渲染框选并联动词卡。
- 生词收藏：本地 `uni.setStorage` 存储收藏记录，支持查看与删除。
- 调试能力：`/` 与 `/docs` 提供健康检查与 Swagger 文档，便于联调。

## 技术栈与第三方

- 后端：Python 3.8+、FastAPI、httpx、Pillow、Uvicorn。
- AI 服务：ModelScope Inference API（可分别指定视觉/翻译/定义模型 ID）。
- 前端：uni-app（Vue 语法）、Canvas、localStorage、HBuilderX。
- 工具：pip、npm/HBuilderX

## 目录结构

```
AI_Translator/
├─backend/
│  ├─main.py                  # FastAPI 入口
│  ├─services/
│  │  ├─modelscope_qwen_fast.py
│  │  └─modelscope_qwen.py
│  ├─requirements.txt
│  ├─.env             # 环境变量
├─frontend/
│  ├─pages/
│  ├─utils/、static/
│  ├─manifest.json、pages.json
│  ├─App.vue、main.js、package.json
└─README.md
```

## 环境要求

- Python ≥ 3.8，pip 可用。
- Node.js ≥ 14（仅前端构建/调试需要）。
- 操作系统：Windows / macOS / Linux。
- HBuilderX（推荐调试与原生打包），或任意支持 uni-app 的工具链。

## 启动前准备（API 相关需在启动时传入）

1. 在 [ModelScope 控制台](https://www.modelscope.cn/)生成 API Key，并确认推理接口 Base URL 与模型 ID。
2. **每次启动后端前都要通过环境变量显式传入**：

   ```powershell
   # Windows PowerShell
   $env:MODELSCOPE_API_KEY = "ms-xxxxxxxx"
   $env:MODELSCOPE_BASE_URL = "https://api-inference.modelscope.cn/v1"
   $env:MODELSCOPE_MODEL = "AI模型"
   python main.py
   ```

   ```bash
   # macOS / Linux
   export MODELSCOPE_API_KEY=ms-xxxxxxxx
   export MODELSCOPE_BASE_URL=https://api-inference.modelscope.cn/v1
   export MODELSCOPE_MODEL=AI模型
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. 也可以直接将配置写入 `backend/.env`。

## 快速启动

### 后端（FastAPI）

```bash
cd backend
pip install -r requirements.txt
python main.py
```

### 前端（uni-app）

- **HBuilderX**
  1. 安装 HBuilderX 并打开 `frontend` 目录。
  2. 选择运行目标（Chrome、H5、Android 模拟器等）即可实时预览，也可以进行app云打包。
