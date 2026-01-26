"""
Run Monitoring - Standalone script for news and event monitoring
Monitors all portfolio companies in parallel for:
1. News events (earnings, regulatory, M&A, etc.)
2. Price movements
3. List changes (new companies)
4. Competitor activity

Usage:
    python run_monitoring.py              # Run full scan
    python run_monitoring.py --ticker "LEGN US"  # Monitor specific ticker
    python run_monitoring.py --list-only  # Only check for list changes
"""

import asyncio
import argparse
from datetime import datetime
from pathlib import Path

from agents.monitoring_agents import (
    MonitoringOrchestrator,
    NewsMonitorAgent,
    PriceMonitorAgent,
    ListMonitorAgent,
    CompetitorMonitorAgent
)
from config import EQUITIES

# Visualizer integration
try:
    from visualizer.visualizer_bridge import VisualizerBridge
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False


def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           EQUITY RESEARCH MONITORING SYSTEM                   ║
║           News, Price, and Event Tracking                     ║
╚═══════════════════════════════════════════════════════════════╝
    """)


async def run_full_monitoring():
    """Run full monitoring scan"""
    print_banner()

    # Initialize visualizer
    visualizer = None
    if VISUALIZER_AVAILABLE:
        visualizer = VisualizerBridge("context")
        # Spawn monitoring orchestrator
        visualizer.spawn_agent(
            agent_type="orchestrator",
            name="Monitoring Orchestrator",
            tier=0,
            task="Coordinating monitoring",
            agent_id="monitoring-orchestrator"
        )
        visualizer.activate_agent("monitoring-orchestrator", "Starting monitoring scan")

        # Spawn monitoring worker agents
        for agent_info in [
            ("news-monitor", "News Monitor", "specialist"),
            ("price-monitor", "Price Monitor", "specialist"),
            ("list-monitor", "List Monitor", "specialist"),
            ("competitor-monitor", "Competitor Monitor", "specialist")
        ]:
            agent_id, name, agent_type = agent_info
            visualizer.spawn_agent(
                agent_type=agent_type,
                name=name,
                parent_id="monitoring-orchestrator",
                tier=2,
                task=f"Monitoring {len(EQUITIES)} equities",
                agent_id=agent_id
            )
            visualizer.activate_agent(agent_id, f"Scanning {len(EQUITIES)} equities")

    orchestrator = MonitoringOrchestrator()
    print(f"Starting full monitoring scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Monitoring {len(EQUITIES)} equities...\n")

    report = await orchestrator.run_full_scan()

    # Update visualizer with completion
    if visualizer:
        for agent_id in ["news-monitor", "price-monitor", "list-monitor", "competitor-monitor"]:
            visualizer.update_agent_task(agent_id, "Monitoring complete", progress=100)
        visualizer.update_agent_task("monitoring-orchestrator", "Monitoring complete", progress=100)

    # Print detailed summary
    print(f"\n{'='*60}")
    print("MONITORING RESULTS")
    print(f"{'='*60}")

    if report.events:
        print(f"\nEVENTS DETECTED ({len(report.events)}):")
        print("-" * 40)
        for event in report.events:
            severity_icon = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🔵'
            }.get(event.severity.value if hasattr(event.severity, 'value') else event.severity, '⚪')

            print(f"\n  {severity_icon} [{event.ticker}] {event.headline}")
            print(f"     Type: {event.event_type.value if hasattr(event.event_type, 'value') else event.event_type}")
            print(f"     Impact: {event.valuation_impact}")
            if event.requires_update:
                print(f"     ⚠️ REQUIRES REPORT UPDATE")

    if report.tickers_requiring_update:
        print(f"\n{'='*60}")
        print("TICKERS REQUIRING UPDATE")
        print(f"{'='*60}")
        for ticker in report.tickers_requiring_update:
            print(f"  • {ticker}")

    if report.new_companies_detected:
        print(f"\n{'='*60}")
        print("NEW COMPANIES DETECTED")
        print(f"{'='*60}")
        for ticker in report.new_companies_detected:
            company = EQUITIES.get(ticker, {}).get('name', 'Unknown')
            print(f"  • {ticker} - {company}")
            print(f"    → Full research workflow required")

    # Terminate monitoring agents
    if visualizer:
        for agent_id in ["news-monitor", "price-monitor", "list-monitor", "competitor-monitor"]:
            visualizer.terminate_agent(agent_id, reason="completed")
        visualizer.terminate_agent("monitoring-orchestrator", reason="completed")

    return report


async def check_list_changes():
    """Check only for list changes"""
    print_banner()
    print("Checking for list changes...\n")

    # Initialize visualizer
    visualizer = None
    if VISUALIZER_AVAILABLE:
        visualizer = VisualizerBridge("context")
        visualizer.spawn_agent(
            agent_type="specialist",
            name="List Monitor",
            tier=2,
            task="Checking list changes",
            agent_id="list-check"
        )
        visualizer.activate_agent("list-check", "Checking equity list")

    monitor = ListMonitorAgent()
    new_tickers, removed_tickers, has_changes = await monitor.check_for_changes()

    if has_changes:
        print("LIST HAS CHANGED!")
        if new_tickers:
            print(f"\nNew companies added ({len(new_tickers)}):")
            for t in new_tickers:
                print(f"  + {t}")
        if removed_tickers:
            print(f"\nCompanies removed ({len(removed_tickers)}):")
            for t in removed_tickers:
                print(f"  - {t}")
    else:
        print("No changes detected in equity list.")

    # Cleanup visualizer
    if visualizer:
        visualizer.update_agent_task("list-check", "Check complete", progress=100)
        visualizer.terminate_agent("list-check", reason="completed")

    return new_tickers, removed_tickers


def main():
    parser = argparse.ArgumentParser(description="Monitor Equity Research Portfolio")
    parser.add_argument('--ticker', '-t', help='Monitor specific ticker')
    parser.add_argument('--list-only', action='store_true', help='Only check for list changes')
    parser.add_argument('--prices', action='store_true', help='Only check price movements')

    args = parser.parse_args()

    if args.list_only:
        asyncio.run(check_list_changes())
    else:
        asyncio.run(run_full_monitoring())


if __name__ == "__main__":
    main()
