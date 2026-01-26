"""
Node Executor - Executes individual nodes in the workflow
Inspired by ChatDev's runtime/node/executor architecture

Now includes Python-based valuation engine for the Financial Modeler node,
which uses real mathematical calculations instead of AI hallucination.
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from .workflow_loader import NodeConfig

# Import valuation module for Python-based calculations
try:
    from agents.valuation import ValuationOrchestrator, run_valuation_node
    VALUATION_AVAILABLE = True
except ImportError:
    VALUATION_AVAILABLE = False
    print("[WARNING] Valuation module not available. Financial Modeler will use AI fallback.")


# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 2.0  # seconds
MAX_DELAY = 60.0  # seconds


async def retry_with_backoff(func, max_retries=MAX_RETRIES, base_delay=BASE_DELAY):
    """
    Retry an async function with exponential backoff for rate limits.
    Parses retry-after from error messages when available.
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            error_str = str(e)
            last_exception = e

            # Check if this is a rate limit error (429)
            is_rate_limit = (
                "429" in error_str or
                "rate_limit" in error_str.lower() or
                "rate limit" in error_str.lower() or
                "too many requests" in error_str.lower()
            )

            if not is_rate_limit:
                # Not a rate limit error, don't retry
                raise e

            if attempt >= max_retries:
                # Max retries exceeded
                raise e

            # Try to parse retry-after time from error message
            delay = base_delay * (2 ** attempt)  # Exponential backoff

            # Look for "Please try again in X.Xs" pattern
            retry_match = re.search(r'try again in ([\d.]+)s', error_str, re.IGNORECASE)
            if retry_match:
                suggested_delay = float(retry_match.group(1))
                delay = max(delay, suggested_delay + 0.5)  # Add small buffer

            delay = min(delay, MAX_DELAY)

            print(f"    [RATE LIMIT] Attempt {attempt + 1}/{max_retries + 1} failed. "
                  f"Retrying in {delay:.1f}s...", flush=True)

            await asyncio.sleep(delay)

    raise last_exception


@dataclass
class Message:
    """Message passed between nodes"""
    role: str  # "user", "assistant", "system"
    content: str
    metadata: Dict[str, Any] = None
    source: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "source": self.source,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            role=data.get("role", "assistant"),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            source=data.get("source", ""),
            timestamp=data.get("timestamp", "")
        )


class NodeExecutor:
    """Executes a single node in the workflow graph"""

    # Provider-specific client mappings
    PROVIDERS = {
        "openai": "_execute_openai",
        "google": "_execute_google",
        "gemini": "_execute_google",
        "xai": "_execute_xai",
        "grok": "_execute_xai",
        "dashscope": "_execute_dashscope",
        "qwen": "_execute_dashscope",
        "deepseek": "_execute_deepseek",
    }

    def __init__(self, node_config: NodeConfig, api_keys: Dict[str, str]):
        self.config = node_config
        self.api_keys = api_keys
        self.execution_history: List[Message] = []

    async def execute(self, input_messages: List[Message]) -> Message:
        """Execute the node with given input messages"""
        provider = self.config.provider.lower()

        # Get the appropriate execution method
        method_name = self.PROVIDERS.get(provider)
        if not method_name:
            raise ValueError(f"Unsupported provider: {provider}")

        method = getattr(self, method_name)

        # Build the prompt from input messages
        context = self._build_context(input_messages)

        # Execute and return result
        result = await method(context)

        # Record execution
        self.execution_history.append(result)

        return result

    def _build_context(self, messages: List[Message]) -> str:
        """Build context string from input messages"""
        parts = []

        # Add the system role/instructions
        if self.config.role:
            parts.append(f"[INSTRUCTIONS]\n{self.config.role}\n")

        # Add input messages
        for msg in messages:
            source = msg.source or msg.role
            parts.append(f"[{source.upper()}]\n{msg.content}\n")

        return "\n".join(parts)

    def _get_api_key(self, key_name: str) -> str:
        """Get API key from available sources"""
        # Check direct key name
        if key_name in self.api_keys:
            return self.api_keys[key_name]

        # Check common variations
        variations = [
            key_name,
            key_name.upper(),
            key_name.lower(),
            f"{key_name}_API_KEY",
            f"{key_name.upper()}_API_KEY"
        ]

        for var in variations:
            if var in self.api_keys:
                return self.api_keys[var]

        return ""

    async def _execute_openai(self, context: str) -> Message:
        """Execute using OpenAI API with retry logic for rate limits"""
        import openai

        api_key = self._get_api_key("openai") or self._get_api_key("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found")

        client = openai.AsyncOpenAI(api_key=api_key)

        async def make_request():
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.config.role},
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=4096
            )
            return response

        try:
            # Use retry logic for rate limits
            response = await retry_with_backoff(make_request)

            content = response.choices[0].message.content

            return Message(
                role="assistant",
                content=content,
                source=self.config.id,
                metadata={
                    "provider": "openai",
                    "model": self.config.model,
                    "tokens": {
                        "prompt": response.usage.prompt_tokens,
                        "completion": response.usage.completion_tokens
                    }
                }
            )
        except Exception as e:
            return Message(
                role="assistant",
                content=f"Error executing OpenAI node: {str(e)}",
                source=self.config.id,
                metadata={"error": str(e), "is_error": True}
            )

    async def _execute_google(self, context: str) -> Message:
        """Execute using Google Gemini API"""
        import google.generativeai as genai

        api_key = self._get_api_key("google") or self._get_api_key("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Google API key not found")

        genai.configure(api_key=api_key)

        try:
            model = genai.GenerativeModel(self.config.model)

            # Build prompt with system instructions
            full_prompt = f"{self.config.role}\n\n{context}"

            response = await asyncio.to_thread(
                model.generate_content,
                full_prompt
            )

            content = response.text

            return Message(
                role="assistant",
                content=content,
                source=self.config.id,
                metadata={
                    "provider": "google",
                    "model": self.config.model
                }
            )
        except Exception as e:
            return Message(
                role="assistant",
                content=f"Error executing Google node: {str(e)}",
                source=self.config.id,
                metadata={"error": str(e)}
            )

    async def _execute_xai(self, context: str) -> Message:
        """Execute using xAI (Grok) API with retry logic"""
        import httpx

        api_key = self._get_api_key("xai") or self._get_api_key("XAI_API_KEY")
        if not api_key:
            raise ValueError("xAI API key not found")

        async def make_request():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.config.model or "grok-2",
                        "messages": [
                            {"role": "system", "content": self.config.role},
                            {"role": "user", "content": context}
                        ],
                        "temperature": 0.7
                    },
                    timeout=120.0
                )

                if response.status_code == 429:
                    raise Exception(f"xAI API rate limit: 429 - {response.text}")
                if response.status_code != 200:
                    raise Exception(f"xAI API error: {response.status_code} - {response.text}")

                data = response.json()
                return data

        try:
            data = await retry_with_backoff(make_request)
            content = data["choices"][0]["message"]["content"]

            return Message(
                role="assistant",
                content=content,
                source=self.config.id,
                metadata={
                    "provider": "xai",
                    "model": self.config.model
                }
            )
        except Exception as e:
            return Message(
                role="assistant",
                content=f"Error executing xAI node: {str(e)}",
                source=self.config.id,
                metadata={"error": str(e), "is_error": True}
            )

    async def _execute_dashscope(self, context: str) -> Message:
        """Execute using Alibaba DashScope (Qwen) API with retry logic"""
        import httpx

        api_key = self._get_api_key("dashscope") or self._get_api_key("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("DashScope API key not found")

        async def make_request():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.config.model or "qwen-plus",
                        "messages": [
                            {"role": "system", "content": self.config.role},
                            {"role": "user", "content": context}
                        ]
                    },
                    timeout=120.0
                )

                if response.status_code == 429:
                    raise Exception(f"DashScope API rate limit: 429 - {response.text}")
                if response.status_code != 200:
                    raise Exception(f"DashScope API error: {response.status_code} - {response.text}")

                data = response.json()
                return data

        try:
            data = await retry_with_backoff(make_request)
            content = data["choices"][0]["message"]["content"]

            return Message(
                role="assistant",
                content=content,
                source=self.config.id,
                metadata={
                    "provider": "dashscope",
                    "model": self.config.model
                }
            )
        except Exception as e:
            return Message(
                role="assistant",
                content=f"Error executing DashScope node: {str(e)}",
                source=self.config.id,
                metadata={"error": str(e), "is_error": True}
            )

    async def _execute_deepseek(self, context: str) -> Message:
        """Execute using DeepSeek API"""
        import httpx

        api_key = self._get_api_key("deepseek") or self._get_api_key("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DeepSeek API key not found")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.config.model or "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": self.config.role},
                            {"role": "user", "content": context}
                        ]
                    },
                    timeout=120.0
                )

                if response.status_code != 200:
                    raise Exception(f"DeepSeek API error: {response.status_code}")

                data = response.json()
                content = data["choices"][0]["message"]["content"]

                return Message(
                    role="assistant",
                    content=content,
                    source=self.config.id,
                    metadata={
                        "provider": "deepseek",
                        "model": self.config.model
                    }
                )
        except Exception as e:
            return Message(
                role="assistant",
                content=f"Error executing DeepSeek node: {str(e)}",
                source=self.config.id,
                metadata={"error": str(e)}
            )


class PassthroughExecutor:
    """Executor for passthrough nodes that just forward messages"""

    def __init__(self, node_config: NodeConfig):
        self.config = node_config

    async def execute(self, input_messages: List[Message]) -> Message:
        """Simply pass through the last message"""
        if input_messages:
            last_msg = input_messages[-1]
            return Message(
                role=last_msg.role,
                content=last_msg.content,
                source=self.config.id,
                metadata={"passthrough": True, **last_msg.metadata}
            )

        return Message(
            role="user",
            content="",
            source=self.config.id,
            metadata={"passthrough": True}
        )


class PythonValuationExecutor:
    """
    Executor for valuation nodes using Python math instead of AI.

    This executor intercepts the "Financial Modeler" node and runs
    actual DCF, Comps, DDM, and Reverse DCF calculations using real
    formulas instead of asking an AI to hallucinate numbers.

    Cross-checks all methods to ensure convergence and produces
    a comprehensive valuation report.
    """

    # Node IDs that should use Python valuation (exact or contains match)
    # Only match the main Financial Modeler node, not auxiliary valuation agents
    VALUATION_NODES_EXACT = [
        "financial_modeler",
        "financial-modeler",
        "financial modeler",
    ]

    def __init__(self, node_config: NodeConfig, context: Dict[str, Any] = None, use_multi_ai: bool = True):
        self.config = node_config
        self.context = context or {}
        self.use_multi_ai = use_multi_ai
        if VALUATION_AVAILABLE:
            # Use multi-AI extraction by default - NO HARDCODED DEFAULTS
            self.orchestrator = ValuationOrchestrator(use_multi_ai=use_multi_ai)
        else:
            self.orchestrator = None

    @classmethod
    def should_handle(cls, node_id: str) -> bool:
        """Check if this node should use Python valuation"""
        node_id_lower = node_id.lower().replace("_", " ").replace("-", " ").strip()
        # Check for exact match with Financial Modeler
        return node_id_lower in [n.replace("_", " ").replace("-", " ") for n in cls.VALUATION_NODES_EXACT]

    async def execute(self, input_messages: List[Message], prior_outputs: Dict[str, str] = None) -> Message:
        """
        Execute valuation using Python engines.

        Args:
            input_messages: Messages from upstream nodes
            prior_outputs: Dict mapping node names to their outputs

        Returns:
            Message containing comprehensive valuation results
        """
        if not VALUATION_AVAILABLE or not self.orchestrator:
            return Message(
                role="assistant",
                content="[ERROR] Valuation module not available. Please install agents.valuation module.",
                source=self.config.id,
                metadata={"error": "module_not_available", "is_error": True}
            )

        try:
            # Extract ticker from context
            ticker = self.context.get("ticker", "UNKNOWN")

            # Build debate outputs from prior node outputs
            prior_outputs = prior_outputs or {}
            debate_outputs = {
                'debate_critic': self._find_prior_output(prior_outputs, ['Debate Critic', 'debate_critic']),
                'bull_r2': self._find_prior_output(prior_outputs, ['Bull Advocate R2', 'bull_advocate_r2', 'Bull R2']),
                'bear_r2': self._find_prior_output(prior_outputs, ['Bear Advocate R2', 'bear_advocate_r2', 'Bear R2'])
            }

            # Get additional outputs for multi-AI extraction
            industry_researcher_output = self._find_prior_output(
                prior_outputs,
                ['Industry Deep Dive', 'industry_deep_dive', 'Industry Researcher', 'industry_researcher']
            )
            business_model_output = self._find_prior_output(
                prior_outputs,
                ['Company Deep Dive', 'company_deep_dive', 'Business Model', 'business_model']
            )
            company_name = self.context.get("company_name", ticker)

            # CRITICAL: Get Dot Connector output - PRIORITIZED for parameters!
            # Dot Connector synthesizes parameters from research and may include REVISIONS
            dot_connector_output = self._find_prior_output(
                prior_outputs,
                ['Dot Connector', 'dot_connector', 'DotConnector']
            )
            if dot_connector_output:
                print(f"  [Python Valuation Engine] Using Dot Connector parameters ({len(dot_connector_output)} chars)")
                if '[REVISED]' in dot_connector_output or 'REVISION REQUESTED' in dot_connector_output:
                    print(f"  [Python Valuation Engine] DOT CONNECTOR HAS REVISED PARAMETERS!")

            # Get market data from context
            market_data = self.context.get("market_data", {}).copy()

            # Try to extract market data from prior node outputs
            market_data_text = self._find_prior_output(
                prior_outputs,
                ['Market Data Collector', 'market_data_collector', 'Data Checkpoint', 'data_checkpoint']
            )
            if market_data_text:
                extracted = self._extract_market_data_from_text(market_data_text)
                # Only update if we found values
                for key, value in extracted.items():
                    if value is not None and (key not in market_data or market_data.get(key) in [None, 0]):
                        market_data[key] = value

            # Also try to extract market data from input messages
            for msg in input_messages:
                if msg.metadata and "market_data" in msg.metadata:
                    market_data.update(msg.metadata["market_data"])

            # Run valuation with multi-AI extraction (if enabled)
            # Pass dot_connector_output for parameter priority
            result = await asyncio.to_thread(
                self.orchestrator.run_valuation,
                ticker=ticker,
                debate_outputs=debate_outputs,
                market_data_raw=market_data,
                industry_researcher_output=industry_researcher_output,
                business_model_output=business_model_output,
                company_name=company_name,
                dot_connector_output=dot_connector_output
            )

            # Build formatted output
            output_text = self._format_valuation_output(result)

            return Message(
                role="assistant",
                content=output_text,
                source=self.config.id,
                metadata={
                    "provider": "python_valuation",
                    "engine": "multi_method_dcf",
                    "valuation_result": result,
                    "methods_used": list(result.get("cross_check", {}).get("method_values", {}).keys()),
                    "convergence": result.get("cross_check", {}).get("convergence_level", "UNKNOWN")
                }
            )

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            return Message(
                role="assistant",
                content=f"[VALUATION ERROR] Failed to run Python valuation: {str(e)}\n\n{error_trace}",
                source=self.config.id,
                metadata={"error": str(e), "is_error": True}
            )

    def _find_prior_output(self, prior_outputs: Dict[str, str], possible_keys: List[str]) -> str:
        """Find output from prior nodes using possible key names"""
        for key in possible_keys:
            if key in prior_outputs:
                return prior_outputs[key]
            # Try case-insensitive match
            for pk in prior_outputs:
                if pk.lower().replace(" ", "_") == key.lower().replace(" ", "_"):
                    return prior_outputs[pk]
        return ""

    def _extract_market_data_from_text(self, text: str) -> Dict[str, Any]:
        """Extract financial metrics from node output text using regex"""
        import re
        data = {}

        # Patterns for common financial metrics
        # Note: Patterns should handle multiple currencies (USD, HKD, CNY, etc.)
        patterns = {
            'current_price': [
                r'CURRENT_PRICE[:\s]*([\d,.]+)',  # CURRENT_PRICE: 60.45
                r'current\s*price[:\s]*(?:\$|HKD|USD|CNY|RMB)?\s*([\d,.]+)',
                r'price[:\s]*(?:\$|HKD|USD|CNY|RMB)?\s*([\d,.]+)\s*(?:HKD|USD|CNY|RMB)',
                r'trading\s*at[:\s]*(?:\$|HKD|USD|CNY|RMB)?\s*([\d,.]+)',
            ],
            'revenue_ttm': [
                r'revenue[:\s]*(?:TTM[:\s]*)?(?:\$|HKD|USD|CNY|RMB)?\s*([\d,.]+)\s*(?:B|billion)',
                r'revenue[:\s]*(?:TTM[:\s]*)?(?:\$|HKD|USD|CNY|RMB)?\s*([\d,.]+)\s*(?:M|million)',
                r'TTM revenue[:\s]*(?:\$|HKD|USD|CNY|RMB)?\s*([\d,.]+)\s*(?:B|billion)',
                r'Revenue[:\s]*(?:\$|HKD|USD|CNY|RMB)?\s*([\d,.]+)\s*(?:M|million)',
            ],
            'market_cap': [
                r'market\s*cap(?:italization)?[:\s]*(?:\$|HKD|USD|CNY|RMB)?\s*([\d,.]+)\s*(?:B|billion)',
                r'market\s*cap(?:italization)?[:\s]*(?:\$|HKD|USD|CNY|RMB)?\s*([\d,.]+)\s*(?:M|million)',
                r'market\s*cap(?:italization)?[:\s]*([\d,.]+)\s*(?:B|billion)\s*(?:HKD|USD|CNY|RMB)',
            ],
            'pe_ratio': [
                r'P/E(?:\s*ratio)?[:\s]*([\d,.]+)',
                r'PE(?:\s*ratio)?[:\s]*([\d,.]+)',
                r'price.to.earnings[:\s]*([\d,.]+)',
            ],
            'ev_ebitda': [
                r'EV/EBITDA[:\s]*([\d,.]+)',
                r'enterprise.value.to.EBITDA[:\s]*([\d,.]+)',
            ],
            'beta': [
                r'beta[:\s]*([\d,.]+)',
            ],
            'shares_outstanding': [
                r'shares\s*outstanding[:\s]*([\d,.]+)\s*(?:B|billion)',
                r'shares\s*outstanding[:\s]*([\d,.]+)\s*(?:M|million)',
            ],
            'net_income': [
                r'net\s*income[:\s]*(?:\$|HKD|USD|CNY|RMB)?\s*([\d,.]+)\s*(?:B|billion)',
                r'net\s*income[:\s]*(?:\$|HKD|USD|CNY|RMB)?\s*([\d,.]+)\s*(?:M|million)',
            ],
            'ebit_ttm': [
                r'(?:operating\s*income|EBIT)[:\s]*(?:\$|HKD|USD|CNY|RMB)?\s*([\d,.]+)\s*(?:B|billion)',
                r'(?:operating\s*income|EBIT)[:\s]*(?:\$|HKD|USD|CNY|RMB)?\s*([\d,.]+)\s*(?:M|million)',
            ],
        }

        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        value_str = match.group(1).replace(',', '')
                        value = float(value_str)

                        # Adjust for billions/millions in the pattern
                        pattern_lower = pattern.lower()
                        if 'billion' in pattern_lower or re.search(r'\(B\|', pattern):
                            value *= 1000  # Convert to millions
                        # Values in millions stay as-is

                        data[field] = value
                        break
                    except (ValueError, IndexError):
                        continue

        # Calculate shares_outstanding from market_cap / current_price if not found
        if 'shares_outstanding' not in data and data.get('market_cap') and data.get('current_price'):
            # market_cap is in millions, current_price is per share
            # shares = market_cap (in millions) / price = result in millions
            data['shares_outstanding'] = data['market_cap'] / data['current_price']

        return data

    def _format_valuation_output(self, result: Dict[str, Any]) -> str:
        """Format valuation result into readable text"""
        lines = []

        # Header
        lines.append("=" * 70)
        lines.append(f"MULTI-METHOD VALUATION REPORT: {result.get('ticker', 'UNKNOWN')}")
        lines.append("=" * 70)
        lines.append("")

        # Consensus
        consensus = result.get("consensus", {})
        currency = result.get('currency', '')
        current_price = result.get('current_price', 0)
        pwv = consensus.get('fair_value', 0)

        lines.append(f"Current Price: {currency} {current_price:.2f}")
        lines.append(f"CONSENSUS FAIR VALUE: {currency} {pwv:.2f}")
        lines.append(f"Implied Upside: {consensus.get('implied_upside', 0)*100:+.1f}%")
        lines.append(f"RECOMMENDATION: {consensus.get('recommendation', 'N/A')}")
        lines.append(f"Confidence: {consensus.get('confidence', 'N/A')}")
        lines.append("")

        # ============================================
        # BROKER CONSENSUS - CRITICAL FOR DCF VALIDATOR
        # This section is parsed by DCF Validator to compare our valuation
        # ============================================
        broker_target = result.get('broker_target_avg')
        broker_low = result.get('broker_target_low')
        broker_high = result.get('broker_target_high')
        broker_count = result.get('broker_count', 5)

        if broker_target and broker_target > 0:
            divergence_pct = ((pwv - broker_target) / broker_target) * 100 if broker_target else 0

            # Classify divergence
            abs_div = abs(divergence_pct)
            if abs_div < 15:
                div_class = "ALIGNED"
            elif abs_div < 30:
                div_class = "MODERATE"
            else:
                div_class = "SIGNIFICANT"

            lines.append("=" * 70)
            lines.append("*** BROKER CONSENSUS DATA (FROM LOCAL RESEARCH) ***")
            lines.append("*** DCF VALIDATOR: USE THESE VALUES - DO NOT HALLUCINATE ***")
            lines.append("=" * 70)
            lines.append(f"BROKER_AVG_TARGET: {currency} {broker_target:.2f}")
            if broker_low:
                lines.append(f"BROKER_TARGET_LOW: {currency} {broker_low:.2f}")
            if broker_high:
                lines.append(f"BROKER_TARGET_HIGH: {currency} {broker_high:.2f}")
            lines.append(f"BROKER_COUNT: {broker_count}")
            lines.append(f"OUR_DCF_TARGET: {currency} {pwv:.2f}")
            lines.append(f"DIVERGENCE_PCT: {divergence_pct:.1f}%")
            lines.append(f"DIVERGENCE_CLASS: {div_class}")
            lines.append("=" * 70)
            lines.append("")
        else:
            lines.append("=" * 70)
            lines.append("*** WARNING: NO BROKER CONSENSUS DATA AVAILABLE ***")
            lines.append("*** DCF Validator will use conservative assumptions ***")
            lines.append("=" * 70)
            lines.append("")

        # Cross-check
        cross = result.get("cross_check", {})
        lines.append("-" * 50)
        lines.append("CROSS-CHECK VALIDATION:")
        lines.append(f"  Convergence Level: {cross.get('convergence_level', 'N/A')}")
        lines.append(f"  Value Spread: {cross.get('value_spread', 0)*100:.1f}%")
        lines.append(f"  Market Alignment: {cross.get('market_alignment', 'N/A')}")
        if cross.get("issues_found"):
            lines.append("  Issues Found:")
            for issue in cross.get("issues_found", []):
                lines.append(f"    - {issue}")
        lines.append("")

        # Method breakdown
        lines.append("-" * 50)
        lines.append("METHOD BREAKDOWN:")
        lines.append("")

        # DCF
        dcf = result.get("dcf", {})
        if dcf.get("is_valid"):
            lines.append(f"  DCF (Probability-Weighted): {result.get('currency', '')} {dcf.get('probability_weighted_value', 0):.2f}")
            lines.append(f"    Implied Upside: {dcf.get('implied_upside', 0)*100:+.1f}%")
            scenarios = dcf.get("scenarios", {})
            for name, scenario in scenarios.items():
                lines.append(f"    - {name}: {result.get('currency', '')} {scenario.get('fair_value', 0):.2f} "
                           f"({scenario.get('probability', 0)*100:.0f}% prob)")

        # Comps
        comps = result.get("comps", {})
        if comps.get("is_valid"):
            lines.append(f"\n  Comps Analysis: {result.get('currency', '')} {comps.get('weighted_target', 0):.2f}")
            lines.append(f"    Implied Upside: {comps.get('implied_upside', 0)*100:+.1f}%")
            medians = comps.get("median_multiples", {})
            if medians.get("pe"):
                lines.append(f"    Peer P/E: {medians['pe']:.1f}x")
            if medians.get("ev_ebitda"):
                lines.append(f"    Peer EV/EBITDA: {medians['ev_ebitda']:.1f}x")

        # DDM
        ddm = result.get("ddm", {})
        if ddm.get("is_applicable"):
            lines.append(f"\n  DDM (Gordon Growth): {result.get('currency', '')} {ddm.get('fair_value', 0):.2f}")
            lines.append(f"    Dividend Yield: {ddm.get('dividend_yield', 0)*100:.2f}%")
            lines.append(f"    Dividend Growth: {ddm.get('dividend_growth', 0)*100:.2f}%")

        # Reverse DCF
        rdcf = result.get("reverse_dcf", {})
        if rdcf.get("is_valid"):
            lines.append(f"\n  Reverse DCF (Market Expectations):")
            lines.append(f"    Implied Growth: {rdcf.get('implied_growth_rate', 0)*100:.1f}%")
            lines.append(f"    Our Base Case: {rdcf.get('our_base_growth', 0)*100:.1f}%")
            lines.append(f"    Market View: {rdcf.get('market_view', 'N/A')}")

        # Key insights
        lines.append("")
        lines.append("-" * 50)
        lines.append("KEY DRIVERS:")
        for driver in result.get("key_drivers", []):
            lines.append(f"  + {driver}")

        lines.append("\nKEY RISKS:")
        for risk in result.get("key_risks", []):
            lines.append(f"  - {risk}")

        lines.append("")
        lines.append("=" * 70)
        lines.append("[Calculated using Python math engines - not AI hallucination]")

        return "\n".join(lines)


def get_executor(node_config: NodeConfig, api_keys: Dict[str, str], context: Dict[str, Any] = None):
    """
    Factory function to get the appropriate executor for a node.

    Returns PythonValuationExecutor for valuation nodes,
    PassthroughExecutor for passthrough nodes,
    or NodeExecutor for AI-based nodes.
    """
    # Check if this is a valuation node
    if PythonValuationExecutor.should_handle(node_config.id):
        print(f"  [Python Valuation Engine] Using mathematical models for {node_config.id}")
        return PythonValuationExecutor(node_config, context)

    # Check if passthrough
    if node_config.provider.lower() == "passthrough":
        return PassthroughExecutor(node_config)

    # Default to AI-based executor
    return NodeExecutor(node_config, api_keys)
