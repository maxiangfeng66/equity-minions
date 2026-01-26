"""
AI-Powered Assumption Extraction Agents

Multi-AI system to extract DCF assumptions from:
1. Broker research (PDFs/Excel) - Private data source
2. Public sources (company filings, industry data)
3. AI debate outputs (qualitative insights)

Then reconcile all sources into validated assumptions.
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sys
import os

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.local_research_loader import LocalResearchLoader, get_excel_model_data, get_local_research_context
from agents.ai_providers import get_ai_response


@dataclass
class ExtractedAssumptions:
    """Structured assumptions extracted from any source"""
    source: str  # 'broker', 'public', 'debate', 'reconciled'
    confidence: float  # 0.0 to 1.0

    # Growth rates (as decimals, e.g., 0.15 = 15%)
    revenue_growth_y1_3: Optional[float] = None
    revenue_growth_y4_5: Optional[float] = None
    revenue_growth_y6_10: Optional[float] = None
    terminal_growth: Optional[float] = None

    # Margins
    current_ebit_margin: Optional[float] = None
    target_ebit_margin: Optional[float] = None
    years_to_target_margin: Optional[int] = None

    # WACC components
    wacc: Optional[float] = None
    risk_free_rate: Optional[float] = None
    beta: Optional[float] = None
    equity_risk_premium: Optional[float] = None
    country_risk_premium: Optional[float] = None
    cost_of_debt: Optional[float] = None
    tax_rate: Optional[float] = None
    debt_to_equity: Optional[float] = None

    # Revenue projections (if available)
    revenue_projections: Optional[Dict[str, float]] = None  # {year: revenue_in_millions}

    # Broker-specific
    broker_target_price: Optional[float] = None
    broker_rating: Optional[str] = None
    broker_firm: Optional[str] = None

    # Rationale
    rationale: str = ""
    warnings: List[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding None values"""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result


class BrokerDataExtractor:
    """
    AI agent to extract assumptions from broker research reports.
    Uses local_research_loader to access PDFs/Excel from private folder.
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.loader = LocalResearchLoader()

    def extract(self, ticker: str) -> ExtractedAssumptions:
        """
        Extract assumptions from broker research for a ticker.

        Args:
            ticker: Stock ticker (e.g., "6682 HK", "LEGN US")

        Returns:
            ExtractedAssumptions with data from broker reports
        """
        # Load research context
        context = self.loader.load_research(ticker, extract_excel=True)

        if not context:
            return ExtractedAssumptions(
                source='broker',
                confidence=0.0,
                rationale=f"No broker research found for {ticker}",
                warnings=[f"No research folder found for {ticker}"]
            )

        # Get Excel model data (most structured)
        excel_data = get_excel_model_data(ticker)

        # Get PDF content for AI extraction
        pdf_content = self._get_pdf_summary(context)

        # Get research summary
        research_summary = self.loader.get_research_summary(ticker)

        # Use AI to extract structured assumptions
        extracted = self._ai_extract_from_research(
            ticker=ticker,
            excel_data=excel_data,
            pdf_content=pdf_content,
            research_summary=research_summary
        )

        return extracted

    def _get_pdf_summary(self, context) -> str:
        """Get summary of PDF content for AI extraction"""
        pdf_texts = []

        for doc in context.documents[:5]:  # Limit to 5 PDFs
            if doc.doc_type == 'pdf':
                content = self.loader.extract_pdf_content(doc.filepath, max_pages=3)
                if content:
                    pdf_texts.append(f"=== {doc.filename} ===\n{content[:3000]}")

        return "\n\n".join(pdf_texts) if pdf_texts else ""

    def _ai_extract_from_research(
        self,
        ticker: str,
        excel_data: Optional[Dict],
        pdf_content: str,
        research_summary: str
    ) -> ExtractedAssumptions:
        """Use AI to extract structured assumptions from research"""

        prompt = f"""You are a financial analyst extracting DCF model assumptions from broker research.

TICKER: {ticker}

EXCEL MODEL DATA (if available):
{json.dumps(excel_data, indent=2, default=str) if excel_data else "No Excel data available"}

RESEARCH SUMMARY:
{research_summary[:4000]}

PDF CONTENT EXCERPTS:
{pdf_content[:6000] if pdf_content else "No PDF content available"}

TASK: Extract the following assumptions from the research.
IMPORTANT: Only provide values you can directly find or reasonably infer from the data above.
DO NOT guess or use typical industry defaults. If not found, leave as null.

Output ONLY a valid JSON object with these fields:
{{
    "revenue_growth_y1_3": <decimal e.g. 0.25 for 25%, or null if not found>,
    "revenue_growth_y4_5": <decimal or null>,
    "revenue_growth_y6_10": <decimal or null>,
    "terminal_growth": <decimal e.g. 0.025 for 2.5%, or null>,
    "current_ebit_margin": <decimal or null>,
    "target_ebit_margin": <decimal or null>,
    "years_to_target_margin": <integer or null>,
    "wacc": <decimal e.g. 0.10 for 10%, or null>,
    "risk_free_rate": <decimal or null>,
    "beta": <number or null>,
    "equity_risk_premium": <decimal or null>,
    "cost_of_debt": <decimal or null>,
    "tax_rate": <decimal or null>,
    "debt_to_equity": <decimal or null>,
    "broker_target_price": <number or null>,
    "broker_rating": <"BUY", "HOLD", or "SELL", or null>,
    "broker_firm": <string or null>,
    "confidence": <0.0 to 1.0 based on data quality>,
    "rationale": "<brief explanation of what you found>"
}}

CRITICAL:
- Use ONLY data from the research above
- Convert percentages to decimals (15% -> 0.15)
- If Excel model has WACC or growth rates, use those
- If multiple sources disagree, use the most detailed/recent one
- Be conservative with confidence score
"""

        try:
            response = get_ai_response(
                prompt=prompt,
                model=self.model,
                temperature=0.1,
                max_tokens=2000
            )

            # Parse JSON from response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                return ExtractedAssumptions(
                    source='broker',
                    confidence=data.get('confidence', 0.5),
                    revenue_growth_y1_3=data.get('revenue_growth_y1_3'),
                    revenue_growth_y4_5=data.get('revenue_growth_y4_5'),
                    revenue_growth_y6_10=data.get('revenue_growth_y6_10'),
                    terminal_growth=data.get('terminal_growth'),
                    current_ebit_margin=data.get('current_ebit_margin'),
                    target_ebit_margin=data.get('target_ebit_margin'),
                    years_to_target_margin=data.get('years_to_target_margin'),
                    wacc=data.get('wacc'),
                    risk_free_rate=data.get('risk_free_rate'),
                    beta=data.get('beta'),
                    equity_risk_premium=data.get('equity_risk_premium'),
                    cost_of_debt=data.get('cost_of_debt'),
                    tax_rate=data.get('tax_rate'),
                    debt_to_equity=data.get('debt_to_equity'),
                    broker_target_price=data.get('broker_target_price'),
                    broker_rating=data.get('broker_rating'),
                    broker_firm=data.get('broker_firm'),
                    rationale=data.get('rationale', ''),
                    warnings=[]
                )
            else:
                return ExtractedAssumptions(
                    source='broker',
                    confidence=0.0,
                    rationale="Failed to parse AI response",
                    warnings=["AI response did not contain valid JSON"]
                )

        except Exception as e:
            return ExtractedAssumptions(
                source='broker',
                confidence=0.0,
                rationale=f"Error during extraction: {str(e)}",
                warnings=[str(e)]
            )


class PublicDataCollector:
    """
    AI agent to collect assumptions from public sources.
    Uses company filings, industry data, forward guidance.
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def collect(
        self,
        ticker: str,
        company_name: str,
        market_data: Dict[str, Any],
        industry_researcher_output: str = "",
        business_model_output: str = ""
    ) -> ExtractedAssumptions:
        """
        Collect assumptions from public sources.

        Args:
            ticker: Stock ticker
            company_name: Full company name
            market_data: Current market data (from market data agent)
            industry_researcher_output: Output from Industry Researcher node
            business_model_output: Output from Business Model node

        Returns:
            ExtractedAssumptions from public sources
        """

        prompt = f"""You are a financial analyst extracting DCF assumptions from public information.

TICKER: {ticker}
COMPANY: {company_name}

MARKET DATA:
{json.dumps(market_data, indent=2, default=str)}

INDUSTRY RESEARCH:
{industry_researcher_output[:4000] if industry_researcher_output else "Not available"}

BUSINESS MODEL ANALYSIS:
{business_model_output[:4000] if business_model_output else "Not available"}

TASK: Based on the public information above, extract reasonable DCF assumptions.

Consider:
1. Industry growth rates (what is the TAM growth?)
2. Company's historical growth vs industry
3. Margin trajectory based on business model maturity
4. Risk profile based on market position

Output ONLY a valid JSON object:
{{
    "revenue_growth_y1_3": <decimal based on company guidance/industry, or null>,
    "revenue_growth_y4_5": <decimal, typically slower than y1-3, or null>,
    "revenue_growth_y6_10": <decimal, converging to industry average, or null>,
    "terminal_growth": <decimal, typically 2-3% for mature markets>,
    "current_ebit_margin": <from market data if available>,
    "target_ebit_margin": <based on industry comps/business model>,
    "years_to_target_margin": <integer>,
    "industry_growth_rate": <decimal, overall industry TAM growth>,
    "company_market_share_trend": <"increasing", "stable", "decreasing">,
    "confidence": <0.0 to 1.0>,
    "rationale": "<brief explanation>"
}}

CRITICAL: Base estimates on the data provided. Be explicit about uncertainty.
"""

        try:
            response = get_ai_response(
                prompt=prompt,
                model=self.model,
                temperature=0.1,
                max_tokens=1500
            )

            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                return ExtractedAssumptions(
                    source='public',
                    confidence=data.get('confidence', 0.4),
                    revenue_growth_y1_3=data.get('revenue_growth_y1_3'),
                    revenue_growth_y4_5=data.get('revenue_growth_y4_5'),
                    revenue_growth_y6_10=data.get('revenue_growth_y6_10'),
                    terminal_growth=data.get('terminal_growth'),
                    current_ebit_margin=data.get('current_ebit_margin'),
                    target_ebit_margin=data.get('target_ebit_margin'),
                    years_to_target_margin=data.get('years_to_target_margin'),
                    rationale=data.get('rationale', ''),
                    warnings=[]
                )
            else:
                return ExtractedAssumptions(
                    source='public',
                    confidence=0.0,
                    rationale="Failed to parse AI response",
                    warnings=["No valid JSON in response"]
                )

        except Exception as e:
            return ExtractedAssumptions(
                source='public',
                confidence=0.0,
                rationale=f"Error: {str(e)}",
                warnings=[str(e)]
            )


class DebateInsightsSynthesizer:
    """
    AI agent to synthesize assumptions from Bull/Bear debate outputs.
    Extracts qualitative insights and converts to quantitative ranges.
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def synthesize(
        self,
        ticker: str,
        debate_critic_output: str,
        bull_advocate_output: str,
        bear_advocate_output: str
    ) -> Tuple[ExtractedAssumptions, ExtractedAssumptions, ExtractedAssumptions]:
        """
        Synthesize assumptions from debate outputs.

        Returns:
            Tuple of (base_case, bull_case, bear_case) assumptions
        """

        prompt = f"""You are a financial analyst synthesizing DCF assumptions from investment debates.

TICKER: {ticker}

DEBATE SYNTHESIS (most important):
{debate_critic_output[:5000] if debate_critic_output else "Not available"}

BULL ADVOCATE VIEW:
{bull_advocate_output[:3000] if bull_advocate_output else "Not available"}

BEAR ADVOCATE VIEW:
{bear_advocate_output[:3000] if bear_advocate_output else "Not available"}

TASK: Extract THREE sets of assumptions - base, bull, and bear cases.

Consider:
- Bull case: What growth/margins does the bull advocate justify?
- Bear case: What risks/slower growth does the bear advocate highlight?
- Base case: What is the debate-weighted most likely outcome?

Output ONLY a valid JSON object with THREE scenarios:
{{
    "base_case": {{
        "revenue_growth_y1_3": <decimal>,
        "revenue_growth_y4_5": <decimal>,
        "revenue_growth_y6_10": <decimal>,
        "terminal_growth": <decimal>,
        "target_ebit_margin": <decimal>,
        "years_to_target_margin": <integer>,
        "wacc_adjustment": 0.0,
        "confidence": <0.0 to 1.0>,
        "rationale": "<what drives base case>"
    }},
    "bull_case": {{
        "revenue_growth_y1_3": <decimal, higher than base>,
        "revenue_growth_y4_5": <decimal>,
        "revenue_growth_y6_10": <decimal>,
        "terminal_growth": <decimal>,
        "target_ebit_margin": <decimal, higher than base>,
        "years_to_target_margin": <integer, faster than base>,
        "wacc_adjustment": -0.01,
        "confidence": <0.0 to 1.0>,
        "rationale": "<bull thesis summary>"
    }},
    "bear_case": {{
        "revenue_growth_y1_3": <decimal, lower than base>,
        "revenue_growth_y4_5": <decimal>,
        "revenue_growth_y6_10": <decimal>,
        "terminal_growth": <decimal>,
        "target_ebit_margin": <decimal, lower than base>,
        "years_to_target_margin": <integer, slower than base>,
        "wacc_adjustment": 0.015,
        "confidence": <0.0 to 1.0>,
        "rationale": "<bear thesis summary>"
    }}
}}

CRITICAL:
- Bull case growth should be > base case > bear case
- Be specific about the debate points that drive each scenario
- If debates don't mention specific numbers, use qualitative signals to estimate
"""

        try:
            response = get_ai_response(
                prompt=prompt,
                model=self.model,
                temperature=0.2,
                max_tokens=2000
            )

            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())

                def to_assumptions(case_data: Dict, case_name: str) -> ExtractedAssumptions:
                    return ExtractedAssumptions(
                        source=f'debate_{case_name}',
                        confidence=case_data.get('confidence', 0.5),
                        revenue_growth_y1_3=case_data.get('revenue_growth_y1_3'),
                        revenue_growth_y4_5=case_data.get('revenue_growth_y4_5'),
                        revenue_growth_y6_10=case_data.get('revenue_growth_y6_10'),
                        terminal_growth=case_data.get('terminal_growth'),
                        target_ebit_margin=case_data.get('target_ebit_margin'),
                        years_to_target_margin=case_data.get('years_to_target_margin'),
                        rationale=case_data.get('rationale', ''),
                        warnings=[]
                    )

                base = to_assumptions(data.get('base_case', {}), 'base')
                bull = to_assumptions(data.get('bull_case', {}), 'bull')
                bear = to_assumptions(data.get('bear_case', {}), 'bear')

                return base, bull, bear

        except Exception as e:
            empty = ExtractedAssumptions(
                source='debate',
                confidence=0.0,
                rationale=f"Error: {str(e)}",
                warnings=[str(e)]
            )
            return empty, empty, empty

        # Default return if parsing fails
        empty = ExtractedAssumptions(
            source='debate',
            confidence=0.0,
            rationale="Failed to parse debate insights",
            warnings=["Parsing failed"]
        )
        return empty, empty, empty


class AssumptionReconciler:
    """
    AI agent to reconcile assumptions from multiple sources.
    Applies weights, cross-validates, and outputs final validated assumptions.
    """

    # Source weights for reconciliation
    DEFAULT_WEIGHTS = {
        'broker': 0.50,   # Most weight to broker research (structured data)
        'debate': 0.30,   # Debate insights for qualitative adjustment
        'public': 0.20    # Public sources for context
    }

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def reconcile(
        self,
        ticker: str,
        broker_assumptions: ExtractedAssumptions,
        public_assumptions: ExtractedAssumptions,
        debate_base: ExtractedAssumptions,
        debate_bull: ExtractedAssumptions,
        debate_bear: ExtractedAssumptions,
        current_price: float,
        weights: Dict[str, float] = None
    ) -> Dict[str, ExtractedAssumptions]:
        """
        Reconcile assumptions from all sources into final validated assumptions.

        Args:
            ticker: Stock ticker
            broker_assumptions: From BrokerDataExtractor
            public_assumptions: From PublicDataCollector
            debate_base/bull/bear: From DebateInsightsSynthesizer
            current_price: Current stock price for sanity checks
            weights: Optional custom weights

        Returns:
            Dict with 'base', 'bull', 'bear', 'super_bull', 'super_bear' scenarios
        """
        weights = weights or self.DEFAULT_WEIGHTS

        prompt = f"""You are a senior financial analyst reconciling DCF assumptions from multiple sources.

TICKER: {ticker}
CURRENT PRICE: {current_price}

SOURCE 1 - BROKER RESEARCH (weight: {weights['broker']*100:.0f}%):
{json.dumps(broker_assumptions.to_dict(), indent=2)}

SOURCE 2 - PUBLIC DATA (weight: {weights['public']*100:.0f}%):
{json.dumps(public_assumptions.to_dict(), indent=2)}

SOURCE 3 - DEBATE INSIGHTS (weight: {weights['debate']*100:.0f}%):
Base Case: {json.dumps(debate_base.to_dict(), indent=2)}
Bull Case: {json.dumps(debate_bull.to_dict(), indent=2)}
Bear Case: {json.dumps(debate_bear.to_dict(), indent=2)}

TASK: Reconcile these sources into FIVE validated scenarios for DCF valuation.

RECONCILIATION RULES:
1. If broker data has a value, weight it heavily (most reliable)
2. Use debate insights to adjust bull/bear cases
3. Public data provides sanity checks
4. If sources conflict, explain why you chose one over another
5. Super_bull = bull case + extra upside; Super_bear = bear case + extra downside

Output ONLY a valid JSON object with FIVE scenarios:
{{
    "super_bear": {{
        "probability": 0.10,
        "revenue_growth_y1_3": <decimal>,
        "revenue_growth_y4_5": <decimal>,
        "revenue_growth_y6_10": <decimal>,
        "terminal_growth": <decimal, typically 1.5-2%>,
        "target_ebit_margin": <decimal>,
        "years_to_target_margin": <integer>,
        "wacc_adjustment": 0.03,
        "rationale": "<worst case thesis>"
    }},
    "bear": {{
        "probability": 0.20,
        "revenue_growth_y1_3": <decimal>,
        "revenue_growth_y4_5": <decimal>,
        "revenue_growth_y6_10": <decimal>,
        "terminal_growth": <decimal>,
        "target_ebit_margin": <decimal>,
        "years_to_target_margin": <integer>,
        "wacc_adjustment": 0.015,
        "rationale": "<bear case thesis>"
    }},
    "base": {{
        "probability": 0.40,
        "revenue_growth_y1_3": <decimal>,
        "revenue_growth_y4_5": <decimal>,
        "revenue_growth_y6_10": <decimal>,
        "terminal_growth": <decimal, typically 2-2.5%>,
        "target_ebit_margin": <decimal>,
        "years_to_target_margin": <integer>,
        "wacc_adjustment": 0.0,
        "rationale": "<most likely outcome>"
    }},
    "bull": {{
        "probability": 0.20,
        "revenue_growth_y1_3": <decimal>,
        "revenue_growth_y4_5": <decimal>,
        "revenue_growth_y6_10": <decimal>,
        "terminal_growth": <decimal>,
        "target_ebit_margin": <decimal>,
        "years_to_target_margin": <integer>,
        "wacc_adjustment": -0.01,
        "rationale": "<bull case thesis>"
    }},
    "super_bull": {{
        "probability": 0.10,
        "revenue_growth_y1_3": <decimal>,
        "revenue_growth_y4_5": <decimal>,
        "revenue_growth_y6_10": <decimal>,
        "terminal_growth": <decimal, typically 3-3.5%>,
        "target_ebit_margin": <decimal>,
        "years_to_target_margin": <integer>,
        "wacc_adjustment": -0.02,
        "rationale": "<best case thesis>"
    }},
    "wacc_inputs": {{
        "risk_free_rate": <decimal, use broker if available>,
        "beta": <number>,
        "equity_risk_premium": <decimal>,
        "country_risk_premium": <decimal, 0 for US, 1-2% for HK/China>,
        "cost_of_debt": <decimal>,
        "tax_rate": <decimal>,
        "debt_to_equity": <decimal>
    }},
    "reconciliation_notes": "<explain how you weighted and reconciled sources>",
    "confidence": <overall confidence 0.0-1.0>,
    "warnings": [<list any data quality issues>]
}}

CRITICAL:
- Probabilities must sum to 1.0
- Growth rates should be realistic (not >50% for y1-3 unless hypergrowth company)
- Terminal growth should be <= GDP growth (2-3%)
- If broker data is missing, rely more heavily on debate + public
"""

        try:
            response = get_ai_response(
                prompt=prompt,
                model=self.model,
                temperature=0.1,
                max_tokens=3000
            )

            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())

                scenarios = {}
                for scenario_name in ['super_bear', 'bear', 'base', 'bull', 'super_bull']:
                    scenario_data = data.get(scenario_name, {})
                    scenarios[scenario_name] = ExtractedAssumptions(
                        source='reconciled',
                        confidence=data.get('confidence', 0.7),
                        revenue_growth_y1_3=scenario_data.get('revenue_growth_y1_3'),
                        revenue_growth_y4_5=scenario_data.get('revenue_growth_y4_5'),
                        revenue_growth_y6_10=scenario_data.get('revenue_growth_y6_10'),
                        terminal_growth=scenario_data.get('terminal_growth'),
                        target_ebit_margin=scenario_data.get('target_ebit_margin'),
                        years_to_target_margin=scenario_data.get('years_to_target_margin'),
                        rationale=scenario_data.get('rationale', ''),
                        warnings=data.get('warnings', [])
                    )

                # Add WACC inputs to base case
                wacc_inputs = data.get('wacc_inputs', {})
                scenarios['base'].risk_free_rate = wacc_inputs.get('risk_free_rate')
                scenarios['base'].beta = wacc_inputs.get('beta')
                scenarios['base'].equity_risk_premium = wacc_inputs.get('equity_risk_premium')
                scenarios['base'].country_risk_premium = wacc_inputs.get('country_risk_premium')
                scenarios['base'].cost_of_debt = wacc_inputs.get('cost_of_debt')
                scenarios['base'].tax_rate = wacc_inputs.get('tax_rate')
                scenarios['base'].debt_to_equity = wacc_inputs.get('debt_to_equity')

                # Store reconciliation notes
                scenarios['base'].rationale = data.get('reconciliation_notes', scenarios['base'].rationale)

                return scenarios

        except Exception as e:
            print(f"Reconciliation error: {e}")

        # Return empty scenarios if failed
        return self._create_empty_scenarios()

    def _create_empty_scenarios(self) -> Dict[str, ExtractedAssumptions]:
        """Create empty scenario dict for error cases"""
        scenarios = {}
        for name in ['super_bear', 'bear', 'base', 'bull', 'super_bull']:
            scenarios[name] = ExtractedAssumptions(
                source='reconciled',
                confidence=0.0,
                rationale="Reconciliation failed",
                warnings=["No valid assumptions could be reconciled"]
            )
        return scenarios


def extract_validated_assumptions(
    ticker: str,
    company_name: str,
    current_price: float,
    market_data: Dict[str, Any],
    debate_critic_output: str = "",
    bull_advocate_output: str = "",
    bear_advocate_output: str = "",
    industry_researcher_output: str = "",
    business_model_output: str = "",
    model: str = "gpt-4o"
) -> Dict[str, Any]:
    """
    Main entry point for multi-AI assumption extraction.

    This function orchestrates the full extraction pipeline:
    1. Extract from broker research (private data)
    2. Collect from public sources
    3. Synthesize from debate outputs
    4. Reconcile all sources

    Args:
        ticker: Stock ticker
        company_name: Full company name
        current_price: Current stock price
        market_data: Market data dictionary
        debate_critic_output: Output from Debate Critic node
        bull_advocate_output: Output from Bull Advocate R2
        bear_advocate_output: Output from Bear Advocate R2
        industry_researcher_output: Output from Industry Researcher
        business_model_output: Output from Business Model node
        model: AI model to use

    Returns:
        Dictionary with:
        - scenarios: Dict of 5 scenarios with assumptions
        - wacc_inputs: WACC calculation inputs
        - metadata: Extraction metadata
    """
    print(f"[Assumption Extraction] Starting multi-AI extraction for {ticker}")

    # Step 1: Extract from broker research
    print(f"[Assumption Extraction] Step 1: Extracting from broker research...")
    broker_extractor = BrokerDataExtractor(model=model)
    broker_assumptions = broker_extractor.extract(ticker)
    print(f"  Broker confidence: {broker_assumptions.confidence:.2f}")

    # Step 2: Collect from public sources
    print(f"[Assumption Extraction] Step 2: Collecting from public sources...")
    public_collector = PublicDataCollector(model=model)
    public_assumptions = public_collector.collect(
        ticker=ticker,
        company_name=company_name,
        market_data=market_data,
        industry_researcher_output=industry_researcher_output,
        business_model_output=business_model_output
    )
    print(f"  Public confidence: {public_assumptions.confidence:.2f}")

    # Step 3: Synthesize from debates
    print(f"[Assumption Extraction] Step 3: Synthesizing from debates...")
    debate_synthesizer = DebateInsightsSynthesizer(model=model)
    debate_base, debate_bull, debate_bear = debate_synthesizer.synthesize(
        ticker=ticker,
        debate_critic_output=debate_critic_output,
        bull_advocate_output=bull_advocate_output,
        bear_advocate_output=bear_advocate_output
    )
    print(f"  Debate base confidence: {debate_base.confidence:.2f}")

    # Step 4: Reconcile all sources
    print(f"[Assumption Extraction] Step 4: Reconciling assumptions...")
    reconciler = AssumptionReconciler(model=model)
    scenarios = reconciler.reconcile(
        ticker=ticker,
        broker_assumptions=broker_assumptions,
        public_assumptions=public_assumptions,
        debate_base=debate_base,
        debate_bull=debate_bull,
        debate_bear=debate_bear,
        current_price=current_price
    )

    # Build result
    base_scenario = scenarios.get('base', ExtractedAssumptions(source='reconciled', confidence=0.0))

    # Determine region-specific defaults based on ticker
    if '_HK' in ticker or '_CH' in ticker or 'HK' in ticker.upper():
        default_rf = 0.035  # China 10Y ~3.5%
        default_crp = 0.015  # China country risk premium
    else:
        default_rf = 0.045  # US 10Y ~4.5%
        default_crp = 0.0

    # Use real beta from market_data if available
    real_beta = market_data.get('beta') if market_data.get('beta') and 0.3 < market_data.get('beta', 1.0) < 3.0 else None

    # IMPORTANT: Priority for WACC inputs:
    # 1. AI-extracted value from reconciliation (base_scenario)
    # 2. Real market data (from yfinance via market_data dict)
    # 3. Region-specific default (only as last resort)
    result = {
        'scenarios': {name: assum.to_dict() for name, assum in scenarios.items()},
        'wacc_inputs': {
            'risk_free_rate': base_scenario.risk_free_rate or default_rf,
            'beta': base_scenario.beta or real_beta or 1.0,  # Use real beta from yfinance
            'equity_risk_premium': base_scenario.equity_risk_premium or 0.055,
            'country_risk_premium': base_scenario.country_risk_premium if base_scenario.country_risk_premium is not None else default_crp,
            'cost_of_debt': base_scenario.cost_of_debt or 0.05,
            'tax_rate': base_scenario.tax_rate or 0.25,
            'debt_to_equity': base_scenario.debt_to_equity or 0.2
        },
        'metadata': {
            'ticker': ticker,
            'company_name': company_name,
            'current_price': current_price,
            'extraction_sources': ['broker', 'public', 'debate'],
            'broker_confidence': broker_assumptions.confidence,
            'public_confidence': public_assumptions.confidence,
            'debate_confidence': debate_base.confidence,
            'overall_confidence': base_scenario.confidence,
            'broker_target_price': broker_assumptions.broker_target_price,
            'broker_rating': broker_assumptions.broker_rating,
            'broker_firm': broker_assumptions.broker_firm,
            'wacc_source': 'AI-extracted' if base_scenario.risk_free_rate else 'market-data/default'
        }
    }

    # Log WACC inputs for transparency
    wi = result['wacc_inputs']
    print(f"[Assumption Extraction] WACC Inputs: Rf={wi['risk_free_rate']:.2%}, β={wi['beta']:.2f}, ERP={wi['equity_risk_premium']:.2%}, CRP={wi['country_risk_premium']:.2%}")

    print(f"[Assumption Extraction] Complete. Overall confidence: {base_scenario.confidence:.2f}")

    return result


if __name__ == "__main__":
    # Test the extraction
    import sys

    ticker = sys.argv[1] if len(sys.argv) > 1 else "6682 HK"

    result = extract_validated_assumptions(
        ticker=ticker,
        company_name="Test Company",
        current_price=100.0,
        market_data={"ticker": ticker, "price": 100.0},
        model="gpt-4o"
    )

    print("\n" + "="*60)
    print("EXTRACTION RESULT:")
    print(json.dumps(result, indent=2, default=str))
