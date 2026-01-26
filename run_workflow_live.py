#!/usr/bin/env python3
"""
Live Workflow Runner with WebSocket visualization
Runs equity research workflows for single or multiple tickers with live visualization

Usage:
    python run_workflow_live.py "9660_HK"                    # Single ticker
    python run_workflow_live.py "9660_HK" "LEGN_US"          # Multiple tickers
    python run_workflow_live.py "9660_HK" "LEGN_US" -c 3     # With concurrency limit
"""

import asyncio
import json
import argparse
from datetime import datetime
from pathlib import Path
import webbrowser

import websockets

from config import API_KEYS, EQUITIES
from workflow.workflow_loader import WorkflowLoader
from workflow.graph_executor import GraphExecutor
from workflow.node_executor import Message

# Import visualizer bridge for minions.html
try:
    from visualizer.visualizer_bridge import VisualizerBridge
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False

# Global visualizer instance
visualizer = None

# Global list to store connected websocket clients
connected_clients = set()
event_queue = asyncio.Queue()


async def broadcast_event(event_type: str, data: dict):
    """Broadcast event to all connected clients and update minions visualizer"""
    global visualizer

    message = json.dumps({
        "type": event_type,
        "timestamp": datetime.now().isoformat(),
        "data": data
    })

    if connected_clients:
        await asyncio.gather(
            *[client.send(message) for client in connected_clients],
            return_exceptions=True
        )

    # Update minions visualizer bridge
    if visualizer:
        node_id = data.get('node_id', '')
        if event_type == 'workflow_init':
            visualizer.start_research(data.get('ticker', ''), data.get('company_name', ''))
        elif event_type == 'node_start':
            # Pass provider if available
            provider = data.get('details', {}).get('provider', 'openai')
            visualizer.node_start(node_id, provider)
        elif event_type == 'node_complete':
            visualizer.node_complete(node_id, data.get('details', {}).get('output_length', 0))
        elif event_type == 'node_error':
            visualizer.node_error(node_id, data.get('message', 'Error'))
        elif event_type == 'workflow_complete':
            visualizer.complete_research(data.get('ticker', ''))
        elif event_type == 'node_output':
            # Store the output content for the modal display
            content = data.get('content_preview', '')
            visualizer.node_output(node_id, content)

    # Also print to console
    print(f"[{event_type}] {data.get('node_id', '')} - {data.get('message', '')}", flush=True)


async def websocket_handler(websocket):
    """Handle WebSocket connections"""
    connected_clients.add(websocket)
    print(f"Client connected. Total: {len(connected_clients)}")

    try:
        # Send welcome message
        await websocket.send(json.dumps({
            "type": "connected",
            "timestamp": datetime.now().isoformat(),
            "data": {"message": "Connected to workflow visualizer"}
        }))

        # Keep connection alive
        async for message in websocket:
            # Handle any incoming messages (like start commands)
            data = json.loads(message)
            if data.get("command") == "ping":
                await websocket.send(json.dumps({"type": "pong"}))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"Client disconnected. Total: {len(connected_clients)}")


async def run_live_workflow(ticker: str, workflow_name: str = "equity_research_v4", verified_price: float = None, prefetched_data: dict = None):
    """Run workflow with live visualization

    Args:
        ticker: Stock ticker
        workflow_name: Workflow to run
        verified_price: Verified current price
        prefetched_data: Dict with market_cap, shares_outstanding, beta from prefetch
    """

    # Broadcast workflow start
    await broadcast_event("workflow_init", {
        "ticker": ticker,
        "workflow": workflow_name,
        "message": f"Starting equity research for {ticker}"
    })

    # Get company info
    company_info = EQUITIES.get(ticker, {})
    company_name = company_info.get("name", ticker)
    sector = company_info.get("sector", "Unknown")
    industry = company_info.get("industry", "Unknown")

    await broadcast_event("company_info", {
        "ticker": ticker,
        "company_name": company_name,
        "sector": sector,
        "industry": industry,
        "message": f"Researching {company_name}"
    })

    # Determine currency based on market
    currency = "HKD" if "HK" in ticker.upper() else "USD"

    # Build price context if verified price provided
    price_context = ""
    if verified_price:
        price_context = f"""
============================================================
VERIFIED MARKET DATA (Pre-fetched and Cross-Validated):
============================================================
VERIFIED CURRENT PRICE: {currency} {verified_price}
Data Source: Multi-source cross-validation (StockAnalysis, Yahoo, Bloomberg)
Data Quality: HIGH CONFIDENCE

CRITICAL INSTRUCTION: You MUST use this verified price ({currency} {verified_price})
in ALL your analysis. Do NOT use prices from your training data or hallucinate
different prices. This is the authoritative, real-time market price.
============================================================
"""

    # Load local research context if available (with enhanced financial data extraction)
    local_research_context = ""
    broker_consensus = {}
    try:
        from utils.local_research_loader import LocalResearchLoader
        loader = LocalResearchLoader()

        # Get research summary with financial consensus
        local_research_context = loader.get_research_summary(ticker, include_financial_consensus=True)
        if local_research_context and "No local research found" not in local_research_context:
            local_research_context = f"""
============================================================
{local_research_context}
============================================================
"""
            # Get consensus data for validation
            broker_consensus = loader.get_financial_consensus(ticker)

            research = loader.load_research(ticker)
            await broadcast_event("local_research", {
                "ticker": ticker,
                "documents": len(research.documents) if research else 0,
                "broker_target": broker_consensus.get('avg_target_price'),
                "message": f"Loaded {len(research.documents) if research else 0} research docs with broker consensus"
            })
        else:
            local_research_context = ""
    except Exception as e:
        print(f"Local research load error: {e}", flush=True)

    # Build task prompt with strong company identity enforcement
    task_prompt = f"""
{price_context}
{local_research_context}
============================================================
CRITICAL: COMPANY IDENTITY ENFORCEMENT
============================================================
You are researching ONLY this company:

TICKER: {ticker}
COMPANY NAME: {company_name}
SECTOR: {sector}
INDUSTRY: {industry}
CURRENCY: {currency}
{"VERIFIED CURRENT PRICE: " + currency + " " + str(verified_price) if verified_price else ""}

STRICT RULES:
1. ONLY use data for {company_name} ({ticker})
2. Do NOT include data from Apple, Amazon, Microsoft, Google, Tesla, or other unrelated companies
3. If you cannot find data for {company_name}, say "DATA NOT FOUND" - do NOT substitute other companies
4. All prices MUST be in {currency} for this {ticker.split()[-1] if ' ' in ticker else 'US'} listed stock
5. Use the VERIFIED CURRENT PRICE above - do NOT hallucinate different prices
============================================================

Conduct comprehensive equity research on {company_name} ({ticker}):

1. Industry analysis with TAM/SAM/SOM sizing
2. Company analysis with competitive positioning
3. Financial analysis with key metrics
4. DCF valuation with 5 scenarios
5. Bull case arguments
6. Bear case arguments
7. Investment recommendation

Remember: This research is ONLY for {company_name} ({ticker}). Any data from other companies is WRONG.
"""

    # Load workflow
    loader = WorkflowLoader()
    config = loader.load(workflow_name)

    # Send workflow structure
    nodes_info = []
    for node_id, node_config in config.nodes.items():
        nodes_info.append({
            "id": node_id,
            "type": node_config.type,
            "provider": node_config.provider,
            "model": node_config.model
        })

    await broadcast_event("workflow_structure", {
        "nodes": nodes_info,
        "edges": [{"from": e.from_node, "to": e.to_node, "trigger": e.trigger} for e in config.edges],
        "message": f"Loaded workflow with {len(nodes_info)} nodes"
    })

    # Prepare API keys
    api_keys = {
        "OPENAI_API_KEY": API_KEYS.get("openai", ""),
        "GOOGLE_API_KEY": API_KEYS.get("google", ""),
        "XAI_API_KEY": API_KEYS.get("xai", ""),
        "DASHSCOPE_API_KEY": API_KEYS.get("dashscope", ""),
        "DEEPSEEK_API_KEY": API_KEYS.get("deepseek", "")
    }

    # Build context for Python valuation nodes
    # Build market data from prefetched sources (private + public)
    market_data = {
        "current_price": verified_price or 0,
        "currency": currency,
        "broker_target_avg": broker_consensus.get('avg_target_price') if broker_consensus else None,
    }

    # Add prefetched data from Yahoo Finance (public source)
    if prefetched_data:
        if prefetched_data.get('market_cap'):
            market_data['market_cap'] = prefetched_data['market_cap']
        if prefetched_data.get('shares_outstanding'):
            market_data['shares_outstanding'] = prefetched_data['shares_outstanding']
        if prefetched_data.get('beta'):
            market_data['beta'] = prefetched_data['beta']
        # NEW: Add financial data for DCF validation (prevents market_cap/3 fallback)
        if prefetched_data.get('total_revenue'):
            market_data['revenue_ttm'] = prefetched_data['total_revenue']
            print(f"  Revenue (TTM): {prefetched_data.get('total_revenue'):.1f}M", flush=True)
        if prefetched_data.get('ebitda'):
            market_data['ebitda'] = prefetched_data['ebitda']
        if prefetched_data.get('operating_income'):
            market_data['operating_income'] = prefetched_data['operating_income']
        # CRITICAL: Pass operating margin (can be negative for loss-making companies!)
        if prefetched_data.get('operating_margin') is not None:
            market_data['operating_margin'] = prefetched_data['operating_margin']
            margin_pct = prefetched_data['operating_margin'] * 100
            if margin_pct < 0:
                print(f"  Operating Margin: {margin_pct:.1f}% (LOSS-MAKING)", flush=True)
            else:
                print(f"  Operating Margin: {margin_pct:.1f}%", flush=True)

    workflow_context = {
        "ticker": ticker,
        "company_name": company_name,
        "sector": sector,
        "industry": industry,
        "currency": currency,
        "market_data": market_data
    }

    # Create executor with context for Python valuation nodes
    executor = GraphExecutor(config, api_keys, output_dir="context", context=workflow_context)

    # Override the log method to broadcast
    original_log = executor.log
    def live_log(event, node_id="", details=None):
        original_log(event, node_id, details)
        asyncio.create_task(broadcast_event(event, {
            "node_id": node_id,
            "details": details or {},
            "iteration": executor.iteration_count
        }))
    executor.log = live_log

    # Execute workflow
    await broadcast_event("execution_start", {"message": "Beginning workflow execution..."})

    result = await executor.execute(task_prompt)

    # Broadcast completion
    await broadcast_event("workflow_complete", {
        "success": result.success,
        "execution_time": result.execution_time,
        "nodes_executed": len(result.node_outputs),
        "message": f"Workflow completed in {result.execution_time:.1f}s"
    })

    # Send final outputs (with full content for modal display)
    for node_id, messages in result.node_outputs.items():
        if messages:
            last_msg = messages[-1]
            # Send more content for modal display (up to 5000 chars)
            full_content = last_msg.content[:5000] if len(last_msg.content) > 5000 else last_msg.content
            await broadcast_event("node_output", {
                "node_id": node_id,
                "content_preview": full_content,
                "content_length": len(last_msg.content),
                "provider": last_msg.metadata.get("provider", "unknown")
            })

    # Save results
    output_file = executor.save_results(ticker)
    await broadcast_event("results_saved", {
        "file": output_file,
        "message": f"Results saved to {output_file}"
    })

    return result


async def run_single_ticker(ticker: str, workflow: str, semaphore: asyncio.Semaphore = None):
    """Run workflow for a single ticker with optional semaphore control"""

    async def _run():
        print(f"\n{'='*60}")
        print(f"STARTING WORKFLOW: {ticker}")
        print(f"{'='*60}\n")

        try:
            # Prefetch price and market data
            print(f"[{ticker}] Prefetching market data...", flush=True)
            prefetched_data = None
            verified_price = None

            try:
                from prefetch_data import prefetch_market_data
                prefetched_data = await prefetch_market_data(ticker)
                if prefetched_data and prefetched_data.get("confidence") in ["HIGH", "MEDIUM"]:
                    verified_price = prefetched_data.get("verified_price")
                    currency = prefetched_data.get('currency', 'USD')
                    print(f"[{ticker}] Verified price: {currency} {verified_price} (Confidence: {prefetched_data.get('confidence')})", flush=True)
                    if prefetched_data.get('shares_outstanding'):
                        print(f"[{ticker}]   Shares Outstanding: {prefetched_data.get('shares_outstanding'):.1f}M", flush=True)
                    if prefetched_data.get('market_cap'):
                        print(f"[{ticker}]   Market Cap: {prefetched_data.get('market_cap')/1e9:.2f}B", flush=True)
                else:
                    print(f"[{ticker}] WARNING: Could not verify price automatically.", flush=True)
            except Exception as e:
                print(f"[{ticker}] Price prefetch error: {e}", flush=True)

            # Run workflow
            print(f"[{ticker}] Running workflow...", flush=True)
            result = await run_live_workflow(ticker, workflow, verified_price, prefetched_data)

            if result and result.success:
                # Generate report
                print(f"[{ticker}] Generating report...", flush=True)
                try:
                    from generate_workflow_report import generate_workflow_report
                    workflow_path = f"context/{ticker.replace(' ', '_')}_workflow_result.json"
                    report_path = generate_workflow_report(workflow_path)
                    print(f"[{ticker}] Report generated: {report_path}", flush=True)
                except Exception as e:
                    print(f"[{ticker}] Report generation error: {e}", flush=True)

            print(f"\n[{ticker}] COMPLETED SUCCESSFULLY\n", flush=True)
            return ticker, True, None

        except Exception as e:
            print(f"\n[{ticker}] FAILED: {str(e)}\n", flush=True)
            return ticker, False, str(e)

    if semaphore:
        async with semaphore:
            return await _run()
    else:
        return await _run()


async def run_multiple_tickers(tickers: list, workflow: str, max_concurrent: int = 2):
    """Run multiple workflows in parallel with concurrency limit"""

    print("=" * 70)
    print("PARALLEL WORKFLOW EXECUTION")
    print("=" * 70)
    print(f"Tickers: {tickers}")
    print(f"Max concurrent: {max_concurrent}")
    print()

    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = [run_single_ticker(ticker, workflow, semaphore) for ticker in tickers]
    results = await asyncio.gather(*tasks)

    print("\n" + "=" * 70)
    print("EXECUTION SUMMARY")
    print("=" * 70)
    for ticker, success, error in results:
        status = "SUCCESS" if success else f"FAILED: {error}"
        print(f"  {ticker}: {status}")
    print("=" * 70)

    return results


async def run_workflows(tickers: list, port: int = 8765, workflow: str = "equity_research_v4", max_concurrent: int = 2):
    """Main entry point for single or multiple tickers"""
    global visualizer

    if VISUALIZER_AVAILABLE:
        visualizer = VisualizerBridge("context")
        visualizer.open_visualizer(port=8888)
        print(f"[Visualizer] Minions visualizer opened at http://localhost:8888", flush=True)

    print(f"Starting WebSocket server on ws://localhost:{port}", flush=True)
    ws_server = await websockets.serve(websocket_handler, "localhost", port)

    try:
        if len(tickers) == 1:
            await run_single_ticker(tickers[0], workflow)
        else:
            await run_multiple_tickers(tickers, workflow, max_concurrent)
    except Exception as e:
        await broadcast_event("error", {"message": str(e)})
        print(f"Error: {e}", flush=True)

    print("\nKeeping visualizer open for 30 seconds...", flush=True)
    await asyncio.sleep(30)

    ws_server.close()
    await ws_server.wait_closed()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run equity research workflow with live visualization")
    parser.add_argument("tickers", nargs="+", help="Equity tickers (e.g., '9660_HK' 'LEGN_US')")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port (default: 8765)")
    parser.add_argument("--workflow", type=str, default="equity_research_v4", help="Workflow name")
    parser.add_argument("--max-concurrent", "-c", type=int, default=2, help="Max concurrent workflows")

    args = parser.parse_args()

    asyncio.run(run_workflows(args.tickers, args.port, args.workflow, args.max_concurrent))
