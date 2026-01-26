"""
DCF Parameter Bridge - The authoritative source for ALL DCF model inputs

This module creates a clear "dot connection" bridge between:
1. Qualitative analysis (Industry, Company, Debates)
2. Quantitative DCF model parameters

DESIGN PRINCIPLE:
- Dot Connector PROPOSES all DCF parameters
- DCF Challenger VALIDATES parameter logic
- They DEBATE discrepancies
- Final parameters are AGREED upon before DCF runs

PARAMETERS COVERED:
1. Revenue Projections
   - Base revenue (current year)
   - Growth rates: Y1-3, Y4-5, Y6-10
2. Margin Projections
   - Current EBIT margin
   - Target EBIT margin
   - Years to target
3. WACC Components
   - Risk-free rate (Rf)
   - Beta (β)
   - Equity Risk Premium (ERP)
   - Country Risk Premium (CRP)
   - Cost of Debt (Kd)
   - Tax rate
   - Debt-to-Capital ratio
4. Terminal Value
   - Terminal growth rate
   - Exit multiple (if applicable)
5. Scenario Probabilities
   - Super Bear, Bear, Base, Bull, Super Bull weights
"""

import json
import re
import sys
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.ai_providers import get_ai_response


@dataclass
class DCFParameter:
    """A single DCF parameter with full traceability"""
    name: str                    # Parameter name (e.g., "revenue_growth_y1_3")
    value: float                 # The numeric value
    unit: str                    # "percent", "ratio", "millions", "years"
    source_node: str             # Which workflow node provided this
    source_quote: str            # Direct quote from source that justifies value
    reasoning: str               # Why this value was chosen
    confidence: float            # 0.0-1.0 confidence in this parameter
    alternative_values: List[float]  # Other values considered
    sensitivity: str             # "high", "medium", "low" - impact on valuation


@dataclass
class DCFParameterSet:
    """Complete set of DCF parameters with traceability"""
    ticker: str
    company_name: str
    currency: str
    current_price: float

    # Revenue parameters
    base_revenue: DCFParameter
    revenue_growth_y1_3: DCFParameter
    revenue_growth_y4_5: DCFParameter
    revenue_growth_y6_10: DCFParameter

    # Margin parameters
    current_ebit_margin: DCFParameter
    target_ebit_margin: DCFParameter
    years_to_target_margin: DCFParameter

    # WACC components
    risk_free_rate: DCFParameter
    beta: DCFParameter
    equity_risk_premium: DCFParameter
    country_risk_premium: DCFParameter
    cost_of_debt: DCFParameter
    tax_rate: DCFParameter
    debt_to_capital: DCFParameter

    # Terminal value
    terminal_growth: DCFParameter

    # Scenario weights
    prob_super_bear: DCFParameter
    prob_bear: DCFParameter
    prob_base: DCFParameter
    prob_bull: DCFParameter
    prob_super_bull: DCFParameter

    # Metadata
    total_confidence: float
    warnings: List[str]

    def to_dict(self) -> Dict:
        return asdict(self)

    def get_parameter_table(self) -> str:
        """Generate markdown table of all parameters"""
        rows = []
        rows.append("| Parameter | Value | Unit | Source | Confidence | Sensitivity |")
        rows.append("|-----------|-------|------|--------|------------|-------------|")

        params = [
            ("Base Revenue", self.base_revenue),
            ("Revenue Growth Y1-3", self.revenue_growth_y1_3),
            ("Revenue Growth Y4-5", self.revenue_growth_y4_5),
            ("Revenue Growth Y6-10", self.revenue_growth_y6_10),
            ("Current EBIT Margin", self.current_ebit_margin),
            ("Target EBIT Margin", self.target_ebit_margin),
            ("Years to Target", self.years_to_target_margin),
            ("Risk-Free Rate", self.risk_free_rate),
            ("Beta", self.beta),
            ("Equity Risk Premium", self.equity_risk_premium),
            ("Country Risk Premium", self.country_risk_premium),
            ("Cost of Debt", self.cost_of_debt),
            ("Tax Rate", self.tax_rate),
            ("Debt/Capital", self.debt_to_capital),
            ("Terminal Growth", self.terminal_growth),
        ]

        for name, param in params:
            if param.unit == "percent":
                val_str = f"{param.value*100:.1f}%"
            elif param.unit == "ratio":
                val_str = f"{param.value:.2f}"
            elif param.unit == "millions":
                val_str = f"{param.value:,.0f}M"
            else:
                val_str = str(param.value)

            conf_str = f"{param.confidence*100:.0f}%"
            rows.append(f"| {name} | {val_str} | {param.unit} | {param.source_node} | {conf_str} | {param.sensitivity} |")

        return "\n".join(rows)


class DotConnector:
    """
    Extracts and connects qualitative analysis to quantitative DCF parameters.

    This is the FIRST step before DCF - it proposes all parameters with justifications.
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def extract_parameters(
        self,
        ticker: str,
        company_name: str,
        current_price: float,
        currency: str,
        prior_outputs: Dict[str, str],
        market_data: Dict[str, Any] = None
    ) -> DCFParameterSet:
        """
        Extract all DCF parameters from prior workflow outputs.

        Args:
            ticker: Stock ticker
            company_name: Company name
            current_price: Verified current stock price
            currency: Currency (USD, HKD, etc.)
            prior_outputs: Dict of {node_name: output_content}
            market_data: Market data from prefetch (beta, revenue, etc.)

        Returns:
            DCFParameterSet with all parameters and justifications
        """
        print(f"[Dot Connector] Extracting ALL DCF parameters for {ticker}")

        # Get key analysis outputs
        industry_analysis = prior_outputs.get('Industry Deep Dive',
                            prior_outputs.get('Industry_Researcher', ''))
        company_analysis = prior_outputs.get('Company Deep Dive',
                           prior_outputs.get('Business_Model', ''))
        bull_thesis = prior_outputs.get('Bull Advocate R2',
                      prior_outputs.get('Bull_Advocate_R2', ''))
        bear_thesis = prior_outputs.get('Bear Advocate R2',
                      prior_outputs.get('Bear_Advocate_R2', ''))
        debate_synthesis = prior_outputs.get('Debate Critic',
                           prior_outputs.get('Debate_Critic', ''))
        market_data_output = prior_outputs.get('Market Data Collector', '')

        # Build comprehensive prompt
        prompt = self._build_extraction_prompt(
            ticker=ticker,
            company_name=company_name,
            current_price=current_price,
            currency=currency,
            industry_analysis=industry_analysis,
            company_analysis=company_analysis,
            bull_thesis=bull_thesis,
            bear_thesis=bear_thesis,
            debate_synthesis=debate_synthesis,
            market_data_output=market_data_output,
            market_data=market_data
        )

        try:
            response = get_ai_response(
                prompt=prompt,
                model=self.model,
                temperature=0.1,
                max_tokens=4000
            )

            return self._parse_response(response, ticker, company_name, current_price, currency)

        except Exception as e:
            print(f"[Dot Connector] Error: {e}")
            return self._create_default_parameters(ticker, company_name, current_price, currency, str(e))

    def _build_extraction_prompt(
        self,
        ticker: str,
        company_name: str,
        current_price: float,
        currency: str,
        industry_analysis: str,
        company_analysis: str,
        bull_thesis: str,
        bear_thesis: str,
        debate_synthesis: str,
        market_data_output: str,
        market_data: Dict[str, Any]
    ) -> str:
        """Build the parameter extraction prompt"""

        # Get real data from market_data if available
        real_beta = market_data.get('beta', 1.0) if market_data else 1.0
        real_revenue = market_data.get('total_revenue', 0) if market_data else 0
        real_ebit_margin = market_data.get('operating_margin', 0) if market_data else 0

        # Determine region for defaults
        if '_HK' in ticker or '_CH' in ticker or 'HK' in ticker.upper():
            default_rf = 0.035
            default_crp = 0.015
            region = "Hong Kong/China"
        else:
            default_rf = 0.045
            default_crp = 0.0
            region = "US"

        return f"""You are a senior equity analyst extracting DCF model parameters.

CRITICAL: Every parameter MUST be justified by specific quotes or data from the prior analysis.
If no supporting evidence exists, you MUST say "No specific evidence - using default" and flag low confidence.

=== COMPANY INFORMATION ===
TICKER: {ticker}
COMPANY: {company_name}
CURRENT PRICE: {currency} {current_price}
REGION: {region}

=== REAL MARKET DATA (USE THESE AS BASELINE) ===
- Real Beta (from yfinance): {real_beta:.2f}
- Real Revenue TTM: {currency} {real_revenue:,.0f}M
- Real EBIT Margin: {real_ebit_margin*100:.1f}% (can be negative for loss-making companies)
- Region Default Rf: {default_rf*100:.1f}%
- Region Default CRP: {default_crp*100:.1f}%

=== PRIOR ANALYSIS OUTPUTS ===

--- INDUSTRY ANALYSIS ---
{industry_analysis[:1500] if industry_analysis else "Not available"}

--- COMPANY ANALYSIS ---
{company_analysis[:1500] if company_analysis else "Not available"}

--- MARKET DATA COLLECTED ---
{market_data_output[:1000] if market_data_output else "Not available"}

--- BULL THESIS ---
{bull_thesis[:1200] if bull_thesis else "Not available"}

--- BEAR THESIS ---
{bear_thesis[:1200] if bear_thesis else "Not available"}

--- DEBATE SYNTHESIS ---
{debate_synthesis[:1500] if debate_synthesis else "Not available"}

=== YOUR TASK ===

Extract ALL DCF parameters with CLEAR DOT CONNECTIONS to the analysis above.
For EACH parameter, you MUST provide:
1. The specific value
2. The source node that provided evidence
3. A DIRECT QUOTE from that source supporting the value
4. Your reasoning for choosing this value
5. Your confidence (0.0-1.0) in this parameter

Output a JSON object with this EXACT structure:

{{
    "base_revenue": {{
        "value": <number in millions>,
        "source_node": "<Industry/Company/Market Data>",
        "source_quote": "<exact quote from analysis>",
        "reasoning": "<why this value>",
        "confidence": <0.0-1.0>,
        "alternatives": [<other values considered>],
        "sensitivity": "<high/medium/low>"
    }},
    "revenue_growth_y1_3": {{
        "value": <decimal e.g., 0.20 for 20%>,
        "source_node": "<source>",
        "source_quote": "<quote mentioning growth or TAM>",
        "reasoning": "<how industry growth + company position = this growth rate>",
        "confidence": <0.0-1.0>,
        "alternatives": [<bull growth, bear growth>],
        "sensitivity": "high"
    }},
    "revenue_growth_y4_5": {{
        "value": <decimal>,
        "source_node": "<source>",
        "source_quote": "<quote>",
        "reasoning": "<reasoning>",
        "confidence": <0.0-1.0>,
        "alternatives": [],
        "sensitivity": "medium"
    }},
    "revenue_growth_y6_10": {{
        "value": <decimal>,
        "source_node": "<source>",
        "source_quote": "<quote>",
        "reasoning": "<reasoning for convergence to industry rate>",
        "confidence": <0.0-1.0>,
        "alternatives": [],
        "sensitivity": "medium"
    }},
    "current_ebit_margin": {{
        "value": <decimal, can be negative for loss-making companies>,
        "source_node": "Market Data",
        "source_quote": "<quote with margin data>",
        "reasoning": "<current profitability status>",
        "confidence": <0.0-1.0>,
        "alternatives": [],
        "sensitivity": "high"
    }},
    "target_ebit_margin": {{
        "value": <decimal>,
        "source_node": "<Company Analysis/Industry>",
        "source_quote": "<quote about margin potential or industry comps>",
        "reasoning": "<path to profitability or margin expansion>",
        "confidence": <0.0-1.0>,
        "alternatives": [],
        "sensitivity": "high"
    }},
    "years_to_target_margin": {{
        "value": <integer 3-10>,
        "source_node": "<source>",
        "source_quote": "<quote>",
        "reasoning": "<reasoning>",
        "confidence": <0.0-1.0>,
        "alternatives": [],
        "sensitivity": "medium"
    }},
    "risk_free_rate": {{
        "value": <decimal e.g., 0.035 for 3.5%>,
        "source_node": "Market Data",
        "source_quote": "Using {region} 10Y government bond yield",
        "reasoning": "<regional rate justification>",
        "confidence": 0.9,
        "alternatives": [],
        "sensitivity": "medium"
    }},
    "beta": {{
        "value": {real_beta:.2f},
        "source_node": "Market Data (yfinance)",
        "source_quote": "Real historical beta from market data",
        "reasoning": "<why this beta is appropriate>",
        "confidence": 0.8,
        "alternatives": [1.0, 1.2, 1.5],
        "sensitivity": "medium"
    }},
    "equity_risk_premium": {{
        "value": 0.055,
        "source_node": "Standard Market",
        "source_quote": "Historical equity risk premium",
        "reasoning": "Standard ERP for equity valuation",
        "confidence": 0.8,
        "alternatives": [0.05, 0.06],
        "sensitivity": "medium"
    }},
    "country_risk_premium": {{
        "value": {default_crp},
        "source_node": "Market Data",
        "source_quote": "{region} country risk premium",
        "reasoning": "<regional risk justification>",
        "confidence": 0.8,
        "alternatives": [],
        "sensitivity": "low"
    }},
    "cost_of_debt": {{
        "value": <decimal>,
        "source_node": "<Company Analysis>",
        "source_quote": "<quote about debt or interest costs>",
        "reasoning": "<debt cost justification>",
        "confidence": <0.0-1.0>,
        "alternatives": [],
        "sensitivity": "low"
    }},
    "tax_rate": {{
        "value": <decimal>,
        "source_node": "<Company Analysis>",
        "source_quote": "<quote or regional default>",
        "reasoning": "<tax rate justification>",
        "confidence": 0.8,
        "alternatives": [],
        "sensitivity": "low"
    }},
    "debt_to_capital": {{
        "value": <decimal>,
        "source_node": "<Company Analysis>",
        "source_quote": "<quote about capital structure>",
        "reasoning": "<capital structure justification>",
        "confidence": <0.0-1.0>,
        "alternatives": [],
        "sensitivity": "low"
    }},
    "terminal_growth": {{
        "value": <decimal, typically 0.02-0.03>,
        "source_node": "<Industry Analysis>",
        "source_quote": "<quote about long-term industry growth>",
        "reasoning": "Terminal growth should be <= GDP growth",
        "confidence": 0.7,
        "alternatives": [0.02, 0.025, 0.03],
        "sensitivity": "high"
    }},
    "scenario_probabilities": {{
        "super_bear": 0.10,
        "bear": 0.20,
        "base": 0.40,
        "bull": 0.20,
        "super_bull": 0.10,
        "reasoning": "<why these weights based on debate balance>"
    }},
    "overall_confidence": <0.0-1.0 average of all confidences>,
    "warnings": ["<list any data gaps or concerns>"]
}}

CRITICAL RULES:
1. Use REAL market data values (beta, revenue, margin) as starting point
2. Every growth rate MUST be supported by TAM/SAM analysis from Industry
3. Every margin assumption MUST be supported by business model analysis
4. If Bull and Bear disagree, use DEBATE SYNTHESIS to weight
5. Flag ANY parameter with confidence < 0.5
6. For loss-making companies, current_ebit_margin CAN be negative

Output ONLY the JSON, no other text.
"""

    def _parse_response(
        self,
        response: str,
        ticker: str,
        company_name: str,
        current_price: float,
        currency: str
    ) -> DCFParameterSet:
        """Parse the AI response into DCFParameterSet"""

        # Find JSON in response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            raise ValueError("No JSON found in response")

        data = json.loads(json_match.group())

        def make_param(param_data: Dict, name: str, default_value: float, unit: str) -> DCFParameter:
            if isinstance(param_data, dict):
                return DCFParameter(
                    name=name,
                    value=param_data.get('value', default_value),
                    unit=unit,
                    source_node=param_data.get('source_node', 'Default'),
                    source_quote=param_data.get('source_quote', 'No quote available'),
                    reasoning=param_data.get('reasoning', 'Using default assumption'),
                    confidence=param_data.get('confidence', 0.5),
                    alternative_values=param_data.get('alternatives', []),
                    sensitivity=param_data.get('sensitivity', 'medium')
                )
            else:
                return DCFParameter(
                    name=name,
                    value=param_data if isinstance(param_data, (int, float)) else default_value,
                    unit=unit,
                    source_node='Default',
                    source_quote='No quote available',
                    reasoning='Using default assumption',
                    confidence=0.3,
                    alternative_values=[],
                    sensitivity='medium'
                )

        # Extract scenario probabilities
        probs = data.get('scenario_probabilities', {})

        return DCFParameterSet(
            ticker=ticker,
            company_name=company_name,
            currency=currency,
            current_price=current_price,

            # Revenue
            base_revenue=make_param(data.get('base_revenue', {}), 'base_revenue', 1000, 'millions'),
            revenue_growth_y1_3=make_param(data.get('revenue_growth_y1_3', {}), 'revenue_growth_y1_3', 0.15, 'percent'),
            revenue_growth_y4_5=make_param(data.get('revenue_growth_y4_5', {}), 'revenue_growth_y4_5', 0.10, 'percent'),
            revenue_growth_y6_10=make_param(data.get('revenue_growth_y6_10', {}), 'revenue_growth_y6_10', 0.05, 'percent'),

            # Margins
            current_ebit_margin=make_param(data.get('current_ebit_margin', {}), 'current_ebit_margin', 0.10, 'percent'),
            target_ebit_margin=make_param(data.get('target_ebit_margin', {}), 'target_ebit_margin', 0.15, 'percent'),
            years_to_target_margin=make_param(data.get('years_to_target_margin', {}), 'years_to_target_margin', 5, 'years'),

            # WACC
            risk_free_rate=make_param(data.get('risk_free_rate', {}), 'risk_free_rate', 0.04, 'percent'),
            beta=make_param(data.get('beta', {}), 'beta', 1.0, 'ratio'),
            equity_risk_premium=make_param(data.get('equity_risk_premium', {}), 'equity_risk_premium', 0.055, 'percent'),
            country_risk_premium=make_param(data.get('country_risk_premium', {}), 'country_risk_premium', 0.0, 'percent'),
            cost_of_debt=make_param(data.get('cost_of_debt', {}), 'cost_of_debt', 0.05, 'percent'),
            tax_rate=make_param(data.get('tax_rate', {}), 'tax_rate', 0.25, 'percent'),
            debt_to_capital=make_param(data.get('debt_to_capital', {}), 'debt_to_capital', 0.20, 'percent'),

            # Terminal
            terminal_growth=make_param(data.get('terminal_growth', {}), 'terminal_growth', 0.0, 'percent'),  # CONSERVATIVE: 0%

            # Scenario probabilities
            prob_super_bear=make_param({'value': probs.get('super_bear', 0.10), 'source_node': 'Debate Synthesis',
                                        'source_quote': 'Standard probability weighting', 'reasoning': probs.get('reasoning', 'Standard distribution'),
                                        'confidence': 0.7, 'alternatives': [], 'sensitivity': 'low'},
                                       'prob_super_bear', 0.10, 'percent'),
            prob_bear=make_param({'value': probs.get('bear', 0.20)}, 'prob_bear', 0.20, 'percent'),
            prob_base=make_param({'value': probs.get('base', 0.40)}, 'prob_base', 0.40, 'percent'),
            prob_bull=make_param({'value': probs.get('bull', 0.20)}, 'prob_bull', 0.20, 'percent'),
            prob_super_bull=make_param({'value': probs.get('super_bull', 0.10)}, 'prob_super_bull', 0.10, 'percent'),

            total_confidence=data.get('overall_confidence', 0.5),
            warnings=data.get('warnings', [])
        )

    def _create_default_parameters(
        self,
        ticker: str,
        company_name: str,
        current_price: float,
        currency: str,
        error: str
    ) -> DCFParameterSet:
        """Create default parameters when extraction fails"""

        def default_param(name: str, value: float, unit: str) -> DCFParameter:
            return DCFParameter(
                name=name,
                value=value,
                unit=unit,
                source_node='Default (extraction failed)',
                source_quote=f'Error: {error}',
                reasoning='Using conservative default due to extraction failure',
                confidence=0.3,
                alternative_values=[],
                sensitivity='high'
            )

        return DCFParameterSet(
            ticker=ticker,
            company_name=company_name,
            currency=currency,
            current_price=current_price,
            base_revenue=default_param('base_revenue', 1000, 'millions'),
            revenue_growth_y1_3=default_param('revenue_growth_y1_3', 0.10, 'percent'),
            revenue_growth_y4_5=default_param('revenue_growth_y4_5', 0.08, 'percent'),
            revenue_growth_y6_10=default_param('revenue_growth_y6_10', 0.05, 'percent'),
            current_ebit_margin=default_param('current_ebit_margin', 0.10, 'percent'),
            target_ebit_margin=default_param('target_ebit_margin', 0.15, 'percent'),
            years_to_target_margin=default_param('years_to_target_margin', 5, 'years'),
            risk_free_rate=default_param('risk_free_rate', 0.04, 'percent'),
            beta=default_param('beta', 1.0, 'ratio'),
            equity_risk_premium=default_param('equity_risk_premium', 0.055, 'percent'),
            country_risk_premium=default_param('country_risk_premium', 0.0, 'percent'),
            cost_of_debt=default_param('cost_of_debt', 0.05, 'percent'),
            tax_rate=default_param('tax_rate', 0.25, 'percent'),
            debt_to_capital=default_param('debt_to_capital', 0.20, 'percent'),
            terminal_growth=default_param('terminal_growth', 0.0, 'percent'),  # CONSERVATIVE: 0%
            prob_super_bear=default_param('prob_super_bear', 0.10, 'percent'),
            prob_bear=default_param('prob_bear', 0.20, 'percent'),
            prob_base=default_param('prob_base', 0.40, 'percent'),
            prob_bull=default_param('prob_bull', 0.20, 'percent'),
            prob_super_bull=default_param('prob_super_bull', 0.10, 'percent'),
            total_confidence=0.3,
            warnings=[f'Parameter extraction failed: {error}', 'Using conservative defaults']
        )


class DCFChallenger:
    """
    Challenges and validates DCF parameters from the Dot Connector.

    This creates a debate between qualitative insights and quantitative logic.
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def challenge(
        self,
        parameters: DCFParameterSet,
        prior_outputs: Dict[str, str]
    ) -> Tuple[List[Dict], DCFParameterSet]:
        """
        Challenge the proposed parameters and return:
        1. List of challenges with reasoning
        2. Potentially revised parameters

        Args:
            parameters: Proposed DCF parameters from Dot Connector
            prior_outputs: Original analysis outputs for verification

        Returns:
            (challenges, revised_parameters)
        """
        print(f"[DCF Challenger] Validating parameters for {parameters.ticker}")

        prompt = self._build_challenge_prompt(parameters, prior_outputs)

        try:
            response = get_ai_response(
                prompt=prompt,
                model=self.model,
                temperature=0.2,
                max_tokens=3000
            )

            return self._parse_challenges(response, parameters)

        except Exception as e:
            print(f"[DCF Challenger] Error: {e}")
            return [], parameters

    def _build_challenge_prompt(
        self,
        params: DCFParameterSet,
        prior_outputs: Dict[str, str]
    ) -> str:
        """Build the challenge prompt"""

        param_table = params.get_parameter_table()

        return f"""You are a senior DCF model validator. Your job is to CHALLENGE the proposed parameters.

=== PROPOSED DCF PARAMETERS ===
{param_table}

=== VALIDATION CHECKS ===

For each parameter, verify:
1. MATHEMATICAL CONSISTENCY: Do the numbers make sense together?
   - WACC > Terminal Growth (required for Gordon Growth Model)
   - Revenue growth should decline over time (convergence)
   - Margin expansion should be realistic for the industry

2. EVIDENCE QUALITY: Is the source quote actually supporting the value?
   - Does the quote directly mention this metric?
   - Is the source relevant and recent?

3. RANGE REASONABLENESS: Is the value within normal ranges?
   - Revenue growth: typically 5-50% for growth companies
   - EBIT margins: industry-specific, 5-30% typical
   - Beta: 0.5-2.5 typical range
   - Terminal growth: 1.5-3.5% (should be < GDP growth)

=== YOUR TASK ===

Output a JSON with your challenges:

{{
    "challenges": [
        {{
            "parameter": "<parameter name>",
            "issue": "<what's wrong>",
            "severity": "<HIGH/MEDIUM/LOW>",
            "current_value": <value>,
            "suggested_value": <corrected value or null if no change>,
            "reasoning": "<why this is a problem and what you suggest>"
        }}
    ],
    "overall_assessment": "<PASS/REVISE/REJECT>",
    "confidence_adjustment": <adjustment to total confidence, e.g., -0.1>,
    "summary": "<2-3 sentence summary of key issues>"
}}

CRITICAL RULES:
1. Challenge EVERY parameter - don't assume anything is correct
2. If WACC <= Terminal Growth, this is a CRITICAL error
3. If revenue growth increases over time, flag it
4. If no quote supports a value, flag low evidence quality
5. Be specific about what's wrong and how to fix it

Output ONLY the JSON.
"""

    def _parse_challenges(
        self,
        response: str,
        original_params: DCFParameterSet
    ) -> Tuple[List[Dict], DCFParameterSet]:
        """Parse challenges and potentially revise parameters"""

        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            return [], original_params

        data = json.loads(json_match.group())

        challenges = data.get('challenges', [])

        # For now, return original params - in full debate system,
        # we would have back-and-forth to resolve
        # This is a placeholder for the debate mechanism

        return challenges, original_params


def run_dcf_parameter_debate(
    ticker: str,
    company_name: str,
    current_price: float,
    currency: str,
    prior_outputs: Dict[str, str],
    market_data: Dict[str, Any] = None,
    model: str = "gpt-4o",
    max_rounds: int = 2
) -> Tuple[DCFParameterSet, List[Dict]]:
    """
    Run the full Dot Connector -> DCF Challenger debate.

    Args:
        ticker: Stock ticker
        company_name: Company name
        current_price: Current stock price
        currency: Currency
        prior_outputs: Dict of prior analysis outputs
        market_data: Market data from prefetch
        model: AI model to use
        max_rounds: Maximum debate rounds

    Returns:
        (final_parameters, debate_log)
    """
    debate_log = []

    # Step 1: Dot Connector proposes parameters
    connector = DotConnector(model=model)
    params = connector.extract_parameters(
        ticker=ticker,
        company_name=company_name,
        current_price=current_price,
        currency=currency,
        prior_outputs=prior_outputs,
        market_data=market_data
    )

    debate_log.append({
        'round': 1,
        'agent': 'Dot Connector',
        'action': 'PROPOSE',
        'parameters': params.to_dict(),
        'confidence': params.total_confidence
    })

    # Step 2: DCF Challenger validates
    challenger = DCFChallenger(model=model)
    challenges, revised_params = challenger.challenge(params, prior_outputs)

    debate_log.append({
        'round': 1,
        'agent': 'DCF Challenger',
        'action': 'CHALLENGE',
        'challenges': challenges,
        'assessment': 'REVISE' if challenges else 'PASS'
    })

    # For now, return the original parameters
    # Full implementation would iterate until consensus

    return params, debate_log


# CLI for testing
if __name__ == "__main__":
    import sys

    ticker = sys.argv[1] if len(sys.argv) > 1 else "6682_HK"

    # Load workflow result
    context_dir = Path(__file__).parent.parent.parent / "context"
    result_file = context_dir / f"{ticker}_workflow_result.json"

    if result_file.exists():
        print(f"Loading workflow result from {result_file}")
        with open(result_file, 'r', encoding='utf-8') as f:
            workflow_result = json.load(f)

        # Extract prior outputs
        prior_outputs = {}
        for node_id, outputs in workflow_result.get('node_outputs', {}).items():
            if outputs:
                prior_outputs[node_id] = outputs[-1].get('content', '')

        current_price = workflow_result.get('verified_price', 100.0)
        currency = workflow_result.get('currency', 'USD')
        company_name = workflow_result.get('context', {}).get('company_name', ticker)

        print(f"\n{'='*60}")
        print(f"DCF PARAMETER BRIDGE TEST: {ticker}")
        print(f"{'='*60}")

        # Run the debate
        params, debate_log = run_dcf_parameter_debate(
            ticker=ticker,
            company_name=company_name,
            current_price=current_price,
            currency=currency,
            prior_outputs=prior_outputs,
            model="gpt-4o"
        )

        print(f"\n{'='*60}")
        print("DCF PARAMETER TABLE")
        print(f"{'='*60}")
        print(params.get_parameter_table())

        print(f"\n{'='*60}")
        print("DEBATE LOG")
        print(f"{'='*60}")
        for entry in debate_log:
            print(f"\nRound {entry['round']} - {entry['agent']} ({entry['action']})")
            if entry['action'] == 'CHALLENGE' and entry.get('challenges'):
                for c in entry['challenges']:
                    print(f"  [{c.get('severity', 'N/A')}] {c.get('parameter')}: {c.get('issue')}")

        print(f"\n{'='*60}")
        print(f"TOTAL CONFIDENCE: {params.total_confidence*100:.0f}%")
        print(f"WARNINGS: {params.warnings}")

    else:
        print(f"No workflow result found at {result_file}")
