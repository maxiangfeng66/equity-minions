"""
HTML Generator - Creates equity research reports in HTML format
"""

import os
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path


class HTMLGenerator:
    """Generates HTML reports for equity research"""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_equity_report(self, context: Dict[str, Any]) -> str:
        """Generate HTML report for a single equity"""

        ticker = context.get("ticker", "Unknown")
        company_name = context.get("company_name", "Unknown Company")

        # Extract data
        industry_analysis = context.get("industry_analysis", "Not available")
        company_analysis = context.get("company_analysis", "Not available")
        governance_analysis = context.get("governance_analysis", "Not available")
        scenario_analysis = context.get("scenario_analysis", {})
        debate_log = context.get("debate_log", [])

        # Build valuation table HTML
        valuation_table = self._build_valuation_table(scenario_analysis)

        # Build debate summary
        debate_summary = self._build_debate_summary(debate_log)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} - {company_name} Research Report</title>
    <style>
        :root {{
            --primary-color: #1a365d;
            --secondary-color: #2c5282;
            --accent-color: #3182ce;
            --bg-light: #f7fafc;
            --bg-dark: #edf2f7;
            --text-primary: #2d3748;
            --text-secondary: #4a5568;
            --success: #48bb78;
            --warning: #ed8936;
            --danger: #f56565;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background: var(--bg-light);
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 40px 20px;
            margin-bottom: 30px;
        }}

        header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}

        header .subtitle {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}

        .meta-info {{
            display: flex;
            gap: 20px;
            margin-top: 15px;
            flex-wrap: wrap;
        }}

        .meta-info span {{
            background: rgba(255,255,255,0.2);
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
        }}

        .section {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}

        .section h2 {{
            color: var(--primary-color);
            border-bottom: 3px solid var(--accent-color);
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}

        .section-content {{
            white-space: pre-wrap;
            font-size: 0.95rem;
            line-height: 1.8;
        }}

        .valuation-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}

        .valuation-table th,
        .valuation-table td {{
            padding: 12px 15px;
            text-align: center;
            border: 1px solid #e2e8f0;
        }}

        .valuation-table th {{
            background: var(--primary-color);
            color: white;
        }}

        .valuation-table tr:nth-child(even) {{
            background: var(--bg-dark);
        }}

        .valuation-table .scenario-super-bear {{ color: var(--danger); font-weight: bold; }}
        .valuation-table .scenario-bear {{ color: var(--warning); }}
        .valuation-table .scenario-base {{ color: var(--text-primary); font-weight: bold; }}
        .valuation-table .scenario-bull {{ color: var(--success); }}
        .valuation-table .scenario-super-bull {{ color: var(--success); font-weight: bold; }}

        .probability-weighted {{
            background: var(--bg-dark);
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }}

        .probability-weighted h3 {{
            color: var(--primary-color);
            margin-bottom: 15px;
        }}

        .probability-weighted .value {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent-color);
        }}

        .debate-log {{
            max-height: 500px;
            overflow-y: auto;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
        }}

        .debate-message {{
            margin-bottom: 15px;
            padding: 15px;
            border-radius: 8px;
            background: var(--bg-light);
        }}

        .debate-message.analyst {{ border-left: 4px solid var(--accent-color); }}
        .debate-message.bull {{ border-left: 4px solid var(--success); }}
        .debate-message.bear {{ border-left: 4px solid var(--danger); }}
        .debate-message.critic {{ border-left: 4px solid var(--warning); }}
        .debate-message.synthesizer {{ border-left: 4px solid var(--primary-color); }}

        .debate-message .role {{
            font-weight: bold;
            text-transform: uppercase;
            font-size: 0.8rem;
            margin-bottom: 5px;
        }}

        .nav-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: var(--accent-color);
            text-decoration: none;
        }}

        .nav-link:hover {{
            text-decoration: underline;
        }}

        footer {{
            text-align: center;
            padding: 30px;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}

        @media (max-width: 768px) {{
            header h1 {{
                font-size: 1.8rem;
            }}

            .section {{
                padding: 20px;
            }}

            .valuation-table {{
                font-size: 0.85rem;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>{ticker}</h1>
            <div class="subtitle">{company_name}</div>
            <div class="meta-info">
                <span>Sector: {context.get("sector", "N/A")}</span>
                <span>Industry: {context.get("industry", "N/A")}</span>
                <span>Report Date: {datetime.now().strftime("%Y-%m-%d")}</span>
            </div>
        </div>
    </header>

    <div class="container">
        <a href="index.html" class="nav-link">&larr; Back to Index</a>

        <section class="section">
            <h2>Executive Summary</h2>
            <div class="section-content">
{self._extract_executive_summary(context)}
            </div>
        </section>

        <section class="section">
            <h2>Valuation Summary</h2>
            {valuation_table}

            <div class="probability-weighted">
                <h3>Probability-Weighted Fair Value</h3>
                <div class="value">{self._get_probability_weighted_value(scenario_analysis)}</div>
            </div>
        </section>

        <section class="section">
            <h2>Industry Analysis</h2>
            <div class="section-content">{industry_analysis}</div>
        </section>

        <section class="section">
            <h2>Company Analysis</h2>
            <div class="section-content">{company_analysis}</div>
        </section>

        <section class="section">
            <h2>Corporate Governance</h2>
            <div class="section-content">{governance_analysis}</div>
        </section>

        <section class="section">
            <h2>Multi-Agent Debate Log</h2>
            <div class="debate-log">
                {debate_summary}
            </div>
        </section>
    </div>

    <footer>
        <p>Generated by Equity Research Multi-Agent System</p>
        <p>This report is for informational purposes only and does not constitute investment advice.</p>
    </footer>
</body>
</html>"""

        # Save the file
        filename = f"{ticker.replace(' ', '_')}.html"
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(filepath)

    def generate_index(self, equities: Dict[str, Dict[str, Any]]) -> str:
        """Generate index HTML with links to all equity reports"""

        equity_cards = ""
        for ticker, info in equities.items():
            filename = f"{ticker.replace(' ', '_')}.html"
            equity_cards += f"""
                <a href="{filename}" class="equity-card">
                    <div class="ticker">{ticker}</div>
                    <div class="name">{info.get('name', 'Unknown')}</div>
                    <div class="sector">{info.get('sector', 'N/A')}</div>
                    <div class="industry">{info.get('industry', 'N/A')}</div>
                </a>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Equity Research Reports</title>
    <style>
        :root {{
            --primary-color: #1a365d;
            --secondary-color: #2c5282;
            --accent-color: #3182ce;
            --bg-light: #f7fafc;
            --text-primary: #2d3748;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-light);
            min-height: 100vh;
        }}

        header {{
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 50px 20px;
            text-align: center;
        }}

        header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}

        header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}

        .stats {{
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-bottom: 40px;
        }}

        .stat {{
            text-align: center;
        }}

        .stat .number {{
            font-size: 2.5rem;
            font-weight: bold;
            color: var(--accent-color);
        }}

        .stat .label {{
            color: var(--text-primary);
        }}

        .equity-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }}

        .equity-card {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            text-decoration: none;
            color: var(--text-primary);
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .equity-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}

        .equity-card .ticker {{
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--primary-color);
            margin-bottom: 5px;
        }}

        .equity-card .name {{
            font-size: 1.1rem;
            margin-bottom: 15px;
        }}

        .equity-card .sector,
        .equity-card .industry {{
            font-size: 0.9rem;
            color: #718096;
        }}

        footer {{
            text-align: center;
            padding: 30px;
            color: #718096;
        }}
    </style>
</head>
<body>
    <header>
        <h1>Equity Research Reports</h1>
        <p>Multi-Agent Analysis with Scenario-Based Valuations</p>
    </header>

    <div class="container">
        <div class="stats">
            <div class="stat">
                <div class="number">{len(equities)}</div>
                <div class="label">Equities Analyzed</div>
            </div>
            <div class="stat">
                <div class="number">10</div>
                <div class="label">Debate Rounds</div>
            </div>
            <div class="stat">
                <div class="number">5</div>
                <div class="label">Scenarios per Equity</div>
            </div>
        </div>

        <div class="equity-grid">
            {equity_cards}
        </div>
    </div>

    <footer>
        <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
        <p>Reports are for informational purposes only.</p>
    </footer>
</body>
</html>"""

        filepath = self.output_dir / "index.html"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(filepath)

    def _build_valuation_table(self, scenario_analysis: Dict[str, Any]) -> str:
        """Build HTML table for valuation matrix"""
        if not scenario_analysis or "intrinsic_values" not in scenario_analysis:
            return "<p>Valuation data not yet available</p>"

        intrinsic_values = scenario_analysis.get("intrinsic_values", {})
        scenarios = ["super_bear", "bear", "base", "bull", "super_bull"]
        scenario_labels = {
            "super_bear": "Super Bear (5%)",
            "bear": "Bear (20%)",
            "base": "Base (50%)",
            "bull": "Bull (20%)",
            "super_bull": "Super Bull (5%)"
        }

        header_row = "<tr><th>Discount Rate</th>"
        for s in scenarios:
            header_row += f"<th>{scenario_labels.get(s, s)}</th>"
        header_row += "</tr>"

        body_rows = ""
        for rate in ["8%", "9%", "10%", "11%"]:
            body_rows += f"<tr><td><strong>{rate}</strong></td>"
            rate_values = intrinsic_values.get(rate, {})
            for s in scenarios:
                value = rate_values.get(s, "N/A")
                css_class = f"scenario-{s.replace('_', '-')}"
                body_rows += f'<td class="{css_class}">{value}</td>'
            body_rows += "</tr>"

        return f"""
        <table class="valuation-table">
            <thead>{header_row}</thead>
            <tbody>{body_rows}</tbody>
        </table>
        """

    def _build_debate_summary(self, debate_log: List[Dict[str, Any]]) -> str:
        """Build HTML summary of debate log"""
        if not debate_log:
            return "<p>No debate log available</p>"

        html = ""
        for msg in debate_log[-10:]:  # Show last 10 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:500]  # Truncate for display
            html += f"""
            <div class="debate-message {role}">
                <div class="role">{role}</div>
                <div class="content">{content}...</div>
            </div>
            """
        return html

    def _extract_executive_summary(self, context: Dict[str, Any]) -> str:
        """Extract or generate executive summary"""
        # Look for synthesizer's final message
        debate_log = context.get("debate_log", [])
        for msg in reversed(debate_log):
            if msg.get("role") == "synthesizer" and "final" in msg.get("metadata", {}).get("type", ""):
                return msg.get("content", "")[:1500]

        return "Executive summary will be generated after analysis is complete."

    def _get_probability_weighted_value(self, scenario_analysis: Dict[str, Any]) -> str:
        """Get the probability-weighted fair value"""
        if "probability_weighted_value" in scenario_analysis:
            pw = scenario_analysis["probability_weighted_value"]
            if isinstance(pw, dict):
                # Return the 10% discount rate value as default
                return f"${pw.get('10%', 'N/A')}"
            return f"${pw}"

        if "recommended_fair_value" in scenario_analysis:
            return f"${scenario_analysis['recommended_fair_value']}"

        return "To be calculated"
