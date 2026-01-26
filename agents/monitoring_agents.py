"""
Monitoring Agents - Continuous surveillance of companies and portfolio
These agents watch for news, events, and changes that require updates
"""

import json
import asyncio
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Visualizer integration
try:
    from visualizer.visualizer_bridge import VisualizerBridge
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False


class EventSeverity(Enum):
    CRITICAL = "critical"      # Requires immediate report update
    HIGH = "high"              # Should trigger re-analysis
    MEDIUM = "medium"          # Note for next review
    LOW = "low"                # Informational only


class EventType(Enum):
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    MANAGEMENT = "management"
    REGULATORY = "regulatory"
    PRODUCT = "product"
    PARTNERSHIP = "partnership"
    ACQUISITION = "acquisition"
    FINANCING = "financing"
    LEGAL = "legal"
    MARKET = "market"
    COMPETITOR = "competitor"
    MACRO = "macro"


@dataclass
class NewsEvent:
    """A news event for a company"""
    ticker: str
    company_name: str
    event_type: EventType
    severity: EventSeverity
    headline: str
    summary: str
    source: str
    url: str
    published_date: str
    valuation_impact: str  # 'positive', 'negative', 'neutral', 'unknown'
    requires_update: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MonitoringReport:
    """Daily monitoring report"""
    date: str
    events: List[NewsEvent] = field(default_factory=list)
    tickers_requiring_update: List[str] = field(default_factory=list)
    new_companies_detected: List[str] = field(default_factory=list)
    summary: str = ""


class NewsMonitorAgent:
    """
    Monitors news and events for all portfolio companies
    - Earnings announcements
    - Guidance updates
    - Management changes
    - Regulatory news
    - Product launches/approvals
    - M&A activity
    - Financing events
    """

    def __init__(self, context_dir: str = "context"):
        self.context_dir = Path(context_dir)
        self.news_cache_dir = self.context_dir / "news_cache"
        self.news_cache_dir.mkdir(exist_ok=True)
        self.agent_name = "NewsMonitor"

        # Keywords that indicate significant events
        self.high_impact_keywords = {
            'earnings': ['beat', 'miss', 'profit', 'loss', 'revenue', 'guidance'],
            'management': ['ceo', 'cfo', 'resign', 'appoint', 'step down', 'executive'],
            'regulatory': ['fda', 'approval', 'reject', 'clearance', 'investigation', 'fine'],
            'product': ['launch', 'release', 'recall', 'trial', 'phase', 'data'],
            'deal': ['acquire', 'merger', 'partnership', 'license', 'collaboration'],
            'financing': ['offering', 'raise', 'debt', 'equity', 'dilution', 'buyback']
        }

    async def monitor_company(self, ticker: str, company_name: str) -> List[NewsEvent]:
        """Monitor news for a single company"""
        events = []

        # Run different news checks in parallel
        checks = await asyncio.gather(
            self._check_earnings_news(ticker, company_name),
            self._check_regulatory_news(ticker, company_name),
            self._check_product_news(ticker, company_name),
            self._check_management_news(ticker, company_name),
            self._check_deal_news(ticker, company_name),
            self._check_market_news(ticker, company_name),
            return_exceptions=True
        )

        for check_result in checks:
            if isinstance(check_result, list):
                events.extend(check_result)

        return events

    async def _check_earnings_news(self, ticker: str, company_name: str) -> List[NewsEvent]:
        """Check for earnings-related news"""
        # In production, this would call news APIs
        # For now, return structure for demonstration
        return []

    async def _check_regulatory_news(self, ticker: str, company_name: str) -> List[NewsEvent]:
        """Check for regulatory news (especially important for biotech)"""
        return []

    async def _check_product_news(self, ticker: str, company_name: str) -> List[NewsEvent]:
        """Check for product-related news"""
        return []

    async def _check_management_news(self, ticker: str, company_name: str) -> List[NewsEvent]:
        """Check for management changes"""
        return []

    async def _check_deal_news(self, ticker: str, company_name: str) -> List[NewsEvent]:
        """Check for M&A, partnerships, licensing deals"""
        return []

    async def _check_market_news(self, ticker: str, company_name: str) -> List[NewsEvent]:
        """Check for market-moving news"""
        return []

    def _assess_event_severity(self, event_type: EventType, headline: str, content: str) -> EventSeverity:
        """Assess the severity of a news event"""
        headline_lower = headline.lower()
        content_lower = content.lower()

        # Critical events
        critical_patterns = [
            'bankruptcy', 'fraud', 'delisting', 'halt', 'investigation',
            'ceo resign', 'cfo resign', 'restatement', 'recall'
        ]
        for pattern in critical_patterns:
            if pattern in headline_lower or pattern in content_lower:
                return EventSeverity.CRITICAL

        # High impact events
        high_patterns = [
            'acquisition', 'merger', 'guidance', 'beat', 'miss',
            'approval', 'rejection', 'phase 3', 'partnership'
        ]
        for pattern in high_patterns:
            if pattern in headline_lower:
                return EventSeverity.HIGH

        # Medium impact
        medium_patterns = [
            'launch', 'upgrade', 'downgrade', 'target', 'analyst'
        ]
        for pattern in medium_patterns:
            if pattern in headline_lower:
                return EventSeverity.MEDIUM

        return EventSeverity.LOW

    def _should_trigger_update(self, event: NewsEvent) -> bool:
        """Determine if event should trigger a report update"""
        if event.severity in [EventSeverity.CRITICAL, EventSeverity.HIGH]:
            return True

        if event.event_type in [EventType.EARNINGS, EventType.GUIDANCE,
                                EventType.REGULATORY, EventType.ACQUISITION]:
            return True

        return False


class PriceMonitorAgent:
    """
    Monitors price movements and alerts on significant changes
    - Daily price changes
    - Comparison to target prices
    - Unusual volume
    - Technical signals
    """

    def __init__(self, context_dir: str = "context"):
        self.context_dir = Path(context_dir)
        self.agent_name = "PriceMonitor"

        # Thresholds
        self.daily_move_threshold = 0.05  # 5% daily move
        self.weekly_move_threshold = 0.10  # 10% weekly move
        self.target_breach_threshold = 0.05  # Within 5% of target

    async def monitor_company(self, ticker: str, context_data: Dict) -> List[NewsEvent]:
        """Monitor price for a single company"""
        events = []

        checks = await asyncio.gather(
            self._check_price_movement(ticker, context_data),
            self._check_target_proximity(ticker, context_data),
            self._check_volume_anomaly(ticker, context_data),
            return_exceptions=True
        )

        for check_result in checks:
            if isinstance(check_result, list):
                events.extend(check_result)

        return events

    async def _check_price_movement(self, ticker: str, data: Dict) -> List[NewsEvent]:
        """Check for significant price movements"""
        events = []
        # Would fetch real-time price data in production
        return events

    async def _check_target_proximity(self, ticker: str, data: Dict) -> List[NewsEvent]:
        """Check if price is approaching target"""
        events = []
        current_price = data.get('current_price', 0)
        target_price = data.get('target_price', 0)

        if current_price > 0 and target_price > 0:
            proximity = abs(current_price - target_price) / target_price

            if proximity < self.target_breach_threshold:
                events.append(NewsEvent(
                    ticker=ticker,
                    company_name=data.get('company_name', ticker),
                    event_type=EventType.MARKET,
                    severity=EventSeverity.MEDIUM,
                    headline=f"{ticker} approaching target price",
                    summary=f"Current: {current_price}, Target: {target_price}",
                    source="PriceMonitor",
                    url="",
                    published_date=datetime.now().isoformat(),
                    valuation_impact="neutral",
                    requires_update=True
                ))

        return events

    async def _check_volume_anomaly(self, ticker: str, data: Dict) -> List[NewsEvent]:
        """Check for unusual trading volume"""
        return []


class ListMonitorAgent:
    """
    Monitors the equity list for changes
    - Detects new companies added
    - Detects removed companies
    - Tracks list modifications
    """

    def __init__(self, list_file: str = "list.txt", context_dir: str = "context"):
        self.list_file = Path(list_file)
        self.context_dir = Path(context_dir)
        self.state_file = self.context_dir / "list_monitor_state.json"
        self.agent_name = "ListMonitor"

    def _get_list_hash(self, content: str) -> str:
        """Get hash of list content"""
        return hashlib.md5(content.encode()).hexdigest()

    def _parse_list(self, content: str) -> Dict[str, str]:
        """Parse equity list into ticker -> company name mapping"""
        equities = {}
        for line in content.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Parse "TICKER - Company Name" format
                if ' - ' in line:
                    parts = line.split(' - ', 1)
                    ticker = parts[0].strip()
                    company = parts[1].strip() if len(parts) > 1 else ticker
                    equities[ticker] = company
                else:
                    # Just ticker
                    equities[line] = line
        return equities

    def _load_previous_state(self) -> Dict:
        """Load previous monitoring state"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {'hash': '', 'equities': {}, 'last_check': ''}

    def _save_state(self, state: Dict):
        """Save current state"""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    async def check_for_changes(self) -> Tuple[List[str], List[str], bool]:
        """
        Check if list has changed
        Returns: (new_tickers, removed_tickers, has_changes)
        """
        if not self.list_file.exists():
            return [], [], False

        with open(self.list_file, 'r', encoding='utf-8') as f:
            content = f.read()

        current_hash = self._get_list_hash(content)
        current_equities = self._parse_list(content)

        previous_state = self._load_previous_state()
        previous_equities = previous_state.get('equities', {})

        # Find changes
        new_tickers = [t for t in current_equities if t not in previous_equities]
        removed_tickers = [t for t in previous_equities if t not in current_equities]
        has_changes = current_hash != previous_state.get('hash', '')

        # Update state
        self._save_state({
            'hash': current_hash,
            'equities': current_equities,
            'last_check': datetime.now().isoformat()
        })

        if new_tickers:
            print(f"  [ListMonitor] New companies detected: {new_tickers}")
        if removed_tickers:
            print(f"  [ListMonitor] Companies removed: {removed_tickers}")

        return new_tickers, removed_tickers, has_changes

    def get_current_list(self) -> Dict[str, str]:
        """Get current equity list"""
        if not self.list_file.exists():
            return {}

        with open(self.list_file, 'r', encoding='utf-8') as f:
            content = f.read()

        return self._parse_list(content)


class CompetitorMonitorAgent:
    """
    Monitors competitor activity for portfolio companies
    - New product launches by competitors
    - Competitor earnings
    - Market share changes
    """

    def __init__(self, context_dir: str = "context"):
        self.context_dir = Path(context_dir)
        self.agent_name = "CompetitorMonitor"

    async def monitor_competitors(self, ticker: str, context_data: Dict) -> List[NewsEvent]:
        """Monitor competitor news for a company"""
        events = []
        competitors = context_data.get('competitors', [])

        # Would monitor each competitor in parallel
        if competitors:
            checks = await asyncio.gather(
                *[self._check_competitor(ticker, comp) for comp in competitors[:5]],  # Limit to top 5
                return_exceptions=True
            )
            for check_result in checks:
                if isinstance(check_result, list):
                    events.extend(check_result)

        return events

    async def _check_competitor(self, ticker: str, competitor: str) -> List[NewsEvent]:
        """Check news for a specific competitor"""
        return []


class MonitoringOrchestrator:
    """
    Orchestrates all monitoring agents
    Runs on schedule (6am and 6pm) or on-demand
    """

    def __init__(self, context_dir: str = "context", visualizer=None):
        self.context_dir = Path(context_dir)
        self.reports_dir = self.context_dir / "monitoring_reports"
        self.reports_dir.mkdir(exist_ok=True)

        # Visualizer for real-time updates
        self.visualizer = visualizer
        if self.visualizer is None and VISUALIZER_AVAILABLE:
            try:
                self.visualizer = VisualizerBridge(context_dir)
            except:
                self.visualizer = None

        # Initialize agents
        self.news_monitor = NewsMonitorAgent(context_dir)
        self.price_monitor = PriceMonitorAgent(context_dir)
        self.list_monitor = ListMonitorAgent(context_dir=context_dir)
        self.competitor_monitor = CompetitorMonitorAgent(context_dir)

    async def run_full_scan(self) -> MonitoringReport:
        """Run complete monitoring scan on all equities"""
        report = MonitoringReport(date=datetime.now().strftime('%Y-%m-%d'))

        print(f"\n{'='*60}")
        print(f"MONITORING SCAN: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*60}")

        # Update visualizer
        if self.visualizer:
            self.visualizer.update_agent_task(
                "orchestrator",
                "Starting monitoring scan",
                progress=5
            )

        # Check for list changes first
        new_tickers, removed_tickers, list_changed = await self.list_monitor.check_for_changes()
        report.new_companies_detected = new_tickers

        # Get all equities to monitor
        equities = self.list_monitor.get_current_list()

        # Load context for each equity
        equity_contexts = {}
        for ticker in equities:
            context_file = self.context_dir / f"{ticker.replace(' ', '_').replace('.', '_')}.json"
            if context_file.exists():
                with open(context_file, 'r', encoding='utf-8') as f:
                    equity_contexts[ticker] = json.load(f)
            else:
                # Try to find file with similar name
                for f in self.context_dir.glob("*.json"):
                    if ticker.replace(' ', '_') in f.stem:
                        with open(f, 'r', encoding='utf-8') as file:
                            equity_contexts[ticker] = json.load(file)
                        break

        # Run monitoring for each equity in parallel
        print(f"  Monitoring {len(equities)} equities...")

        # Update visualizer
        if self.visualizer:
            self.visualizer.update_agent_task(
                "orchestrator",
                f"Monitoring {len(equities)} equities",
                progress=30
            )

        all_events = await asyncio.gather(
            *[self._monitor_single_equity(ticker, equity_contexts.get(ticker, {}))
              for ticker in equities],
            return_exceptions=True
        )

        # Update visualizer progress
        if self.visualizer:
            self.visualizer.update_agent_task(
                "orchestrator",
                f"Processing monitoring results",
                progress=80
            )

        # Aggregate events
        for events in all_events:
            if isinstance(events, list):
                report.events.extend(events)
                for event in events:
                    if event.requires_update and event.ticker not in report.tickers_requiring_update:
                        report.tickers_requiring_update.append(event.ticker)

        # Add new companies to update list
        report.tickers_requiring_update.extend(new_tickers)

        # Generate summary
        report.summary = self._generate_summary(report)

        # Save report
        report_file = self.reports_dir / f"monitoring_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'date': report.date,
                'events': [vars(e) for e in report.events],
                'tickers_requiring_update': report.tickers_requiring_update,
                'new_companies_detected': report.new_companies_detected,
                'summary': report.summary
            }, f, indent=2, default=str)

        print(f"\n{report.summary}")
        print(f"\nReport saved: {report_file}")

        # Update visualizer completion
        if self.visualizer:
            self.visualizer.update_agent_task(
                "orchestrator",
                f"Monitoring complete - {len(report.events)} events",
                progress=100
            )

        return report

    async def _monitor_single_equity(self, ticker: str, context_data: Dict) -> List[NewsEvent]:
        """Run all monitors for a single equity"""
        events = []

        monitors = await asyncio.gather(
            self.news_monitor.monitor_company(ticker, context_data.get('company_name', ticker)),
            self.price_monitor.monitor_company(ticker, context_data),
            self.competitor_monitor.monitor_competitors(ticker, context_data),
            return_exceptions=True
        )

        for result in monitors:
            if isinstance(result, list):
                events.extend(result)

        return events

    def _generate_summary(self, report: MonitoringReport) -> str:
        """Generate human-readable summary"""
        lines = [
            f"MONITORING SUMMARY - {report.date}",
            f"{'='*40}",
            f"Total events detected: {len(report.events)}",
            f"Tickers requiring update: {len(report.tickers_requiring_update)}",
            f"New companies detected: {len(report.new_companies_detected)}",
        ]

        if report.tickers_requiring_update:
            lines.append(f"\nUpdates needed for: {', '.join(report.tickers_requiring_update)}")

        if report.new_companies_detected:
            lines.append(f"\nNew companies to research: {', '.join(report.new_companies_detected)}")

        # Count by severity
        severity_counts = {}
        for event in report.events:
            sev = event.severity.value if isinstance(event.severity, EventSeverity) else event.severity
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if severity_counts:
            lines.append(f"\nEvents by severity:")
            for sev, count in sorted(severity_counts.items()):
                lines.append(f"  - {sev}: {count}")

        return '\n'.join(lines)


async def run_monitoring_scan():
    """Run a full monitoring scan"""
    orchestrator = MonitoringOrchestrator()
    return await orchestrator.run_full_scan()


if __name__ == "__main__":
    asyncio.run(run_monitoring_scan())
