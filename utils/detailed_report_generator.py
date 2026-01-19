"""
Detailed HTML Report Generator
Creates comprehensive single-page reports with all research data
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class DetailedReportGenerator:
    """Generates detailed HTML reports from context JSON files"""

    def __init__(self, context_dir: str = "context", output_dir: str = "reports"):
        self.context_dir = Path(context_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_all_detailed_reports(self) -> List[str]:
        """Generate detailed reports for all equities with context files"""
        generated = []

        for json_file in self.context_dir.glob("*.json"):
            if json_file.name in ["session_state.json", "verified_prices.json"]:
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if "ticker" in data:
                    output_path = self.generate_detailed_report(data)
                    generated.append(output_path)
                    print(f"Generated: {output_path}")
            except Exception as e:
                print(f"Error processing {json_file}: {e}")

        return generated

    def generate_detailed_report(self, data: Dict[str, Any]) -> str:
        """Generate a detailed HTML report for a single equity"""

        ticker = data.get("ticker", "Unknown")
        company = data.get("company", "Unknown Company")
        sector = data.get("sector", "")

        # Load debate data if available
        debate_data = self._load_debate_data(ticker)

        html = self._build_html(data, debate_data)

        # Save with _detailed suffix
        filename = f"{ticker.replace(' ', '_')}_detailed.html"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(filepath)

    def _load_debate_data(self, ticker: str) -> Dict:
        """Load debate data for the equity"""
        debate_file = self.context_dir / "debates" / f"debate_{ticker.replace(' ', '_')}.json"
        if debate_file.exists():
            with open(debate_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _build_html(self, data: Dict, debate_data: Dict) -> str:
        """Build the complete HTML document"""

        ticker = data.get("ticker", "Unknown")
        company = data.get("company", "Unknown Company")
        sector = data.get("sector", "")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} - Detailed Research Report | {company}</title>
    <style>
{self._get_css()}
    </style>
</head>
<body>
    <nav class="sidebar">
        <div class="nav-header">
            <h3>{ticker}</h3>
            <p>{company[:30]}{'...' if len(company) > 30 else ''}</p>
        </div>
        <ul class="nav-links">
            <li><a href="#executive-summary">Executive Summary</a></li>
            <li><a href="#industry-analysis">Industry Analysis</a></li>
            <li><a href="#company-analysis">Company Analysis</a></li>
            <li><a href="#financial-data">Financial Data</a></li>
            <li><a href="#dcf-valuation">DCF Valuation</a></li>
            <li><a href="#scenarios">Scenario Analysis</a></li>
            <li><a href="#risks">Risk Assessment</a></li>
            <li><a href="#recommendation">Recommendation</a></li>
            <li><a href="#debate-log">Debate Log</a></li>
        </ul>
        <div class="nav-footer">
            <a href="{ticker.replace(' ', '_')}.html" class="back-link">← Back to Summary</a>
            <a href="index.html" class="back-link">← Portfolio Index</a>
        </div>
    </nav>

    <main class="content">
        <header>
            <div class="header-info">
                <h1>{ticker}</h1>
                <h2>{company}</h2>
                <p class="sector">{sector}</p>
            </div>
            {self._build_recommendation_badge(data)}
        </header>

        {self._build_executive_summary(data)}
        {self._build_industry_analysis(data)}
        {self._build_company_analysis(data)}
        {self._build_financial_data(data)}
        {self._build_dcf_valuation(data)}
        {self._build_scenarios(data)}
        {self._build_risks(data)}
        {self._build_recommendation(data)}
        {self._build_debate_log(debate_data)}

        <footer>
            <p>Detailed Research Report | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p>This report is for informational purposes only and does not constitute investment advice.</p>
        </footer>
    </main>

    <script>
        // Smooth scrolling for navigation
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', function (e) {{
                e.preventDefault();
                document.querySelector(this.getAttribute('href')).scrollIntoView({{
                    behavior: 'smooth'
                }});
            }});
        }});

        // Highlight current section in nav
        const sections = document.querySelectorAll('section[id]');
        const navLinks = document.querySelectorAll('.nav-links a');

        window.addEventListener('scroll', () => {{
            let current = '';
            sections.forEach(section => {{
                const sectionTop = section.offsetTop;
                if (scrollY >= sectionTop - 100) {{
                    current = section.getAttribute('id');
                }}
            }});

            navLinks.forEach(link => {{
                link.classList.remove('active');
                if (link.getAttribute('href') === '#' + current) {{
                    link.classList.add('active');
                }}
            }});
        }});
    </script>
</body>
</html>"""

    def _get_css(self) -> str:
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            line-height: 1.6;
        }

        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            width: 250px;
            height: 100vh;
            background: #161b22;
            border-right: 1px solid #30363d;
            padding: 20px 0;
            overflow-y: auto;
            z-index: 100;
        }

        .nav-header {
            padding: 0 20px 20px;
            border-bottom: 1px solid #30363d;
        }

        .nav-header h3 {
            color: #58a6ff;
            font-size: 1.3em;
        }

        .nav-header p {
            color: #8b949e;
            font-size: 0.85em;
        }

        .nav-links {
            list-style: none;
            padding: 15px 0;
        }

        .nav-links li a {
            display: block;
            padding: 10px 20px;
            color: #8b949e;
            text-decoration: none;
            font-size: 0.9em;
            transition: all 0.2s;
        }

        .nav-links li a:hover,
        .nav-links li a.active {
            color: #58a6ff;
            background: rgba(88, 166, 255, 0.1);
            border-left: 3px solid #58a6ff;
        }

        .nav-footer {
            padding: 20px;
            border-top: 1px solid #30363d;
        }

        .back-link {
            display: block;
            color: #58a6ff;
            text-decoration: none;
            font-size: 0.85em;
            margin-bottom: 10px;
        }

        .back-link:hover {
            text-decoration: underline;
        }

        .content {
            margin-left: 250px;
            padding: 30px 40px;
            max-width: 1200px;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 30px;
            background: linear-gradient(135deg, #161b22 0%, #21262d 100%);
            border-radius: 12px;
            border: 1px solid #30363d;
            margin-bottom: 30px;
        }

        header h1 {
            color: #58a6ff;
            font-size: 2.5em;
        }

        header h2 {
            color: #c9d1d9;
            font-size: 1.3em;
            font-weight: normal;
        }

        header .sector {
            color: #8b949e;
            margin-top: 8px;
        }

        .recommendation-badge {
            padding: 15px 25px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 1.2em;
            text-transform: uppercase;
        }

        .badge-buy { background: #238636; color: #fff; }
        .badge-hold { background: #9e6a03; color: #fff; }
        .badge-sell { background: #da3633; color: #fff; }
        .badge-outperform { background: #1f6feb; color: #fff; }

        section {
            background: #161b22;
            border-radius: 12px;
            border: 1px solid #30363d;
            padding: 30px;
            margin-bottom: 25px;
        }

        section h2 {
            color: #58a6ff;
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #30363d;
        }

        section h3 {
            color: #c9d1d9;
            font-size: 1.2em;
            margin: 20px 0 15px;
        }

        section h4 {
            color: #8b949e;
            font-size: 1em;
            margin: 15px 0 10px;
        }

        .highlight-box {
            background: linear-gradient(135deg, #1f3a5c 0%, #1a2733 100%);
            border-left: 4px solid #58a6ff;
            padding: 20px;
            border-radius: 0 8px 8px 0;
            margin: 15px 0;
        }

        .key-points {
            list-style: none;
            padding: 0;
        }

        .key-points li {
            padding: 10px 0 10px 25px;
            position: relative;
            border-bottom: 1px solid #21262d;
        }

        .key-points li:before {
            content: "→";
            position: absolute;
            left: 0;
            color: #58a6ff;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }

        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #30363d;
        }

        th {
            background: #21262d;
            color: #58a6ff;
            font-weight: 600;
        }

        tr:hover {
            background: rgba(88, 166, 255, 0.05);
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }

        .metric-card {
            background: #21262d;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }

        .metric-card .label {
            color: #8b949e;
            font-size: 0.8em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .metric-card .value {
            color: #58a6ff;
            font-size: 1.5em;
            font-weight: bold;
            margin-top: 5px;
        }

        .metric-card .value.positive { color: #3fb950; }
        .metric-card .value.negative { color: #f85149; }

        .scenario-card {
            background: #21262d;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
        }

        .scenario-card.super-bear { border-left: 4px solid #da3633; }
        .scenario-card.bear { border-left: 4px solid #f85149; }
        .scenario-card.base { border-left: 4px solid #58a6ff; }
        .scenario-card.bull { border-left: 4px solid #3fb950; }
        .scenario-card.super-bull { border-left: 4px solid #238636; }

        .scenario-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .scenario-header h4 {
            margin: 0;
            color: #c9d1d9;
        }

        .probability-badge {
            background: #30363d;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.85em;
        }

        .risk-item {
            background: #21262d;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #f85149;
        }

        .risk-item.medium { border-left-color: #9e6a03; }
        .risk-item.low { border-left-color: #3fb950; }

        .risk-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }

        .risk-header h5 {
            color: #c9d1d9;
            margin: 0;
        }

        .impact-badge {
            font-size: 0.75em;
            padding: 3px 8px;
            border-radius: 10px;
            background: #30363d;
        }

        .debate-round {
            background: #21262d;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
        }

        .debate-round h4 {
            color: #58a6ff;
            margin-bottom: 15px;
        }

        .debate-message {
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            background: #0d1117;
        }

        .debate-message.analyst { border-left: 3px solid #58a6ff; }
        .debate-message.bull { border-left: 3px solid #3fb950; }
        .debate-message.bear { border-left: 3px solid #f85149; }
        .debate-message.critic { border-left: 3px solid #9e6a03; }
        .debate-message.synthesizer { border-left: 3px solid #a371f7; }

        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 0.85em;
        }

        .message-role {
            font-weight: bold;
            text-transform: uppercase;
        }

        .message-role.analyst { color: #58a6ff; }
        .message-role.bull { color: #3fb950; }
        .message-role.bear { color: #f85149; }
        .message-role.critic { color: #9e6a03; }
        .message-role.synthesizer { color: #a371f7; }

        .message-ai { color: #8b949e; }

        footer {
            text-align: center;
            padding: 30px;
            color: #8b949e;
            font-size: 0.9em;
            border-top: 1px solid #30363d;
            margin-top: 30px;
        }

        .collapsible {
            cursor: pointer;
            user-select: none;
        }

        .collapsible:after {
            content: " ▼";
            font-size: 0.7em;
        }

        .collapsible.collapsed:after {
            content: " ▶";
        }

        @media (max-width: 900px) {
            .sidebar {
                display: none;
            }
            .content {
                margin-left: 0;
                padding: 20px;
            }
        }
        """

    def _build_recommendation_badge(self, data: Dict) -> str:
        rec = data.get("recommendation", {})
        rating = rec.get("rating", data.get("executive_summary", {}).get("rating", "HOLD"))

        badge_class = "badge-hold"
        if "BUY" in rating.upper() or "OUTPERFORM" in rating.upper():
            badge_class = "badge-buy"
        elif "SELL" in rating.upper() or "UNDERPERFORM" in rating.upper():
            badge_class = "badge-sell"

        return f'<div class="recommendation-badge {badge_class}">{rating}</div>'

    def _build_executive_summary(self, data: Dict) -> str:
        summary = data.get("executive_summary", {})

        if not summary:
            return ""

        overview = summary.get("overview", "")
        thesis = summary.get("investment_thesis", "")
        highlights = summary.get("key_highlights", [])

        highlights_html = ""
        if highlights:
            highlights_html = "<ul class='key-points'>"
            for h in highlights:
                highlights_html += f"<li>{h}</li>"
            highlights_html += "</ul>"

        target = summary.get("target_price_range", {})
        target_html = ""
        if target:
            target_html = f"""
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="label">Target (Low)</div>
                    <div class="value">${target.get('low', 'N/A')}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Target (Base)</div>
                    <div class="value">${target.get('base', 'N/A')}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Target (High)</div>
                    <div class="value">${target.get('high', 'N/A')}</div>
                </div>
            </div>
            """

        return f"""
        <section id="executive-summary">
            <h2>Executive Summary</h2>

            <div class="highlight-box">
                <p>{overview}</p>
            </div>

            <h3>Investment Thesis</h3>
            <p>{thesis}</p>

            <h3>Key Highlights</h3>
            {highlights_html}

            {target_html}
        </section>
        """

    def _build_industry_analysis(self, data: Dict) -> str:
        industry = data.get("industry_analysis", {})

        if not industry:
            return """
        <section id="industry-analysis">
            <h2>Industry Analysis</h2>
            <p>Industry analysis data not available.</p>
        </section>
        """

        # Build market overview
        market = industry.get("car_t_market_overview", industry.get("market_overview", {}))
        market_html = ""
        if market:
            market_html = f"""
            <h3>Market Overview</h3>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="label">Market Size (2024)</div>
                    <div class="value">{market.get('market_size_2024', 'N/A')}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Projected (2030)</div>
                    <div class="value">{market.get('market_size_2030_projected', 'N/A')}</div>
                </div>
                <div class="metric-card">
                    <div class="label">CAGR</div>
                    <div class="value positive">{market.get('cagr_2024_2030', 'N/A')}</div>
                </div>
            </div>
            """

            drivers = market.get("key_drivers", [])
            if drivers:
                market_html += "<h4>Key Growth Drivers</h4><ul class='key-points'>"
                for d in drivers:
                    market_html += f"<li>{d}</li>"
                market_html += "</ul>"

        # Build competitive landscape
        competitive = industry.get("competitive_landscape", {})
        competitive_html = ""
        if competitive:
            players = competitive.get("major_players", [])
            if players:
                competitive_html = """
                <h3>Competitive Landscape</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Company</th>
                            <th>Product</th>
                            <th>Target</th>
                            <th>2024 Sales Est.</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for p in players:
                    competitive_html += f"""
                        <tr>
                            <td>{p.get('company', 'N/A')}</td>
                            <td>{p.get('product', 'N/A')}</td>
                            <td>{p.get('target', 'N/A')}</td>
                            <td>{p.get('2024_sales_estimate', 'N/A')}</td>
                        </tr>
                    """
                competitive_html += "</tbody></table>"

            threats = competitive.get("emerging_threats", [])
            if threats:
                competitive_html += "<h4>Emerging Threats</h4><ul class='key-points'>"
                for t in threats:
                    competitive_html += f"<li>{t}</li>"
                competitive_html += "</ul>"

        return f"""
        <section id="industry-analysis">
            <h2>Industry Analysis</h2>
            {market_html}
            {competitive_html}
        </section>
        """

    def _build_company_analysis(self, data: Dict) -> str:
        company = data.get("company_analysis", {})

        if not company:
            return """
        <section id="company-analysis">
            <h2>Company Analysis</h2>
            <p>Company analysis data not available.</p>
        </section>
        """

        # Product overview
        product = company.get("carvykti_overview", company.get("product_overview", {}))
        product_html = ""
        if product:
            product_html = f"""
            <h3>Lead Product</h3>
            <div class="highlight-box">
                <p><strong>{product.get('generic_name', 'N/A')}</strong></p>
                <p>{product.get('mechanism', 'N/A')}</p>
            </div>
            """

            # Clinical efficacy
            efficacy = product.get("clinical_efficacy", {})
            if efficacy:
                product_html += "<h4>Clinical Efficacy Data</h4>"
                for trial, trial_data in efficacy.items():
                    product_html += f"""
                    <div class="scenario-card base">
                        <h4>{trial.upper()}</h4>
                        <div class="metrics-grid">
                    """
                    for key, val in trial_data.items():
                        if key != "population":
                            product_html += f"""
                            <div class="metric-card">
                                <div class="label">{key.upper()}</div>
                                <div class="value">{val}</div>
                            </div>
                            """
                    product_html += "</div>"
                    if "population" in trial_data:
                        product_html += f"<p style='color: #8b949e; margin-top: 10px;'>Population: {trial_data['population']}</p>"
                    product_html += "</div>"

            # Commercial performance
            commercial = product.get("commercial_performance", {})
            if commercial:
                product_html += """
                <h4>Commercial Performance</h4>
                <table>
                    <thead><tr><th>Period</th><th>Sales</th></tr></thead>
                    <tbody>
                """
                for period, sales in commercial.items():
                    product_html += f"<tr><td>{period.replace('_', ' ').title()}</td><td>{sales}</td></tr>"
                product_html += "</tbody></table>"

        # Pipeline
        pipeline = company.get("pipeline", {})
        pipeline_html = ""
        if pipeline:
            clinical = pipeline.get("clinical_stage", [])
            if clinical:
                pipeline_html = """
                <h3>Pipeline</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Program</th>
                            <th>Target</th>
                            <th>Indication</th>
                            <th>Stage</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for prog in clinical:
                    pipeline_html += f"""
                        <tr>
                            <td>{prog.get('program', 'N/A')}</td>
                            <td>{prog.get('target', 'N/A')}</td>
                            <td>{prog.get('indication', 'N/A')}</td>
                            <td>{prog.get('stage', 'N/A')}</td>
                            <td>{prog.get('status', 'N/A')}</td>
                        </tr>
                    """
                pipeline_html += "</tbody></table>"

        # Competitive advantages
        advantages = company.get("competitive_advantages", [])
        advantages_html = ""
        if advantages:
            advantages_html = "<h3>Competitive Advantages</h3><ul class='key-points'>"
            for a in advantages:
                advantages_html += f"<li>{a}</li>"
            advantages_html += "</ul>"

        return f"""
        <section id="company-analysis">
            <h2>Company Analysis</h2>
            {product_html}
            {pipeline_html}
            {advantages_html}
        </section>
        """

    def _build_financial_data(self, data: Dict) -> str:
        fin = data.get("financial_data", {})

        if not fin:
            return """
        <section id="financial-data">
            <h2>Financial Data</h2>
            <p>Financial data not available.</p>
        </section>
        """

        # Income statement
        income = fin.get("income_statement", {})
        income_html = ""
        if income:
            income_html = """
            <h3>Income Statement Summary</h3>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
            """
            years = [k for k in income.keys() if k.startswith("fy")]
            for year in sorted(years):
                income_html += f"<th>{year.upper()}</th>"
            income_html += "</tr></thead><tbody>"

            metrics = ["total_revenue", "operating_income", "net_income", "eps_basic"]
            metric_labels = {"total_revenue": "Total Revenue", "operating_income": "Operating Income",
                           "net_income": "Net Income", "eps_basic": "EPS (Basic)"}

            for metric in metrics:
                income_html += f"<tr><td>{metric_labels.get(metric, metric)}</td>"
                for year in sorted(years):
                    val = income.get(year, {}).get(metric, "N/A")
                    if isinstance(val, (int, float)) and metric != "eps_basic":
                        val = f"${val/1e6:.1f}M" if abs(val) >= 1e6 else f"${val:,.0f}"
                    elif isinstance(val, float) and metric == "eps_basic":
                        val = f"${val:.2f}"
                    income_html += f"<td>{val}</td>"
                income_html += "</tr>"
            income_html += "</tbody></table>"

        # Balance sheet
        balance = fin.get("balance_sheet", {})
        balance_html = ""
        if balance:
            balance_html = f"""
            <h3>Balance Sheet Highlights</h3>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="label">Cash Position</div>
                    <div class="value">${balance.get('total_cash_position', 0)/1e6:.0f}M</div>
                </div>
                <div class="metric-card">
                    <div class="label">Total Debt</div>
                    <div class="value">${balance.get('total_debt', 0)/1e6:.0f}M</div>
                </div>
                <div class="metric-card">
                    <div class="label">Shareholders Equity</div>
                    <div class="value">${balance.get('shareholders_equity', 0)/1e6:.0f}M</div>
                </div>
            </div>
            """

        # Market data
        market = fin.get("market_data", {})
        market_html = ""
        if market:
            market_html = f"""
            <h3>Market Data</h3>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="label">Market Cap</div>
                    <div class="value">${market.get('market_cap', 0)/1e9:.1f}B</div>
                </div>
                <div class="metric-card">
                    <div class="label">Enterprise Value</div>
                    <div class="value">${market.get('enterprise_value', 0)/1e9:.1f}B</div>
                </div>
                <div class="metric-card">
                    <div class="label">52W High</div>
                    <div class="value">${market.get('52_week_high', 'N/A')}</div>
                </div>
                <div class="metric-card">
                    <div class="label">52W Low</div>
                    <div class="value">${market.get('52_week_low', 'N/A')}</div>
                </div>
            </div>
            """

        return f"""
        <section id="financial-data">
            <h2>Financial Data</h2>
            {income_html}
            {balance_html}
            {market_html}
        </section>
        """

    def _build_dcf_valuation(self, data: Dict) -> str:
        dcf = data.get("dcf_valuation", {})
        pwp = data.get("probability_weighted_price", {})

        if not dcf and not pwp:
            return """
        <section id="dcf-valuation">
            <h2>DCF Valuation</h2>
            <p>DCF valuation data not available.</p>
        </section>
        """

        # Key assumptions
        assumptions = dcf.get("key_assumptions", {})
        assumptions_html = ""
        if assumptions:
            wacc = assumptions.get("wacc_range", {})
            assumptions_html = f"""
            <h3>Key Assumptions</h3>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="label">WACC (Base)</div>
                    <div class="value">{wacc.get('base', 'N/A')}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Terminal Growth</div>
                    <div class="value">{assumptions.get('terminal_growth', 'N/A')}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Tax Rate</div>
                    <div class="value">{assumptions.get('tax_rate', 'N/A')}</div>
                </div>
            </div>
            """

        # Probability weighted values
        pwp_html = ""
        if pwp:
            calcs = pwp.get("calculations", {})
            summary = pwp.get("summary", {})

            if calcs:
                pwp_html = """
                <h3>Probability-Weighted Valuation by Discount Rate</h3>
                <table>
                    <thead>
                        <tr>
                            <th>WACC</th>
                            <th>Super Bear</th>
                            <th>Bear</th>
                            <th>Base</th>
                            <th>Bull</th>
                            <th>Super Bull</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for wacc_key, wacc_data in calcs.items():
                    if isinstance(wacc_data, dict):
                        pwp_html += f"""
                        <tr>
                            <td>{wacc_key.replace('at_', '').replace('_percent_wacc', '%').replace('_', ' ').title()}</td>
                            <td>${wacc_data.get('super_bear_contribution', 0):.2f}</td>
                            <td>${wacc_data.get('bear_contribution', 0):.2f}</td>
                            <td>${wacc_data.get('base_contribution', 0):.2f}</td>
                            <td>${wacc_data.get('bull_contribution', 0):.2f}</td>
                            <td>${wacc_data.get('super_bull_contribution', 0):.2f}</td>
                            <td><strong>${wacc_data.get('total', 0):.2f}</strong></td>
                        </tr>
                        """
                pwp_html += "</tbody></table>"

            if summary:
                pwp_html += f"""
                <div class="highlight-box">
                    <h4>Valuation Summary</h4>
                    <p><strong>Recommended Fair Value:</strong> ${summary.get('recommended_fair_value', 'N/A')}</p>
                    <p><strong>Implied Upside:</strong> {summary.get('implied_upside', 'N/A')}</p>
                    <p style="color: #8b949e; margin-top: 10px;">{summary.get('notes', '')}</p>
                </div>
                """

        return f"""
        <section id="dcf-valuation">
            <h2>DCF Valuation</h2>
            {assumptions_html}
            {pwp_html}
        </section>
        """

    def _build_scenarios(self, data: Dict) -> str:
        scenarios = data.get("scenarios", {})

        if not scenarios:
            return """
        <section id="scenarios">
            <h2>Scenario Analysis</h2>
            <p>Scenario analysis data not available.</p>
        </section>
        """

        scenario_order = ["super_bear", "bear", "base", "bull", "super_bull"]
        scenarios_html = ""

        for scenario_key in scenario_order:
            scenario = scenarios.get(scenario_key, {})
            if not scenario:
                continue

            prob = scenario.get("probability", 0) * 100
            desc = scenario.get("description", "")
            assumptions = scenario.get("assumptions", [])
            base_val = scenario.get("base_case_value", "N/A")

            assumptions_html = ""
            if assumptions:
                assumptions_html = "<ul class='key-points'>"
                for a in assumptions[:5]:  # Limit to 5
                    assumptions_html += f"<li>{a}</li>"
                assumptions_html += "</ul>"

            scenarios_html += f"""
            <div class="scenario-card {scenario_key.replace('_', '-')}">
                <div class="scenario-header">
                    <h4>{scenario_key.replace('_', ' ').title()} Case</h4>
                    <span class="probability-badge">{prob:.0f}% probability</span>
                </div>
                <p>{desc}</p>
                <h4>Key Assumptions</h4>
                {assumptions_html}
                <div class="metrics-grid" style="margin-top: 15px;">
                    <div class="metric-card">
                        <div class="label">Base Case Value</div>
                        <div class="value">${base_val}</div>
                    </div>
                </div>
            </div>
            """

        return f"""
        <section id="scenarios">
            <h2>Scenario Analysis</h2>
            {scenarios_html}
        </section>
        """

    def _build_risks(self, data: Dict) -> str:
        risks = data.get("risks", {})

        if not risks:
            return """
        <section id="risks">
            <h2>Risk Assessment</h2>
            <p>Risk assessment data not available.</p>
        </section>
        """

        risks_html = ""

        for category, risk_list in risks.items():
            if not isinstance(risk_list, list):
                continue

            risks_html += f"<h3>{category.replace('_', ' ').title()}</h3>"

            for risk in risk_list:
                if isinstance(risk, dict):
                    impact = risk.get("impact", "Medium").lower()
                    risk_class = "low" if "low" in impact else ("medium" if "medium" in impact else "")

                    risks_html += f"""
                    <div class="risk-item {risk_class}">
                        <div class="risk-header">
                            <h5>{risk.get('risk', 'Unknown Risk')}</h5>
                            <span class="impact-badge">Impact: {risk.get('impact', 'N/A')} | Prob: {risk.get('probability', 'N/A')}</span>
                        </div>
                        <p>{risk.get('description', '')}</p>
                        <p style="color: #3fb950; margin-top: 8px;"><strong>Mitigation:</strong> {risk.get('mitigation', 'N/A')}</p>
                    </div>
                    """

        return f"""
        <section id="risks">
            <h2>Risk Assessment</h2>
            {risks_html}
        </section>
        """

    def _build_recommendation(self, data: Dict) -> str:
        rec = data.get("recommendation", {})

        if not rec:
            return """
        <section id="recommendation">
            <h2>Recommendation</h2>
            <p>Recommendation data not available.</p>
        </section>
        """

        rationale = rec.get("rationale", [])
        rationale_html = ""
        if rationale:
            rationale_html = "<ul class='key-points'>"
            for r in rationale:
                rationale_html += f"<li>{r}</li>"
            rationale_html += "</ul>"

        catalysts = rec.get("key_catalysts", [])
        catalysts_html = ""
        if catalysts:
            catalysts_html = """
            <h3>Key Catalysts</h3>
            <table>
                <thead><tr><th>Catalyst</th><th>Timing</th><th>Impact</th></tr></thead>
                <tbody>
            """
            for c in catalysts:
                if isinstance(c, dict):
                    catalysts_html += f"""
                    <tr>
                        <td>{c.get('catalyst', 'N/A')}</td>
                        <td>{c.get('timing', 'N/A')}</td>
                        <td>{c.get('impact', 'N/A')}</td>
                    </tr>
                    """
            catalysts_html += "</tbody></table>"

        return f"""
        <section id="recommendation">
            <h2>Recommendation</h2>

            <div class="highlight-box">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="label">Rating</div>
                        <div class="value">{rec.get('rating', 'N/A')}</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Target Price</div>
                        <div class="value">${rec.get('target_price', 'N/A')}</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Upside</div>
                        <div class="value positive">{rec.get('upside', 'N/A')}</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Conviction</div>
                        <div class="value">{rec.get('conviction_level', 'N/A')}</div>
                    </div>
                </div>
            </div>

            <h3>Investment Rationale</h3>
            {rationale_html}

            {catalysts_html}
        </section>
        """

    def _build_debate_log(self, debate_data: Dict) -> str:
        if not debate_data:
            return """
        <section id="debate-log">
            <h2>Multi-AI Debate Log</h2>
            <p>Debate log not available.</p>
        </section>
        """

        rounds = debate_data.get("debate_rounds", [])
        if not rounds:
            return """
        <section id="debate-log">
            <h2>Multi-AI Debate Log</h2>
            <p>No debate rounds recorded.</p>
        </section>
        """

        rounds_html = ""
        for round_data in rounds[:5]:  # Show first 5 rounds
            round_num = round_data.get("round_num", "?")
            messages = round_data.get("messages", [])

            messages_html = ""
            for msg in messages[:4]:  # Limit messages per round
                role = msg.get("role", "unknown")
                ai = msg.get("ai_provider", "Unknown AI")
                content = msg.get("content", "")[:500]  # Truncate

                messages_html += f"""
                <div class="debate-message {role}">
                    <div class="message-header">
                        <span class="message-role {role}">{role.upper()}</span>
                        <span class="message-ai">{ai}</span>
                    </div>
                    <p>{content}{'...' if len(msg.get('content', '')) > 500 else ''}</p>
                </div>
                """

            disagreements = round_data.get("key_disagreements", [])
            consensus = round_data.get("consensus_points", [])

            rounds_html += f"""
            <div class="debate-round">
                <h4>Round {round_num}</h4>
                {messages_html}
            </div>
            """

        # Final thesis
        final = debate_data.get("final_thesis", {})
        final_html = ""
        if final:
            final_html = f"""
            <h3>Final Synthesis</h3>
            <div class="highlight-box">
                <p><strong>Recommendation:</strong> {final.get('recommendation', 'N/A')}</p>
                <p><strong>Investment Thesis:</strong> {final.get('investment_thesis', 'N/A')}</p>
            </div>
            """

        return f"""
        <section id="debate-log">
            <h2>Multi-AI Debate Log</h2>
            <p style="color: #8b949e; margin-bottom: 20px;">
                Showing key excerpts from the {len(rounds)}-round debate between multiple AI providers.
            </p>
            {rounds_html}
            {final_html}
        </section>
        """


def main():
    """Generate all detailed reports"""
    generator = DetailedReportGenerator()
    generated = generator.generate_all_detailed_reports()
    print(f"\nGenerated {len(generated)} detailed reports")


if __name__ == "__main__":
    main()
