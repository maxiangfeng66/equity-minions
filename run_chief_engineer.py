#!/usr/bin/env python3
"""
Run Chief Engineer - Autonomous Project Oversight

The Chief Engineer monitors the entire Equity Minions project,
ensuring all components are functioning correctly and identifying issues.

Usage:
    python run_chief_engineer.py [command]

Commands:
    health      - Run health check on all components
    report      - Generate comprehensive system report
    monitor     - Start continuous monitoring
    validate    - Validate a specific workflow execution
    audit       - Audit workflow definitions
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def run_health_check():
    """Run health check on all components"""
    from agents.oversight.chief_engineer import ChiefEngineerAgent

    print("=" * 60)
    print("CHIEF ENGINEER - HEALTH CHECK")
    print("=" * 60)
    print()

    engineer = ChiefEngineerAgent(str(project_root))
    await engineer.initialize()

    health = await engineer.run_health_check()

    print("\nComponent Health Status:")
    print("-" * 40)

    for name, status in health.items():
        icon = "✓" if status.status.value == "healthy" else "⚠" if status.status.value == "degraded" else "✗"
        print(f"  {icon} {name}: {status.status.value.upper()}")

        if status.issues:
            for issue in status.issues:
                print(f"      - {issue}")

    print()
    return engineer


async def generate_report():
    """Generate comprehensive system report"""
    from agents.oversight.chief_engineer import ChiefEngineerAgent

    print("=" * 60)
    print("CHIEF ENGINEER - SYSTEM REPORT")
    print("=" * 60)
    print()

    engineer = ChiefEngineerAgent(str(project_root))
    await engineer.initialize()

    report = await engineer.get_system_report()

    print(f"Generated at: {report['generated_at']}")
    print(f"Overall Health: {report['overall_health']}")
    print(f"Healthy Components: {report['healthy_components']}/{report['total_components']}")
    print()

    if report['all_issues']:
        print("ISSUES FOUND:")
        for issue in report['all_issues']:
            print(f"  - {issue}")
        print()

    if report['all_recommendations']:
        print("RECOMMENDATIONS:")
        for rec in report['all_recommendations']:
            print(f"  - {rec}")
        print()

    # Save report
    report_path = project_root / "context" / "chief_engineer_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Full report saved to: {report_path}")

    return report


async def start_monitoring(interval: int = 300):
    """Start continuous monitoring"""
    from agents.oversight.chief_engineer import ChiefEngineerAgent

    print("=" * 60)
    print("CHIEF ENGINEER - CONTINUOUS MONITORING")
    print(f"Interval: {interval} seconds")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    engineer = ChiefEngineerAgent(str(project_root))
    await engineer.initialize()

    try:
        await engineer.continuous_monitoring(interval_seconds=interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")


async def validate_workflow(ticker: str):
    """Validate a workflow execution"""
    from agents.oversight.dcf_quality_controller import DCFQualityController
    from agents.oversight.workflow_auditor import WorkflowAuditorAgent

    print("=" * 60)
    print(f"VALIDATING WORKFLOW - {ticker}")
    print("=" * 60)
    print()

    # Audit workflow definition
    auditor = WorkflowAuditorAgent(
        name="WorkflowAuditor",
        project_root=str(project_root)
    )

    print("Auditing workflow definition...")
    audit = await auditor.audit_workflow()

    print(f"  Nodes: {audit.node_count}, Edges: {audit.edge_count}")
    print(f"  Valid: {'YES' if audit.is_valid else 'NO'}")

    if audit.critical_issues:
        print("  Critical Issues:")
        for issue in audit.critical_issues:
            print(f"    - {issue}")

    print()

    # Validate execution
    print(f"Validating execution for {ticker}...")
    execution_result = await auditor.validate_execution(ticker)

    print(f"  Valid: {'YES' if execution_result.get('valid') else 'NO'}")
    if execution_result.get('issues'):
        for issue in execution_result['issues']:
            print(f"    - {issue}")

    print()

    # DCF quality check
    dcf_controller = DCFQualityController(
        name="DCFQualityController",
        project_root=str(project_root)
    )

    print(f"Validating DCF output for {ticker}...")
    dcf_report = await dcf_controller.validate_workflow_dcf(ticker)

    print(f"  Price Match: {'YES' if dcf_report.price_match else 'NO'}")
    print(f"  WACC Valid: {'YES' if dcf_report.wacc_valid else 'NO'}")
    print(f"  Scenarios Valid: {'YES' if dcf_report.scenarios_valid else 'NO'}")
    print(f"  Overall Valid: {'YES' if dcf_report.is_valid else 'NO'}")

    if dcf_report.recommendations:
        print("  Recommendations:")
        for rec in dcf_report.recommendations:
            print(f"    - {rec}")


async def audit_workflows():
    """Audit all workflow definitions"""
    from agents.oversight.workflow_auditor import WorkflowAuditorAgent

    print("=" * 60)
    print("WORKFLOW AUDIT")
    print("=" * 60)
    print()

    auditor = WorkflowAuditorAgent(
        name="WorkflowAuditor",
        project_root=str(project_root)
    )

    # Find workflow files
    workflow_dir = project_root / "workflows"
    workflow_files = list(workflow_dir.glob("*.yaml"))

    for wf_file in workflow_files:
        rel_path = wf_file.relative_to(project_root)
        print(f"\nAuditing: {rel_path}")
        print("-" * 40)

        audit = await auditor.audit_workflow(str(rel_path))

        print(f"  Nodes: {audit.node_count}")
        print(f"  Edges: {audit.edge_count}")
        print(f"  Start Nodes: {audit.start_nodes}")
        print(f"  End Nodes: {audit.end_nodes}")
        print(f"  Valid: {'YES' if audit.is_valid else 'NO'}")

        if audit.orphan_nodes:
            print(f"  Orphan Nodes: {audit.orphan_nodes}")

        if audit.unreachable_nodes:
            print(f"  Unreachable Nodes: {audit.unreachable_nodes}")

        if audit.providers_used:
            print(f"  Providers: {audit.providers_used}")

        if audit.critical_issues:
            print("  Critical Issues:")
            for issue in audit.critical_issues:
                print(f"    - {issue}")

        if audit.warnings:
            print("  Warnings:")
            for warning in audit.warnings:
                print(f"    - {warning}")


async def run_dcf_test(ticker: str):
    """Test the new DCF modeling agent"""
    from agents.specialized.dcf_agent import DCFModelingAgent

    print("=" * 60)
    print(f"DCF MODEL TEST - {ticker}")
    print("=" * 60)
    print()

    agent = DCFModelingAgent()

    print(f"Building DCF model for {ticker}...")
    print("(This fetches real market data from Yahoo Finance)")
    print()

    try:
        result = await agent.build_dcf_model(
            ticker=ticker,
            company_name="Test Company",
            growth_phase1=0.15,
            growth_phase2=0.10,
            growth_phase3=0.05,
            beta=1.2
        )

        print(agent.format_dcf_output(result))

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="Chief Engineer - Equity Minions Project Oversight"
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Health check
    subparsers.add_parser('health', help='Run health check on all components')

    # Report
    subparsers.add_parser('report', help='Generate comprehensive system report')

    # Monitor
    monitor_parser = subparsers.add_parser('monitor', help='Start continuous monitoring')
    monitor_parser.add_argument(
        '--interval', type=int, default=300,
        help='Check interval in seconds (default: 300)'
    )

    # Validate
    validate_parser = subparsers.add_parser('validate', help='Validate a workflow execution')
    validate_parser.add_argument('ticker', help='Ticker to validate (e.g., "6682 HK")')

    # Audit
    subparsers.add_parser('audit', help='Audit workflow definitions')

    # DCF test
    dcf_parser = subparsers.add_parser('dcf', help='Test DCF modeling agent')
    dcf_parser.add_argument('ticker', help='Ticker for DCF test (e.g., "AAPL")')

    args = parser.parse_args()

    if args.command == 'health':
        asyncio.run(run_health_check())
    elif args.command == 'report':
        asyncio.run(generate_report())
    elif args.command == 'monitor':
        asyncio.run(start_monitoring(args.interval))
    elif args.command == 'validate':
        asyncio.run(validate_workflow(args.ticker))
    elif args.command == 'audit':
        asyncio.run(audit_workflows())
    elif args.command == 'dcf':
        asyncio.run(run_dcf_test(args.ticker))
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python run_chief_engineer.py health")
        print("  python run_chief_engineer.py report")
        print("  python run_chief_engineer.py monitor --interval 60")
        print('  python run_chief_engineer.py validate "6682 HK"')
        print("  python run_chief_engineer.py audit")
        print("  python run_chief_engineer.py dcf AAPL")


if __name__ == "__main__":
    main()
