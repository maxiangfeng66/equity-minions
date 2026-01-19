"""
AI Provider Manager - Interfaces with multiple AI APIs
Supports: OpenAI (GPT), Google (Gemini), xAI (Grok), DeepSeek, Alibaba (Qwen)
"""

import os
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import aiohttp


class AIProvider(ABC):
    """Base class for AI providers"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class OpenAIProvider(AIProvider):
    """OpenAI GPT Provider"""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        super().__init__(api_key)
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"

    @property
    def name(self) -> str:
        return "GPT"

    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error = await resp.text()
                    raise Exception(f"OpenAI API error: {error}")


class GeminiProvider(AIProvider):
    """Google Gemini Provider"""

    def __init__(self, api_key: str, model: str = "gemini-pro"):
        super().__init__(api_key)
        self.model = model
        self.base_url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent"

    @property
    def name(self) -> str:
        return "Gemini"

    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, params=params, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    error = await resp.text()
                    raise Exception(f"Gemini API error: {error}")


class GrokProvider(AIProvider):
    """xAI Grok Provider"""

    def __init__(self, api_key: str, model: str = "grok-beta"):
        super().__init__(api_key)
        self.model = model
        self.base_url = "https://api.x.ai/v1/chat/completions"

    @property
    def name(self) -> str:
        return "Grok"

    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error = await resp.text()
                    raise Exception(f"Grok API error: {error}")


class DeepSeekProvider(AIProvider):
    """DeepSeek Provider"""

    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        super().__init__(api_key)
        self.model = model
        self.base_url = "https://api.deepseek.com/v1/chat/completions"

    @property
    def name(self) -> str:
        return "DeepSeek"

    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error = await resp.text()
                    raise Exception(f"DeepSeek API error: {error}")


class QwenProvider(AIProvider):
    """Alibaba Qwen Provider (via DashScope)"""

    def __init__(self, api_key: str, model: str = "qwen-turbo"):
        super().__init__(api_key)
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    @property
    def name(self) -> str:
        return "Qwen"

    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "input": {"messages": messages},
            "parameters": {"temperature": 0.7, "max_tokens": 4096}
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["output"]["text"]
                else:
                    error = await resp.text()
                    raise Exception(f"Qwen API error: {error}")


class AIProviderManager:
    """Manages multiple AI providers and distributes requests"""

    def __init__(self, config: Dict[str, str]):
        self.providers: List[AIProvider] = []
        self._setup_providers(config)

    def _setup_providers(self, config: Dict[str, str]):
        """Initialize available providers based on config"""
        if config.get("openai"):
            self.providers.append(OpenAIProvider(config["openai"]))
        if config.get("google"):
            self.providers.append(GeminiProvider(config["google"]))
        if config.get("xai"):
            self.providers.append(GrokProvider(config["xai"]))
        if config.get("deepseek"):
            self.providers.append(DeepSeekProvider(config["deepseek"]))
        if config.get("dashscope"):
            self.providers.append(QwenProvider(config["dashscope"]))

    def get_provider(self, name: str = None) -> Optional[AIProvider]:
        """Get a specific provider or first available"""
        if name:
            for p in self.providers:
                if p.name.lower() == name.lower():
                    return p
        return self.providers[0] if self.providers else None

    def get_all_providers(self) -> List[AIProvider]:
        """Get all available providers"""
        return self.providers

    async def generate_with_all(self, prompt: str, system_prompt: str = None) -> Dict[str, str]:
        """Generate responses from all providers in parallel"""
        tasks = []
        for provider in self.providers:
            tasks.append(self._safe_generate(provider, prompt, system_prompt))

        results = await asyncio.gather(*tasks)
        return {p.name: r for p, r in zip(self.providers, results) if r is not None}

    async def _safe_generate(self, provider: AIProvider, prompt: str, system_prompt: str = None) -> Optional[str]:
        """Safely generate with error handling"""
        try:
            return await provider.generate(prompt, system_prompt)
        except Exception as e:
            print(f"Error with {provider.name}: {e}")
            return None
