#!/usr/bin/env python3
"""
Regenerate all equity reports using the updated HTMLGenerator with canonical template.
This script reads existing context files and regenerates HTML reports.
"""

import json
import sys
from pathlib import Path
from config import EQUITIES
from utils.html_generator import HTMLGenerator

def main():
    """Regenerate all equity reports from existing context files."""
    context_dir = Path("context")
    generator = HTMLGenerator("reports")

    # Track success/failure
    success = []
    failed = []

    print("=" * 60)
    print("REGENERATING ALL EQUITY REPORTS")
    print("Using canonical detailed template with sidebar navigation")
    print("=" * 60)

    for ticker, info in EQUITIES.items():
        # Normalize ticker for filename
        ticker_normalized = ticker.replace(" ", "_")

        # Try to find the context file
        context_file = None
        possible_names = [
            f"{ticker_normalized}_context.json",
            f"{ticker_normalized}_{info['name'].replace(' ', '_')}.json",
        ]

        for name in possible_names:
            path = context_dir / name
            if path.exists():
                context_file = path
                break

        if not context_file:
            print(f"[SKIP] {ticker} - No context file found")
            failed.append((ticker, "No context file"))
            continue

        try:
            # Load context
            with open(context_file, 'r', encoding='utf-8') as f:
                context = json.load(f)

            # Add ticker and company info if missing
            context.setdefault("ticker", ticker)
            context.setdefault("company_name", info.get("name", "Unknown"))
            context.setdefault("sector", info.get("sector", "N/A"))
            context.setdefault("industry", info.get("industry", "N/A"))

            # Also try to load debate log if separate
            debate_file = context_dir / "debates" / f"debate_{ticker_normalized}.json"
            if debate_file.exists():
                with open(debate_file, 'r', encoding='utf-8') as f:
                    debate_data = json.load(f)
                    if "debate_log" not in context and "messages" in debate_data:
                        context["debate_log"] = debate_data["messages"]

            # Generate report
            output_path = generator.generate_equity_report(context)
            print(f"[OK] {ticker} -> {output_path}")
            success.append(ticker)

        except Exception as e:
            print(f"[ERROR] {ticker} - {str(e)}")
            failed.append((ticker, str(e)))

    # Generate index page
    try:
        index_path = generator.generate_index(EQUITIES)
        print(f"\n[OK] Index page -> {index_path}")
    except Exception as e:
        print(f"\n[ERROR] Failed to generate index: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("REGENERATION COMPLETE")
    print("=" * 60)
    print(f"Success: {len(success)}/{len(EQUITIES)}")
    if failed:
        print(f"Failed: {len(failed)}")
        for ticker, reason in failed:
            print(f"  - {ticker}: {reason}")

    return len(failed) == 0

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
