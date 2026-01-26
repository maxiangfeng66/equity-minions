"""
Main Orchestrator - Entry point for equity research system
Runs multi-agent research for all equities in parallel
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import API_KEYS, EQUITIES, DEBATE_ROUNDS
from agents.ai_providers import AIProviderManager
from agents.debate_system import DebateSystem, ParallelDebateRunner
from agents.base_agent import ResearchContext
from utils.context_manager import ContextManager
from utils.html_generator import HTMLGenerator

# Visualizer integration (optional - works without it)
try:
    from visualizer.visualizer_bridge import VisualizerBridge
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False
    VisualizerBridge = None

# Hierarchical system (new architecture)
try:
    from agents.hierarchical_debate_system import HierarchicalDebateSystem, HierarchicalParallelRunner
    from agents.core.agent_registry import AgentRegistry
    HIERARCHICAL_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] Hierarchical system not available: {e}")
    HIERARCHICAL_AVAILABLE = False
    HierarchicalDebateSystem = None
    HierarchicalParallelRunner = None


def print_banner():
    """Print startup banner"""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║         EQUITY RESEARCH MULTI-AGENT SYSTEM                    ║
║         Multi-AI Debate-Based Valuation Analysis              ║
╚═══════════════════════════════════════════════════════════════╝
    """)


def check_api_keys() -> bool:
    """Check if at least one API key is configured"""
    configured = [k for k, v in API_KEYS.items() if v]
    if not configured:
        print("ERROR: No API keys configured!")
        print("Please edit config.py and add at least one API key:")
        print("  - openai: GPT API key")
        print("  - google: Gemini API key")
        print("  - xai: Grok API key")
        print("  - deepseek: DeepSeek API key")
        print("  - dashscope: Qwen (Alibaba) API key")
        return False

    print(f"Configured AI providers: {', '.join(configured)}")
    return True


async def run_single_equity(ticker: str, info: dict, ai_manager: AIProviderManager,
                            context_manager: ContextManager, html_generator: HTMLGenerator,
                            visualizer: 'VisualizerBridge' = None):
    """Run research for a single equity"""

    print(f"\n{'='*60}")
    print(f"Starting research for: {ticker} - {info['name']}")
    print(f"{'='*60}")

    # Check if already completed
    if context_manager.is_completed(ticker):
        print(f"  Skipping {ticker} - already completed")
        return

    context_manager.mark_equity_started(ticker)

    # Notify visualizer
    if visualizer:
        visualizer.start_research(ticker, info['name'])

    try:
        # Create research context
        context = ResearchContext(
            ticker=ticker,
            company_name=info["name"],
            sector=info["sector"],
            industry=info["industry"]
        )

        # Create debate system
        debate_system = DebateSystem(ai_manager, debate_rounds=DEBATE_ROUNDS)

        # Progress callback with visualizer updates
        phase_progress = {'current': 0}

        def progress(msg):
            print(f"  [{ticker}] {msg}")

            # Update visualizer based on message content
            if visualizer:
                msg_lower = msg.lower()
                if 'data' in msg_lower or 'gather' in msg_lower:
                    visualizer.update_phase(ticker, 'data_gathering')
                elif 'industry' in msg_lower:
                    visualizer.update_phase(ticker, 'industry_analysis')
                elif 'company' in msg_lower or 'moat' in msg_lower:
                    visualizer.update_phase(ticker, 'company_analysis')
                elif 'dcf' in msg_lower or 'valuation' in msg_lower:
                    visualizer.update_phase(ticker, 'dcf_valuation')
                elif 'scenario' in msg_lower:
                    visualizer.update_phase(ticker, 'scenario_analysis')
                elif 'debate' in msg_lower:
                    visualizer.update_phase(ticker, 'debate')
                elif 'synthe' in msg_lower:
                    visualizer.update_phase(ticker, 'synthesis')
                elif 'report' in msg_lower:
                    visualizer.update_phase(ticker, 'report_generation')
                else:
                    # Increment progress gradually
                    phase_progress['current'] = min(95, phase_progress['current'] + 5)
                    visualizer.update_progress(ticker, phase_progress['current'], msg[:50])

        # Run full research
        context = await debate_system.run_full_research(context, progress)

        # Save context for persistence
        context_manager.save_equity_context(ticker, context.to_dict())

        # Generate HTML report
        if visualizer:
            visualizer.update_phase(ticker, 'report_generation')

        report_path = html_generator.generate_equity_report(context.to_dict())
        print(f"  [{ticker}] Report generated: {report_path}")

        # Mark as completed
        context_manager.mark_equity_completed(ticker)

        if visualizer:
            visualizer.complete_research(ticker)

        print(f"  [{ticker}] COMPLETED")

    except Exception as e:
        print(f"  [{ticker}] ERROR: {e}")
        context_manager.mark_equity_error(ticker, str(e))

        if visualizer:
            visualizer.error_research(ticker, str(e))

        raise


async def run_all_parallel(max_concurrent: int = 3, use_visualizer: bool = True):
    """Run research for all equities with controlled concurrency"""

    print_banner()

    # Check API keys
    if not check_api_keys():
        return

    # Initialize components
    ai_manager = AIProviderManager(API_KEYS)
    context_manager = ContextManager("context")
    html_generator = HTMLGenerator("reports")

    # Initialize visualizer bridge (optional)
    visualizer = None
    if use_visualizer and VISUALIZER_AVAILABLE:
        visualizer = VisualizerBridge("context")
        # Set all tasks in visualizer
        visualizer.set_all_tasks([
            {'ticker': t, 'company': i['name'], 'status': 'pending'}
            for t, i in EQUITIES.items()
        ])
        # Auto-open visualizer in browser
        visualizer.open_visualizer()
        print("[Visualizer] Real-time updates enabled - browser opened")
    elif use_visualizer:
        print("[Visualizer] Not available (missing dependencies)")

    # Set pending equities
    all_tickers = list(EQUITIES.keys())
    context_manager.set_pending_equities(all_tickers)

    print(f"\nTotal equities to analyze: {len(all_tickers)}")
    print(f"Max concurrent: {max_concurrent}")
    print(f"Debate rounds per equity: {DEBATE_ROUNDS}")

    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)

    async def research_with_semaphore(ticker: str, info: dict):
        async with semaphore:
            await run_single_equity(ticker, info, ai_manager, context_manager, html_generator, visualizer)

    # Create tasks for all equities
    tasks = [
        research_with_semaphore(ticker, info)
        for ticker, info in EQUITIES.items()
    ]

    # Run all with gather (continue on error)
    start_time = datetime.now()
    print(f"\nStarting parallel research at {start_time.strftime('%H:%M:%S')}")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Check results
    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        print(f"\n{len(errors)} equities had errors")

    # Generate index page
    print("\nGenerating index page...")
    index_path = html_generator.generate_index(EQUITIES)
    print(f"Index page: {index_path}")

    # Final status
    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "="*60)
    print("RESEARCH COMPLETE")
    print("="*60)
    print(context_manager.get_status_report())
    print(f"Total duration: {duration}")
    print(f"\nReports available in: {html_generator.output_dir}")


async def run_single(ticker: str, use_visualizer: bool = True):
    """Run research for a single equity (for testing)"""

    print_banner()

    if not check_api_keys():
        return

    if ticker not in EQUITIES:
        print(f"ERROR: Unknown ticker {ticker}")
        print(f"Available: {', '.join(EQUITIES.keys())}")
        return

    ai_manager = AIProviderManager(API_KEYS)
    context_manager = ContextManager("context")
    html_generator = HTMLGenerator("reports")

    # Initialize visualizer
    visualizer = None
    if use_visualizer and VISUALIZER_AVAILABLE:
        visualizer = VisualizerBridge("context")
        # Auto-open visualizer in browser
        visualizer.open_visualizer()
        print("[Visualizer] Real-time updates enabled - browser opened")

    await run_single_equity(ticker, EQUITIES[ticker], ai_manager, context_manager, html_generator, visualizer)

    # Generate index
    html_generator.generate_index(EQUITIES)


async def run_hierarchical(max_concurrent: int = 3, use_visualizer: bool = True):
    """
    Run research using the new hierarchical agent system.

    Features:
    - Dynamic agent spawning and termination
    - Supervisor health monitoring
    - Quality gates before publishing
    - Full visualizer integration with animations
    - Automatic agent logging
    """

    print_banner()
    print("\n[HIERARCHICAL AGENT SYSTEM]")
    print("    - Tier 0: Architect Agents (strategy)")
    print("    - Tier 1: Supervisor Agents (oversight)")
    print("    - Tier 2: Worker Agents (execution)")
    print("    - Tier 3: Goalkeeper Agents (quality)\n")

    if not HIERARCHICAL_AVAILABLE:
        print("ERROR: Hierarchical system not available!")
        print("Falling back to standard system...")
        await run_all_parallel(max_concurrent, use_visualizer)
        return

    if not check_api_keys():
        return

    # Initialize agent logger
    try:
        from agents.agent_logger import AgentLogger
        agent_logger = AgentLogger.get_instance()
        agent_logger.start_session(f"Hierarchical Research - {len(EQUITIES)} equities")
        print("[AgentLogger] Session logging enabled")
    except ImportError:
        agent_logger = None
        print("[AgentLogger] Not available")

    # Initialize components
    ai_manager = AIProviderManager(API_KEYS)
    context_manager = ContextManager("context")
    html_generator = HTMLGenerator("reports")

    # Initialize visualizer bridge
    visualizer = None
    if use_visualizer and VISUALIZER_AVAILABLE:
        visualizer = VisualizerBridge("context")
        visualizer.set_all_tasks([
            {'ticker': t, 'company': i['name'], 'status': 'pending'}
            for t, i in EQUITIES.items()
        ])
        # Auto-open visualizer in browser
        visualizer.open_visualizer()
        print("[Visualizer] Hierarchical mode enabled - browser opened")

    # Set pending equities
    all_tickers = list(EQUITIES.keys())
    context_manager.set_pending_equities(all_tickers)

    print(f"\nTotal equities to analyze: {len(all_tickers)}")
    print(f"Max concurrent: {max_concurrent}")
    print(f"Debate rounds per equity: {DEBATE_ROUNDS}")

    # Create hierarchical runner
    runner = HierarchicalParallelRunner(
        ai_manager=ai_manager,
        max_concurrent=max_concurrent,
        debate_rounds=DEBATE_ROUNDS
    )

    def progress_callback(msg: str):
        print(f"  {msg}")

    # Run research
    start_time = datetime.now()
    print(f"\nStarting hierarchical research at {start_time.strftime('%H:%M:%S')}")

    try:
        results = await runner.run_all(
            equities=EQUITIES,
            progress_callback=progress_callback,
            visualizer=visualizer
        )

        # Generate reports for approved results
        for ticker, context in results.items():
            try:
                # Save context
                context_manager.save_equity_context(ticker, context.to_dict())

                # Generate report
                report_path = html_generator.generate_equity_report(context.to_dict())
                print(f"  [{ticker}] Report generated: {report_path}")

                # Mark completed
                context_manager.mark_equity_completed(ticker)

                if visualizer:
                    visualizer.complete_research(ticker)

            except Exception as e:
                print(f"  [{ticker}] Report generation error: {e}")
                context_manager.mark_equity_error(ticker, str(e))

                if visualizer:
                    visualizer.error_research(ticker, str(e))

    except Exception as e:
        print(f"\nSystem error: {e}")
        import traceback
        traceback.print_exc()

    # Generate index page
    print("\nGenerating index page...")
    index_path = html_generator.generate_index(EQUITIES)
    print(f"Index page: {index_path}")

    # Final status
    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "="*60)
    print("HIERARCHICAL RESEARCH COMPLETE")
    print("="*60)
    print(context_manager.get_status_report())
    print(f"Total duration: {duration}")
    print(f"\nReports available in: {html_generator.output_dir}")

    # Save agent logs
    if agent_logger:
        agent_logger.end_session()
        agent_logger.print_hierarchy()
        agent_logger.print_provider_stats()
        log_file = agent_logger.save_log()
        readable_log = agent_logger.save_readable_log()
        print(f"\n[AgentLogger] Logs saved:")
        print(f"  JSON: {log_file}")
        print(f"  Readable: {readable_log}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Equity Research Multi-Agent System")
    parser.add_argument("--ticker", "-t", help="Research a single ticker")
    parser.add_argument("--concurrent", "-c", type=int, default=2,
                        help="Max concurrent research (default: 2, safe for 30K TPM limit)")
    parser.add_argument("--clear", action="store_true",
                        help="Clear previous session and start fresh")
    parser.add_argument("--no-visualizer", action="store_true",
                        help="Disable visualizer updates")
    parser.add_argument("--hierarchical", "-H", action="store_true",
                        help="Use new hierarchical agent system with spawn/terminate, supervisors, and quality gates")

    args = parser.parse_args()

    use_visualizer = not args.no_visualizer

    # Warn about rate limits for high concurrency
    if args.concurrent > 2:
        print("\n[WARNING] Running with high concurrency may hit rate limits!")
        print("   OpenAI has a 30,000 tokens/minute limit.")
        print("   The system now includes automatic rate limiting and will")
        print("   wait when approaching the limit. Expect slower operation.\n")

    if args.clear:
        cm = ContextManager("context")
        cm.clear_session()
        print("Session cleared")

    if args.ticker:
        asyncio.run(run_single(args.ticker, use_visualizer))
    elif args.hierarchical:
        asyncio.run(run_hierarchical(args.concurrent, use_visualizer))
    else:
        asyncio.run(run_all_parallel(args.concurrent, use_visualizer))


if __name__ == "__main__":
    main()
