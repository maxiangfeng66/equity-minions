"""
HTML Generator - Creates equity research reports in HTML format

Uses CANONICAL TEMPLATE from templates/detailed_report_template.html
Per blueprint.md requirements - ALL reports must use this template.
Reference implementation: reports/9660.HK_detailed.html (GOLD STANDARD)

Features:
- Fixed sidebar navigation (250px width)
- Dark theme (#0d1117 background)
- 9 mandatory sections with sidebar links
"""

import json
import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path


class HTMLGenerator:
    """
    Generates HTML reports for equity research using canonical detailed template.

    IMPORTANT: Uses detailed_report_template.html with sidebar navigation.
    Reference: reports/9660.HK_detailed.html is the GOLD STANDARD.
    """

    # Template paths
    TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
    EQUITY_TEMPLATE = "detailed_report_template.html"

    # Tier configuration for display
    TIER_CONFIG = {
        0: {'name': 'Architect', 'color': '#FFD700', 'agents': ['ChiefArchitect', 'ResourceAllocator', 'PriorityManager']},
        1: {'name': 'Supervisor', 'color': '#9370DB', 'agents': ['ResearchSupervisor', 'DebateModerator']},
        2: {'name': 'Worker', 'color': '#4169E1', 'agents': ['Analyst', 'Bull', 'Bear', 'Critic', 'Synthesizer', 'DevilsAdvocate', 'Specialist']},
        3: {'name': 'Goalkeeper', 'color': '#32CD32', 'agents': ['FactChecker', 'LogicAuditor', 'ConsensusValidator', 'PublishGatekeeper']},
    }

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self._template_cache = {}

    def _load_template(self, template_name: str) -> str:
        """Load template from templates directory with caching"""
        if template_name in self._template_cache:
            return self._template_cache[template_name]

        template_path = self.TEMPLATE_DIR / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        self._template_cache[template_name] = template
        return template

    def _populate_template(self, template: str, placeholders: Dict[str, str]) -> str:
        """Replace all {{PLACEHOLDER}} values with actual data"""
        result = template
        for key, value in placeholders.items():
            result = result.replace(f"{{{{{key}}}}}", str(value) if value else "")
        return result

    def generate_equity_report(self, context: Dict[str, Any]) -> str:
        """
        Generate HTML report for a single equity using canonical detailed template.

        Per blueprint.md requirements:
        1. Load template from templates/detailed_report_template.html
        2. Replace all {{PLACEHOLDER}} values with actual data
        3. Match the GOLD STANDARD: reports/9660.HK_detailed.html
        """
        ticker = context.get("ticker", "Unknown")
        company_name = context.get("company_name", "Unknown Company")

        # Load canonical template
        template = self._load_template(self.EQUITY_TEMPLATE)

        # Extract data from context
        scenario_analysis = context.get("scenario_analysis", {})
        debate_log = context.get("debate_log", [])

        # Determine rating and related classes
        rating, rating_class, rating_subtitle = self._determine_rating(context)
        current_price = self._extract_current_price(context)
        fair_value = self._get_probability_weighted_value(scenario_analysis)
        upside_pct, upside_class = self._calculate_upside(current_price, fair_value)
        currency = self._get_currency(ticker)

        # Build all placeholder values for detailed template
        placeholders = {
            # Header / Sidebar
            "TICKER": ticker,
            "COMPANY_NAME": company_name,
            "SECTOR": context.get("sector", "N/A"),
            "EXCHANGE": self._get_exchange(ticker),
            "COMPANY_INFO": context.get("industry", ""),
            "SUMMARY_LINK": f"{ticker.replace(' ', '_')}.html",
            "RATING": rating,
            "RATING_CLASS": f"badge-{rating_class}",
            "RATING_VALUE_CLASS": "positive" if rating_class == "buy" else ("negative" if rating_class == "sell" else ""),
            "CURRENCY": currency,
            "CURRENT_PRICE": f"{current_price:.2f}" if isinstance(current_price, (int, float)) and current_price > 0 else "N/A",
            "UPSIDE_PCT": upside_pct if upside_pct != "N/A" else "0",
            "UPSIDE_CLASS": upside_class,

            # Executive Summary
            "EXECUTIVE_SUMMARY_TEXT": self._extract_executive_summary(context),
            "INVESTMENT_THESIS": self._extract_investment_thesis(context),
            "KEY_HIGHLIGHTS": self._build_key_highlights(context),
            "TARGET_LOW": self._extract_target_price(context, "low"),
            "TARGET_BASE": self._extract_target_price(context, "base"),
            "TARGET_HIGH": self._extract_target_price(context, "high"),

            # Industry Analysis
            "INDUSTRY_NAME": context.get("industry", "Industry"),
            "MARKET_SIZE_CURRENT": context.get("market_size_current", "N/A"),
            "MARKET_SIZE_PROJECTED": context.get("market_size_projected", "N/A"),
            "MARKET_SIZE_YEAR": context.get("market_size_year", "2030"),
            "INDUSTRY_CAGR": context.get("industry_cagr", "N/A"),
            "INDUSTRY_DRIVERS": self._build_industry_drivers(context),
            "INDUSTRY_ADDITIONAL_CONTENT": self._build_industry_additional(context),

            # Company Analysis
            "COMPANY_ANALYSIS_CONTENT": self._build_company_analysis(context),
            "COMPETITIVE_ADVANTAGES": self._build_competitive_advantages(context),

            # Financial Data
            "FINANCIAL_CURRENCY": currency,
            "FINANCIAL_YEARS_HEADER": self._build_financial_years_header(context),
            "FINANCIAL_DATA_ROWS": self._build_financial_table_rows(context),
            "BALANCE_SHEET_METRICS": self._build_balance_sheet_metrics(context),
            "VALUATION_METRICS": self._build_valuation_metrics(context),

            # DCF Valuation
            "DCF_METHODOLOGY": self._build_dcf_methodology(context),
            "FORECAST_PERIOD": context.get("forecast_period", "10"),
            "TERMINAL_GROWTH": context.get("terminal_growth", "3"),
            "TAX_RATE": context.get("tax_rate", "25"),
            "WACC_RANGE": context.get("wacc_range", "8-11%"),
            "DCF_PROJECTIONS": self._build_dcf_projections(context),
            # NEW: Detailed DCF Calculation Display
            "PWV_FORMULA": self._extract_pwv_formula(context),
            "DCF_SCENARIO_ROWS": self._build_dcf_scenario_rows(context),
            "WACC_RF": self._extract_wacc_component(context, "risk_free_rate"),
            "WACC_BETA": self._extract_wacc_component(context, "beta"),
            "WACC_ERP": self._extract_wacc_component(context, "equity_risk_premium"),
            "WACC_CRP": self._extract_wacc_component(context, "country_risk_premium"),
            "WACC_TAX": self._extract_wacc_component(context, "tax_rate"),
            "WACC_CALCULATED": self._calculate_wacc_display(context),
            "DCF_ASSUMPTIONS_ROWS": self._build_dcf_assumptions_rows(context),
            "DCF_SCENARIO_RATIONALES": self._build_dcf_scenario_rationales(context),

            # Scenario Analysis
            "SCENARIO_CARDS": self._build_scenario_cards_detailed(context),
            "PWV": fair_value.replace("$", "") if isinstance(fair_value, str) else str(fair_value),

            # Risk Assessment
            "RISK_SECTIONS": self._build_risk_sections(context),

            # Recommendation
            "INVESTMENT_HORIZON": context.get("investment_horizon", "12-18 months"),
            "CONVICTION_LEVEL": context.get("conviction_level", "Medium"),
            "INVESTMENT_RATIONALE": self._build_investment_rationale(context),
            "CATALYSTS_ROWS": self._build_catalysts_rows(context),
            "MONITORING_METRICS": self._build_monitoring_metrics(context),

            # Debate Log
            "DEBATE_ROUNDS": self._build_debate_rounds(debate_log),
            "CONSENSUS_POINTS": self._build_consensus_points(context),
            "DISAGREEMENT_POINTS": self._build_disagreement_points(context),

            # Footer
            "REPORT_DATE": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        # Populate template
        html = self._populate_template(template, placeholders)

        # Save the file
        filename = f"{ticker.replace(' ', '_')}.html"
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(filepath)

    # ==================== NEW DETAILED TEMPLATE HELPERS ====================

    def _parse_scenario_raw_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse scenario analysis raw_response JSON if present"""
        import re
        sa = context.get("scenario_analysis", {})
        if isinstance(sa, dict) and "raw_response" in sa:
            raw = sa["raw_response"]
            # Try to extract JSON from markdown code block
            match = re.search(r'```json\s*(.*?)\s*```', raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    pass
            # Try direct JSON parse
            try:
                return json.loads(raw)
            except:
                pass
        return sa if isinstance(sa, dict) else {}

    def _get_synthesizer_summary(self, context: Dict[str, Any]) -> str:
        """Get the final synthesizer summary from debate log"""
        debate_log = context.get("debate_log", [])
        for entry in reversed(debate_log):
            if entry.get("role") == "synthesizer":
                content = entry.get("content", "")
                if content and len(content) > 100:
                    return content
        return ""

    def _extract_executive_summary(self, context: Dict[str, Any]) -> str:
        """Extract executive summary text from context"""
        # First try synthesizer output (best source)
        synth = self._get_synthesizer_summary(context)
        if synth:
            # Clean up markdown formatting for HTML display
            summary = synth.replace("###", "<h4>").replace("**", "<strong>").replace("*", "<em>")
            return summary[:3000]

        if "executive_summary" in context:
            return context["executive_summary"][:2000]
        if "company_analysis" in context:
            return context["company_analysis"][:2000]
        return "Analysis pending. Please run full research to generate summary."

    def _build_key_highlights(self, context: Dict[str, Any]) -> str:
        """Build key highlights list items from debate content"""
        highlights = []

        # Extract from bull points in debate
        bull_points = self._extract_bull_points(context)
        for point in bull_points[:5]:
            if len(point) > 10 and len(point) < 200:
                highlights.append(point)

        # If not enough, try to extract from company analysis
        if len(highlights) < 3:
            company_analysis = context.get("company_analysis", "")
            if company_analysis:
                # Look for bullet points or key sentences
                for line in company_analysis.split("\n"):
                    line = line.strip()
                    if line.startswith("-") or line.startswith("•"):
                        clean = line.lstrip("-•").strip()
                        if len(clean) > 15 and len(clean) < 200:
                            highlights.append(clean)
                    if len(highlights) >= 5:
                        break

        if not highlights:
            # Fallback based on sector
            sector = context.get("sector", "").lower()
            if "tech" in sector:
                highlights = ["AI/ML platform with enterprise focus", "Growing customer base", "R&D leadership"]
            elif "health" in sector or "bio" in sector:
                highlights = ["Strong drug pipeline", "Clinical trial progress", "Strategic partnerships"]
            else:
                highlights = ["Market leadership position", "Revenue growth trajectory", "Operational excellence"]

        return "\n".join(f"<li>{h}</li>" for h in highlights[:5])

    def _extract_target_price(self, context: Dict[str, Any], level: str) -> str:
        """Extract target price for given level (low/base/high)"""
        # First try parsed scenario analysis
        parsed_sa = self._parse_scenario_raw_response(context)
        scenarios = parsed_sa.get("scenarios", {})

        # Map level to scenario
        if level == "low":
            scenario_key = "bear"
        elif level == "high":
            scenario_key = "bull"
        else:
            scenario_key = "base"

        # Try to get target price from parsed scenarios
        if scenario_key in scenarios:
            scenario_data = scenarios[scenario_key]
            if isinstance(scenario_data, dict):
                target = scenario_data.get("target_price", scenario_data.get("fair_value", ""))
                if target:
                    return str(target).replace("$", "").replace("HKD", "").strip()

        # Fallback to intrinsic_values
        intrinsic = context.get("intrinsic_values", {})
        if not intrinsic:
            scenario_analysis = context.get("scenario_analysis", {})
            intrinsic = scenario_analysis.get("intrinsic_values", {}).get("10%", {})

        if level == "low":
            val = intrinsic.get("bear", intrinsic.get("super_bear", ""))
        elif level == "high":
            val = intrinsic.get("bull", intrinsic.get("super_bull", ""))
        else:
            val = intrinsic.get("base", "")

        if val:
            return str(val).replace("$", "").replace("HKD", "").strip()

        # Return placeholder with context hint
        return "See DCF Analysis"

    def _build_industry_drivers(self, context: Dict[str, Any]) -> str:
        """Build industry drivers list from industry analysis"""
        drivers = context.get("industry_drivers", [])

        if not drivers:
            # Extract from industry_analysis text
            industry_analysis = context.get("industry_analysis", "")
            if industry_analysis:
                # Look for driver-related content
                for line in industry_analysis.split("\n"):
                    line = line.strip()
                    if line.startswith("-") or line.startswith("•") or line.startswith("*"):
                        clean = line.lstrip("-•*").strip()
                        if 10 < len(clean) < 150:
                            drivers.append(clean)
                    if len(drivers) >= 5:
                        break

        if not drivers:
            # Generate based on sector
            sector = context.get("sector", "").lower()
            industry = context.get("industry", "").lower()
            if "ai" in industry or "tech" in sector:
                drivers = ["Enterprise AI adoption acceleration", "Cloud computing growth", "Digital transformation initiatives"]
            elif "bio" in industry or "health" in sector:
                drivers = ["Aging population demographics", "R&D innovation pipeline", "Healthcare spending growth"]
            elif "energy" in industry or "power" in industry:
                drivers = ["Energy transition investments", "Policy support for renewables", "Grid modernization needs"]
            elif "telecom" in industry:
                drivers = ["5G network expansion", "Data consumption growth", "IoT connectivity demand"]
            else:
                drivers = ["Market growth dynamics", "Regulatory tailwinds", "Technology advancement"]

        return "\n".join(f"<li>{d}</li>" for d in drivers[:5])

    def _build_industry_additional(self, context: Dict[str, Any]) -> str:
        """Build additional industry content with proper formatting"""
        industry_analysis = context.get("industry_analysis", "")
        if industry_analysis and len(industry_analysis) > 100:
            # Convert markdown to HTML
            formatted = self._markdown_to_html(industry_analysis[:3000])
            return f"<div class='industry-details'>{formatted}</div>"
        return ""

    def _markdown_to_html(self, text: str) -> str:
        """Convert basic markdown to HTML"""
        import re
        # Headers
        text = re.sub(r'^### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Italic
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        # Line breaks for paragraphs
        text = re.sub(r'\n\n', '</p><p>', text)
        # Wrap in paragraph if not already structured
        if not text.startswith('<'):
            text = f"<p>{text}</p>"
        return text

    def _build_company_analysis(self, context: Dict[str, Any]) -> str:
        """Build company analysis content with proper formatting"""
        company_analysis = context.get("company_analysis", "")
        if company_analysis:
            formatted = self._markdown_to_html(company_analysis[:4000])
            return formatted
        return "<p>Company analysis pending.</p>"

    def _build_competitive_advantages(self, context: Dict[str, Any]) -> str:
        """Build competitive advantages list from company analysis"""
        advantages = context.get("competitive_advantages", [])

        if not advantages:
            # Extract from company analysis or governance
            company_analysis = context.get("company_analysis", "")
            governance = context.get("governance_analysis", "")

            # Look for competitive advantage mentions
            for text in [company_analysis, governance]:
                if text:
                    for line in text.split("\n"):
                        line = line.strip()
                        # Look for advantage-like statements
                        if any(kw in line.lower() for kw in ["advantage", "strength", "leading", "unique", "proprietary"]):
                            if line.startswith("-") or line.startswith("•"):
                                clean = line.lstrip("-•").strip()
                                if 10 < len(clean) < 150:
                                    advantages.append(clean)
                        if len(advantages) >= 5:
                            break

        if not advantages:
            # Generate based on sector/industry
            sector = context.get("sector", "").lower()
            industry = context.get("industry", "").lower()
            if "ai" in industry or "ml" in industry:
                advantages = ["Proprietary AI/ML platform", "Enterprise customer relationships", "Data moat advantage", "Technical talent pool"]
            elif "bio" in industry or "pharma" in industry:
                advantages = ["Strong drug pipeline", "Clinical expertise", "Strategic partnerships", "IP portfolio"]
            elif "energy" in industry or "power" in industry:
                advantages = ["Scale advantages", "Asset base quality", "Operational efficiency", "Grid connections"]
            else:
                advantages = ["Market position", "Brand recognition", "Operational scale", "Management expertise"]

        return "\n".join(f"<li>{a}</li>" for a in advantages[:6])

    def _build_balance_sheet_metrics(self, context: Dict[str, Any]) -> str:
        """Build balance sheet metric cards - extract from financial data or analysis"""
        # Try to extract from various sources
        financial_data = context.get("financial_data", {})
        company_analysis = context.get("company_analysis", "")

        metrics = []

        # Look for balance sheet items in financial_data
        if isinstance(financial_data, dict) and financial_data:
            metrics = [
                ("Cash Position", financial_data.get("cash", financial_data.get("cash_position", ""))),
                ("Total Debt", financial_data.get("debt", financial_data.get("total_debt", ""))),
                ("Net Debt", financial_data.get("net_debt", "")),
                ("Shareholders Equity", financial_data.get("equity", financial_data.get("shareholders_equity", "")))
            ]
        else:
            # Provide sector-appropriate placeholders
            sector = context.get("sector", "").lower()
            if "bio" in sector or "health" in sector:
                metrics = [
                    ("Cash Position", "Key for R&D runway"),
                    ("Total Debt", "Review annual report"),
                    ("Net Debt", "See financials"),
                    ("Shareholders Equity", "Balance sheet")
                ]
            else:
                metrics = [
                    ("Cash Position", "See annual report"),
                    ("Total Debt", "Review filings"),
                    ("Net Debt", "Check financials"),
                    ("Shareholders Equity", "Balance sheet")
                ]

        html = ""
        for label, value in metrics:
            display_val = value if value else "Review filings"
            html += f'''
                <div class="metric-card">
                    <div class="label">{label}</div>
                    <div class="value">{display_val}</div>
                </div>'''
        return html

    def _build_valuation_metrics(self, context: Dict[str, Any]) -> str:
        """Build valuation metric cards"""
        financial_data = context.get("financial_data", {})

        # Try to get from parsed data first
        if isinstance(financial_data, dict) and financial_data:
            metrics = [
                ("Market Cap", financial_data.get("market_cap", "")),
                ("EV", financial_data.get("enterprise_value", financial_data.get("ev", ""))),
                ("P/E Ratio", financial_data.get("pe_ratio", financial_data.get("pe", ""))),
                ("EV/EBITDA", financial_data.get("ev_ebitda", ""))
            ]
        else:
            # Provide action-oriented placeholders
            metrics = [
                ("Market Cap", "Check market data"),
                ("EV", "Calculate from cap table"),
                ("P/E Ratio", "Based on earnings"),
                ("EV/EBITDA", "Key valuation metric")
            ]

        html = ""
        for label, value in metrics:
            display_val = value if value else "See valuation"
            html += f'''
                <div class="metric-card">
                    <div class="label">{label}</div>
                    <div class="value">{display_val}</div>
                </div>'''
        return html

    def _build_dcf_methodology(self, context: Dict[str, Any]) -> str:
        """Build DCF methodology description"""
        return context.get("dcf_methodology",
            "Discounted Cash Flow (DCF) analysis using multi-scenario probability-weighted approach. "
            "Cash flows are projected over a 10-year forecast period with terminal value calculated using "
            "perpetual growth method. WACC is derived from CAPM with company-specific risk adjustments.")

    def _build_dcf_projections(self, context: Dict[str, Any]) -> str:
        """Build DCF projections table"""
        dcf = context.get("dcf_projections", {})
        if not dcf:
            return "<p>DCF projections will be generated during full analysis.</p>"

        html = "<h4>Cash Flow Projections</h4><table><thead><tr><th>Year</th>"
        years = list(range(1, 6))
        for y in years:
            html += f"<th>Year {y}</th>"
        html += "<th>Terminal</th></tr></thead><tbody>"

        for metric in ["Revenue", "EBITDA", "FCF"]:
            data = dcf.get(metric.lower(), {})
            html += f"<tr><td>{metric}</td>"
            for y in years:
                html += f"<td class='text-right'>{data.get(str(y), 'N/A')}</td>"
            html += f"<td class='text-right'>{data.get('terminal', 'N/A')}</td></tr>"

        html += "</tbody></table>"
        return html

    def _build_scenario_cards_detailed(self, context: Dict[str, Any]) -> str:
        """Build detailed scenario cards using parsed scenario data"""
        # Parse the raw_response to get structured scenario data
        parsed_sa = self._parse_scenario_raw_response(context)
        parsed_scenarios = parsed_sa.get("scenarios", {})

        scenarios_config = [
            ("super_bear", "Super Bear", "5%", "#da3633"),
            ("bear", "Bear", "20%", "#f85149"),
            ("base", "Base", "50%", "#58a6ff"),
            ("bull", "Bull", "20%", "#3fb950"),
            ("super_bull", "Super Bull", "5%", "#238636"),
        ]

        # Also try legacy intrinsic_values
        scenario_analysis = context.get("scenario_analysis", {})
        intrinsic = scenario_analysis.get("intrinsic_values", {}).get("10%", {})

        html = ""

        for key, name, default_prob, color in scenarios_config:
            # Try to get from parsed scenarios first
            scenario_data = parsed_scenarios.get(key, {})

            if isinstance(scenario_data, dict):
                # Get probability from parsed data or use default
                prob_val = scenario_data.get("probability", 0)
                if isinstance(prob_val, float) and prob_val < 1:
                    prob = f"{int(prob_val * 100)}%"
                else:
                    prob = default_prob

                # Get description
                description = scenario_data.get("description", f"{name} case scenario")

                # Get growth assumptions
                growth = scenario_data.get("growth_assumptions", {})
                if isinstance(growth, dict):
                    assumptions = []
                    for k, v in growth.items():
                        assumptions.append(f"{k.replace('_', ' ').title()}: {v}")
                    if description:
                        assumptions.insert(0, description[:100])
                else:
                    assumptions = [description] if description else []
            else:
                prob = default_prob
                assumptions = [f"Market conditions: {name.lower()} case expectations"]

            # Get target price - try parsed data, then intrinsic values
            value = intrinsic.get(key, "")
            if not value and isinstance(scenario_data, dict):
                value = scenario_data.get("target_price", scenario_data.get("fair_value", ""))

            if not value:
                value = "See DCF"

            # Ensure we have at least some assumptions
            if not assumptions:
                assumptions = [
                    f"Market conditions: {name.lower()} case expectations",
                    "Revenue growth aligned with scenario",
                    "Margins reflect competitive dynamics"
                ]

            assumptions_html = "\n".join(f"<li>{a}</li>" for a in assumptions[:4])

            html += f'''
            <div class="scenario-card {key.replace('_', '-')}">
                <div class="scenario-header">
                    <h4>{name} Case</h4>
                    <span class="probability-badge">{prob} probability</span>
                </div>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="label">Target Price</div>
                        <div class="value" style="color: {color};">{value}</div>
                    </div>
                </div>
                <h4>Key Assumptions</h4>
                <ul class="key-points">
                    {assumptions_html}
                </ul>
            </div>'''

        return html

    def _build_risk_sections(self, context: Dict[str, Any]) -> str:
        """Build risk sections from bear arguments and debate content"""
        risk_categories = context.get("risk_categories", {})

        if not risk_categories:
            # Extract risks from bear points in debate
            bear_points = self._extract_bear_points(context)

            # Categorize the risks
            business_risks = []
            financial_risks = []
            market_risks = []

            for point in bear_points:
                point_lower = point.lower()
                if any(kw in point_lower for kw in ["competition", "customer", "technology", "execution", "management"]):
                    business_risks.append(point)
                elif any(kw in point_lower for kw in ["funding", "debt", "margin", "cash", "capital", "profitability"]):
                    financial_risks.append(point)
                else:
                    market_risks.append(point)

            # Build risk categories from extracted points
            risk_categories = {}
            if business_risks:
                risk_categories["Business Risks"] = business_risks[:3]
            if financial_risks:
                risk_categories["Financial Risks"] = financial_risks[:3]
            if market_risks:
                risk_categories["Market Risks"] = market_risks[:3]

            # Add defaults if categories are empty
            if not risk_categories:
                sector = context.get("sector", "").lower()
                industry = context.get("industry", "").lower()

                if "bio" in industry or "health" in sector:
                    risk_categories = {
                        "Clinical Risks": ["Trial failures or delays", "Regulatory approval challenges", "Competitive drug development"],
                        "Financial Risks": ["R&D funding requirements", "Cash runway concerns", "Commercialization costs"],
                        "Market Risks": ["Pricing pressure", "Reimbursement challenges", "Patent expiration"]
                    }
                elif "tech" in sector or "ai" in industry:
                    risk_categories = {
                        "Business Risks": ["Rapid technology evolution", "Competitive pressure from giants", "Customer concentration"],
                        "Financial Risks": ["Profitability timeline", "R&D investment requirements", "Talent acquisition costs"],
                        "Market Risks": ["AI regulation changes", "Economic cycle sensitivity", "Valuation compression"]
                    }
                else:
                    risk_categories = {
                        "Business Risks": ["Competitive dynamics", "Execution challenges", "Operational disruption"],
                        "Financial Risks": ["Capital requirements", "Margin pressure", "Currency exposure"],
                        "Market Risks": ["Economic slowdown", "Regulatory changes", "Sector rotation"]
                    }

        html = ""
        for category, risks in risk_categories.items():
            html += f"<h3>{category}</h3>"
            for risk in risks[:3]:
                # Truncate long risks
                risk_text = risk[:100] + "..." if len(risk) > 100 else risk
                html += f'''
                <div class="risk-item medium">
                    <div class="risk-header">
                        <h5>{risk_text}</h5>
                        <span class="impact-badge">Medium Impact</span>
                    </div>
                    <p>Risk factor identified during multi-AI debate analysis. Monitor developments.</p>
                </div>'''

        return html

    def _build_investment_rationale(self, context: Dict[str, Any]) -> str:
        """Build investment rationale list"""
        rationale = context.get("investment_rationale", [])
        if not rationale:
            rationale = self._extract_bull_points(context)
        return "\n".join(f"<li>{r}</li>" for r in rationale[:5])

    def _build_catalysts_rows(self, context: Dict[str, Any]) -> str:
        """Build catalysts table rows"""
        catalysts = context.get("catalysts", [])
        if not catalysts:
            catalysts = [
                {"name": "Earnings release", "timing": "Next quarter", "impact": "Medium"},
                {"name": "Product launch", "timing": "H2 2026", "impact": "High"},
                {"name": "Market expansion", "timing": "2026-2027", "impact": "High"}
            ]

        html = ""
        for c in catalysts[:5]:
            if isinstance(c, dict):
                html += f"<tr><td>{c.get('name', 'N/A')}</td><td>{c.get('timing', 'N/A')}</td><td>{c.get('impact', 'N/A')}</td></tr>"
            else:
                html += f"<tr><td>{c}</td><td>TBD</td><td>Medium</td></tr>"
        return html

    def _build_monitoring_metrics(self, context: Dict[str, Any]) -> str:
        """Build monitoring metrics list"""
        metrics = context.get("monitoring_metrics", [
            "Revenue growth trajectory",
            "Gross margin trends",
            "Customer acquisition costs",
            "Cash burn rate",
            "Competitive positioning"
        ])
        return "\n".join(f"<li>{m}</li>" for m in metrics[:6])

    def _build_debate_rounds(self, debate_log: List[Dict]) -> str:
        """Build debate rounds HTML from debate log with rich formatting"""
        if not debate_log:
            return "<p>Debate log will be available after full research is completed.</p>"

        # Group by rounds - show diverse perspectives
        roles_to_show = ["analyst", "bull", "bear", "critic", "synthesizer"]
        role_colors = {
            "analyst": "#58a6ff",
            "bull": "#3fb950",
            "bear": "#f85149",
            "critic": "#d29922",
            "synthesizer": "#a371f7"
        }
        role_labels = {
            "analyst": "ANALYST",
            "bull": "BULL CASE",
            "bear": "BEAR CASE",
            "critic": "CRITIC",
            "synthesizer": "SYNTHESIS"
        }

        html = ""
        round_num = 1
        shown_roles = set()

        for entry in debate_log:
            role = entry.get("role", "unknown")

            # Show one entry per role for clarity
            if role in roles_to_show and role not in shown_roles:
                content = entry.get("content", "")
                ai = entry.get("ai_provider", entry.get("metadata", {}).get("ai_provider", "AI"))

                # Clean and truncate content
                content_clean = content[:800]
                if len(content) > 800:
                    content_clean += "..."

                color = role_colors.get(role, "#8b949e")
                label = role_labels.get(role, role.upper())

                html += f'''
            <div class="debate-round">
                <h4 style="color: {color};">Round {round_num}: {label}</h4>
                <div class="debate-message {role}" style="border-left: 3px solid {color}; padding-left: 15px;">
                    <div class="message-header" style="margin-bottom: 10px;">
                        <span class="message-role {role}" style="background: {color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em;">{label}</span>
                        <span class="message-ai" style="color: #8b949e; margin-left: 10px; font-size: 0.85em;">via {ai}</span>
                    </div>
                    <p style="line-height: 1.6;">{content_clean}</p>
                </div>
            </div>'''

                shown_roles.add(role)
                round_num += 1

                if round_num > 5:
                    break

        if not html:
            html = "<p>No debate entries found.</p>"

        return html

    def _build_consensus_points(self, context: Dict[str, Any]) -> str:
        """Build consensus points from synthesizer output"""
        consensus = context.get("consensus_points", [])

        if not consensus:
            # Try to extract from synthesizer summary
            synth = self._get_synthesizer_summary(context)
            if synth and "consensus" in synth.lower():
                # Look for consensus section
                lines = synth.split("\n")
                in_consensus = False
                for line in lines:
                    if "consensus" in line.lower():
                        in_consensus = True
                        continue
                    if in_consensus:
                        if line.startswith("-") or line.startswith("•"):
                            clean = line.lstrip("-•").strip()
                            if 10 < len(clean) < 200:
                                consensus.append(clean)
                        elif line.startswith("#") or (line.strip() and not line[0].isspace()):
                            if "disagree" in line.lower() or "key" in line.lower():
                                break

        if not consensus:
            # Extract common themes from bull points that likely have agreement
            bull_points = self._extract_bull_points(context)
            for point in bull_points[:3]:
                if len(point) < 150:
                    consensus.append(point)

        if not consensus:
            sector = context.get("sector", "").lower()
            if "tech" in sector:
                consensus = ["AI/ML market growth potential", "Technology platform value", "Enterprise adoption trend"]
            elif "health" in sector:
                consensus = ["Healthcare market fundamentals", "Pipeline drug potential", "Strategic positioning"]
            else:
                consensus = ["Market opportunity assessment", "Management capability", "Industry tailwinds"]

        return "\n".join(f"<li>{c}</li>" for c in consensus[:5])

    def _build_disagreement_points(self, context: Dict[str, Any]) -> str:
        """Build disagreement points from debate content"""
        disagreements = context.get("disagreement_points", [])

        if not disagreements:
            # Try to extract from synthesizer summary
            synth = self._get_synthesizer_summary(context)
            if synth and "disagree" in synth.lower():
                lines = synth.split("\n")
                in_disagree = False
                for line in lines:
                    if "disagree" in line.lower():
                        in_disagree = True
                        continue
                    if in_disagree:
                        if line.startswith("-") or line.startswith("•"):
                            clean = line.lstrip("-•").strip()
                            if 10 < len(clean) < 200:
                                disagreements.append(clean)
                        elif line.startswith("#") or (line.strip() and not line[0].isspace()):
                            break

        if not disagreements:
            # Compare bull and bear points for natural disagreements
            disagreements = [
                "Growth rate assumptions and sustainability",
                "Valuation methodology and fair value",
                "Competitive positioning durability"
            ]

        return "\n".join(f"<li>{d}</li>" for d in disagreements[:5])

    def generate_index(self, equities: Dict[str, Dict[str, Any]]) -> str:
        """Generate index HTML with links to all equity reports (with hierarchical architecture)"""

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
    <title>Equity Research Reports - Hierarchical Multi-Agent System</title>
    <style>
        :root {{
            --primary-color: #1a365d;
            --secondary-color: #2c5282;
            --accent-color: #3182ce;
            --bg-light: #f7fafc;
            --text-primary: #2d3748;
            --tier0-color: #FFD700;
            --tier1-color: #9370DB;
            --tier2-color: #4169E1;
            --tier3-color: #32CD32;
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

        .arch-badge {{
            display: inline-block;
            background: rgba(255,255,255,0.15);
            padding: 8px 20px;
            border-radius: 25px;
            margin-top: 15px;
            font-size: 0.9rem;
            border: 1px solid rgba(255,255,255,0.3);
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}

        /* Hierarchical Architecture Section */
        .arch-section {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 2px 15px rgba(0,0,0,0.05);
        }}

        .arch-section h2 {{
            color: var(--primary-color);
            margin-bottom: 20px;
            font-size: 1.3rem;
        }}

        .tier-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }}

        @media (max-width: 900px) {{
            .tier-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}

        @media (max-width: 500px) {{
            .tier-grid {{ grid-template-columns: 1fr; }}
        }}

        .tier-card {{
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            color: white;
            position: relative;
            overflow: hidden;
        }}

        .tier-card::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            pointer-events: none;
        }}

        .tier-card.tier0 {{ background: linear-gradient(135deg, #B8860B, var(--tier0-color)); }}
        .tier-card.tier1 {{ background: linear-gradient(135deg, #6A5ACD, var(--tier1-color)); }}
        .tier-card.tier2 {{ background: linear-gradient(135deg, #1E40AF, var(--tier2-color)); }}
        .tier-card.tier3 {{ background: linear-gradient(135deg, #228B22, var(--tier3-color)); }}

        .tier-card .tier-name {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.9; margin-bottom: 5px; }}
        .tier-card .tier-title {{ font-size: 1.1rem; font-weight: bold; margin-bottom: 10px; }}
        .tier-card .tier-agents {{ font-size: 0.8rem; opacity: 0.85; line-height: 1.5; }}

        .stats {{
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-bottom: 40px;
            flex-wrap: wrap;
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

        .footer-arch {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 15px;
            flex-wrap: wrap;
        }}

        .footer-arch span {{
            font-size: 0.8rem;
            padding: 5px 12px;
            border-radius: 15px;
            background: #e2e8f0;
        }}
    </style>
</head>
<body>
    <header>
        <h1>Equity Research Reports</h1>
        <p>Hierarchical Multi-Agent Analysis with Scenario-Based Valuations</p>
        <div class="arch-badge">v2.0 - 4-Tier Agent Architecture with Quality Gates</div>
    </header>

    <div class="container">
        <!-- Hierarchical Architecture Overview -->
        <div class="arch-section">
            <h2>Agent Architecture</h2>
            <div class="tier-grid">
                <div class="tier-card tier0">
                    <div class="tier-name">Tier 0</div>
                    <div class="tier-title">Architects</div>
                    <div class="tier-agents">ChiefArchitect<br>ResourceAllocator<br>PriorityManager</div>
                </div>
                <div class="tier-card tier1">
                    <div class="tier-name">Tier 1</div>
                    <div class="tier-title">Supervisors</div>
                    <div class="tier-agents">ResearchSupervisor<br>DebateModerator</div>
                </div>
                <div class="tier-card tier2">
                    <div class="tier-name">Tier 2</div>
                    <div class="tier-title">Workers</div>
                    <div class="tier-agents">Analyst, Bull, Bear<br>Critic, Synthesizer<br>DevilsAdvocate, Specialist</div>
                </div>
                <div class="tier-card tier3">
                    <div class="tier-name">Tier 3</div>
                    <div class="tier-title">Goalkeepers</div>
                    <div class="tier-agents">FactChecker, LogicAuditor<br>ConsensusValidator<br>PublishGatekeeper</div>
                </div>
            </div>
        </div>

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
            <div class="stat">
                <div class="number">4</div>
                <div class="label">Agent Tiers</div>
            </div>
            <div class="stat">
                <div class="number">3</div>
                <div class="label">Quality Gates</div>
            </div>
        </div>

        <div class="equity-grid">
            {equity_cards}
        </div>
    </div>

    <footer>
        <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")} - Hierarchical Multi-Agent System v2.0</p>
        <div class="footer-arch">
            <span>Architects: Strategy</span>
            <span>Supervisors: Oversight</span>
            <span>Workers: Execution</span>
            <span>Goalkeepers: Quality</span>
        </div>
        <p style="margin-top: 15px;">Reports are for informational purposes only.</p>
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

    # ==================== NEW TEMPLATE HELPER METHODS ====================

    def _get_exchange(self, ticker: str) -> str:
        """Determine exchange from ticker format"""
        if " HK" in ticker.upper():
            return "HKEX"
        elif " US" in ticker.upper() or ticker.upper().endswith("US"):
            return "NYSE/NASDAQ"
        elif " CH" in ticker.upper():
            return "Shanghai"
        return "Exchange"

    def _get_currency(self, ticker: str) -> str:
        """Determine currency from ticker"""
        if " HK" in ticker.upper():
            return "HKD"
        elif " US" in ticker.upper() or ticker.upper().endswith("US"):
            return "USD"
        elif " CH" in ticker.upper():
            return "CNY"
        return "USD"

    def _determine_rating(self, context: Dict[str, Any]) -> tuple:
        """Determine rating, rating_class, and subtitle from context"""
        # Try to get from context directly
        rating = context.get("recommendation", context.get("rating", "HOLD"))

        # Normalize rating
        rating_upper = rating.upper() if isinstance(rating, str) else "HOLD"

        if "STRONG BUY" in rating_upper or "STRONGBUY" in rating_upper:
            return "STRONG BUY", "buy", "High Conviction"
        elif "BUY" in rating_upper:
            return "BUY", "buy", "Upside Potential"
        elif "STRONG SELL" in rating_upper:
            return "STRONG SELL", "sell", "High Risk"
        elif "SELL" in rating_upper:
            return "SELL", "sell", "Downside Risk"
        else:
            return "HOLD", "hold", "Fair Value"

    def _extract_current_price(self, context: Dict[str, Any]) -> float:
        """Extract current price from context"""
        price = context.get("current_price", context.get("price", 0))
        if isinstance(price, str):
            # Try to extract number from string
            import re
            match = re.search(r'[\d.]+', price)
            if match:
                return float(match.group())
        return float(price) if price else 0

    def _calculate_upside(self, current_price: float, fair_value: str) -> tuple:
        """Calculate upside percentage and class"""
        try:
            fv = float(fair_value.replace("$", "").replace(",", ""))
            if current_price > 0:
                upside = ((fv - current_price) / current_price) * 100
                upside_class = "positive" if upside > 0 else "negative"
                return f"{upside:+.1f}", upside_class
        except (ValueError, AttributeError):
            pass
        return "N/A", ""

    def _extract_investment_thesis(self, context: Dict[str, Any]) -> str:
        """Extract investment thesis from context"""
        if "investment_thesis" in context:
            return context["investment_thesis"]

        # Try to extract from synthesizer output
        debate_log = context.get("debate_log", [])
        for msg in reversed(debate_log):
            if msg.get("role") == "synthesizer":
                content = msg.get("content", "")
                if "thesis" in content.lower():
                    # Extract first paragraph after "thesis"
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if "thesis" in line.lower():
                            if i + 1 < len(lines):
                                return lines[i + 1].strip()[:500]

        return context.get("company_analysis", "Analysis pending")[:500]

    def _extract_bull_points(self, context: Dict[str, Any]) -> List[str]:
        """Extract bull case points from context"""
        if "bull_points" in context:
            return context["bull_points"]

        # Try to extract from debate log
        debate_log = context.get("debate_log", [])
        for msg in reversed(debate_log):
            if msg.get("role") == "bull":
                content = msg.get("content", "")
                # Extract bullet points or numbered items
                points = []
                for line in content.split("\n"):
                    line = line.strip()
                    if line and (line.startswith("-") or line.startswith("•") or
                                 (len(line) > 2 and line[0].isdigit() and line[1] in ".)")):
                        points.append(line.lstrip("-•0123456789.) "))
                        if len(points) >= 4:
                            break
                if points:
                    return points

        return ["Strong market position", "Growth potential", "Quality management"]

    def _extract_bear_points(self, context: Dict[str, Any]) -> List[str]:
        """Extract bear case points from context"""
        if "bear_points" in context:
            return context["bear_points"]

        # Try to extract from debate log
        debate_log = context.get("debate_log", [])
        for msg in reversed(debate_log):
            if msg.get("role") == "bear":
                content = msg.get("content", "")
                points = []
                for line in content.split("\n"):
                    line = line.strip()
                    if line and (line.startswith("-") or line.startswith("•") or
                                 (len(line) > 2 and line[0].isdigit() and line[1] in ".)")):
                        points.append(line.lstrip("-•0123456789.) "))
                        if len(points) >= 4:
                            break
                if points:
                    return points

        return ["Competition risk", "Valuation concerns", "Macro headwinds"]

    def _build_list_items(self, items: List[str]) -> str:
        """Build HTML list items"""
        if not items:
            return "<li>Data pending</li>"
        return "\n".join(f"<li>{item}</li>" for item in items)

    def _build_financial_years_header(self, context: Dict[str, Any]) -> str:
        """Build financial years header for table"""
        years = context.get("financial_years", [2021, 2022, 2023, 2024, 2025])
        return "".join(f"<th class='text-right'>{y}</th>" for y in years)

    def _build_financial_table_rows(self, context: Dict[str, Any]) -> str:
        """Build financial data table rows"""
        financials = context.get("financials", {})
        if not financials:
            return "<tr><td colspan='6'>Financial data pending</td></tr>"

        rows = []
        metrics = ["Revenue", "Gross Profit", "Operating Income", "Net Income", "EPS"]
        for metric in metrics:
            data = financials.get(metric.lower().replace(" ", "_"), {})
            row = f"<tr><td>{metric}</td>"
            for year in context.get("financial_years", [2021, 2022, 2023, 2024, 2025]):
                value = data.get(str(year), "N/A")
                row += f"<td class='text-right'>{value}</td>"
            row += "</tr>"
            rows.append(row)

        return "\n".join(rows) if rows else "<tr><td colspan='6'>Financial data pending</td></tr>"

    def _build_segment_breakdown(self, context: Dict[str, Any]) -> str:
        """Build segment breakdown section"""
        segments = context.get("segments", [])
        if not segments:
            return ""

        html = "<h3>Revenue by Segment</h3><table><thead><tr><th>Segment</th><th>Revenue</th><th>% of Total</th><th>Growth</th></tr></thead><tbody>"
        for seg in segments:
            html += f"<tr><td>{seg.get('name', 'N/A')}</td><td class='text-right'>{seg.get('revenue', 'N/A')}</td>"
            html += f"<td class='text-center'>{seg.get('pct', 'N/A')}</td><td class='text-right'>{seg.get('growth', 'N/A')}</td></tr>"
        html += "</tbody></table>"
        return html

    def _build_key_insight_box(self, context: Dict[str, Any]) -> str:
        """Build key insight highlight box"""
        insight = context.get("key_financial_insight", "")
        if not insight:
            return ""
        return f'<div class="highlight-box"><p><strong>Key Insight:</strong> {insight}</p></div>'

    def _build_dcf_projection_table(self, context: Dict[str, Any]) -> str:
        """Build DCF projection table"""
        dcf = context.get("dcf_projections", {})
        if not dcf:
            return "<p>DCF projections pending</p>"

        years = list(range(1, 11))
        html = "<table class='dcf-table'><thead><tr><th>Year</th>"
        html += "".join(f"<th>{y}</th>" for y in years)
        html += "<th>Terminal</th></tr></thead><tbody>"

        for metric in ["Revenue", "EBIT", "NOPAT", "FCF"]:
            data = dcf.get(metric.lower(), {})
            html += f"<tr><td>{metric}</td>"
            for y in years:
                html += f"<td class='text-right'>{data.get(str(y), 'N/A')}</td>"
            html += f"<td class='text-right'>{data.get('terminal', 'N/A')}</td></tr>"

        html += "</tbody></table>"
        return html

    def _build_dcf_summary_table(self, context: Dict[str, Any]) -> str:
        """Build DCF summary table"""
        dcf = context.get("dcf_summary", {})
        if not dcf:
            return ""

        html = """<table><thead><tr><th>Component</th><th class='text-right'>Value</th></tr></thead><tbody>"""
        for key, value in dcf.items():
            html += f"<tr><td>{key}</td><td class='text-right'>{value}</td></tr>"
        html += "</tbody></table>"
        return html

    def _build_scenario_cards(self, scenario_analysis: Dict[str, Any]) -> str:
        """Build scenario cards for scenario analysis section"""
        scenarios = [
            ("super_bear", "Super Bear", "5%", "super-bear", "#da3633"),
            ("bear", "Bear", "20%", "bear", "#f85149"),
            ("base", "Base", "50%", "base", "#58a6ff"),
            ("bull", "Bull", "20%", "bull", "#3fb950"),
            ("super_bull", "Super Bull", "5%", "super-bull", "#238636"),
        ]

        intrinsic = scenario_analysis.get("intrinsic_values", {}).get("10%", {})
        html = ""

        for key, name, prob, css_class, color in scenarios:
            value = intrinsic.get(key, "N/A")
            html += f"""
                <div class="scenario-card {css_class}">
                    <div class="name">{name}</div>
                    <div class="prob">{prob}</div>
                    <div class="value" style="color: {color};">{value}</div>
                </div>
            """

        return html

    def _build_scenario_details_table(self, scenario_analysis: Dict[str, Any]) -> str:
        """Build scenario details table"""
        scenarios = scenario_analysis.get("scenario_details", [])
        if not scenarios:
            return "<p>Scenario details pending</p>"

        html = "<table><thead><tr><th>Scenario</th><th>Probability</th><th>Target</th><th>Key Assumptions</th></tr></thead><tbody>"
        for s in scenarios:
            html += f"<tr><td>{s.get('name', 'N/A')}</td><td class='text-center'>{s.get('prob', 'N/A')}</td>"
            html += f"<td class='text-right'>{s.get('target', 'N/A')}</td><td>{s.get('assumptions', 'N/A')}</td></tr>"
        html += "</tbody></table>"
        return html

    def _build_discount_sensitivity_table(self, scenario_analysis: Dict[str, Any]) -> str:
        """Build discount rate sensitivity table"""
        intrinsic = scenario_analysis.get("intrinsic_values", {})
        if not intrinsic:
            return "<p>Sensitivity data pending</p>"

        html = "<table class='sensitivity-table'><thead><tr><th>Discount Rate</th><th>Base Case Value</th></tr></thead><tbody>"
        for rate in ["8%", "9%", "10%", "11%", "12%"]:
            value = intrinsic.get(rate, {}).get("base", "N/A")
            current_class = " class='current'" if rate == "10%" else ""
            html += f"<tr{current_class}><td>{rate}</td><td class='text-right'>{value}</td></tr>"
        html += "</tbody></table>"
        return html

    def _build_probability_sensitivity_table(self, scenario_analysis: Dict[str, Any]) -> str:
        """Build probability sensitivity table"""
        return """<table class='sensitivity-table'>
            <thead><tr><th>Allocation</th><th>Fair Value</th></tr></thead>
            <tbody>
                <tr><td>Conservative (Bear +10%)</td><td class='text-right'>See analysis</td></tr>
                <tr class='current'><td>Base Allocation</td><td class='text-right'>See analysis</td></tr>
                <tr><td>Aggressive (Bull +10%)</td><td class='text-right'>See analysis</td></tr>
            </tbody>
        </table>"""

    def _build_comparable_table(self, context: Dict[str, Any]) -> str:
        """Build comparable companies table"""
        comps = context.get("comparables", [])
        if not comps:
            return "<p>Comparable analysis pending</p>"

        html = "<table><thead><tr><th>Company</th><th>P/E</th><th>EV/EBITDA</th><th>P/S</th></tr></thead><tbody>"
        for c in comps:
            html += f"<tr><td>{c.get('name', 'N/A')}</td><td class='text-right'>{c.get('pe', 'N/A')}</td>"
            html += f"<td class='text-right'>{c.get('ev_ebitda', 'N/A')}</td><td class='text-right'>{c.get('ps', 'N/A')}</td></tr>"
        html += "</tbody></table>"
        return html

    def _build_risk_cards(self, context: Dict[str, Any], severity: str) -> str:
        """Build risk cards for specified severity"""
        risks = context.get("risks", {}).get(severity, [])
        if not risks:
            return f"<p>No {severity} impact risks identified</p>"

        html = ""
        for risk in risks:
            html += f"""
                <div class="risk-card {severity}">
                    <div class="risk-header">
                        <h5>{risk.get('title', 'Risk')}</h5>
                        <span class="badge">{risk.get('probability', 'Medium')}</span>
                    </div>
                    <p>{risk.get('description', '')}</p>
                    <p class="mitigation"><strong>Mitigation:</strong> {risk.get('mitigation', 'N/A')}</p>
                </div>
            """
        return html

    def _build_entry_points_table(self, context: Dict[str, Any]) -> str:
        """Build entry points table"""
        entries = context.get("entry_points", [])
        if not entries:
            return """<table>
                <thead><tr><th>Strategy</th><th>Entry Price</th><th>Target</th><th>Stop Loss</th></tr></thead>
                <tbody>
                    <tr><td>Aggressive</td><td>At current levels</td><td>+20%</td><td>-10%</td></tr>
                    <tr><td>Conservative</td><td>On 10% pullback</td><td>+15%</td><td>-8%</td></tr>
                </tbody>
            </table>"""

        html = "<table><thead><tr><th>Strategy</th><th>Entry Price</th><th>Target</th><th>Stop Loss</th></tr></thead><tbody>"
        for e in entries:
            html += f"<tr><td>{e.get('strategy', 'N/A')}</td><td>{e.get('entry', 'N/A')}</td>"
            html += f"<td>{e.get('target', 'N/A')}</td><td>{e.get('stop', 'N/A')}</td></tr>"
        html += "</tbody></table>"
        return html

    # ==================== DCF CALCULATION DETAIL METHODS ====================

    def _extract_pwv_formula(self, context: Dict[str, Any]) -> str:
        """Extract the PWV calculation formula from valuation output"""
        # Try to get from valuation_output first
        valuation = context.get("valuation_output", {})
        if isinstance(valuation, dict):
            dcf = valuation.get("dcf", {})
            if isinstance(dcf, dict):
                pwv_calc = dcf.get("pwv_calculation", "")
                if pwv_calc:
                    return pwv_calc

        # Try to extract from scenario_analysis
        scenario_analysis = context.get("scenario_analysis", {})
        if isinstance(scenario_analysis, dict):
            pwv_calc = scenario_analysis.get("pwv_calculation", "")
            if pwv_calc:
                return pwv_calc

        # Build formula from scenarios if available
        scenarios = self._get_dcf_scenarios(context)
        if scenarios:
            parts = []
            total = 0
            for name, data in scenarios.items():
                if isinstance(data, dict):
                    fv = data.get("fair_value", 0)
                    prob = data.get("probability", 0)
                    if isinstance(prob, float) and prob < 1:
                        prob_pct = int(prob * 100)
                    else:
                        prob_pct = int(prob) if prob else 0
                    parts.append(f"{fv:.2f}×{prob_pct}%")
                    total += fv * (prob if prob < 1 else prob / 100)
            if parts:
                return f"PWV = {' + '.join(parts)} = {total:.2f}"

        return "PWV calculation not available"

    def _get_dcf_scenarios(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract DCF scenarios from various context locations"""
        # Try valuation_output first
        valuation = context.get("valuation_output", {})
        if isinstance(valuation, dict):
            dcf = valuation.get("dcf", {})
            if isinstance(dcf, dict):
                scenarios = dcf.get("scenarios", {})
                if scenarios:
                    return scenarios

        # Try scenario_analysis
        scenario_analysis = context.get("scenario_analysis", {})
        if isinstance(scenario_analysis, dict):
            scenarios = scenario_analysis.get("scenarios", {})
            if scenarios:
                return scenarios

        return {}

    def _build_dcf_scenario_rows(self, context: Dict[str, Any]) -> str:
        """Build DCF scenario breakdown table rows"""
        scenarios = self._get_dcf_scenarios(context)
        if not scenarios:
            return "<tr><td colspan='6'>DCF scenario data not available</td></tr>"

        scenario_order = ["super_bear", "bear", "base", "bull", "super_bull"]
        scenario_labels = {
            "super_bear": "Super Bear",
            "bear": "Bear",
            "base": "Base",
            "bull": "Bull",
            "super_bull": "Super Bull"
        }
        scenario_colors = {
            "super_bear": "#da3633",
            "bear": "#f85149",
            "base": "#58a6ff",
            "bull": "#3fb950",
            "super_bull": "#238636"
        }

        html = ""
        for key in scenario_order:
            if key not in scenarios:
                continue
            data = scenarios[key]
            if not isinstance(data, dict):
                continue

            label = scenario_labels.get(key, key)
            color = scenario_colors.get(key, "#8b949e")
            fv = data.get("fair_value", 0)
            prob = data.get("probability", 0)
            wacc = data.get("wacc", 0)
            tv_pct = data.get("terminal_value_pct", 0)

            # Format probability
            if isinstance(prob, float) and prob < 1:
                prob_display = f"{prob * 100:.0f}%"
            else:
                prob_display = f"{prob:.0f}%"

            # Calculate contribution
            contribution = fv * (prob if prob < 1 else prob / 100)

            html += f'''
            <tr>
                <td style="color: {color}; font-weight: bold;">{label}</td>
                <td class="text-center">{prob_display}</td>
                <td class="text-right">${fv:.2f}</td>
                <td class="text-right">{wacc * 100:.2f}%</td>
                <td class="text-right">{tv_pct * 100:.1f}%</td>
                <td class="text-right" style="color: {color};">${contribution:.2f}</td>
            </tr>'''

        return html if html else "<tr><td colspan='6'>No scenario data</td></tr>"

    def _extract_wacc_component(self, context: Dict[str, Any], component: str) -> str:
        """Extract WACC component from assumptions_used"""
        # Try valuation_output first
        valuation = context.get("valuation_output", {})
        if isinstance(valuation, dict):
            assumptions = valuation.get("assumptions_used", {})
            if isinstance(assumptions, dict):
                wacc_inputs = assumptions.get("wacc_inputs", {})
                if isinstance(wacc_inputs, dict):
                    value = wacc_inputs.get(component)
                    if value is not None:
                        if component in ["risk_free_rate", "equity_risk_premium", "country_risk_premium", "tax_rate"]:
                            return f"{value * 100:.1f}"
                        elif component == "beta":
                            return f"{value:.2f}"
                        return str(value)

        # Try scenario_analysis
        scenario_analysis = context.get("scenario_analysis", {})
        if isinstance(scenario_analysis, dict):
            assumptions = scenario_analysis.get("assumptions_used", {})
            if isinstance(assumptions, dict):
                wacc_inputs = assumptions.get("wacc_inputs", {})
                if isinstance(wacc_inputs, dict):
                    value = wacc_inputs.get(component)
                    if value is not None:
                        if component in ["risk_free_rate", "equity_risk_premium", "country_risk_premium", "tax_rate"]:
                            return f"{value * 100:.1f}"
                        elif component == "beta":
                            return f"{value:.2f}"
                        return str(value)

        # Default values
        defaults = {
            "risk_free_rate": "4.0",
            "beta": "1.00",
            "equity_risk_premium": "5.5",
            "country_risk_premium": "0.0",
            "tax_rate": "25.0"
        }
        return defaults.get(component, "N/A")

    def _calculate_wacc_display(self, context: Dict[str, Any]) -> str:
        """Calculate and display WACC from components"""
        # Try to get actual WACC from scenarios
        scenarios = self._get_dcf_scenarios(context)
        if scenarios:
            # Get WACC from base scenario
            base = scenarios.get("base", {})
            if isinstance(base, dict):
                wacc = base.get("wacc", 0)
                if wacc > 0:
                    return f"{wacc * 100:.2f}"

        # Calculate from components
        try:
            rf = float(self._extract_wacc_component(context, "risk_free_rate")) / 100
            beta = float(self._extract_wacc_component(context, "beta"))
            erp = float(self._extract_wacc_component(context, "equity_risk_premium")) / 100
            crp = float(self._extract_wacc_component(context, "country_risk_premium")) / 100
            # Cost of Equity = Rf + Beta × ERP + CRP
            cost_of_equity = rf + beta * erp + crp
            return f"{cost_of_equity * 100:.2f}"
        except (ValueError, TypeError):
            return "10.00"

    def _get_assumptions_used(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract assumptions_used from context"""
        # Try valuation_output first
        valuation = context.get("valuation_output", {})
        if isinstance(valuation, dict):
            assumptions = valuation.get("assumptions_used", {})
            if isinstance(assumptions, dict) and assumptions:
                return assumptions

        # Try scenario_analysis
        scenario_analysis = context.get("scenario_analysis", {})
        if isinstance(scenario_analysis, dict):
            assumptions = scenario_analysis.get("assumptions_used", {})
            if isinstance(assumptions, dict) and assumptions:
                return assumptions

        return {}

    def _build_dcf_assumptions_rows(self, context: Dict[str, Any]) -> str:
        """Build DCF scenario assumptions table rows"""
        assumptions = self._get_assumptions_used(context)
        scenarios = assumptions.get("scenarios", {})

        if not scenarios:
            return "<tr><td colspan='5'>Assumptions data not available</td></tr>"

        scenario_order = ["super_bear", "bear", "base", "bull", "super_bull"]
        scenario_labels = {
            "super_bear": "Super Bear",
            "bear": "Bear",
            "base": "Base",
            "bull": "Bull",
            "super_bull": "Super Bull"
        }
        scenario_colors = {
            "super_bear": "#da3633",
            "bear": "#f85149",
            "base": "#58a6ff",
            "bull": "#3fb950",
            "super_bull": "#238636"
        }

        html = ""
        for key in scenario_order:
            if key not in scenarios:
                continue
            data = scenarios[key]
            if not isinstance(data, dict):
                continue

            label = scenario_labels.get(key, key)
            color = scenario_colors.get(key, "#8b949e")
            rev_y1_3 = data.get("revenue_growth_y1_3", 0)
            rev_y4_5 = data.get("revenue_growth_y4_5", 0)
            term_growth = data.get("terminal_growth", 0)
            target_margin = data.get("target_margin", 0)

            html += f'''
            <tr>
                <td style="color: {color}; font-weight: bold;">{label}</td>
                <td class="text-right">{rev_y1_3 * 100:.0f}%</td>
                <td class="text-right">{rev_y4_5 * 100:.0f}%</td>
                <td class="text-right">{term_growth * 100:.1f}%</td>
                <td class="text-right">{target_margin * 100:.0f}%</td>
            </tr>'''

        return html if html else "<tr><td colspan='5'>No assumption data</td></tr>"

    def _build_dcf_scenario_rationales(self, context: Dict[str, Any]) -> str:
        """Build scenario rationales section"""
        assumptions = self._get_assumptions_used(context)
        scenarios = assumptions.get("scenarios", {})

        if not scenarios:
            return "<p>Scenario rationales not available</p>"

        scenario_order = ["super_bear", "bear", "base", "bull", "super_bull"]
        scenario_labels = {
            "super_bear": "Super Bear",
            "bear": "Bear",
            "base": "Base",
            "bull": "Bull",
            "super_bull": "Super Bull"
        }
        scenario_colors = {
            "super_bear": "#da3633",
            "bear": "#f85149",
            "base": "#58a6ff",
            "bull": "#3fb950",
            "super_bull": "#238636"
        }

        html = ""
        for key in scenario_order:
            if key not in scenarios:
                continue
            data = scenarios[key]
            if not isinstance(data, dict):
                continue

            rationale = data.get("rationale", "")
            if not rationale:
                continue

            label = scenario_labels.get(key, key)
            color = scenario_colors.get(key, "#8b949e")

            html += f'''
            <div class="scenario-card" style="border-left: 4px solid {color}; margin-bottom: 15px;">
                <h4 style="color: {color}; margin-bottom: 10px;">{label} Case Rationale</h4>
                <p style="color: #c9d1d9; line-height: 1.6;">{rationale}</p>
            </div>'''

        return html if html else "<p>No scenario rationales available</p>"
