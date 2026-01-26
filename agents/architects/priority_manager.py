"""
Priority Manager Agent - Research queue prioritization

Responsibilities:
- Maintain prioritized research queue
- Factor in events, staleness, market conditions
- Rebalance priorities dynamically
- Track urgency levels
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import heapq

from agents.core.spawnable_agent import SpawnableAgent
from agents.base_agent import ResearchContext


@dataclass(order=True)
class PrioritizedTicker:
    """Ticker with priority score for heap operations"""
    priority_score: float  # Higher = more urgent
    ticker: str = field(compare=False)
    company: str = field(compare=False)
    metadata: Dict = field(default_factory=dict, compare=False)

    def __post_init__(self):
        # Negate score for max-heap behavior (heapq is min-heap)
        self.priority_score = -self.priority_score


class PriorityManagerAgent(SpawnableAgent):
    """
    Determines research order and urgency (Tier 0).

    Uses multiple factors to calculate priority:
    - Staleness: Days since last update
    - Events: Upcoming earnings, catalysts
    - Volatility: Recent price movement
    - User priority: Explicit priority boosts

    Usage:
        priority_mgr = PriorityManagerAgent(ai_provider)
        await priority_mgr.activate()

        # Add tickers with metadata
        priority_mgr.add_ticker("9660 HK", "Linklogis", {
            'last_updated': '2026-01-15',
            'has_upcoming_earnings': True
        })

        # Get next batch to research
        next_batch = priority_mgr.get_next_batch(3)
    """

    # Priority weights
    STALENESS_WEIGHT = 30      # Max 30 points for staleness
    EVENT_WEIGHT = 40          # Max 40 points for events
    VOLATILITY_WEIGHT = 20     # Max 20 points for volatility
    USER_PRIORITY_WEIGHT = 10  # Max 10 points for user boost

    def __init__(self, ai_provider, config: Optional[Dict] = None):
        super().__init__(
            ai_provider=ai_provider,
            role="priority_manager",
            parent_id=None,
            tier=0,
            config=config
        )

        # Priority queue (max-heap via negated scores)
        self._priority_heap: List[PrioritizedTicker] = []

        # Ticker metadata: ticker -> metadata dict
        self._ticker_metadata: Dict[str, Dict] = {}

        # Configuration
        self.staleness_threshold_days = config.get('staleness_threshold_days', 30) if config else 30

        # Processing state
        self._in_progress: set = set()
        self._completed: set = set()
        self._failed: set = set()

    def _get_system_prompt(self) -> str:
        return """You are a Priority Manager for equity research.

Your role is to determine research order based on:
1. Upcoming catalysts (earnings dates, product launches, regulatory events)
2. Research staleness (days since last update)
3. Market volatility (recent price movements)
4. User-specified priorities

Guidelines:
- Earnings within 2 weeks = highest priority
- Research older than 30 days = elevated priority
- High volatility (>5% recent move) = elevated priority
- Balance urgent needs with portfolio coverage

Provide clear prioritization logic and recommendations."""

    async def analyze(self, context: ResearchContext, **kwargs) -> str:
        """Analyze and provide priority recommendations"""
        action = kwargs.get('action', 'status')

        if action == 'recommend':
            return await self._recommend_priorities()
        elif action == 'explain':
            ticker = kwargs.get('ticker')
            return await self._explain_priority(ticker)
        else:
            return await self._get_priority_status()

    # ==========================================
    # Queue Management
    # ==========================================

    def add_ticker(
        self,
        ticker: str,
        company: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add a ticker to the priority queue.

        Args:
            ticker: Stock ticker
            company: Company name
            metadata: Additional info for priority calculation:
                - last_updated: ISO date of last research
                - has_upcoming_earnings: bool
                - has_catalyst: bool
                - recent_volatility: float (0-1)
                - user_priority: bool (explicit boost)
                - sector: str
                - industry: str
        """
        meta = metadata or {}
        self._ticker_metadata[ticker] = {
            'company': company,
            'added_at': datetime.now().isoformat(),
            **meta
        }

        score = self.calculate_priority_score(ticker, meta)

        item = PrioritizedTicker(
            priority_score=score,
            ticker=ticker,
            company=company,
            metadata=meta
        )

        heapq.heappush(self._priority_heap, item)

    def add_tickers_bulk(self, tickers: List[Dict]):
        """
        Add multiple tickers at once.

        Args:
            tickers: List of {'ticker': str, 'company': str, ...metadata}
        """
        for t in tickers:
            ticker = t.get('ticker') or t.get('Ticker')
            company = t.get('company') or t.get('name') or t.get('Company')
            metadata = {k: v for k, v in t.items() if k not in ('ticker', 'Ticker', 'company', 'name', 'Company')}
            if ticker:
                self.add_ticker(ticker, company or ticker, metadata)

    def remove_ticker(self, ticker: str):
        """Remove a ticker from the queue"""
        self._priority_heap = [t for t in self._priority_heap if t.ticker != ticker]
        heapq.heapify(self._priority_heap)

        if ticker in self._ticker_metadata:
            del self._ticker_metadata[ticker]

    def update_ticker_metadata(self, ticker: str, metadata: Dict):
        """Update metadata and recalculate priority"""
        if ticker in self._ticker_metadata:
            self._ticker_metadata[ticker].update(metadata)
            # Remove and re-add to update priority
            self.remove_ticker(ticker)
            self.add_ticker(
                ticker,
                self._ticker_metadata[ticker].get('company', ticker),
                self._ticker_metadata[ticker]
            )

    # ==========================================
    # Priority Calculation
    # ==========================================

    def calculate_priority_score(self, ticker: str, metadata: Dict) -> float:
        """
        Calculate priority score for a ticker.

        Higher score = higher priority.

        Factors:
        - Staleness: days since last update (max 30 points)
        - Events: upcoming earnings/catalysts (max 40 points)
        - Volatility: recent price movement (max 20 points)
        - User boost: explicit priority (max 10 points)

        Args:
            ticker: Stock ticker
            metadata: Ticker metadata

        Returns:
            Priority score (0-100)
        """
        score = 0.0

        # Staleness factor
        last_updated = metadata.get('last_updated')
        if last_updated:
            try:
                if isinstance(last_updated, str):
                    last_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                else:
                    last_dt = last_updated
                days_old = (datetime.now() - last_dt.replace(tzinfo=None)).days
                staleness_score = min(self.STALENESS_WEIGHT, days_old)
            except:
                staleness_score = self.STALENESS_WEIGHT  # Parse error = assume stale
        else:
            staleness_score = self.STALENESS_WEIGHT  # Never updated = max staleness

        score += staleness_score

        # Event factor
        if metadata.get('has_upcoming_earnings'):
            score += self.EVENT_WEIGHT  # Full points for earnings
        elif metadata.get('has_catalyst'):
            score += self.EVENT_WEIGHT * 0.6  # 60% for other catalysts
        elif metadata.get('upcoming_event'):
            score += self.EVENT_WEIGHT * 0.4  # 40% for generic events

        # Volatility factor
        volatility = metadata.get('recent_volatility', 0)
        if isinstance(volatility, (int, float)):
            # volatility is expected as decimal (0.05 = 5%)
            vol_score = min(self.VOLATILITY_WEIGHT, volatility * 100 * 2)  # 10% move = max
            score += vol_score

        # User priority boost
        if metadata.get('user_priority') or metadata.get('priority') == 'high':
            score += self.USER_PRIORITY_WEIGHT
        elif metadata.get('priority') == 'urgent':
            score += self.USER_PRIORITY_WEIGHT * 1.5  # 150% for urgent

        return score

    def recalculate_all_priorities(self):
        """Recalculate priorities for all tickers"""
        tickers_to_readd = []

        for item in self._priority_heap:
            meta = self._ticker_metadata.get(item.ticker, {})
            tickers_to_readd.append((item.ticker, item.company, meta))

        self._priority_heap = []

        for ticker, company, meta in tickers_to_readd:
            self.add_ticker(ticker, company, meta)

    # ==========================================
    # Queue Access
    # ==========================================

    def get_next_batch(self, batch_size: int = 3) -> List[Dict]:
        """
        Get next batch of tickers to research.

        Args:
            batch_size: Number of tickers to return

        Returns:
            List of {'ticker': str, 'company': str, 'priority_score': float, ...}
        """
        batch = []

        # Create copy of heap for iteration without modification
        heap_copy = list(self._priority_heap)

        while len(batch) < batch_size and heap_copy:
            item = heapq.heappop(heap_copy)

            # Skip if already in progress or completed
            if item.ticker in self._in_progress or item.ticker in self._completed:
                continue

            batch.append({
                'ticker': item.ticker,
                'company': item.company,
                'priority_score': -item.priority_score,  # Un-negate
                **item.metadata
            })

        return batch

    def peek_queue(self, count: int = 10) -> List[Dict]:
        """
        Peek at top items in queue without removing them.

        Args:
            count: Number of items to peek

        Returns:
            List of ticker info dicts
        """
        # Sort by priority (remember scores are negated)
        sorted_items = sorted(self._priority_heap)[:count]

        return [{
            'ticker': item.ticker,
            'company': item.company,
            'priority_score': -item.priority_score,
            'status': 'in_progress' if item.ticker in self._in_progress
                     else 'completed' if item.ticker in self._completed
                     else 'pending',
            **item.metadata
        } for item in sorted_items]

    def mark_in_progress(self, ticker: str):
        """Mark a ticker as being researched"""
        self._in_progress.add(ticker)

    def mark_completed(self, ticker: str, success: bool = True):
        """Mark a ticker as completed"""
        self._in_progress.discard(ticker)
        if success:
            self._completed.add(ticker)
        else:
            self._failed.add(ticker)

    def get_queue_size(self) -> int:
        """Get number of pending tickers"""
        return len([t for t in self._priority_heap
                   if t.ticker not in self._in_progress
                   and t.ticker not in self._completed])

    def get_statistics(self) -> Dict:
        """Get queue statistics"""
        return {
            'total': len(self._priority_heap),
            'pending': self.get_queue_size(),
            'in_progress': len(self._in_progress),
            'completed': len(self._completed),
            'failed': len(self._failed)
        }

    # ==========================================
    # AI-Powered Analysis
    # ==========================================

    async def _get_priority_status(self) -> str:
        """Get priority queue status"""
        stats = self.get_statistics()
        top_items = self.peek_queue(5)

        prompt = f"""Generate a priority queue status report.

Statistics:
{stats}

Top 5 Priorities:
{top_items}

Provide:
1. Queue health assessment
2. Current priorities summary
3. Any concerns (bottlenecks, neglected tickers)
4. Recommendations"""

        return await self.respond(prompt)

    async def _recommend_priorities(self) -> str:
        """Get AI recommendations for priority adjustments"""
        all_items = self.peek_queue(20)

        prompt = f"""Analyze the current priority queue and recommend adjustments.

Current Queue (top 20):
{all_items}

Scoring Weights:
- Staleness: {self.STALENESS_WEIGHT} points max
- Events: {self.EVENT_WEIGHT} points max
- Volatility: {self.VOLATILITY_WEIGHT} points max
- User Priority: {self.USER_PRIORITY_WEIGHT} points max

Recommend:
1. Any tickers that should be reprioritized
2. Tickers that might need metadata updates
3. Suggested batch groupings
4. Overall queue optimization suggestions"""

        return await self.respond(prompt)

    async def _explain_priority(self, ticker: str) -> str:
        """Explain why a ticker has its current priority"""
        if ticker not in self._ticker_metadata:
            return f"Ticker {ticker} not found in queue."

        meta = self._ticker_metadata[ticker]
        score = self.calculate_priority_score(ticker, meta)

        prompt = f"""Explain the priority calculation for {ticker}.

Metadata:
{meta}

Calculated Score: {score}/100

Break down:
1. Staleness contribution
2. Event contribution
3. Volatility contribution
4. User priority contribution
5. Justification for current position in queue"""

        return await self.respond(prompt)

    # ==========================================
    # Lifecycle Hooks
    # ==========================================

    async def _on_activate(self):
        """Initialize on activation"""
        self.set_task("Managing research priorities")
