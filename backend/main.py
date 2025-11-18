from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import base64
import io
import asyncio
from PIL import Image, ImageOps
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

from services.modelscope_qwen_fast import ModelScopeQwenService

load_dotenv()

app = FastAPI(title="多语言学习APP", description="物体识别与翻译API", version="1.0.0")

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
qwen_service = ModelScopeQwenService(
    api_key=os.getenv("MODELSCOPE_API_KEY"),
    base_url=os.getenv("MODELSCOPE_BASE_URL"),
    # 兼容旧环境变量；若未提供，将在服务内回退到Qwen3
    model_vision=os.getenv("MODELSCOPE_MODEL_VISION") or os.getenv("MODELSCOPE_MODEL"),
    model_translation=os.getenv("MODELSCOPE_MODEL_TRANSLATION") or os.getenv("MODELSCOPE_MODEL"),
    model_definition=os.getenv("MODELSCOPE_MODEL_DEFINITION") or os.getenv("MODELSCOPE_MODEL")
)


async def _preprocess_image(contents: bytes, max_side: int = 1280, quality: int = 85) -> str:
    """图片预处理：EXIF 方向纠正、尺寸限制、JPEG 压缩并返回 Base64 字符串"""
    def _work() -> str:
        with Image.open(io.BytesIO(contents)) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            w, h = img.size
            max_wh = max(w, h)
            if max_wh > max_side:
                scale = max_side / float(max_wh)
                new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
                img = img.resize(new_size, Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            return base64.b64encode(buf.getvalue()).decode("utf-8")

    return await asyncio.to_thread(_work)

@app.post("/api/detect")
async def detect_objects(file: UploadFile = File(...)):
    """
    物体识别接口
    """
    try:
        # 检查文件大小 (10MB)
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小超过10MB限制")

        # 检查文件格式
        try:
            image = Image.open(io.BytesIO(contents))
            image.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="不支持的图片格式")

        # 图片预处理后再转base64（降低带宽与推理耗时）
        base64_image = await _preprocess_image(contents)

        # 使用统一模型一次性完成识别+三语名称+释义+三语描述句
        result = await qwen_service.analyze_image_multilingual(base64_image)
        # 直接返回标准化后的结构，包含 objects 与 sentences
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@app.get("/")
async def root():
    return {"message": "多语言学习APP API服务运行正常"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# 优雅关闭：回收HTTP连接
@app.on_event("shutdown")
async def _on_shutdown():
    try:
        await qwen_service.aclose()
    except Exception:
        pass