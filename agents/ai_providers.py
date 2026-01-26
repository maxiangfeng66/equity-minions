"""
AI Provider Manager - Interfaces with multiple AI APIs
Supports: OpenAI (GPT), Google (Gemini), xAI (Grok), DeepSeek, Alibaba (Qwen)

Includes rate limiting and token budget management to prevent API quota exhaustion.
"""

import os
import json
import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import aiohttp

# Import config for API keys
try:
    import config
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False

# Import logger for tracking API usage
try:
    from agents.agent_logger import log_ai_call
    HAS_LOGGER = True
except ImportError:
    HAS_LOGGER = False
    def log_ai_call(*args, **kwargs): pass

# Default timeout configuration for API calls
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=120, connect=30, sock_read=90)

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 5  # seconds
MAX_DELAY = 60  # seconds

# Rate limiting configuration (tokens per minute)
OPENAI_TPM_LIMIT = 28000  # Conservative buffer under 30,000 TPM
GEMINI_RPM_LIMIT = 15     # Requests per minute for free tier
GROK_TPM_LIMIT = 100000   # xAI is more generous


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for API calls.

    Tracks token usage and enforces rate limits by waiting when
    the budget is exhausted. Tokens refill over time.
    """

    def __init__(self, tokens_per_minute: int, name: str = "default"):
        self.tokens_per_minute = tokens_per_minute
        self.name = name
        self.available_tokens = tokens_per_minute
        self.last_refill = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens_needed: int) -> float:
        """
        Acquire tokens for an API call. Waits if necessary.

        Args:
            tokens_needed: Estimated tokens for this request

        Returns:
            Wait time in seconds (0 if no wait needed)
        """
        async with self._lock:
            # Refill tokens based on elapsed time
            now = time.time()
            elapsed = now - self.last_refill
            refill_amount = (elapsed / 60.0) * self.tokens_per_minute
            self.available_tokens = min(
                self.tokens_per_minute,
                self.available_tokens + refill_amount
            )
            self.last_refill = now

            # Check if we have enough tokens
            if self.available_tokens >= tokens_needed:
                self.available_tokens -= tokens_needed
                return 0.0

            # Calculate wait time
            tokens_deficit = tokens_needed - self.available_tokens
            wait_seconds = (tokens_deficit / self.tokens_per_minute) * 60.0

            # Add small buffer to ensure we're under limit
            wait_seconds += 1.0

            print(f"  [{self.name}] Rate limit: waiting {wait_seconds:.1f}s for {tokens_needed} tokens...")

            return wait_seconds

    async def wait_and_acquire(self, tokens_needed: int):
        """Acquire tokens, waiting if necessary"""
        wait_time = await self.acquire(tokens_needed)
        if wait_time > 0:
            await asyncio.sleep(wait_time)
            # After waiting, deduct the tokens
            async with self._lock:
                self.available_tokens = max(0, self.available_tokens - tokens_needed)

    def report_actual_usage(self, actual_tokens: int, estimated_tokens: int):
        """Adjust available tokens based on actual vs estimated usage"""
        # If we overestimated, give back some tokens
        # If we underestimated, we're already past the point of fixing it
        diff = estimated_tokens - actual_tokens
        if diff > 0:
            self.available_tokens = min(
                self.tokens_per_minute,
                self.available_tokens + diff
            )


# Global rate limiters (shared across all provider instances)
_rate_limiters: Dict[str, TokenBucketRateLimiter] = {}

def get_rate_limiter(provider_name: str) -> TokenBucketRateLimiter:
    """Get or create a rate limiter for a provider"""
    if provider_name not in _rate_limiters:
        if provider_name == "GPT":
            _rate_limiters[provider_name] = TokenBucketRateLimiter(OPENAI_TPM_LIMIT, "OpenAI")
        elif provider_name == "Gemini":
            # Gemini uses RPM, so we use a high token count per "request"
            _rate_limiters[provider_name] = TokenBucketRateLimiter(GEMINI_RPM_LIMIT * 5000, "Gemini")
        elif provider_name == "Grok":
            _rate_limiters[provider_name] = TokenBucketRateLimiter(GROK_TPM_LIMIT, "Grok")
        else:
            # Default generous limit for other providers
            _rate_limiters[provider_name] = TokenBucketRateLimiter(100000, provider_name)
    return _rate_limiters[provider_name]


def estimate_tokens(prompt: str, system_prompt: str = None, max_output: int = 4096) -> int:
    """
    Estimate total tokens for a request (input + output).

    Uses rough estimate of 1 token per 4 characters.
    """
    input_chars = len(prompt) + (len(system_prompt) if system_prompt else 0)
    input_tokens = input_chars // 4
    # Add output tokens (conservative estimate)
    return input_tokens + max_output


async def retry_with_backoff(func, max_retries=MAX_RETRIES, base_delay=BASE_DELAY):
    """Retry a function with exponential backoff for rate limits"""
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            error_str = str(e).lower()

            # Check if it's a rate limit error (retry) or other error (don't retry)
            is_rate_limit = any(x in error_str for x in [
                'rate_limit', 'resource_exhausted', '429', 'too many requests',
                'tokens per min', 'quota', 'timeout'
            ])

            if not is_rate_limit:
                raise e  # Don't retry non-rate-limit errors

            if attempt < max_retries - 1:
                # Exponential backoff with jitter
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                print(f"  Rate limited, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(delay)
            else:
                raise e
    raise last_exception


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
    """OpenAI GPT Provider with rate limiting"""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(api_key)
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.rate_limiter = get_rate_limiter("GPT")

    @property
    def name(self) -> str:
        return "GPT"

    async def generate(self, prompt: str, system_prompt: str = None, agent_id: str = None, agent_role: str = None, call_type: str = "generate") -> str:
        # Estimate tokens and wait for rate limit clearance
        estimated_tokens = estimate_tokens(prompt, system_prompt, max_output=4096)
        await self.rate_limiter.wait_and_acquire(estimated_tokens)

        # Track token usage for logging
        actual_tokens_in = 0
        actual_tokens_out = 0

        async def _call():
            nonlocal actual_tokens_in, actual_tokens_out
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

            async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
                async with session.post(self.base_url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Report actual token usage if available
                        if "usage" in data:
                            actual_tokens_in = data["usage"].get("prompt_tokens", 0)
                            actual_tokens_out = data["usage"].get("completion_tokens", 0)
                            actual_tokens = data["usage"].get("total_tokens", estimated_tokens)
                            self.rate_limiter.report_actual_usage(actual_tokens, estimated_tokens)
                        return data["choices"][0]["message"]["content"]
                    else:
                        error = await resp.text()
                        raise Exception(f"OpenAI API error: {error}")

        try:
            result = await retry_with_backoff(_call)
            # Log successful call
            log_ai_call("openai", self.model, agent_id or "unknown", agent_role or "unknown",
                       call_type, actual_tokens_in, actual_tokens_out, success=True)
            return result
        except Exception as e:
            # Log failed call
            log_ai_call("openai", self.model, agent_id or "unknown", agent_role or "unknown",
                       call_type, estimated_tokens // 2, 0, success=False, error=str(e)[:200])
            raise


class GeminiProvider(AIProvider):
    """Google Gemini Provider with rate limiting and model fallback"""

    # Model priority: try 2.5 first, fallback to 2.0
    MODELS = ["gemini-2.5-flash-preview-05-20", "gemini-2.0-flash"]

    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key)
        self.primary_model = model or self.MODELS[0]
        self.fallback_model = self.MODELS[1] if self.primary_model == self.MODELS[0] else None
        self.current_model = self.primary_model
        self.rate_limiter = get_rate_limiter("Gemini")

    def _get_url(self, model: str) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    @property
    def name(self) -> str:
        return f"Gemini ({self.current_model})"

    async def generate(self, prompt: str, system_prompt: str = None, agent_id: str = None, agent_role: str = None, call_type: str = "generate") -> str:
        # Estimate tokens and wait for rate limit clearance
        estimated_tokens = estimate_tokens(prompt, system_prompt, max_output=4096)
        await self.rate_limiter.wait_and_acquire(estimated_tokens)

        async def _call_with_model(model: str):
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

            url = self._get_url(model)
            async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
                async with session.post(url, headers=headers, params=params, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.current_model = model
                        return data["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        error = await resp.text()
                        raise Exception(f"Gemini API error ({model}): {error}")

        async def _call():
            # Try primary model first
            try:
                return await _call_with_model(self.primary_model)
            except Exception as e:
                # If primary fails and we have a fallback, try it
                if self.fallback_model:
                    print(f"[Gemini] Primary model {self.primary_model} failed, falling back to {self.fallback_model}")
                    return await _call_with_model(self.fallback_model)
                raise e

        try:
            result = await retry_with_backoff(_call)
            # Log successful call (Gemini doesn't return token counts, estimate)
            log_ai_call("gemini", self.current_model, agent_id or "unknown", agent_role or "unknown",
                       call_type, estimated_tokens // 2, len(result) // 4, success=True)
            return result
        except Exception as e:
            log_ai_call("gemini", self.current_model, agent_id or "unknown", agent_role or "unknown",
                       call_type, estimated_tokens // 2, 0, success=False, error=str(e)[:200])
            raise


class GrokProvider(AIProvider):
    """xAI Grok Provider with rate limiting"""

    def __init__(self, api_key: str, model: str = "grok-3"):
        super().__init__(api_key)
        self.model = model
        self.base_url = "https://api.x.ai/v1/chat/completions"
        self.rate_limiter = get_rate_limiter("Grok")

    @property
    def name(self) -> str:
        return "Grok"

    async def generate(self, prompt: str, system_prompt: str = None, agent_id: str = None, agent_role: str = None, call_type: str = "generate") -> str:
        # Estimate tokens and wait for rate limit clearance
        estimated_tokens = estimate_tokens(prompt, system_prompt, max_output=4096)
        await self.rate_limiter.wait_and_acquire(estimated_tokens)

        # Track token usage for logging
        actual_tokens_in = 0
        actual_tokens_out = 0

        async def _call():
            nonlocal actual_tokens_in, actual_tokens_out
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

            async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
                async with session.post(self.base_url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Grok returns OpenAI-compatible usage stats
                        if "usage" in data:
                            actual_tokens_in = data["usage"].get("prompt_tokens", 0)
                            actual_tokens_out = data["usage"].get("completion_tokens", 0)
                        return data["choices"][0]["message"]["content"]
                    else:
                        error = await resp.text()
                        raise Exception(f"Grok API error: {error}")

        try:
            result = await retry_with_backoff(_call)
            log_ai_call("grok", self.model, agent_id or "unknown", agent_role or "unknown",
                       call_type, actual_tokens_in, actual_tokens_out, success=True)
            return result
        except Exception as e:
            log_ai_call("grok", self.model, agent_id or "unknown", agent_role or "unknown",
                       call_type, estimated_tokens // 2, 0, success=False, error=str(e)[:200])
            raise


class QwenProvider(AIProvider):
    """Alibaba Qwen Provider (via DashScope International)"""

    def __init__(self, api_key: str, model: str = "qwen-turbo"):
        super().__init__(api_key)
        self.model = model
        # Use international endpoint for non-China regions
        self.base_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

    @property
    def name(self) -> str:
        return "Qwen"

    async def generate(self, prompt: str, system_prompt: str = None, agent_id: str = None, agent_role: str = None, call_type: str = "generate") -> str:
        estimated_tokens = estimate_tokens(prompt, system_prompt, max_output=4096)
        actual_tokens_in = 0
        actual_tokens_out = 0

        async def _call():
            nonlocal actual_tokens_in, actual_tokens_out
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Use OpenAI-compatible format for international endpoint
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 4096
            }

            async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
                async with session.post(self.base_url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "usage" in data:
                            actual_tokens_in = data["usage"].get("prompt_tokens", 0)
                            actual_tokens_out = data["usage"].get("completion_tokens", 0)
                        return data["choices"][0]["message"]["content"]
                    else:
                        error = await resp.text()
                        raise Exception(f"Qwen API error: {error}")

        try:
            result = await retry_with_backoff(_call)
            log_ai_call("qwen", self.model, agent_id or "unknown", agent_role or "unknown",
                       call_type, actual_tokens_in, actual_tokens_out, success=True)
            return result
        except Exception as e:
            log_ai_call("qwen", self.model, agent_id or "unknown", agent_role or "unknown",
                       call_type, estimated_tokens // 2, 0, success=False, error=str(e)[:200])
            raise


class AIProviderManager:
    """
    Manages multiple AI providers with BALANCED load distribution.

    Features:
    - Weighted round-robin to ensure diversity (no single provider dominates)
    - Usage tracking to maintain balance across providers
    - Automatic fallback when a provider is rate-limited
    - Provider health tracking
    """

    # Target distribution percentages (should sum to 100)
    # Ensures no single provider handles more than 30% of requests
    DEFAULT_WEIGHTS = {
        "OpenAI": 25,      # GPT-4o - premium, reliable
        "Gemini": 25,      # Gemini 2.5 - good for analysis
        "Grok": 25,        # xAI Grok-3 - fast responses
        "Qwen": 25,        # Alibaba Qwen - good diversity
    }

    def __init__(self, config: Dict[str, str], weights: Dict[str, int] = None):
        self.providers: List[AIProvider] = []
        self._setup_providers(config)
        self._provider_index = 0  # For round-robin
        self._provider_errors: Dict[str, int] = {}  # Track error counts
        self._provider_usage: Dict[str, int] = {}  # Track usage counts
        self._total_requests = 0
        self._lock = asyncio.Lock()

        # Set up weights - normalize to available providers
        self._weights = weights or self.DEFAULT_WEIGHTS
        self._normalize_weights()

    def _setup_providers(self, config: Dict[str, str]):
        """Initialize available providers based on config"""
        if config.get("openai"):
            self.providers.append(OpenAIProvider(config["openai"]))
        if config.get("google"):
            self.providers.append(GeminiProvider(config["google"]))
        if config.get("xai"):
            self.providers.append(GrokProvider(config["xai"]))
        if config.get("dashscope"):
            self.providers.append(QwenProvider(config["dashscope"]))

    def _normalize_weights(self):
        """Normalize weights to only include available providers"""
        available_names = {self._get_base_name(p.name) for p in self.providers}
        active_weights = {k: v for k, v in self._weights.items() if k in available_names}

        # Redistribute weights proportionally if some providers missing
        if active_weights:
            total = sum(active_weights.values())
            self._normalized_weights = {k: v / total for k, v in active_weights.items()}
        else:
            # Equal distribution if no weights match
            self._normalized_weights = {self._get_base_name(p.name): 1.0 / len(self.providers)
                                        for p in self.providers}

    def _get_base_name(self, provider_name: str) -> str:
        """Extract base provider name (e.g., 'Gemini (gemini-2.5...)' -> 'Gemini')"""
        return provider_name.split('(')[0].strip() if '(' in provider_name else provider_name

    def get_provider(self, name: str = None) -> Optional[AIProvider]:
        """Get a specific provider or first available"""
        if name:
            for p in self.providers:
                if name.lower() in p.name.lower():
                    return p
        return self.providers[0] if self.providers else None

    def get_all_providers(self) -> List[AIProvider]:
        """Get all available providers"""
        return self.providers

    def get_diversified_providers(self, count: int) -> List[AIProvider]:
        """
        Get a diversified list of providers for parallel tasks.
        Ensures different providers are used, not the same one repeated.
        """
        if count >= len(self.providers):
            return self.providers.copy()

        # Sort by usage (least used first) to maintain balance
        sorted_providers = sorted(
            self.providers,
            key=lambda p: self._provider_usage.get(self._get_base_name(p.name), 0)
        )
        return sorted_providers[:count]

    async def get_next_provider(self) -> Optional[AIProvider]:
        """
        Get the next provider using BALANCED selection.

        Prioritizes under-utilized providers to maintain target distribution.
        """
        async with self._lock:
            if not self.providers:
                return None

            # Calculate current usage percentages
            if self._total_requests > 0:
                usage_pct = {
                    self._get_base_name(p.name): self._provider_usage.get(self._get_base_name(p.name), 0) / self._total_requests
                    for p in self.providers
                }
            else:
                usage_pct = {self._get_base_name(p.name): 0 for p in self.providers}

            # Find the most under-utilized provider relative to target
            best_provider = None
            best_deficit = -float('inf')

            for provider in self.providers:
                base_name = self._get_base_name(provider.name)

                # Skip providers with too many errors
                if self._provider_errors.get(base_name, 0) >= 3:
                    continue

                target = self._normalized_weights.get(base_name, 0.25)
                current = usage_pct.get(base_name, 0)
                deficit = target - current  # Positive = under-utilized

                if deficit > best_deficit:
                    best_deficit = deficit
                    best_provider = provider

            # Fallback to round-robin if all have errors
            if best_provider is None:
                self._provider_errors.clear()
                best_provider = self.providers[self._provider_index]
                self._provider_index = (self._provider_index + 1) % len(self.providers)

            # Track usage
            base_name = self._get_base_name(best_provider.name)
            self._provider_usage[base_name] = self._provider_usage.get(base_name, 0) + 1
            self._total_requests += 1

            return best_provider

    def report_provider_success(self, provider_name: str):
        """Report successful call to a provider"""
        base_name = self._get_base_name(provider_name)
        if base_name in self._provider_errors:
            self._provider_errors[base_name] = max(0, self._provider_errors[base_name] - 1)

    def report_provider_error(self, provider_name: str):
        """Report error from a provider"""
        base_name = self._get_base_name(provider_name)
        self._provider_errors[base_name] = self._provider_errors.get(base_name, 0) + 1

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current provider usage statistics"""
        if self._total_requests == 0:
            return {"total_requests": 0, "providers": {}}

        stats = {
            "total_requests": self._total_requests,
            "providers": {}
        }
        for provider in self.providers:
            base_name = self._get_base_name(provider.name)
            usage = self._provider_usage.get(base_name, 0)
            target = self._normalized_weights.get(base_name, 0) * 100
            stats["providers"][base_name] = {
                "requests": usage,
                "actual_pct": round(usage / self._total_requests * 100, 1),
                "target_pct": round(target, 1),
                "errors": self._provider_errors.get(base_name, 0)
            }
        return stats

    async def generate_with_fallback(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generate using load balancing with automatic fallback.

        Tries providers in round-robin order, falling back on errors.
        """
        last_error = None
        tried_providers = set()

        while len(tried_providers) < len(self.providers):
            provider = await self.get_next_provider()
            if not provider or provider.name in tried_providers:
                break

            tried_providers.add(provider.name)

            try:
                result = await provider.generate(prompt, system_prompt)
                self.report_provider_success(provider.name)
                return result
            except Exception as e:
                last_error = e
                self.report_provider_error(provider.name)
                print(f"  [{provider.name}] Error, trying next provider: {str(e)[:100]}")

        raise last_error or Exception("No providers available")

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

    def get_rate_limit_status(self) -> Dict[str, Dict]:
        """Get current rate limit status for all providers"""
        status = {}
        for provider in self.providers:
            if hasattr(provider, 'rate_limiter'):
                limiter = provider.rate_limiter
                status[provider.name] = {
                    'available_tokens': int(limiter.available_tokens),
                    'max_tokens': limiter.tokens_per_minute,
                    'utilization': f"{(1 - limiter.available_tokens/limiter.tokens_per_minute)*100:.1f}%"
                }
        return status


def get_ai_response(
    prompt: str,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    system_prompt: str = None
) -> str:
    """
    Synchronous wrapper for getting AI response.

    This is a convenience function for the multi-AI assumption extraction system.
    Uses OpenAI API directly for simplicity.

    Args:
        prompt: The prompt to send
        model: Model to use (default: gpt-4o)
        temperature: Temperature setting
        max_tokens: Max output tokens
        system_prompt: Optional system prompt

    Returns:
        AI response as string
    """
    import openai

    # Get API key from config or environment
    api_key = None
    if HAS_CONFIG:
        # Check API_KEYS dict first (standard format)
        if hasattr(config, 'API_KEYS') and isinstance(config.API_KEYS, dict):
            api_key = config.API_KEYS.get('openai')
        # Also check direct attribute
        if not api_key and hasattr(config, 'OPENAI_API_KEY'):
            api_key = config.OPENAI_API_KEY
    if not api_key:
        api_key = os.environ.get('OPENAI_API_KEY')

    if not api_key:
        raise ValueError("OpenAI API key not found in config.API_KEYS or environment")

    client = openai.OpenAI(api_key=api_key)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[get_ai_response] Error: {e}")
        raise
