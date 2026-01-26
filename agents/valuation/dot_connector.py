"""
Dot Connector Agent - Bridges qualitative analysis to quantitative DCF inputs

This agent creates a clear "dot connection" between:
1. Market analysis outputs (Industry Researcher, Business Model)
2. Debate outputs (Bull Advocate, Bear Advocate, Debate Critic)
3. Final DCF model parameters

The goal is to make the valuation transparent by explaining WHY each
number was chosen based on the preceding qualitative analysis.
"""

import json
import re
import sys
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.ai_providers import get_ai_response


@dataclass
class DotConnection:
    """A single dot connection between insight and parameter"""
    parameter: str  # e.g., "revenue_growth_y1_3"
    value: Any  # e.g., 0.25
    source_node: str  # e.g., "Industry Researcher"
    key_insight: str  # e.g., "AI chip market growing 40% CAGR"
    reasoning: str  # e.g., "Company is market leader, should capture 25% growth"
    confidence: float  # 0.0-1.0


@dataclass
class DotConnectorResult:
    """Complete dot connection summary"""
    ticker: str
    company_name: str

    # Executive summary
    investment_thesis: str
    key_value_drivers: List[str]
    key_risks: List[str]

    # Dot connections for each DCF parameter
    connections: Dict[str, DotConnection]

    # Summary tables
    growth_assumptions_table: str
    wacc_assumptions_table: str
    scenario_summary_table: str

    # Full narrative
    narrative: str

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'company_name': self.company_name,
            'investment_thesis': self.investment_thesis,
            'key_value_drivers': self.key_value_drivers,
            'key_risks': self.key_risks,
            'connections': {k: {
                'parameter': v.parameter,
                'value': v.value,
                'source_node': v.source_node,
                'key_insight': v.key_insight,
                'reasoning': v.reasoning,
                'confidence': v.confidence
            } for k, v in self.connections.items()},
            'growth_assumptions_table': self.growth_assumptions_table,
            'wacc_assumptions_table': self.wacc_assumptions_table,
            'scenario_summary_table': self.scenario_summary_table,
            'narrative': self.narrative
        }


class DotConnectorAgent:
    """
    AI agent that connects qualitative analysis to quantitative DCF inputs.

    This agent reads outputs from prior workflow nodes and creates an
    explicit mapping showing why each DCF parameter was chosen.
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def connect(
        self,
        ticker: str,
        company_name: str,
        current_price: float,
        # Prior workflow outputs
        industry_researcher_output: str = "",
        business_model_output: str = "",
        bull_advocate_output: str = "",
        bear_advocate_output: str = "",
        debate_critic_output: str = "",
        # DCF inputs used
        dcf_inputs: Dict[str, Any] = None,
        # Scenario results
        scenario_results: Dict[str, Any] = None
    ) -> DotConnectorResult:
        """
        Connect prior analysis to DCF parameters.

        Args:
            ticker: Stock ticker
            company_name: Full company name
            current_price: Current stock price
            industry_researcher_output: Output from Industry Researcher node
            business_model_output: Output from Business Model node
            bull_advocate_output: Output from Bull Advocate R2
            bear_advocate_output: Output from Bear Advocate R2
            debate_critic_output: Output from Debate Critic node
            dcf_inputs: The DCF inputs that were used (WACC, scenarios, etc.)
            scenario_results: Results from DCF scenarios

        Returns:
            DotConnectorResult with full dot connection analysis
        """
        print(f"[Dot Connector] Starting dot connection analysis for {ticker}")

        # Build the comprehensive prompt
        prompt = self._build_prompt(
            ticker=ticker,
            company_name=company_name,
            current_price=current_price,
            industry_researcher_output=industry_researcher_output,
            business_model_output=business_model_output,
            bull_advocate_output=bull_advocate_output,
            bear_advocate_output=bear_advocate_output,
            debate_critic_output=debate_critic_output,
            dcf_inputs=dcf_inputs,
            scenario_results=scenario_results
        )

        try:
            response = get_ai_response(
                prompt=prompt,
                model=self.model,
                temperature=0.2,
                max_tokens=4000
            )

            return self._parse_response(response, ticker, company_name)

        except Exception as e:
            print(f"[Dot Connector] Error: {e}")
            return self._create_error_result(ticker, company_name, str(e))

    def _build_prompt(
        self,
        ticker: str,
        company_name: str,
        current_price: float,
        industry_researcher_output: str,
        business_model_output: str,
        bull_advocate_output: str,
        bear_advocate_output: str,
        debate_critic_output: str,
        dcf_inputs: Dict[str, Any],
        scenario_results: Dict[str, Any]
    ) -> str:
        """Build the dot connector prompt"""

        return f"""You are a senior equity research analyst creating a "Dot Connection" summary.
Your job is to create a CLEAR BRIDGE between the qualitative analysis and the quantitative DCF model.

For each DCF parameter, you must explain:
1. WHAT insight from the prior analysis supports this number
2. WHERE that insight came from (which analyst/node)
3. WHY this translates to this specific quantitative assumption

=== COMPANY INFORMATION ===
TICKER: {ticker}
COMPANY: {company_name}
CURRENT PRICE: {current_price}

=== PRIOR ANALYSIS OUTPUTS ===

--- INDUSTRY RESEARCHER OUTPUT ---
{industry_researcher_output[:3000] if industry_researcher_output else "Not available"}

--- BUSINESS MODEL ANALYSIS ---
{business_model_output[:3000] if business_model_output else "Not available"}

--- BULL ADVOCATE THESIS ---
{bull_advocate_output[:2500] if bull_advocate_output else "Not available"}

--- BEAR ADVOCATE THESIS ---
{bear_advocate_output[:2500] if bear_advocate_output else "Not available"}

--- DEBATE CRITIC SYNTHESIS ---
{debate_critic_output[:3000] if debate_critic_output else "Not available"}

=== DCF INPUTS USED ===
{json.dumps(dcf_inputs, indent=2, default=str) if dcf_inputs else "Not available"}

=== SCENARIO RESULTS ===
{json.dumps(scenario_results, indent=2, default=str) if scenario_results else "Not available"}

=== YOUR TASK ===

Create a comprehensive DOT CONNECTION summary in the following JSON format:

{{
    "investment_thesis": "<2-3 sentence summary of the investment case>",

    "key_value_drivers": [
        "<driver 1 from analysis>",
        "<driver 2 from analysis>",
        "<driver 3 from analysis>"
    ],

    "key_risks": [
        "<risk 1 from bear case>",
        "<risk 2 from bear case>",
        "<risk 3 from bear case>"
    ],

    "dot_connections": {{
        "revenue_growth_y1_3": {{
            "value": <the actual value used>,
            "source_node": "<Industry Researcher/Business Model/Debate Critic>",
            "key_insight": "<specific quote or insight that supports this>",
            "reasoning": "<why this insight translates to this growth rate>",
            "confidence": <0.0-1.0>
        }},
        "revenue_growth_y4_5": {{
            "value": <value>,
            "source_node": "<source>",
            "key_insight": "<insight>",
            "reasoning": "<reasoning>",
            "confidence": <0.0-1.0>
        }},
        "revenue_growth_y6_10": {{
            "value": <value>,
            "source_node": "<source>",
            "key_insight": "<insight>",
            "reasoning": "<reasoning>",
            "confidence": <0.0-1.0>
        }},
        "terminal_growth": {{
            "value": <value>,
            "source_node": "<source>",
            "key_insight": "<insight>",
            "reasoning": "<reasoning>",
            "confidence": <0.0-1.0>
        }},
        "target_ebit_margin": {{
            "value": <value>,
            "source_node": "<source>",
            "key_insight": "<insight about margin trajectory>",
            "reasoning": "<why this margin is achievable>",
            "confidence": <0.0-1.0>
        }},
        "wacc": {{
            "value": <value>,
            "source_node": "<source or 'Market Data'>",
            "key_insight": "<insight about risk profile>",
            "reasoning": "<why this discount rate is appropriate>",
            "confidence": <0.0-1.0>
        }},
        "beta": {{
            "value": <value>,
            "source_node": "<Market Data/Debate>",
            "key_insight": "<insight about volatility/risk>",
            "reasoning": "<why this beta>",
            "confidence": <0.0-1.0>
        }}
    }},

    "growth_assumptions_table": "| Period | Growth Rate | Source | Key Driver |\\n|--------|-------------|--------|------------|\\n| Y1-3 | X% | <source> | <driver> |\\n| Y4-5 | X% | <source> | <driver> |\\n| Y6-10 | X% | <source> | <driver> |\\n| Terminal | X% | <source> | <driver> |",

    "wacc_assumptions_table": "| Component | Value | Source | Justification |\\n|-----------|-------|--------|---------------|\\n| Risk-free Rate | X% | <source> | <why> |\\n| Beta | X | <source> | <why> |\\n| Equity Risk Premium | X% | <source> | <why> |\\n| Country Risk Premium | X% | <source> | <why> |\\n| Cost of Debt | X% | <source> | <why> |\\n| WACC | X% | Calculated | <formula> |",

    "scenario_summary_table": "| Scenario | Probability | Fair Value | Key Assumption |\\n|----------|-------------|------------|----------------|\\n| Super Bear | 10% | $X | <assumption> |\\n| Bear | 20% | $X | <assumption> |\\n| Base | 40% | $X | <assumption> |\\n| Bull | 20% | $X | <assumption> |\\n| Super Bull | 10% | $X | <assumption> |",

    "narrative": "<A 3-5 paragraph narrative that tells the complete story: What does this company do? What are the key debates? How did those debates inform our valuation? What is the most likely outcome and why? What would change our view?>"
}}

CRITICAL RULES:
1. EVERY parameter must have a clear source from the prior analysis
2. If no clear source exists, say "Default assumption - no specific insight"
3. Be SPECIFIC about which analyst said what
4. Quote specific numbers/insights from the analysis where possible
5. The narrative should read like a professional equity research note
6. Tables should use markdown format

Output ONLY the JSON object, no other text.
"""

    def _parse_response(
        self,
        response: str,
        ticker: str,
        company_name: str
    ) -> DotConnectorResult:
        """Parse the AI response into DotConnectorResult"""

        try:
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                raise ValueError("No JSON found in response")

            data = json.loads(json_match.group())

            # Parse dot connections
            connections = {}
            for param, conn_data in data.get('dot_connections', {}).items():
                connections[param] = DotConnection(
                    parameter=param,
                    value=conn_data.get('value'),
                    source_node=conn_data.get('source_node', 'Unknown'),
                    key_insight=conn_data.get('key_insight', ''),
                    reasoning=conn_data.get('reasoning', ''),
                    confidence=conn_data.get('confidence', 0.5)
                )

            return DotConnectorResult(
                ticker=ticker,
                company_name=company_name,
                investment_thesis=data.get('investment_thesis', ''),
                key_value_drivers=data.get('key_value_drivers', []),
                key_risks=data.get('key_risks', []),
                connections=connections,
                growth_assumptions_table=data.get('growth_assumptions_table', ''),
                wacc_assumptions_table=data.get('wacc_assumptions_table', ''),
                scenario_summary_table=data.get('scenario_summary_table', ''),
                narrative=data.get('narrative', '')
            )

        except Exception as e:
            print(f"[Dot Connector] Parse error: {e}")
            return self._create_error_result(ticker, company_name, str(e))

    def _create_error_result(
        self,
        ticker: str,
        company_name: str,
        error: str
    ) -> DotConnectorResult:
        """Create an error result"""
        return DotConnectorResult(
            ticker=ticker,
            company_name=company_name,
            investment_thesis=f"Error generating dot connection: {error}",
            key_value_drivers=[],
            key_risks=[],
            connections={},
            growth_assumptions_table="",
            wacc_assumptions_table="",
            scenario_summary_table="",
            narrative=f"Dot connection analysis failed: {error}"
        )


def generate_dot_connection_summary(
    ticker: str,
    company_name: str,
    current_price: float,
    prior_outputs: Dict[str, str],
    dcf_inputs: Dict[str, Any] = None,
    scenario_results: Dict[str, Any] = None,
    model: str = "gpt-4o"
) -> Dict[str, Any]:
    """
    Main entry point for dot connection generation.

    Args:
        ticker: Stock ticker
        company_name: Full company name
        current_price: Current stock price
        prior_outputs: Dict mapping node names to their outputs
        dcf_inputs: DCF inputs used
        scenario_results: DCF scenario results
        model: AI model to use

    Returns:
        Dictionary with dot connection summary
    """
    agent = DotConnectorAgent(model=model)

    result = agent.connect(
        ticker=ticker,
        company_name=company_name,
        current_price=current_price,
        industry_researcher_output=prior_outputs.get('Industry_Researcher',
                                                      prior_outputs.get('industry_researcher', '')),
        business_model_output=prior_outputs.get('Business_Model',
                                                 prior_outputs.get('business_model', '')),
        bull_advocate_output=prior_outputs.get('Bull_Advocate_R2',
                                                prior_outputs.get('bull_advocate', '')),
        bear_advocate_output=prior_outputs.get('Bear_Advocate_R2',
                                                prior_outputs.get('bear_advocate', '')),
        debate_critic_output=prior_outputs.get('Debate_Critic',
                                                prior_outputs.get('debate_critic', '')),
        dcf_inputs=dcf_inputs,
        scenario_results=scenario_results
    )

    return result.to_dict()


# For standalone testing
if __name__ == "__main__":
    import sys
    import os
    from pathlib import Path

    # Test with a sample workflow result
    ticker = sys.argv[1] if len(sys.argv) > 1 else "6682_HK"

    # Try to load a workflow result
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

        # Get price from context
        current_price = workflow_result.get('verified_price', 100.0)
        company_name = workflow_result.get('context', {}).get('company_name', ticker)

        print(f"\n{'='*60}")
        print(f"DOT CONNECTION TEST: {ticker}")
        print(f"{'='*60}")
        print(f"Company: {company_name}")
        print(f"Price: {current_price}")
        print(f"Prior outputs found: {list(prior_outputs.keys())}")

        # Run dot connector
        result = generate_dot_connection_summary(
            ticker=ticker,
            company_name=company_name,
            current_price=current_price,
            prior_outputs=prior_outputs,
            model="gpt-4o"
        )

        print(f"\n{'='*60}")
        print("DOT CONNECTION RESULT:")
        print(f"{'='*60}")
        print(f"\n** Investment Thesis **\n{result.get('investment_thesis', 'N/A')}")
        print(f"\n** Key Value Drivers **")
        for driver in result.get('key_value_drivers', []):
            print(f"  - {driver}")
        print(f"\n** Key Risks **")
        for risk in result.get('key_risks', []):
            print(f"  - {risk}")
        print(f"\n** Growth Assumptions **\n{result.get('growth_assumptions_table', 'N/A')}")
        print(f"\n** WACC Assumptions **\n{result.get('wacc_assumptions_table', 'N/A')}")
        print(f"\n** Narrative **\n{result.get('narrative', 'N/A')}")

    else:
        print(f"No workflow result found at {result_file}")
        print("Run a workflow first: python run_workflow_live.py --ticker 6682_HK")
