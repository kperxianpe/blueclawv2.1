#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 客户端 - 统一封装 OpenAI/Claude/Kimi

Week 20 Sprint 重构：urllib.request → httpx.AsyncClient
支持原生异步、可取消、连接池复用。
保留同步回退接口供非 async 上下文使用。
"""
import os
import json
import urllib.request
import warnings
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

import httpx


class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    KIMI = "kimi"


@dataclass
class Message:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: Optional[str]


class LLMClient:
    """
    Unified LLM Client
    
    Supports OpenAI, Anthropic (Claude), and Kimi (Moonshot)
    """
    
    def __init__(
        self,
        provider: ModelProvider = None,
        model: str = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        # Auto-detect provider from env
        if provider is None:
            if os.getenv('KIMI_API_KEY'):
                provider = ModelProvider.KIMI
                model = model or 'moonshot-v1-8k'
            elif os.getenv('OPENAI_API_KEY'):
                provider = ModelProvider.OPENAI
                model = model or 'gpt-4'
            else:
                provider = ModelProvider.KIMI
                model = model or 'moonshot-v1-8k'
        
        self.provider = provider
        self.model = model or 'moonshot-v1-8k'
        self.api_key = api_key or self._get_api_key()
        self.base_url = base_url or self._get_base_url()
        
        # Feature flag: 紧急情况下回退到同步 urllib 路径
        self._use_sync = os.getenv("USE_SYNC_LLM", "0") == "1"
        
        # 懒加载的 httpx 异步客户端
        self._async_client: Optional[httpx.AsyncClient] = None
    
    def _get_api_key(self) -> str:
        if self.provider == ModelProvider.KIMI:
            return os.getenv('KIMI_API_KEY', '')
        elif self.provider == ModelProvider.OPENAI:
            return os.getenv('OPENAI_API_KEY', '')
        elif self.provider == ModelProvider.ANTHROPIC:
            return os.getenv('ANTHROPIC_API_KEY', '')
        return ''
    
    def _get_base_url(self) -> str:
        if self.provider == ModelProvider.KIMI:
            return os.getenv('KIMI_BASE_URL', 'https://api.moonshot.cn/v1')
        elif self.provider == ModelProvider.OPENAI:
            return 'https://api.openai.com/v1'
        elif self.provider == ModelProvider.ANTHROPIC:
            return 'https://api.anthropic.com/v1'
        return ''
    
    def _get_async_client(self) -> httpx.AsyncClient:
        """懒加载 httpx.AsyncClient，配置连接池与分级超时"""
        if self._async_client is None:
            timeout = httpx.Timeout(60.0, connect=5.0, read=60.0)
            limits = httpx.Limits(max_connections=100)
            self._async_client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits
            )
        return self._async_client
    
    async def chat_completion(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """
        Asynchronous chat completion with cancellation support.
        """
        if self._use_sync:
            warnings.warn(
                "USE_SYNC_LLM=1 is active, falling back to synchronous path",
                RuntimeWarning
            )
            return self.chat_completion_sync(messages, temperature, max_tokens)
        
        if self.provider == ModelProvider.KIMI:
            return await self._kimi_completion(messages, temperature, max_tokens)
        elif self.provider == ModelProvider.OPENAI:
            return await self._openai_completion(messages, temperature, max_tokens)
        else:
            raise NotImplementedError(f"Provider {self.provider} not implemented")
    
    async def _kimi_completion(
        self,
        messages: List[Message],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Kimi API call via httpx.AsyncClient"""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        client = self._get_async_client()
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            finish_reason=data["choices"][0].get("finish_reason")
        )
    
    async def _openai_completion(
        self,
        messages: List[Message],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """OpenAI API call via httpx.AsyncClient"""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        client = self._get_async_client()
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            finish_reason=data["choices"][0].get("finish_reason")
        )
    
    # ======================================================================
    # 同步回退接口（已弃用，仅供非 async 上下文紧急使用）
    # ======================================================================
    def chat_completion_sync(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """
        Synchronous chat completion (deprecated).
        For async, use await chat_completion().
        """
        warnings.warn(
            "chat_completion_sync() is deprecated. Use await chat_completion() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        if self.provider == ModelProvider.KIMI:
            return self._kimi_completion_sync(messages, temperature, max_tokens)
        elif self.provider == ModelProvider.OPENAI:
            return self._openai_completion_sync(messages, temperature, max_tokens)
        else:
            raise NotImplementedError(f"Provider {self.provider} not implemented")
    
    def _kimi_completion_sync(
        self,
        messages: List[Message],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Kimi API call (sync fallback, urllib)"""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                return LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=data.get("model", self.model),
                    usage=data.get("usage", {}),
                    finish_reason=data["choices"][0].get("finish_reason")
                )
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"Kimi API error: {error_body}")
    
    def _openai_completion_sync(
        self,
        messages: List[Message],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """OpenAI API call (sync fallback, urllib)"""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                return LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=data.get("model", self.model),
                    usage=data.get("usage", {}),
                    finish_reason=data["choices"][0].get("finish_reason")
                )
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"OpenAI API error: {error_body}")


# Global client instance
llm_client = LLMClient()
