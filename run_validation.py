"""
Run Validation - Standalone script to validate all existing research
Runs all validation agents in parallel to find:
1. Factual mistakes
2. Logical loopholes
3. Calculation errors
4. Data inconsistencies

Usage:
    python run_validation.py              # Validate all
    python run_validation.py --ticker "LEGN US"  # Validate specific ticker
    python run_validation.py --fix        # Auto-fix what can be fixed
"""

import asyncio
import argparse
import json
from datetime import datetime
from pathlib import Path

from agents.validation_agents import (
    ValidationOrchestrator,
    FactCheckerAgent,
    LogicValidatorAgent,
    DataConsistencyAgent,
    CalculationVerifierAgent
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
║           EQUITY RESEARCH VALIDATION SYSTEM                   ║
║           Parallel Fact-Checking & Logic Analysis             ║
╚═══════════════════════════════════════════════════════════════╝
    """)


def print_validation_report(ticker: str, report):
    """Print detailed validation report for a ticker"""
    print(f"\n{'='*60}")
    print(f"VALIDATION REPORT: {ticker}")
    print(f"Company: {report.company_name}")
    print(f"Overall Score: {report.overall_score:.0f}/100")
    print(f"Needs Revision: {'YES' if report.needs_revision else 'NO'}")
    print(f"{'='*60}")

    sections = [
        ('FACTUAL ISSUES', report.factual_issues),
        ('LOGIC ISSUES', report.logic_issues),
        ('DATA ISSUES', report.data_issues),
        ('CALCULATION ISSUES', report.calculation_issues)
    ]

    for section_name, issues in sections:
        if issues:
            print(f"\n{section_name} ({len(issues)}):")
            print("-" * 40)
            for i, issue in enumerate(issues, 1):
                severity_icon = {
                    'critical': '🔴',
                    'major': '🟠',
                    'minor': '🟡',
                    'info': '🔵'
                }.get(issue.severity, '⚪')

                print(f"\n  {i}. {severity_icon} [{issue.severity.upper()}] {issue.issue}")
                print(f"     Category: {issue.category}")
                if issue.evidence:
                    print(f"     Evidence: {issue.evidence}")
                print(f"     Recommendation: {issue.recommendation}")


async def validate_all(fix_issues: bool = False):
    """Validate all equities"""
    print_banner()

    # Initialize visualizer
    visualizer = None
    if VISUALIZER_AVAILABLE:
        visualizer = VisualizerBridge("context")
        # Spawn validation orchestrator agent
        visualizer.spawn_agent(
            agent_type="orchestrator",
            name="Validation Orchestrator",
            tier=0,
            task="Coordinating validation",
            agent_id="validation-orchestrator"
        )
        visualizer.activate_agent("validation-orchestrator", "Starting validation cycle")

    orchestrator = ValidationOrchestrator()
    tickers = list(EQUITIES.keys())

    print(f"Validating {len(tickers)} equities in parallel...\n")

    # Spawn validation worker agents
    if visualizer:
        # Spawn the 4 validation agents
        for agent_info in [
            ("fact-checker", "Fact Checker", "fact_checker"),
            ("logic-validator", "Logic Validator", "logic_auditor"),
            ("data-consistency", "Data Consistency", "specialist"),
            ("calc-verifier", "Calculation Verifier", "specialist")
        ]:
            agent_id, name, agent_type = agent_info
            visualizer.spawn_agent(
                agent_type=agent_type,
                name=name,
                parent_id="validation-orchestrator",
                tier=2,
                task=f"Validating {len(tickers)} equities",
                agent_id=agent_id
            )
            visualizer.activate_agent(agent_id, f"Checking {len(tickers)} equities")

    # Run validation
    results = await orchestrator.validate_all_equities(tickers)

    # Update visualizer with completion
    if visualizer:
        for agent_id in ["fact-checker", "logic-validator", "data-consistency", "calc-verifier"]:
            visualizer.update_agent_task(agent_id, "Validation complete", progress=100)
        visualizer.update_agent_task("validation-orchestrator", "Validation complete", progress=100)

    # Summary statistics
    total = len(results)
    needs_revision = sum(1 for r in results.values() if hasattr(r, 'needs_revision') and r.needs_revision)
    avg_score = sum(r.overall_score for r in results.values() if hasattr(r, 'overall_score')) / total if total > 0 else 0

    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total Validated: {total}")
    print(f"Needs Revision: {needs_revision}")
    print(f"Average Score: {avg_score:.1f}/100")

    # List issues by ticker
    print(f"\n{'='*60}")
    print("ISSUES BY TICKER")
    print(f"{'='*60}")

    for ticker, report in sorted(results.items(), key=lambda x: x[1].overall_score if hasattr(x[1], 'overall_score') else 100):
        if hasattr(report, 'overall_score'):
            status = "⚠️ NEEDS REVISION" if report.needs_revision else "✅ OK"
            total_issues = len(report.factual_issues) + len(report.logic_issues) + \
                          len(report.data_issues) + len(report.calculation_issues)
            print(f"  {ticker}: {report.overall_score:.0f}/100 - {total_issues} issues - {status}")

    # Critical issues alert
    critical_issues = []
    for ticker, report in results.items():
        if hasattr(report, 'factual_issues'):
            for issue in report.factual_issues + report.logic_issues + \
                        report.data_issues + report.calculation_issues:
                if issue.severity == 'critical':
                    critical_issues.append((ticker, issue))

    if critical_issues:
        print(f"\n{'='*60}")
        print("🔴 CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION")
        print(f"{'='*60}")
        for ticker, issue in critical_issues:
            print(f"\n  [{ticker}] {issue.issue}")
            print(f"    {issue.recommendation}")

    # Terminate validation agents
    if visualizer:
        for agent_id in ["fact-checker", "logic-validator", "data-consistency", "calc-verifier"]:
            visualizer.terminate_agent(agent_id, reason="completed")
        visualizer.terminate_agent("validation-orchestrator", reason="completed")

    return results


async def validate_single(ticker: str):
    """Validate a single ticker"""
    print_banner()
    print(f"Validating: {ticker}\n")

    # Initialize visualizer
    visualizer = None
    if VISUALIZER_AVAILABLE:
        visualizer = VisualizerBridge("context")
        visualizer.spawn_agent(
            agent_type="fact_checker",
            name="Single Validator",
            tier=2,
            task=f"Validating {ticker}",
            agent_id="single-validator"
        )
        visualizer.activate_agent("single-validator", f"Validating {ticker}")

    orchestrator = ValidationOrchestrator()
    report = await orchestrator.validate_equity(ticker)

    print_validation_report(ticker, report)

    # Cleanup visualizer
    if visualizer:
        visualizer.update_agent_task("single-validator", "Validation complete", progress=100)
        visualizer.terminate_agent("single-validator", reason="completed")

    return report


def main():
    parser = argparse.ArgumentParser(description="Validate Equity Research")
    parser.add_argument('--ticker', '-t', help='Validate specific ticker')
    parser.add_argument('--fix', action='store_true', help='Auto-fix issues where possible')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')

    args = parser.parse_args()

    if args.ticker:
        asyncio.run(validate_single(args.ticker))
    else:
        asyncio.run(validate_all(args.fix))


if __name__ == "__main__":
    main()
