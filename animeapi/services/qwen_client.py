# qwen 系列大模型客户端集成微服务

import json
import os
from typing import List, Dict, Optional, Generator, Any, cast
from dashscope import Generation, MultiModalConversation
import dashscope
from django.conf import settings

class QwenClient:
    """
    通义千问系列大模型客户端
    支持文生文、图像理解等多种模型调用
    """
    
    # 支持的模型列表
    SUPPORTED_MODELS = {
        # 文生文
        'qwen-turbo', 'qwen-plus', 'qwen-max', 'qwen-long',
        # 多模态
        'qwen-vl-plus', 'qwen-vl-max',
    }

    def _validate_model(self, model: str):
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"不支持的模型: {model}，支持的模型: {list(self.SUPPORTED_MODELS)}")
    
    def __init__(self, api_key: Optional[str] = None, region: str = 'cn'):
        """
        初始化 Qwen 客户端
        
        Args:
            api_key: 阿里云百炼 API Key，若为 None 则从环境变量 DASHSCOPE_API_KEY 读取
            region: 地域，'cn' 为中国，'intl' 为新加坡等国际地域
        """
        resolved_api_key = api_key \
            or getattr(settings, 'DASHSCOPE_API_KEY', None) \
            or os.getenv('DASHSCOPE_API_KEY')
        if not resolved_api_key:
            raise ValueError("API Key 未设置，请通过参数传入或设置环境变量 DASHSCOPE_API_KEY")
        self.api_key: str = resolved_api_key
        
        # 设置地域
        if region == 'intl':
            dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "qwen-plus",
        stream: bool = False,
        **kwargs
    ) -> Any:
        """
        文生文对话
        
        Args:
            messages: 对话消息列表，格式为 [{"role": "user", "content": "xxx"}]
            model: 模型名称，默认 qwen-plus
            stream: 是否使用流式输出
            **kwargs: 其他参数，如 temperature, top_p, max_tokens 等
            
        Returns:
            非流式：返回响应对象
            流式：返回生成器对象
        """
        self._validate_model(model)
        response = Generation.call(
            api_key=self.api_key,
            model=model,
            messages=cast(Any, messages),
            result_format="message",
            stream=stream,
            **kwargs
        )
        if stream:
            return self._handle_stream_response(response)
        else:
            return self._handle_response(response)
    
    def vision_chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "qwen-vl-plus",
        stream: bool = False,
        **kwargs
    ) -> Any:
        """
        图像理解对话
        
        Args:
            messages: 对话消息列表，支持文本和图像
                示例: [
                    {
                        "role": "user",
                        "content": [
                            {"image": "https://example.com/image.jpg"},
                            {"text": "这张图片里有什么？"}
                        ]
                    }
                ]
            model: 模型名称，默认 qwen-vl-plus
            stream: 是否使用流式输出
            **kwargs: 其他参数
            
        Returns:
            非流式：返回响应对象
            流式：返回生成器对象
        """
        self._validate_model(model)
        response = MultiModalConversation.call(
            api_key=self.api_key,
            model=model,
            messages=cast(Any, messages),
            stream=stream,
            **kwargs
        )
        if stream:
            return self._handle_stream_response(response)
        else:
            return self._handle_response(response)
    
    def simple_chat(
        self,
        user_message: str,
        system_message: str = "You are a helpful assistant.",
        model: str = "qwen-plus",
        **kwargs
    ) -> str:
        """
        简化的单轮对话接口
        
        Args:
            user_message: 用户消息
            system_message: 系统提示词
            model: 模型名称
            **kwargs: 其他参数
            
        Returns:
            模型回复的文本内容
        """
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        response = self.chat(messages=messages, model=model, **kwargs)
        return response.get('content', '')
    
    def _handle_response(self, response) -> Dict[str, Any]:
        """
        处理非流式响应
        
        Args:
            response: API 响应对象
            
        Returns:
            处理后的响应字典
        """
        if response.status_code == 200:
            return {
                'success': True,
                'content': response.output.choices[0].message.content,
                'role': response.output.choices[0].message.role,
                'finish_reason': response.output.choices[0].finish_reason,
                'usage': {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens,
                    'total_tokens': response.usage.total_tokens,
                } if hasattr(response, 'usage') else None,
                'request_id': response.request_id
            }
        else:
            return {
                'success': False,
                'status_code': response.status_code,
                'error_code': response.code,
                'error_message': response.message,
                'request_id': getattr(response, 'request_id', None)
            }
    
    def _handle_stream_response(self, response) -> Generator[Dict[str, Any], None, None]:
        """
        处理流式响应
        
        Args:
            response: API 流式响应对象
            
        Yields:
            每次生成的内容块
        """
        for chunk in response:
            if chunk.status_code == 200:
                yield {
                    'success': True,
                    'content': chunk.output.choices[0].message.content,
                    'finish_reason': chunk.output.choices[0].finish_reason,
                }
            else:
                yield {
                    'success': False,
                    'status_code': chunk.status_code,
                    'error_code': chunk.code,
                    'error_message': chunk.message,
                }
                break


# 示例使用
if __name__ == "__main__":
    # 初始化客户端
    client = QwenClient()
    
    # 示例1: 简单对话
    print("=== 示例1: 简单对话 ===")
    response = client.simple_chat("你是谁？")
    print(response)
    print()
    
    # 示例2: 多轮对话
    print("=== 示例2: 多轮对话 ===")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请用简短的话介绍一下Python"},
    ]
    result = client.chat(messages=messages, model="qwen-plus")
    if result['success']:
        print(f"回复: {result['content']}")
        print(f"Token使用: {result['usage']}")
    else:
        print(f"错误: {result['error_message']}")
    print()
    
    # 示例3: 流式对话
    print("=== 示例3: 流式对话 ===")
    messages = [
        {"role": "user", "content": "写一首关于春天的诗"},
    ]
    for chunk in client.chat(messages=messages, model="qwen-plus", stream=True):
        if chunk['success']:
            print(chunk['content'], end='', flush=True)
    print("\n")
    
    # 示例4: 图像理解（需要提供真实的图片URL）
    print("=== 示例4: 图像理解 ===")
    print("# 取消注释以下代码并提供真实图片URL来测试")
    vision_messages = [
        {
            "role": "user",
            "content": [
                {"image": "https://example.com/image.jpg"},
                {"text": "这张图片里有什么？"}
            ]
        }
    ]
    vision_result = client.vision_chat(messages=vision_messages, model="qwen-vl-plus")
    if vision_result['success']:
        print(f"回复: {vision_result['content']}")
    else:
        print(f"错误: {vision_result['error_message']}")