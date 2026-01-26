"""
Multi-AI Debate Runner
Executes rigorous multi-AI debates on all 14 equities using GPT, Gemini, Grok, Qwen
Each equity goes through 10 rounds of debate where AIs challenge each other.
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import API_KEYS
from agents.multi_ai_debate import MultiAIDebateOrchestrator

# Visualizer integration (optional)
try:
    from visualizer.visualizer_bridge import VisualizerBridge
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False
    VisualizerBridge = None


async def run_single_equity_debate(ticker: str, orchestrator: MultiAIDebateOrchestrator,
                                   context_dir: str, output_dir: str):
    """Run debate for a single equity"""

    # Find the research file
    research_files = os.listdir(context_dir)
    target_file = None

    for f in research_files:
        if ticker.replace(" ", "_").replace(".", "_") in f.replace(" ", "_"):
            target_file = f
            break

    if not target_file:
        print(f"Research file not found for {ticker}")
        return None

    filepath = os.path.join(context_dir, target_file)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            equity_data = json.load(f)

        # Run debate
        debate_result = await orchestrator.run_full_debate(equity_data)

        # Save debate result
        safe_ticker = ticker.replace(" ", "_").replace(".", "_")
        output_file = os.path.join(output_dir, f"debate_{safe_ticker}.json")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(debate_result.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"Saved debate result: {output_file}")
        return debate_result

    except Exception as e:
        print(f"Error debating {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def run_all_debates(num_rounds: int = 10, use_visualizer: bool = True):
    """Run debates for all 14 equities"""

    # Setup paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    context_dir = os.path.join(base_dir, "context")
    output_dir = os.path.join(context_dir, "debates")
    os.makedirs(output_dir, exist_ok=True)

    # Initialize visualizer
    visualizer = None
    if use_visualizer and VISUALIZER_AVAILABLE:
        visualizer = VisualizerBridge(context_dir)
        print("[Visualizer] Real-time debate updates enabled")

    # Check API keys
    available_apis = {k: v for k, v in API_KEYS.items() if v and k != "dashscope_secret"}
    print(f"\nAvailable AI Providers: {list(available_apis.keys())}")

    if len(available_apis) < 2:
        print("ERROR: Need at least 2 AI providers for meaningful debate")
        return

    # Initialize orchestrator
    orchestrator = MultiAIDebateOrchestrator(API_KEYS, num_rounds)
    print(f"Initialized debate orchestrator with {len(orchestrator.provider_manager.get_all_providers())} AI providers")

    # Get all research files
    research_files = [f for f in os.listdir(context_dir)
                      if f.endswith('.json') and f != 'session_state.json'
                      and not f.startswith('debate_') and f != 'minions_state.json'
                      and f != 'verified_prices.json']

    print(f"\nFound {len(research_files)} equities to debate")
    print("="*60)

    results = []

    for i, research_file in enumerate(research_files):
        print(f"\n[{i+1}/{len(research_files)}] Processing: {research_file}")

        filepath = os.path.join(context_dir, research_file)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                equity_data = json.load(f)

            ticker = equity_data.get('ticker', research_file.replace('.json', ''))
            company = equity_data.get('company_name', '')

            # Notify visualizer of debate start
            if visualizer:
                visualizer.start_debate(ticker, company)

            # Create progress callback for real-time visualizer updates
            def debate_progress(round_num, total_rounds, t):
                if visualizer:
                    visualizer.update_debate_round(t, round_num, total_rounds)

            # Run debate with real-time progress updates
            debate_result = await orchestrator.run_full_debate(equity_data, progress_callback=debate_progress)

            # Save debate result
            output_file = os.path.join(output_dir, f"debate_{research_file}")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(debate_result.to_dict(), f, indent=2, ensure_ascii=False)

            results.append({
                "ticker": debate_result.ticker,
                "company": debate_result.company,
                "probability_weighted_price": debate_result.probability_weighted_price,
                "recommendation": debate_result.final_thesis.get("recommendation", "N/A"),
                "conviction": debate_result.final_thesis.get("conviction", "N/A")
            })

            # Notify visualizer of debate completion
            if visualizer:
                visualizer.complete_debate(ticker)

            print(f"  ✓ Debate complete: {debate_result.ticker}")
            print(f"    Recommendation: {debate_result.final_thesis.get('recommendation', 'N/A')}")
            print(f"    Target Price: {debate_result.probability_weighted_price}")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            if visualizer:
                visualizer.complete_debate(ticker)  # Reset agents on error
            continue

    # Save summary
    summary_file = os.path.join(output_dir, "debate_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "num_debates": len(results),
            "num_rounds_per_debate": num_rounds,
            "ai_providers": list(available_apis.keys()),
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print("\n" + "="*60)
    print(f"DEBATE SUMMARY")
    print("="*60)
    print(f"Completed: {len(results)} equities")
    print(f"Rounds per equity: {num_rounds}")
    print(f"Results saved to: {output_dir}")
    print("\nRecommendations:")
    for r in results:
        print(f"  {r['ticker']}: {r['recommendation']} (Conviction: {r['conviction']}) - Target: {r['probability_weighted_price']}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Multi-AI Debates on Equities")
    parser.add_argument("--ticker", type=str, help="Run debate for specific ticker only")
    parser.add_argument("--rounds", type=int, default=10, help="Number of debate rounds (default: 10)")

    args = parser.parse_args()

    print("\n" + "="*60)
    print("MULTI-AI EQUITY DEBATE SYSTEM")
    print("GPT vs Gemini vs Grok vs Qwen")
    print("="*60)

    asyncio.run(run_all_debates(args.rounds))
