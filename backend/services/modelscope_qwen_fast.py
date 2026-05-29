# -*- coding: utf-8 -*-
import json
import asyncio
import time
import hashlib
import logging
import os
import platform
import sys
from typing import Dict, Any, List

import httpx


logger = logging.getLogger(__name__)


def _setup_logger_once() -> None:
    """确保有一个合理的控制台日志输出配置（UTF-8）。
    - 默认级别为 DEBUG，可通过环境变量 LOG_LEVEL 覆盖
    - 若外部已经配置了 handler，则不重复添加
    """
    if logger.handlers:
        return
    level_name = os.getenv("LOG_LEVEL", "DEBUG").upper()
    level = getattr(logging, level_name, logging.DEBUG)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    fmt = "%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)


_setup_logger_once()


class ModelScopeQwenService:
    def __init__(self, api_key: str, base_url: str,
                 model_vision: str | None = None,
                 model_translation: str | None = None,
                 model_definition: str | None = None):
        self.api_key = api_key
        self.base_url = (base_url or '').rstrip('/')
        # 模型配置
        self.model_vision = model_vision
        self.model_translation = model_translation
        self.model_definition = model_definition

        # 连接池与并发控制
        self._client: httpx.AsyncClient | None = None
        self._sem = asyncio.Semaphore(10)

        # 内存缓存: key -> (ts, result)
        self._cache: dict[str, tuple[float, Dict[str, Any]]] = {}
        self._cache_ttl_seconds = 600

        # 启动时记录关键环境与参数（脱敏）
        try:
            masked_key = None
            if isinstance(self.api_key, str) and len(self.api_key) > 8:
                masked_key = f"{self.api_key[:4]}***{self.api_key[-4:]}"
            elif self.api_key:
                masked_key = "***"
            logger.info(
                "ModelScopeQwenService 初始化 | base_url=%s | vision=%s | translation=%s | definition=%s | api_key=%s",
                self.base_url, self.model_vision, self.model_translation, self.model_definition, masked_key,
            )
            logger.debug(
                "运行环境 | python=%s | platform=%s | httpx=%s | pid=%s",
                sys.version.split()[0], platform.platform(), getattr(httpx, "__version__", "?"), os.getpid()
            )
            for k in [
                "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "CUDA_VISIBLE_DEVICES", "MODELSCOPE_BASE_URL",
                "MODELSCOPE_MODEL", "MODELSCOPE_MODEL_VISION", "MODELSCOPE_MODEL_TRANSLATION", "MODELSCOPE_MODEL_DEFINITION"
            ]:
                if os.getenv(k) is not None:
                    logger.debug("ENV %s=%s", k, os.getenv(k))
        except Exception:
            logger.debug("初始化日志记录时发生非致命异常", exc_info=True)

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
            logger.debug(
                "创建 httpx.AsyncClient | base_url=%s | timeout(connect=10, read=110, total=120) | limits=%s",
                self.base_url, limits
            )
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(120.0, connect=10.0, read=110.0),
                limits=limits
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            logger.debug("关闭 httpx.AsyncClient")
            await self._client.aclose()
            self._client = None

    async def _make_request_async(self, messages: List[Dict], max_tokens: int = 1200, model: str | None = None) -> str:
        """调用 ModelScope API（异步，带详细日志）。"""
        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1
        }

        # 日志化请求摘要（不打印图片内容）
        try:
            images = 0
            texts = 0
            for m in messages:
                for c in m.get("content", []):
                    if c.get("type") == "image_url":
                        images += 1
                    elif c.get("type") == "text":
                        texts += 1
            logger.debug(
                "准备请求 ModelScope | model=%s | messages(text=%d, image=%d) | max_tokens=%d",
                model, texts, images, max_tokens
            )
        except Exception:
            logger.debug("统计消息摘要失败（非致命）", exc_info=True)

        client = self._ensure_client()
        async with self._sem:
            t0 = time.time()
            try:
                resp = await client.post('/chat/completions', json=data)
                dt = time.time() - t0
                logger.debug(
                    "HTTP 响应 | status=%d | elapsed=%.3fs",
                    resp.status_code, dt
                )
                if resp.status_code != 200:
                    text = await resp.aread()
                    preview = text[:2048]
                    logger.error(
                        "ModelScope 非 200 状态 | status=%d | body(截断)= %r",
                        resp.status_code, preview
                    )
                    raise Exception(f"ModelScope API 状态码 {resp.status_code}")

                result = resp.json()
                logger.debug("API 原始 JSON 键: %s", list(result.keys()))
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    logger.debug("API choices[0].message.content 长度: %d", len(content) if isinstance(content, str) else -1)
                    return content
                if 'error' in result:
                    logger.error("ModelScope API 返回错误字段: %s", result.get('error'))
                    raise Exception(f"ModelScope API 返回错误: {result['error']}")
                logger.error("ModelScope API 返回格式异常: %s", result)
                raise Exception("ModelScope API 返回格式异常")
            except Exception:
                logger.exception("调用 ModelScope 请求异常")
                raise

    async def analyze_image_multilingual(self, base64_image: str, max_objects: int = 3) -> Dict[str, Any]:
        """
        一次完成：
        - 识别主要物体（名称多语言 + 位置）
        - 生成图片描述（中/英/日）
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "你是视觉理解与多语描述专家。识别图片中最多"
                            f"{max_objects}个重要物体，并返回：\n"
                            "- 名称多语言：zh,en,ja（ja为日语）\n"
                            "- 位置：location 必须是对象，且只包含 left,top,width,height 四个整数像素字段\n"
                            "- 图片描述：zh,en,ja 各用一短句（10-20字），基于识别结果生成\n\n"
                            "仅返回有效JSON，不要任何解释或标记。\n\n"
                            "禁止把位置写成数组或简写，禁止写成 {\"left\":10,10,780,900}。\n"
                            "示例：{\n  \"objects\": [{\n    \"names\":{\"zh\":\"苹果\",\"en\":\"apple\",\"ja\":\"リンゴ\"},\n    \"location\":{\"left\":100,\"top\":150,\"width\":80,\"height\":90}\n  }],\n  \"descriptions\":{\"zh\":\"一句中文描述\",\"en\":\"one English sentence\",\"ja\":\"1文の日本語説明\"}\n}"
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ]

        try:
            # 输入摘要日志（仅长度，避免暴露图片内容）
            try:
                logger.info("开始图像多语言分析 | max_objects=%d | image_b64_len=%d", max_objects, len(base64_image) if base64_image else 0)
            except Exception:
                logger.debug("记录输入摘要失败（非致命）", exc_info=True)

            # 同图去重缓存
            cache_key = hashlib.sha256(base64_image.encode('utf-8')).hexdigest() + f"|{max_objects}|{self.model_vision}"
            now = time.time()
            cached = self._cache.get(cache_key)
            if cached and (now - cached[0] < self._cache_ttl_seconds):
                logger.debug("缓存命中 | key=%s | age=%.1fs", cache_key[:12], now - cached[0])
                return cached[1]

            response_text = await self._make_request_async(
                messages,
                max_tokens=1200,
                model=self.model_vision
            )

            logger.debug("模型原始响应长度: %d", len(response_text) if isinstance(response_text, str) else -1)

            # 清理可能的markdown包裹
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            elif response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            logger.debug("去除 markdown 包裹后的响应预览: %r", response_text[:512])

            # 解析JSON
            result = json.loads(response_text)
            logger.debug("解析后的 JSON 键: %s", list(result.keys()))

            # 标准化输出
            standardized_result: Dict[str, Any] = {
                'objects': [],
                'descriptions': result.get('descriptions', {
                    'zh': '图片内容',
                    'en': 'Image content',
                    'ja': '画像の内容'
                })
            }

            for obj in result.get('objects', []):
                if isinstance(obj, dict) and 'names' in obj:
                    location = obj.get('location', {})
                    location = {
                        'left': max(0, int(location.get('left', 0) or 0)),
                        'top': max(0, int(location.get('top', 0) or 0)),
                        'width': max(50, int(location.get('width', 100) or 100)),
                        'height': max(50, int(location.get('height', 100) or 100))
                    }
                    standardized_obj = {
                        'names': {
                            'zh': obj.get('names', {}).get('zh', '未知'),
                            'en': obj.get('names', {}).get('en', 'unknown'),
                            'ja': obj.get('names', {}).get('ja', '不明')
                        },
                        'location': location
                    }
                    standardized_result['objects'].append(standardized_obj)

            # 写入缓存
            self._cache[cache_key] = (now, standardized_result)
            logger.info("图像分析成功 | 对象数=%d | 有描述=%s", len(standardized_result['objects']), bool(standardized_result.get('descriptions')))
            return standardized_result

        except json.JSONDecodeError:
            logger.exception("解析 JSON 失败，返回兜底数据")
            # Fallback（JSON解析失败）
            return {
                'objects': [{
                    'names': {
                        'zh': '图片内容',
                        'en': 'image content',
                        'ja': '画像の内容'
                    },
                    'location': {'left': 50, 'top': 50, 'width': 200, 'height': 200}
                }],
                'descriptions': {
                    'zh': '图片包含多个物体',
                    'en': 'The image contains multiple objects',
                    'ja': '画像には複数の物体が含まれています'
                }
            }
        except Exception:
            logger.exception("调用模型异常，返回测试兜底数据")
            # Fallback（其他异常）
            return {
                'objects': [{
                    'names': {
                        'zh': '测试物体',
                        'en': 'test object',
                        'ja': 'テストオブジェクト'
                    },
                    'location': {'left': 100, 'top': 100, 'width': 150, 'height': 150}
                }],
                'descriptions': {
                    'zh': '这是一张测试图片',
                    'en': 'This is a test image',
                    'ja': 'これはテスト画像です'
                }
            }

