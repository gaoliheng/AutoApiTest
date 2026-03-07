"""
AI 模型 HTTP 客户端
支持 OpenAI API 兼容的 HTTP 请求，包括流式和非流式响应
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Iterator, Optional

import httpx

from utils.logger import get_logger

_logger = get_logger("ai.client")


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ChatMessage:
    role: MessageRole
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role.value, "content": self.content}


@dataclass
class ConnectionTestResult:
    success: bool
    message: str
    model_info: Optional[str] = None
    latency_ms: Optional[float] = None


@dataclass
class AIModelConfig:
    name: str
    api_base_url: str
    api_key: str
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 60.0
    extra_headers: dict[str, str] = field(default_factory=dict)


class AIClient:
    def __init__(self, config: AIModelConfig):
        self.config = config
        self._client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None
        _logger.info(f"初始化 AI 客户端: model={config.model_name}, base_url={config.api_base_url}")

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self.config.timeout),
                headers=self._build_headers(),
            )
        return self._client

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers=self._build_headers(),
            )
        return self._async_client

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        headers.update(self.config.extra_headers)
        return headers

    def _build_messages(self, messages: list[ChatMessage]) -> list[dict[str, str]]:
        return [msg.to_dict() for msg in messages]

    def _build_request_body(
        self,
        messages: list[ChatMessage],
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.config.model_name,
            "messages": self._build_messages(messages),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": stream,
        }
        if "top_p" in kwargs:
            body["top_p"] = kwargs["top_p"]
        if "presence_penalty" in kwargs:
            body["presence_penalty"] = kwargs["presence_penalty"]
        if "frequency_penalty" in kwargs:
            body["frequency_penalty"] = kwargs["frequency_penalty"]
        if "stop" in kwargs:
            body["stop"] = kwargs["stop"]
        return body

    def chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> dict[str, Any]:
        client = self._get_client()
        url = f"{self.config.api_base_url.rstrip('/')}/chat/completions"
        body = self._build_request_body(messages, stream=False, **kwargs)
        
        _logger.debug(f"发送聊天请求: url={url}, model={self.config.model_name}")
        _logger.debug(f"消息数量: {len(messages)}, max_tokens={body.get('max_tokens')}")
        
        try:
            response = client.post(url, json=body)
            response.raise_for_status()
            result = response.json()
            _logger.info(f"聊天请求成功: response_tokens={result.get('usage', {}).get('completion_tokens', 'N/A')}")
            return result
        except httpx.HTTPStatusError as e:
            _logger.error(f"聊天请求失败: status={e.response.status_code}, body={e.response.text[:500]}")
            raise
        except Exception as e:
            _logger.error(f"聊天请求异常: {str(e)}")
            raise

    async def async_chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> dict[str, Any]:
        client = self._get_async_client()
        url = f"{self.config.api_base_url.rstrip('/')}/chat/completions"
        body = self._build_request_body(messages, stream=False, **kwargs)

        _logger.debug(f"发送异步聊天请求: url={url}")
        
        response = await client.post(url, json=body)
        response.raise_for_status()
        return response.json()

    def stream_chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> Iterator[str]:
        client = self._get_client()
        url = f"{self.config.api_base_url.rstrip('/')}/chat/completions"
        body = self._build_request_body(messages, stream=True, **kwargs)

        _logger.debug(f"发送流式聊天请求: url={url}")

        with client.stream("POST", url, json=body) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    import json

                    try:
                        chunk = json.loads(data)
                        if chunk.get("choices"):
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue

    async def async_stream_chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        client = self._get_async_client()
        url = f"{self.config.api_base_url.rstrip('/')}/chat/completions"
        body = self._build_request_body(messages, stream=True, **kwargs)

        async with client.stream("POST", url, json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    import json

                    try:
                        chunk = json.loads(data)
                        if chunk.get("choices"):
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue

    def test_connection(self) -> ConnectionTestResult:
        import time
        
        _logger.info(f"测试连接: model={self.config.model_name}, url={self.config.api_base_url}")
        
        start_time = time.time()
        client = self._get_client()
        url = f"{self.config.api_base_url.rstrip('/')}/chat/completions"
        
        body = {
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 5,
        }

        try:
            response = client.post(url, json=body)
            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                _logger.info(f"连接测试成功: latency={latency_ms:.0f}ms")
                return ConnectionTestResult(
                    success=True,
                    message="连接成功",
                    model_info=self.config.model_name,
                    latency_ms=latency_ms,
                )
            else:
                _logger.warning(f"连接测试失败: status={response.status_code}")
                return ConnectionTestResult(
                    success=False,
                    message=f"HTTP {response.status_code}: {response.text[:200]}",
                )
        except httpx.ConnectError as e:
            _logger.error(f"连接失败: {str(e)}")
            return ConnectionTestResult(
                success=False,
                message=f"无法连接到服务器: {self.config.api_base_url}",
            )
        except httpx.TimeoutException:
            _logger.error(f"连接超时: timeout={self.config.timeout}s")
            return ConnectionTestResult(
                success=False,
                message=f"连接超时 ({self.config.timeout}秒)",
            )
        except Exception as e:
            _logger.error(f"连接测试异常: {str(e)}")
            return ConnectionTestResult(
                success=False,
                message=f"测试失败: {str(e)}",
            )

    async def async_test_connection(self) -> ConnectionTestResult:
        import time
        
        _logger.info(f"异步测试连接: model={self.config.model_name}")
        
        start_time = time.time()
        client = self._get_async_client()
        url = f"{self.config.api_base_url.rstrip('/')}/chat/completions"
        
        body = {
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 5,
        }

        try:
            response = await client.post(url, json=body)
            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                _logger.info(f"异步连接测试成功: latency={latency_ms:.0f}ms")
                return ConnectionTestResult(
                    success=True,
                    message="连接成功",
                    model_info=self.config.model_name,
                    latency_ms=latency_ms,
                )
            else:
                _logger.warning(f"异步连接测试失败: status={response.status_code}")
                return ConnectionTestResult(
                    success=False,
                    message=f"HTTP {response.status_code}: {response.text[:200]}",
                )
        except Exception as e:
            _logger.error(f"异步连接测试异常: {str(e)}")
            return ConnectionTestResult(
                success=False,
                message=f"测试失败: {str(e)}",
            )

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
        if self._async_client:
            _logger.debug("关闭 AI 客户端")
