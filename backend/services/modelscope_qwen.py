import requests
import json
import base64
from typing import Dict, Any, List
import os

class ModelScopeQwenService:
    def __init__(self, api_key: str, base_url: str, 
                 model_vision: str = None,
                 model_translation: str = None,
                 model_definition: str = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        # 分别配置各功能所用模型
        self.model_vision = model_vision
        self.model_translation = model_translation
        self.model_definition = model_definition

    def _make_request(self, messages: List[Dict], max_tokens: int = 2000, model: str = None) -> str:
        """发送请求到ModelScope API（支持指定模型）"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1
        }

        try:
            print(f"发送请求到: {self.base_url}/chat/completions")
            print(f"使用模型: {model}")

            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=data,
                timeout=240
            )

            print(f"响应状态码: {response.status_code}")

            if response.status_code != 200:
                print(f"响应内容: {response.text}")
                response.raise_for_status()

            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            elif 'error' in result:
                raise Exception(f"ModelScope API错误: {result['error']}")
            else:
                raise Exception(f"ModelScope API返回格式错误: {result}")

        except Exception as e:
            print(f"ModelScope API请求失败: {e}")
            raise Exception(f"ModelScope API请求失败: {e}")

    async def analyze_image_multilingual(self, base64_image: str, max_objects: int = 3) -> Dict[str, Any]:
        """
        一次性完成：
        1. 识别图片中的主要物体
        2. 提供中英日三语名称
        3. 生成中英日三语的图片描述句子
        
        Args:
            base64_image: Base64编码的图片
            max_objects: 最多识别的物体数量（默认3个）
            
        Returns:
            Dict包含:
            - objects: 物体列表，每个物体包含多语言名称和位置
            - descriptions: 中英日三语的图片描述
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""你是一位专业的视觉识别和多语言翻译专家。请分析这张图片并完成以下任务：

**任务1：物体识别**
识别图片中最多{max_objects}个主要物体，为每个物体提供：
- 中文名称
- 英文名称
- 日文名称(注意一定不要翻译为中文)
- 物体位置（边界框坐标：left, top, width, height）

**任务2：图片描述**
使用识别出的物体，用简单的句子描述图片内容（中英日三语各一句）。
描述要求：
- 简洁自然，10-20字
- 使用识别出的物体名称
- 描述物体之间的关系或场景

**输出格式（严格遵循JSON格式）：**
```json
{{
    "objects": [
        {{
            "names": {{
                "zh": "苹果",
                "en": "apple",
                "ja": "りんご"
            }},
            "location": {{
                "left": 100,
                "top": 150,
                "width": 80,
                "height": 90
            }}
        }}
    ],
    "descriptions": {{
        "zh": "桌上有一个红苹果和一本书",
        "en": "There is a red apple and a book on the table",
        "ja": "テーブルの上に赤いリンゴと本があります"
    }}
}}
```

**注意事项：**
1. 只返回JSON，不要任何markdown标记或其他文字
2. 确保所有物体名称翻译准确、地道
3. 边界框坐标为像素值，确保合理
4. 描述句子要自然流畅，符合各语言习惯
5. 如果物体少于{max_objects}个，只返回实际识别到的物体"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]

        try:
            print(f"正在使用视觉模型进行多语言图像分析...")
            response_text = self._make_request(
                messages, 
                max_tokens=3000, 
                model=self.model_vision
            )
            print(f"视觉模型原始响应: {response_text}")

            # 清理响应文本
            response_text = response_text.strip()
            
            # 移除可能的markdown代码块标记
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            elif response_text.startswith('```'):
                response_text = response_text[3:]
            
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            print(f"清理后的响应: {response_text}")

            # 解析JSON
            result = json.loads(response_text)
            print(f"解析后的结果: {result}")

            # 验证和标准化数据
            standardized_result = {
                'objects': [],
                'descriptions': result.get('descriptions', {
                    'zh': '图片内容',
                    'en': 'Image content',
                    'ja': '画像の内容'
                })
            }

            # 标准化物体数据
            for obj in result.get('objects', []):
                if isinstance(obj, dict) and 'names' in obj:
                    # 确保坐标值为正数且合理
                    location = obj.get('location', {})
                    location = {
                        'left': max(0, location.get('left', 0)),
                        'top': max(0, location.get('top', 0)),
                        'width': max(50, location.get('width', 100)),
                        'height': max(50, location.get('height', 100))
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

            print(f"视觉模型标准化后的结果: {standardized_result}")
            return standardized_result

        except json.JSONDecodeError as e:
            print(f"视觉模型 JSON解析失败: {e}, 原始响应: {response_text}")
            
            # Fallback返回
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

        except Exception as e:
            print(f"视觉模型图像分析失败: {e}")
            
            # Fallback返回测试数据
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
   
    # 视觉识别，翻译模型和组句拆开写

    # async def detect_objects_from_image(self, base64_image: str) -> List[Dict[str, Any]]:
    #     """
    #     使用Qwen3模型识别图片中的物体（保留原有功能）
    #     """
    #     messages = [
    #         {
    #             "role": "user",
    #             "content": [
    #                 {
    #                     "type": "text",
    #                     "text": """请以视觉识别专家的身份，仅检测并识别图像中的主要（主体）物体，忽略其他无关的物体，识别数量最多为一个。

    #                     任务要求：
    #                     1. 识别图片中的主要物体
    #                     2. 为每个物体提供准确的中文名称
    #                     3. 估算每个物体在图片中的大致位置和边界框
    #                     4. 给出识别的置信度评分

    #                     请以以下JSON格式返回结果：
    #                     [
    #                         {
    #                             "keyword": "苹果",
    #                             "confidence": 0.95,
    #                             "location": {
    #                                 "left": 100,
    #                                 "top": 150,
    #                                 "width": 80,
    #                                 "height": 90
    #                             }
    #                         }
    #                     ]

    #                     注意事项：
    #                     - 只返回JSON数组，不要任何其他文字或解释
    #                     - keyword必须是准确的中文物体名称
    #                     - confidence范围为0.0-1.0，表示识别置信度
    #                     - location坐标为像素值，left/top为左上角坐标
    #                     - 识别尽可能多的可见物体，包括大物体和小物体
    #                     - 确保边界框坐标合理且符合物体实际位置"""
    #                 },
    #                 {
    #                     "type": "image_url",
    #                     "image_url": {
    #                         "url": f"data:image/jpeg;base64,{base64_image}"
    #                     }
    #                 }
    #             ]
    #         }
    #     ]

    #     try:
    #         print(f"正在使用视觉模型识别图片...")
    #         response_text = self._make_request(messages, max_tokens=2000, model=self.model_vision)
    #         print(f"视觉模型原始响应: {response_text}")

    #         # 清理响应文本，提取JSON
    #         response_text = response_text.strip()

    #         # 移除可能的markdown代码块标记
    #         if response_text.startswith('```json'):
    #             response_text = response_text[7:]
    #         elif response_text.startswith('```'):
    #             response_text = response_text[3:]

    #         if response_text.endswith('```'):
    #             response_text = response_text[:-3]

    #         response_text = response_text.strip()
    #         print(f"清理后的响应: {response_text}")

    #         # 解析JSON
    #         objects = json.loads(response_text)
    #         print(f"解析后的对象: {objects}")

    #         # 验证和标准化数据
    #         standardized_objects = []
    #         for obj in objects:
    #             if isinstance(obj, dict) and 'keyword' in obj:
    #                 # 确保坐标值为正数
    #                 location = obj.get('location', {})
    #                 location = {
    #                     'left': max(0, location.get('left', 0)),
    #                     'top': max(0, location.get('top', 0)),
    #                     'width': max(50, location.get('width', 100)),
    #                     'height': max(50, location.get('height', 100))
    #                 }

    #                 standardized_obj = {
    #                     'keyword': obj.get('keyword', '未知物体'),
    #                     'score': min(1.0, max(0.0, obj.get('confidence', 0.8))),
    #                     'location': location
    #                 }
    #                 standardized_objects.append(standardized_obj)

    #         print(f"Qwen3标准化后的对象: {standardized_objects}")
    #         return standardized_objects

    #     except json.JSONDecodeError as e:
    #         print(f"视觉模型 JSON解析失败: {e}, 原始响应: {response_text}")

    #         # 尝试简单的内容提取作为fallback
    #         if response_text and len(response_text) > 0:
    #             return [{
    #                 'keyword': '图片内容',
    #                 'score': 0.6,
    #                 'location': {'left': 50, 'top': 50, 'width': 200, 'height': 200}
    #             }]
    #         return []

    #     except Exception as e:
    #         print(f"视觉模型图像识别失败: {e}")
    #         # 返回测试数据以验证前端功能
    #         return [{
    #             'keyword': '视觉模型测试',
    #             'score': 0.9,
    #             'location': {'left': 100, 'top': 100, 'width': 150, 'height': 150}
    #         }]

    # async def translate_text(self, text: str, from_lang: str, to_lang: str) -> str:
    #     """
    #     使用专用翻译模型翻译文本（保留原有功能）
    #     """
    #     lang_map = {
    #         'zh-CHS': '中文',
    #         'en': '英文',
    #         'ja': '日文'
    #     }

    #     from_language = lang_map.get(from_lang, from_lang)
    #     to_language = lang_map.get(to_lang, to_lang)

    #     messages = [
    #         {
    #             "role": "user",
    #             "content": f"""请将以下{from_language}词汇精确翻译成{to_language}：

    #             原文："{text}"

    #             要求：
    #             1. 只返回翻译结果，不要其他文字
    #             2. 确保翻译准确、地道
    #             3. 如果是物体名称，使用标准术语
    #             4. 保持简洁明了"""
    #         }
    #     ]

    #     try:
    #         translation = self._make_request(messages, max_tokens=200, model=self.model_translation)
    #         return translation.strip().strip('"').strip("'")
    #     except Exception as e:
    #         print(f"翻译模型调用失败: {e}")
    #         return text

    # async def get_definition(self, word: str) -> str:
    #     """
    #     使用专用释义模型获取词汇释义（保留原有功能）
    #     """
    #     messages = [
    #         {
    #             "role": "user",
    #             "content": f"""请为"{word}"这个词提供简洁的中文释义。

    #             要求：
    #             1. 只返回释义内容，不要其他文字
    #             2. 释义控制在30字以内
    #             3. 如果是物体名称，说明其用途或特征
    #             4. 语言简洁明了"""
    #         }
    #     ]

    #     try:
    #         definition = self._make_request(messages, max_tokens=150, model=self.model_definition)
    #         return definition.strip()
    #     except Exception as e:
    #         print(f"释义模型调用失败: {e}")
    #         return f"关于{word}的常见物体或概念"