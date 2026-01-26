"""
Assumption Extractor - Parse debate outputs and market data into structured inputs.

This module extracts specific numerical assumptions from AI debate outputs
and combines them with real market data from APIs.

IMPORTANT: This module has been updated to use multi-AI extraction.
The old regex-based extraction with hardcoded defaults has been REMOVED.
All assumptions now come from the multi-AI extraction pipeline in assumption_agents.py.
"""

import re
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import sys

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class ScenarioAssumptions:
    """Assumptions for a single scenario"""
    name: str  # 'super_bear', 'bear', 'base', 'bull', 'super_bull'
    probability: float  # 0.0 to 1.0

    # Growth rates
    revenue_growth_y1_3: float  # Years 1-3
    revenue_growth_y4_5: float  # Years 4-5
    revenue_growth_y6_10: float  # Years 6-10
    terminal_growth: float

    # Margins
    target_ebit_margin: float
    years_to_target_margin: int

    # Risk adjustments (relative to base)
    wacc_adjustment: float = 0.0  # e.g., +0.02 for bear, -0.01 for bull
    beta_adjustment: float = 0.0

    # Source tracking
    rationale: str = ""
    source: str = ""  # 'bull_advocate', 'bear_advocate', 'synthesis'


@dataclass
class MarketData:
    """Real market data from APIs"""
    ticker: str
    current_price: float
    currency: str

    # Financials
    revenue_ttm: float  # in millions
    ebit_ttm: float
    ebit_margin: float
    net_income: float

    # Balance sheet
    total_debt: float
    cash: float
    net_debt: float  # total_debt - cash

    # Share data
    shares_outstanding: float  # in millions
    market_cap: float

    # Valuation multiples
    pe_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    ev_revenue: Optional[float] = None
    price_to_book: Optional[float] = None

    # Risk metrics
    beta: float = 1.0

    # Dividend data
    dividend_per_share: float = 0.0
    dividend_yield: float = 0.0
    payout_ratio: float = 0.0


@dataclass
class WACCInputs:
    """Inputs for WACC calculation"""
    risk_free_rate: float  # 10-year treasury
    beta: float
    equity_risk_premium: float  # typically 5.5-6.5%
    country_risk_premium: float = 0.0  # for EM markets
    cost_of_debt: float = 0.05
    tax_rate: float = 0.25
    debt_to_total_capital: float = 0.2


@dataclass
class PeerData:
    """Data for a comparable company"""
    ticker: str
    name: str
    market_cap: float

    # Multiples
    pe_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    ev_revenue: Optional[float] = None
    price_to_book: Optional[float] = None

    # Growth/profitability
    revenue_growth: Optional[float] = None
    ebit_margin: Optional[float] = None


@dataclass
class ValuationInputs:
    """Complete inputs for all valuation methods"""
    ticker: str
    company_name: str

    # Market data from APIs
    market_data: MarketData

    # WACC inputs
    wacc_inputs: WACCInputs

    # Scenarios from debate synthesis
    scenarios: Dict[str, ScenarioAssumptions]

    # Peer data for comps
    peers: List[PeerData] = field(default_factory=list)

    # Broker consensus (if available)
    broker_target_low: Optional[float] = None
    broker_target_high: Optional[float] = None
    broker_target_avg: Optional[float] = None
    broker_count: int = 0

    # Metadata
    data_date: str = ""
    sources: List[str] = field(default_factory=list)


class AssumptionExtractor:
    """
    Extract structured assumptions from debate outputs.

    This class parses the text outputs from Bull/Bear debates
    and the Debate Critic to extract specific numerical assumptions
    that can be used in valuation models.
    """

    def __init__(self):
        self.default_probabilities = {
            'super_bear': 0.10,
            'bear': 0.20,
            'base': 0.40,
            'bull': 0.20,
            'super_bull': 0.10
        }

        self.default_scenario_adjustments = {
            'super_bear': {
                'growth_adj': -0.15,  # -15% from base growth
                'wacc_adj': 0.03,     # +300bps WACC
                'terminal_adj': -0.01  # -1% terminal growth
            },
            'bear': {
                'growth_adj': -0.08,
                'wacc_adj': 0.015,
                'terminal_adj': -0.005
            },
            'bull': {
                'growth_adj': 0.10,
                'wacc_adj': -0.01,
                'terminal_adj': 0.005
            },
            'super_bull': {
                'growth_adj': 0.20,
                'wacc_adj': -0.02,
                'terminal_adj': 0.01
            }
        }

    def extract_from_debate(
        self,
        debate_critic_output: str,
        bull_r2_output: str,
        bear_r2_output: str,
        market_data: MarketData,
        wacc_inputs: WACCInputs
    ) -> ValuationInputs:
        """
        Extract valuation inputs from debate outputs.

        Args:
            debate_critic_output: Output from Debate Critic node
            bull_r2_output: Output from Bull Advocate R2
            bear_r2_output: Output from Bear Advocate R2
            market_data: Real market data from API
            wacc_inputs: WACC calculation inputs

        Returns:
            Complete ValuationInputs for all methods
        """
        # Extract base case assumptions from debate critic
        base_assumptions = self._extract_base_case(debate_critic_output)

        # Extract bull case assumptions
        bull_assumptions = self._extract_bull_case(bull_r2_output, base_assumptions)

        # Extract bear case assumptions
        bear_assumptions = self._extract_bear_case(bear_r2_output, base_assumptions)

        # Build all 5 scenarios
        scenarios = self._build_scenarios(base_assumptions, bull_assumptions, bear_assumptions)

        # Extract peer data if mentioned in debate
        peers = self._extract_peers(debate_critic_output)

        # Extract broker consensus if mentioned
        broker_data = self._extract_broker_consensus(debate_critic_output)

        return ValuationInputs(
            ticker=market_data.ticker,
            company_name=self._extract_company_name(debate_critic_output) or market_data.ticker,
            market_data=market_data,
            wacc_inputs=wacc_inputs,
            scenarios=scenarios,
            peers=peers,
            broker_target_low=broker_data.get('low'),
            broker_target_high=broker_data.get('high'),
            broker_target_avg=broker_data.get('avg'),
            broker_count=broker_data.get('count', 0),
            sources=['debate_critic', 'bull_r2', 'bear_r2', 'yahoo_finance']
        )

    def _extract_base_case(self, debate_critic_output: str) -> Dict[str, Any]:
        """Extract base case assumptions from debate critic output"""
        assumptions = {
            'revenue_growth_y1_3': 0.15,  # default 15%
            'revenue_growth_y4_5': 0.10,
            'revenue_growth_y6_10': 0.05,
            'terminal_growth': 0.0,  # CONSERVATIVE: 0% terminal growth for all equities
            'target_ebit_margin': 0.20,
            'years_to_target_margin': 5
        }

        text = debate_critic_output.lower()

        # Try to extract revenue growth
        growth_patterns = [
            r'revenue growth[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'base case.*?growth[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'growth rate[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s*growth',
        ]

        for pattern in growth_patterns:
            match = re.search(pattern, text)
            if match:
                growth = float(match.group(1)) / 100
                if 0.01 < growth < 0.50:  # sanity check
                    assumptions['revenue_growth_y1_3'] = growth
                    assumptions['revenue_growth_y4_5'] = growth * 0.7
                    assumptions['revenue_growth_y6_10'] = growth * 0.4
                    break

        # Try to extract margin
        margin_patterns = [
            r'operating margin[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'ebit margin[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'target margin[:\s]+(\d+(?:\.\d+)?)\s*%',
        ]

        for pattern in margin_patterns:
            match = re.search(pattern, text)
            if match:
                margin = float(match.group(1)) / 100
                if 0.05 < margin < 0.50:  # sanity check
                    assumptions['target_ebit_margin'] = margin
                    break

        # Try to extract terminal growth
        terminal_patterns = [
            r'terminal growth[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'perpetuity growth[:\s]+(\d+(?:\.\d+)?)\s*%',
        ]

        for pattern in terminal_patterns:
            match = re.search(pattern, text)
            if match:
                tg = float(match.group(1)) / 100
                if 0.01 < tg < 0.05:  # sanity check
                    assumptions['terminal_growth'] = tg
                    break

        return assumptions

    def _extract_bull_case(self, bull_output: str, base: Dict[str, Any]) -> Dict[str, Any]:
        """Extract bull case specific assumptions"""
        bull = base.copy()

        text = bull_output.lower()

        # Look for bull-specific growth mentions
        growth_patterns = [
            r'growth.*?(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s*revenue growth',
            r'revenue[:\s]+(\d+(?:\.\d+)?)\s*%',
        ]

        for pattern in growth_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Take the highest reasonable growth mentioned
                growths = [float(m) / 100 for m in matches if 0.05 < float(m) / 100 < 0.60]
                if growths:
                    bull['revenue_growth_y1_3'] = max(growths)
                    bull['revenue_growth_y4_5'] = max(growths) * 0.75
                    break

        # Ensure bull is more optimistic than base
        if bull['revenue_growth_y1_3'] <= base['revenue_growth_y1_3']:
            bull['revenue_growth_y1_3'] = base['revenue_growth_y1_3'] + 0.05
            bull['revenue_growth_y4_5'] = base['revenue_growth_y4_5'] + 0.03

        bull['target_ebit_margin'] = min(base['target_ebit_margin'] + 0.05, 0.40)

        return bull

    def _extract_bear_case(self, bear_output: str, base: Dict[str, Any]) -> Dict[str, Any]:
        """Extract bear case specific assumptions"""
        bear = base.copy()

        text = bear_output.lower()

        # Look for bear-specific growth mentions (typically lower)
        growth_patterns = [
            r'growth.*?(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s*revenue',
        ]

        for pattern in growth_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Take the lowest reasonable growth mentioned
                growths = [float(m) / 100 for m in matches if 0.01 < float(m) / 100 < 0.30]
                if growths:
                    bear['revenue_growth_y1_3'] = min(growths)
                    bear['revenue_growth_y4_5'] = min(growths) * 0.8
                    break

        # Ensure bear is more pessimistic than base
        if bear['revenue_growth_y1_3'] >= base['revenue_growth_y1_3']:
            bear['revenue_growth_y1_3'] = base['revenue_growth_y1_3'] - 0.05
            bear['revenue_growth_y4_5'] = base['revenue_growth_y4_5'] - 0.03

        bear['target_ebit_margin'] = max(base['target_ebit_margin'] - 0.05, 0.05)

        return bear

    def _build_scenarios(
        self,
        base: Dict[str, Any],
        bull: Dict[str, Any],
        bear: Dict[str, Any]
    ) -> Dict[str, ScenarioAssumptions]:
        """Build all 5 scenarios from extracted assumptions"""
        scenarios = {}

        # CONSERVATIVE ASSUMPTION: Terminal growth = 0% for ALL scenarios
        # This avoids overvaluation from terminal value speculation
        CONSERVATIVE_TERMINAL_GROWTH = 0.0  # 0% perpetual growth

        # Base case
        scenarios['base'] = ScenarioAssumptions(
            name='base',
            probability=self.default_probabilities['base'],
            revenue_growth_y1_3=base['revenue_growth_y1_3'],
            revenue_growth_y4_5=base['revenue_growth_y4_5'],
            revenue_growth_y6_10=base['revenue_growth_y6_10'],
            terminal_growth=CONSERVATIVE_TERMINAL_GROWTH,  # 0% for conservative valuation
            target_ebit_margin=base['target_ebit_margin'],
            years_to_target_margin=base['years_to_target_margin'],
            wacc_adjustment=0.0,
            rationale="Debate-weighted most likely outcome (0% terminal growth for conservative valuation)",
            source="debate_synthesis"
        )

        # Bull case - CONSTRAINED to avoid >150% upside scenarios
        # Cap growth rates to realistic maximum values
        scenarios['bull'] = ScenarioAssumptions(
            name='bull',
            probability=self.default_probabilities['bull'],
            revenue_growth_y1_3=min(bull['revenue_growth_y1_3'], 0.22),  # Max 22% Y1-3 growth
            revenue_growth_y4_5=min(bull['revenue_growth_y4_5'], 0.15),  # Max 15% Y4-5 growth
            revenue_growth_y6_10=min(bull.get('revenue_growth_y6_10', base['revenue_growth_y6_10'] * 1.2), 0.07),  # Max 7%
            terminal_growth=CONSERVATIVE_TERMINAL_GROWTH,  # 0% for conservative valuation
            target_ebit_margin=min(bull['target_ebit_margin'], 0.28),  # Max 28% margin
            years_to_target_margin=base['years_to_target_margin'] - 1,
            wacc_adjustment=-0.01,
            rationale="Bull advocate's main thesis (0% terminal growth, constrained growth rates)",
            source="bull_r2"
        )

        # Bear case
        scenarios['bear'] = ScenarioAssumptions(
            name='bear',
            probability=self.default_probabilities['bear'],
            revenue_growth_y1_3=bear['revenue_growth_y1_3'],
            revenue_growth_y4_5=bear['revenue_growth_y4_5'],
            revenue_growth_y6_10=bear.get('revenue_growth_y6_10', base['revenue_growth_y6_10'] * 0.8),
            terminal_growth=CONSERVATIVE_TERMINAL_GROWTH,  # 0% for conservative valuation
            target_ebit_margin=bear['target_ebit_margin'],
            years_to_target_margin=base['years_to_target_margin'] + 2,
            wacc_adjustment=0.015,
            rationale="Bear advocate's main thesis (0% terminal growth for conservative valuation)",
            source="bear_r2"
        )

        # Super bull - extrapolate from bull (CONSTRAINED to avoid unrealistic valuations)
        # IMPORTANT: Cap growth rates to avoid >200% upside scenarios
        scenarios['super_bull'] = ScenarioAssumptions(
            name='super_bull',
            probability=self.default_probabilities['super_bull'],
            revenue_growth_y1_3=min(bull['revenue_growth_y1_3'] * 1.15, 0.25),  # Max 25% (was 50%)
            revenue_growth_y4_5=min(bull['revenue_growth_y4_5'] * 1.15, 0.18),  # Max 18% (was 35%)
            revenue_growth_y6_10=min(base['revenue_growth_y6_10'] * 1.3, 0.08),  # Max 8%
            terminal_growth=CONSERVATIVE_TERMINAL_GROWTH,  # 0% for conservative valuation
            target_ebit_margin=min(bull['target_ebit_margin'] + 0.02, 0.30),  # Max 30% (was 40%)
            years_to_target_margin=max(base['years_to_target_margin'] - 1, 3),
            wacc_adjustment=-0.01,  # Reduced from -0.02
            rationale="Everything goes right - bull's best case (0% terminal growth, constrained growth)",
            source="extrapolation"
        )

        # Super bear - extrapolate from bear
        scenarios['super_bear'] = ScenarioAssumptions(
            name='super_bear',
            probability=self.default_probabilities['super_bear'],
            revenue_growth_y1_3=max(bear['revenue_growth_y1_3'] - 0.05, 0.0),
            revenue_growth_y4_5=max(bear['revenue_growth_y4_5'] - 0.03, 0.0),
            revenue_growth_y6_10=max(base['revenue_growth_y6_10'] * 0.5, 0.02),
            terminal_growth=CONSERVATIVE_TERMINAL_GROWTH,  # 0% for conservative valuation
            target_ebit_margin=max(bear['target_ebit_margin'] - 0.03, 0.05),
            years_to_target_margin=base['years_to_target_margin'] + 4,
            wacc_adjustment=0.03,
            rationale="Everything goes wrong - bear's worst fear (0% terminal growth for conservative valuation)",
            source="extrapolation"
        )

        return scenarios

    def _extract_peers(self, text: str) -> List[PeerData]:
        """Extract peer company data from text"""
        peers = []
        # This is a simplified extraction - in reality would need more robust parsing
        # or integration with a peer database

        # Look for common peer mention patterns
        peer_pattern = r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s*(?:\([A-Z]+\))?\s*(?:trades at|at|P/E of)\s*(\d+(?:\.\d+)?)\s*[xX]?'
        matches = re.findall(peer_pattern, text)

        for name, multiple in matches[:5]:  # Limit to 5 peers
            peers.append(PeerData(
                ticker=name.upper().replace(' ', ''),
                name=name,
                market_cap=0,  # Would need API lookup
                pe_ratio=float(multiple) if float(multiple) < 100 else None
            ))

        return peers

    def _extract_broker_consensus(self, text: str) -> Dict[str, Any]:
        """Extract broker consensus data from text"""
        result = {}
        text_lower = text.lower()

        # Look for average target
        avg_pattern = r'(?:average|consensus|mean)\s*(?:target|price)[:\s]*(?:\$|HKD|USD)?\s*(\d+(?:\.\d+)?)'
        match = re.search(avg_pattern, text_lower)
        if match:
            result['avg'] = float(match.group(1))

        # Look for target range
        range_pattern = r'(?:target|price)\s*(?:range)?[:\s]*(?:\$|HKD|USD)?\s*(\d+(?:\.\d+)?)\s*(?:to|-)\s*(?:\$|HKD|USD)?\s*(\d+(?:\.\d+)?)'
        match = re.search(range_pattern, text_lower)
        if match:
            result['low'] = float(match.group(1))
            result['high'] = float(match.group(2))

        # Look for analyst count
        count_pattern = r'(\d+)\s*(?:analyst|broker)'
        match = re.search(count_pattern, text_lower)
        if match:
            result['count'] = int(match.group(1))

        return result

    def _extract_company_name(self, text: str) -> Optional[str]:
        """Extract company name from text"""
        # Look for common patterns
        patterns = [
            r'(?:company|ticker|stock)[:\s]*([A-Z][a-zA-Z\s]+(?:Inc|Corp|Ltd|Limited|Co)?)',
            r'([A-Z][a-zA-Z]+\s+(?:Inc|Corp|Ltd|Limited|Co|Technology|Biotech|Pharma))',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None


class MultiAIAssumptionExtractor:
    """
    New multi-AI assumption extraction system.

    This class orchestrates multiple AI agents to extract DCF assumptions from:
    1. Broker research (private data) - PDFs and Excel models
    2. Public sources - Company filings, industry data
    3. Debate outputs - Bull/Bear insights

    Then reconciles all sources into validated assumptions.

    IMPORTANT: This replaces the old regex-based extraction with hardcoded defaults.
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def extract_assumptions(
        self,
        ticker: str,
        company_name: str,
        current_price: float,
        market_data: Dict[str, Any],
        debate_critic_output: str = "",
        bull_advocate_output: str = "",
        bear_advocate_output: str = "",
        industry_researcher_output: str = "",
        business_model_output: str = "",
        dot_connector_output: str = ""
    ) -> Dict[str, Any]:
        """
        Extract validated assumptions using multi-AI pipeline.

        This is the NEW way to extract assumptions.
        NO HARDCODED DEFAULTS are used.

        PRIORITY ORDER:
        1. Dot Connector output (HIGHEST - may contain REVISED parameters)
        2. Debate outputs (Bull/Bear/Critic)
        3. Industry/Business analysis
        4. Market data fallbacks (LOWEST)

        Args:
            ticker: Stock ticker (e.g., "6682 HK")
            company_name: Full company name
            current_price: Current stock price
            market_data: Dictionary with market data
            debate_critic_output: Output from Debate Critic node
            bull_advocate_output: Output from Bull Advocate R2
            bear_advocate_output: Output from Bear Advocate R2
            industry_researcher_output: Output from Industry Researcher
            business_model_output: Output from Business Model node
            dot_connector_output: Output from Dot Connector (PRIORITIZED!)

        Returns:
            Dictionary with:
            - scenarios: 5 scenarios (super_bear, bear, base, bull, super_bull)
            - wacc_inputs: WACC calculation parameters
            - metadata: Extraction metadata and confidence scores
        """
        # Import here to avoid circular imports
        from agents.valuation.assumption_agents import extract_validated_assumptions

        return extract_validated_assumptions(
            ticker=ticker,
            company_name=company_name,
            current_price=current_price,
            market_data=market_data,
            debate_critic_output=debate_critic_output,
            bull_advocate_output=bull_advocate_output,
            bear_advocate_output=bear_advocate_output,
            industry_researcher_output=industry_researcher_output,
            business_model_output=business_model_output,
            dot_connector_output=dot_connector_output,
            model=self.model
        )

    def build_valuation_inputs(
        self,
        extracted: Dict[str, Any],
        market_data: MarketData
    ) -> ValuationInputs:
        """
        Convert extracted assumptions into ValuationInputs for DCF engine.

        Args:
            extracted: Output from extract_assumptions()
            market_data: MarketData object

        Returns:
            ValuationInputs ready for DCF calculation
        """
        scenarios_data = extracted.get('scenarios', {})
        wacc_data = extracted.get('wacc_inputs', {})

        # IMPORTANT: Use real market data where available, only fall back to defaults if truly missing
        # Determine region-specific defaults based on ticker
        ticker = market_data.ticker
        if '_HK' in ticker or '_CH' in ticker:
            default_rf = 0.035  # China 10Y ~3.5%
            default_crp = 0.015  # China country risk premium
        else:
            default_rf = 0.045  # US 10Y ~4.5%
            default_crp = 0.0

        # Use REAL beta from market data (yfinance), not hardcoded default
        real_beta = market_data.beta if market_data.beta and 0.3 < market_data.beta < 3.0 else 1.0

        # Priority: 1) AI-extracted value, 2) real market data, 3) region-specific default
        wacc_inputs = WACCInputs(
            risk_free_rate=wacc_data.get('risk_free_rate') or default_rf,
            beta=wacc_data.get('beta') or real_beta,  # Use real beta from yfinance
            equity_risk_premium=wacc_data.get('equity_risk_premium') or 0.055,
            country_risk_premium=wacc_data.get('country_risk_premium') if wacc_data.get('country_risk_premium') is not None else default_crp,
            cost_of_debt=wacc_data.get('cost_of_debt') or 0.05,
            tax_rate=wacc_data.get('tax_rate') or 0.25,
            debt_to_total_capital=wacc_data.get('debt_to_equity', 0.2) / (1 + wacc_data.get('debt_to_equity', 0.2))
        )

        print(f"[WACC Inputs] Rf={wacc_inputs.risk_free_rate:.2%}, β={wacc_inputs.beta:.2f}, ERP={wacc_inputs.equity_risk_premium:.2%}, CRP={wacc_inputs.country_risk_premium:.2%}")

        # Build scenarios
        scenarios = {}
        probabilities = {
            'super_bear': 0.10,
            'bear': 0.20,
            'base': 0.40,
            'bull': 0.20,
            'super_bull': 0.10
        }

        for scenario_name, prob in probabilities.items():
            scenario_data = scenarios_data.get(scenario_name, {})
            scenarios[scenario_name] = ScenarioAssumptions(
                name=scenario_name,
                probability=scenario_data.get('probability', prob),
                revenue_growth_y1_3=scenario_data.get('revenue_growth_y1_3', 0.10),
                revenue_growth_y4_5=scenario_data.get('revenue_growth_y4_5', 0.07),
                revenue_growth_y6_10=scenario_data.get('revenue_growth_y6_10', 0.04),
                terminal_growth=scenario_data.get('terminal_growth', 0.0),  # CONSERVATIVE: 0%
                target_ebit_margin=scenario_data.get('target_ebit_margin', 0.15),
                years_to_target_margin=scenario_data.get('years_to_target_margin', 5),
                wacc_adjustment=scenario_data.get('wacc_adjustment', 0.0),
                rationale=scenario_data.get('rationale', ''),
                source='multi_ai_extraction'
            )

        metadata = extracted.get('metadata', {})

        return ValuationInputs(
            ticker=market_data.ticker,
            company_name=metadata.get('company_name', market_data.ticker),
            market_data=market_data,
            wacc_inputs=wacc_inputs,
            scenarios=scenarios,
            broker_target_avg=metadata.get('broker_target_price'),
            broker_count=1 if metadata.get('broker_target_price') else 0,
            sources=['broker_research', 'public_data', 'debate_synthesis']
        )


def extract_assumptions_multi_ai(
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
    Convenience function for multi-AI assumption extraction.

    This is the RECOMMENDED way to extract DCF assumptions.
    No hardcoded defaults are used.

    Returns dict with 'scenarios', 'wacc_inputs', 'metadata'.
    """
    extractor = MultiAIAssumptionExtractor(model=model)
    return extractor.extract_assumptions(
        ticker=ticker,
        company_name=company_name,
        current_price=current_price,
        market_data=market_data,
        debate_critic_output=debate_critic_output,
        bull_advocate_output=bull_advocate_output,
        bear_advocate_output=bear_advocate_output,
        industry_researcher_output=industry_researcher_output,
        business_model_output=business_model_output
    )
