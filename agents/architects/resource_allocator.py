"""
Resource Allocator Agent - AI provider management and load balancing

Responsibilities:
- Track AI provider usage and rate limits
- Balance load across available providers
- Allocate providers to research tasks based on role
- Handle provider failures and recovery
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from agents.core.spawnable_agent import SpawnableAgent
from agents.base_agent import ResearchContext


class ResourceAllocatorAgent(SpawnableAgent):
    """
    Manages AI provider allocation and load balancing (Tier 0).

    Tracks usage patterns, errors, and health of each AI provider
    to make intelligent allocation decisions.

    Usage:
        allocator = ResourceAllocatorAgent(ai_provider, ai_manager)
        await allocator.activate()

        # Get optimal provider for a role
        provider = allocator.get_provider_for_role("analyst")
        provider = allocator.get_provider_for_role("critic")
    """

    # Role preferences: which providers work best for each role
    ROLE_PREFERENCES = {
        'analyst': ['GPT', 'Gemini'],      # Strong reasoning
        'synthesizer': ['GPT', 'Gemini'],   # Good at summarization
        'bull': None,                       # Any provider (diversity)
        'bear': None,                       # Any provider (diversity)
        'critic': ['Grok', 'GPT'],          # Contrarian perspective
        'devil_advocate': ['Grok', 'DeepSeek'],  # Alternative views
        'fact_checker': ['Gemini', 'GPT'],  # Factual accuracy
        'specialist': ['GPT', 'Gemini'],    # Domain expertise
    }

    def __init__(
        self,
        ai_provider,
        ai_manager=None,
        config: Optional[Dict] = None
    ):
        super().__init__(
            ai_provider=ai_provider,
            role="resource_allocator",
            parent_id=None,
            tier=0,
            config=config
        )

        self.ai_manager = ai_manager

        # Usage tracking: provider_name -> count
        self.provider_usage: Dict[str, int] = {}

        # Error tracking: provider_name -> count
        self.provider_errors: Dict[str, int] = {}

        # Last error time: provider_name -> datetime
        self.provider_last_error: Dict[str, datetime] = {}

        # Error recovery window (seconds)
        self.error_recovery_window = config.get('error_recovery_window', 300) if config else 300

        # Max errors before marking unhealthy
        self.max_provider_errors = config.get('max_provider_errors', 5) if config else 5

        # Round-robin state for diversity
        self._round_robin_index = 0

    def _get_system_prompt(self) -> str:
        return """You are a Resource Allocator managing AI provider assignments for equity research.

Your role is to:
1. Balance load across available AI providers
2. Match providers to roles based on their strengths
3. Handle rate limits and errors gracefully
4. Ensure diversity of perspectives in debates

Guidelines:
- GPT and Gemini: Best for analytical and synthesis tasks
- Grok: Good for contrarian views and challenging assumptions
- DeepSeek: Alternative perspective, good for technical analysis
- Qwen: Additional diversity, good for general analysis

Track usage and errors to maintain system health."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """Analyze allocation state and provide recommendations"""
        return await self._get_allocation_status()

    # ==========================================
    # Provider Allocation
    # ==========================================

    def get_provider_for_role(self, role: str):
        """
        Get optimal AI provider for a given role.

        Strategy:
        1. Check role preferences
        2. Filter by provider health
        3. Balance load across providers

        Args:
            role: Agent role (analyst, bull, bear, critic, etc.)

        Returns:
            AI provider instance or None
        """
        if not self.ai_manager:
            return self.ai_provider  # Fallback to default

        providers = self.ai_manager.get_all_providers()
        if not providers:
            return None

        # Get preferences for this role
        preferred = self.ROLE_PREFERENCES.get(role)

        # Try preferred providers first
        if preferred:
            for pref_name in preferred:
                provider = self._find_healthy_provider(providers, pref_name)
                if provider:
                    self._track_usage(provider.name)
                    return provider

        # No preference or preferences unavailable - use round-robin for diversity
        healthy_providers = [p for p in providers if self._is_provider_healthy(p.name)]

        if healthy_providers:
            # Round-robin selection for load balancing
            provider = healthy_providers[self._round_robin_index % len(healthy_providers)]
            self._round_robin_index += 1
            self._track_usage(provider.name)
            return provider

        # All providers unhealthy - return least errored
        if providers:
            least_errored = min(providers, key=lambda p: self.provider_errors.get(p.name, 0))
            self._track_usage(least_errored.name)
            return least_errored

        return None

    def get_diverse_providers(self, count: int = 4) -> List:
        """
        Get multiple diverse providers for parallel use.

        Used in debates to ensure different perspectives.

        Args:
            count: Number of providers needed

        Returns:
            List of AI provider instances
        """
        if not self.ai_manager:
            return [self.ai_provider] * min(count, 1)

        providers = self.ai_manager.get_all_providers()
        healthy = [p for p in providers if self._is_provider_healthy(p.name)]

        # If we have enough healthy providers, use them
        if len(healthy) >= count:
            selected = healthy[:count]
        else:
            # Use all healthy + least errored from unhealthy
            selected = healthy.copy()
            unhealthy = [p for p in providers if p not in healthy]
            unhealthy.sort(key=lambda p: self.provider_errors.get(p.name, 0))
            selected.extend(unhealthy[:count - len(selected)])

        for p in selected:
            self._track_usage(p.name)

        return selected

    def _find_healthy_provider(self, providers: List, name: str):
        """Find a healthy provider by name"""
        for p in providers:
            if p.name.lower() == name.lower() and self._is_provider_healthy(p.name):
                return p
        return None

    def _is_provider_healthy(self, provider_name: str) -> bool:
        """
        Check if provider is healthy based on error rate.

        Provider is healthy if:
        - Error count < max_provider_errors, OR
        - Last error was more than recovery_window ago
        """
        errors = self.provider_errors.get(provider_name, 0)

        if errors < self.max_provider_errors:
            return True

        # Check if enough time has passed for recovery
        last_error = self.provider_last_error.get(provider_name)
        if last_error:
            elapsed = (datetime.now() - last_error).total_seconds()
            if elapsed > self.error_recovery_window:
                # Reset error count after recovery window
                self.provider_errors[provider_name] = 0
                return True

        return False

    def _track_usage(self, provider_name: str):
        """Track provider usage"""
        self.provider_usage[provider_name] = self.provider_usage.get(provider_name, 0) + 1

    # ==========================================
    # Error Reporting
    # ==========================================

    def report_error(self, provider_name: str, error_msg: str = None):
        """
        Report a provider error.

        Called when a provider fails (rate limit, timeout, etc.)

        Args:
            provider_name: Name of the failing provider
            error_msg: Optional error message
        """
        self.provider_errors[provider_name] = self.provider_errors.get(provider_name, 0) + 1
        self.provider_last_error[provider_name] = datetime.now()

    def report_success(self, provider_name: str):
        """
        Report a provider success.

        Reduces error count on successful calls.

        Args:
            provider_name: Name of the successful provider
        """
        if provider_name in self.provider_errors:
            self.provider_errors[provider_name] = max(0, self.provider_errors[provider_name] - 1)

    def reset_provider_errors(self, provider_name: str = None):
        """
        Reset error counts.

        Args:
            provider_name: Specific provider to reset, or None for all
        """
        if provider_name:
            self.provider_errors[provider_name] = 0
        else:
            self.provider_errors.clear()

    # ==========================================
    # Status and Statistics
    # ==========================================

    def get_provider_health(self) -> Dict[str, Dict]:
        """Get health status of all providers"""
        if not self.ai_manager:
            return {}

        health = {}
        for provider in self.ai_manager.get_all_providers():
            name = provider.name
            health[name] = {
                'healthy': self._is_provider_healthy(name),
                'usage_count': self.provider_usage.get(name, 0),
                'error_count': self.provider_errors.get(name, 0),
                'last_error': self.provider_last_error.get(name, None)
            }
            if health[name]['last_error']:
                health[name]['last_error'] = health[name]['last_error'].isoformat()

        return health

    def get_usage_statistics(self) -> Dict:
        """Get usage statistics"""
        return {
            'total_requests': sum(self.provider_usage.values()),
            'by_provider': self.provider_usage.copy(),
            'total_errors': sum(self.provider_errors.values()),
            'errors_by_provider': self.provider_errors.copy()
        }

    async def _get_allocation_status(self) -> str:
        """Get AI-generated allocation status"""
        health = self.get_provider_health()
        stats = self.get_usage_statistics()

        prompt = f"""Generate a resource allocation status report.

Provider Health:
{health}

Usage Statistics:
{stats}

Role Preferences:
{self.ROLE_PREFERENCES}

Provide:
1. Overall provider health assessment
2. Load distribution analysis
3. Any concerns (overloaded providers, high error rates)
4. Recommendations for optimization"""

        return await self.respond(prompt)

    # ==========================================
    # Lifecycle Hooks
    # ==========================================

    async def _on_activate(self):
        """Initialize on activation"""
        self.set_task("Managing AI provider allocation")

        # Initialize usage tracking for all providers
        if self.ai_manager:
            for provider in self.ai_manager.get_all_providers():
                if provider.name not in self.provider_usage:
                    self.provider_usage[provider.name] = 0
                if provider.name not in self.provider_errors:
                    self.provider_errors[provider.name] = 0
