"""
Valuation Orchestrator - Main entry point for multi-method valuation.

This orchestrator:
1. Extracts assumptions from prior debate outputs
2. Runs all valuation engines with the SAME inputs
3. Cross-checks results for convergence
4. Builds consensus recommendation

Usage:
    from agents.valuation import ValuationOrchestrator

    orchestrator = ValuationOrchestrator()
    result = orchestrator.run_valuation(
        ticker="9660_HK",
        debate_outputs=debate_outputs,
        market_data_raw=market_data
    )
"""

import json
from typing import Dict, Any, Optional
from dataclasses import asdict

from .assumption_extractor import (
    AssumptionExtractor,
    MultiAIAssumptionExtractor,  # NEW: Multi-AI extraction
    ValuationInputs,
    MarketData,
    WACCInputs,
    PeerData,
    ScenarioAssumptions
)
from .engines.dcf_engine import DCFEngine
from .engines.comps_engine import CompsEngine
from .engines.ddm_engine import DDMEngine
from .engines.reverse_dcf_engine import ReverseDCFEngine
from .cross_checker import CrossChecker
from .consensus_builder import ConsensusBuilder, ConsensusValuation


class ValuationOrchestrator:
    """
    Main orchestrator for multi-method valuation.

    This class coordinates all valuation engines and produces a
    comprehensive valuation report with cross-checked results.
    """

    def __init__(self, projection_years: int = 10, use_multi_ai: bool = True):
        self.dcf_engine = DCFEngine(projection_years)
        self.comps_engine = CompsEngine()
        self.ddm_engine = DDMEngine()
        self.reverse_dcf_engine = ReverseDCFEngine(projection_years)
        self.cross_checker = CrossChecker()
        self.consensus_builder = ConsensusBuilder()
        self.assumption_extractor = AssumptionExtractor()
        self.multi_ai_extractor = MultiAIAssumptionExtractor() if use_multi_ai else None
        self.use_multi_ai = use_multi_ai

    def run_valuation(
        self,
        ticker: str,
        debate_outputs: Dict[str, str],
        market_data_raw: Dict[str, Any],
        peers_data: Optional[list] = None,
        broker_target: Optional[float] = None,
        industry_researcher_output: str = "",
        business_model_output: str = "",
        company_name: str = "",
        dot_connector_output: str = ""
    ) -> Dict[str, Any]:
        """
        Run complete multi-method valuation.

        Args:
            ticker: Stock ticker (e.g., "9660_HK")
            debate_outputs: Dict with keys:
                - 'debate_critic': Debate Critic node output
                - 'bull_r2': Bull Advocate R2 output
                - 'bear_r2': Bear Advocate R2 output
            market_data_raw: Raw market data from API
            peers_data: Optional list of peer company data
            broker_target: Optional broker consensus target price
            industry_researcher_output: Output from Industry Researcher node
            business_model_output: Output from Business Model / Company Deep Dive node
            company_name: Company name for extraction
            dot_connector_output: Output from Dot Connector node (PRIORITIZED for parameter extraction!)

        Returns:
            Comprehensive valuation result as dict
        """
        # Step 1: Prepare market data
        market_data = self._prepare_market_data(ticker, market_data_raw)

        # Step 2: Prepare WACC inputs (will be overridden if using multi-AI)
        wacc_inputs = self._prepare_wacc_inputs(market_data_raw, market_data)

        # Step 3: Extract assumptions - USE MULTI-AI IF ENABLED
        # PRIORITIZE: Dot Connector output contains synthesized parameters!
        if self.use_multi_ai and self.multi_ai_extractor:
            print(f"[ValuationOrchestrator] Using multi-AI extraction for {ticker}")
            if dot_connector_output:
                print(f"[ValuationOrchestrator] USING DOT CONNECTOR PARAMETERS (may include revisions)")
            valuation_inputs = self._run_multi_ai_extraction(
                ticker=ticker,
                company_name=company_name or ticker,
                market_data=market_data,
                debate_outputs=debate_outputs,
                industry_researcher_output=industry_researcher_output,
                business_model_output=business_model_output,
                market_data_raw=market_data_raw,
                dot_connector_output=dot_connector_output
            )
        else:
            # Fall back to old regex-based extraction (NOT RECOMMENDED)
            print(f"[ValuationOrchestrator] WARNING: Using legacy extraction for {ticker}")
            valuation_inputs = self.assumption_extractor.extract_from_debate(
                debate_critic_output=debate_outputs.get('debate_critic', ''),
                bull_r2_output=debate_outputs.get('bull_r2', ''),
                bear_r2_output=debate_outputs.get('bear_r2', ''),
                market_data=market_data,
                wacc_inputs=wacc_inputs
            )

        # Add peers if provided
        if peers_data:
            valuation_inputs.peers = self._prepare_peers(peers_data)

        # Step 4: Run all valuation engines
        dcf_result = self.dcf_engine.calculate(valuation_inputs)
        comps_result = self.comps_engine.calculate(valuation_inputs)
        ddm_result = self.ddm_engine.calculate(valuation_inputs)
        reverse_dcf_result = self.reverse_dcf_engine.calculate(valuation_inputs)

        # Step 5: Cross-check results
        cross_check = self.cross_checker.check(
            dcf_result=dcf_result,
            comps_result=comps_result,
            ddm_result=ddm_result,
            reverse_dcf_result=reverse_dcf_result,
            broker_target=broker_target
        )

        # Step 6: Build consensus
        consensus = self.consensus_builder.build_consensus(
            dcf_result=dcf_result,
            comps_result=comps_result,
            ddm_result=ddm_result,
            reverse_dcf_result=reverse_dcf_result,
            cross_check=cross_check,
            broker_target=broker_target
        )

        # Get broker target from market_data if not provided explicitly
        actual_broker_target = broker_target
        if not actual_broker_target and market_data_raw:
            actual_broker_target = market_data_raw.get('broker_target_avg')

        # Step 7: Build comprehensive output
        output = self._build_output(
            valuation_inputs, dcf_result, comps_result, ddm_result,
            reverse_dcf_result, cross_check, consensus
        )

        # Add broker consensus data for DCF Validator
        if actual_broker_target:
            output['broker_target_avg'] = actual_broker_target
            output['broker_target_low'] = market_data_raw.get('broker_target_low') if market_data_raw else None
            output['broker_target_high'] = market_data_raw.get('broker_target_high') if market_data_raw else None
            output['broker_count'] = market_data_raw.get('broker_count', 5) if market_data_raw else 5

        return output

    def _run_multi_ai_extraction(
        self,
        ticker: str,
        company_name: str,
        market_data: MarketData,
        debate_outputs: Dict[str, str],
        industry_researcher_output: str,
        business_model_output: str,
        market_data_raw: Dict[str, Any],
        dot_connector_output: str = ""
    ) -> ValuationInputs:
        """
        Run multi-AI assumption extraction pipeline.

        This is the NEW way to extract assumptions - NO HARDCODED DEFAULTS.

        PRIORITY ORDER FOR PARAMETERS:
        1. Dot Connector output (highest - may contain revised parameters)
        2. Multi-AI extraction from debates
        3. Market data defaults (lowest)

        Args:
            ticker: Stock ticker
            company_name: Company name
            market_data: Prepared MarketData object
            debate_outputs: Dict with debate outputs
            industry_researcher_output: From Industry Researcher
            business_model_output: From Company Deep Dive
            market_data_raw: Raw market data dict
            dot_connector_output: Output from Dot Connector (PRIORITIZED!)

        Returns:
            ValuationInputs with multi-AI extracted assumptions
        """
        # Run multi-AI extraction - include Dot Connector output for parameter override
        extracted = self.multi_ai_extractor.extract_assumptions(
            ticker=ticker,
            company_name=company_name,
            current_price=market_data.current_price,
            market_data=market_data_raw,
            debate_critic_output=debate_outputs.get('debate_critic', ''),
            bull_advocate_output=debate_outputs.get('bull_r2', ''),
            bear_advocate_output=debate_outputs.get('bear_r2', ''),
            industry_researcher_output=industry_researcher_output,
            business_model_output=business_model_output,
            dot_connector_output=dot_connector_output  # PRIORITIZED!
        )

        # Convert to ValuationInputs
        return self.multi_ai_extractor.build_valuation_inputs(extracted, market_data)

    def _prepare_market_data(self, ticker: str, raw: Dict[str, Any]) -> MarketData:
        """Convert raw market data to structured format with sensible defaults"""
        # Handle various data formats
        currency = raw.get('currency', 'HKD')
        if '_HK' in ticker:
            currency = 'HKD'
        elif '_US' in ticker:
            currency = 'USD'

        def to_millions(value, threshold=1e6):
            """Convert to millions if value appears to be in raw form"""
            if value is None:
                return 0
            try:
                value = float(value)
            except (ValueError, TypeError):
                return 0
            # If value > 1 million, assume it's in raw form and convert
            if abs(value) > threshold:
                return value / 1e6
            return value

        # Get current price first (needed for estimation)
        current_price = raw.get('current_price', raw.get('price', 0))
        if current_price is None or current_price <= 0:
            # Try to get from verified_price in context
            current_price = raw.get('verified_price', 0)
        if current_price is None or current_price <= 0:
            # NO HARDCODED DEFAULTS - warn loudly
            print(f"[ValuationOrchestrator] ERROR: No current_price in market data!")
            print(f"[ValuationOrchestrator] Raw data keys: {list(raw.keys())}")
            # Use a placeholder but warn
            current_price = 1.0  # Minimal placeholder to prevent div/0
            print(f"[ValuationOrchestrator] WARNING: Using placeholder price 1.0 - RESULTS WILL BE WRONG!")

        # Extract financials - convert to millions consistently
        revenue = to_millions(raw.get('revenue_ttm', raw.get('revenue', 0)))
        ebit = to_millions(raw.get('ebit_ttm', raw.get('ebit', raw.get('operating_income', 0))))
        net_income = to_millions(raw.get('net_income', 0))
        market_cap = to_millions(raw.get('market_cap', 0))
        shares = to_millions(raw.get('shares_outstanding', 0))
        total_debt = to_millions(raw.get('total_debt', 0))
        cash = to_millions(raw.get('cash', raw.get('total_cash', 0)))

        # Handle net_debt specially - could be negative (net cash)
        raw_net_debt = raw.get('net_debt', 0)
        if raw_net_debt is None:
            raw_net_debt = 0
        net_debt = raw_net_debt / 1e6 if abs(raw_net_debt) > 1e6 else raw_net_debt

        # Calculate shares from market_cap / price if not directly provided
        # AVOID HARDCODED DEFAULTS - we want real data
        if shares <= 0:
            if market_cap > 0 and current_price > 0:
                shares = market_cap / current_price
                print(f"[ValuationOrchestrator] Calculated shares: {shares:.1f}M from market_cap/price")
            else:
                # Last resort: estimate from typical market cap assumption
                # This is NOT ideal - warn loudly
                print(f"[ValuationOrchestrator] WARNING: No shares_outstanding data. Using estimate.")
                if market_cap > 0:
                    # Assume price around 10-50 for typical stock
                    shares = market_cap / 30  # Rough estimate
                else:
                    # Absolute last resort - but this should be rare
                    shares = 100
                print(f"[ValuationOrchestrator] ESTIMATED shares: {shares:.1f}M - VERIFY THIS VALUE!")

        if market_cap <= 0 and current_price > 0 and shares > 0:
            market_cap = current_price * shares

        # If no revenue, estimate from market cap using typical revenue multiple
        # WARNING: This is a very rough estimate and may produce wrong DCF results!
        if revenue <= 0 and market_cap > 0:
            revenue = market_cap / 3  # Assume 3x EV/Revenue
            print(f"[ValuationOrchestrator] WARNING: No real revenue data!")
            print(f"[ValuationOrchestrator] ESTIMATED revenue = market_cap/3 = {market_cap:.0f}/3 = {revenue:.0f}M")
            print(f"[ValuationOrchestrator] This is a ROUGH ESTIMATE - DCF results may be wrong!")
            print(f"[ValuationOrchestrator] To fix: provide 'revenue_ttm' in market_data from yfinance/broker research")

        # Check if we have operating_margin from yfinance (can be negative for loss-making companies!)
        operating_margin_from_data = raw.get('operating_margin')

        # If no EBIT but we have operating margin, calculate EBIT from margin
        if ebit == 0 and revenue > 0 and operating_margin_from_data is not None:
            ebit = revenue * operating_margin_from_data
            margin_pct = operating_margin_from_data * 100
            if operating_margin_from_data < 0:
                print(f"[ValuationOrchestrator] WARNING: Company is LOSS-MAKING!")
                print(f"[ValuationOrchestrator] Operating Margin: {margin_pct:.1f}% (from yfinance)")
                print(f"[ValuationOrchestrator] EBIT: {ebit:.0f}M (negative)")
            else:
                print(f"[ValuationOrchestrator] Operating Margin: {margin_pct:.1f}% (from yfinance)")
        # Only default to 15% if we have NO margin data at all
        elif ebit <= 0 and revenue > 0 and operating_margin_from_data is None:
            ebit = revenue * 0.15  # Assume 15% operating margin
            print(f"[ValuationOrchestrator] No margin data - using default 15% EBIT margin")

        if net_income <= 0 and ebit > 0:
            net_income = ebit * 0.75  # Assume 25% tax rate

        # Final safeguards
        revenue = max(revenue, 1)  # At least 1 to prevent division by zero
        shares = max(shares, 1)
        market_cap = max(market_cap, 1)

        # Calculate EBIT margin - use actual margin if available
        if operating_margin_from_data is not None:
            ebit_margin = operating_margin_from_data
        elif revenue > 0 and ebit != 0:
            ebit_margin = ebit / revenue
        else:
            ebit_margin = 0.15  # Default only if no data

        return MarketData(
            ticker=ticker,
            current_price=current_price,
            currency=currency,
            revenue_ttm=revenue,
            ebit_ttm=ebit,
            ebit_margin=ebit_margin,
            net_income=net_income,
            total_debt=total_debt,
            cash=cash,
            net_debt=net_debt,
            shares_outstanding=shares,
            market_cap=market_cap,
            pe_ratio=raw.get('pe_ratio', raw.get('trailing_pe')),
            ev_ebitda=raw.get('ev_ebitda', raw.get('enterprise_to_ebitda')),
            ev_revenue=raw.get('ev_revenue', raw.get('enterprise_to_revenue')),
            price_to_book=raw.get('price_to_book', raw.get('pb_ratio')),
            beta=raw.get('beta', 1.0) or 1.0,
            dividend_per_share=raw.get('dividend_per_share', raw.get('dividend', 0)) or 0,
            dividend_yield=raw.get('dividend_yield', 0) or 0,
            payout_ratio=raw.get('payout_ratio', 0) or 0
        )

    def _prepare_wacc_inputs(
        self,
        raw: Dict[str, Any],
        market_data: MarketData
    ) -> WACCInputs:
        """Prepare WACC calculation inputs"""
        # Determine risk-free rate by region
        ticker = market_data.ticker
        if '_HK' in ticker or '_CH' in ticker:
            rf_rate = 0.035  # China 10Y ~3.5%
            country_premium = 0.015  # China country risk
        else:
            rf_rate = 0.045  # US 10Y ~4.5%
            country_premium = 0.0

        # Get beta
        beta = raw.get('beta', market_data.beta)
        if beta <= 0 or beta > 3:
            beta = 1.0

        # Estimate cost of debt
        cost_of_debt = raw.get('cost_of_debt', 0.05)

        # Estimate debt ratio
        if market_data.total_debt > 0 and market_data.market_cap > 0:
            debt_ratio = market_data.total_debt / (market_data.total_debt + market_data.market_cap)
        else:
            debt_ratio = 0.2

        return WACCInputs(
            risk_free_rate=rf_rate,
            beta=beta,
            equity_risk_premium=0.055,  # Standard ERP
            country_risk_premium=country_premium,
            cost_of_debt=cost_of_debt,
            tax_rate=raw.get('tax_rate', 0.25),
            debt_to_total_capital=min(debt_ratio, 0.5)  # Cap at 50%
        )

    def _prepare_peers(self, peers_raw: list) -> list:
        """Convert raw peer data to PeerData objects"""
        peers = []
        for p in peers_raw:
            peers.append(PeerData(
                ticker=p.get('ticker', ''),
                name=p.get('name', p.get('ticker', '')),
                market_cap=p.get('market_cap', 0),
                pe_ratio=p.get('pe_ratio'),
                ev_ebitda=p.get('ev_ebitda'),
                ev_revenue=p.get('ev_revenue'),
                price_to_book=p.get('price_to_book'),
                revenue_growth=p.get('revenue_growth'),
                ebit_margin=p.get('ebit_margin')
            ))
        return peers

    def _build_output(
        self,
        inputs: ValuationInputs,
        dcf, comps, ddm, reverse_dcf, cross_check, consensus
    ) -> Dict[str, Any]:
        """Build comprehensive output dict"""
        return {
            'ticker': inputs.ticker,
            'company_name': inputs.company_name,
            'current_price': inputs.market_data.current_price,
            'currency': inputs.market_data.currency,

            # Consensus valuation
            'consensus': {
                'fair_value': consensus.consensus_fair_value,
                'fair_value_range': list(consensus.fair_value_range),
                'implied_upside': consensus.implied_upside,
                'recommendation': consensus.recommendation,
                'confidence': consensus.confidence
            },

            # Method breakdown
            'dcf': {
                'probability_weighted_value': dcf.pwv,
                'is_valid': dcf.is_valid,
                'implied_upside': dcf.implied_upside,
                'recommendation': dcf.recommendation,
                'scenarios': {
                    name: {
                        'fair_value': s.fair_value_per_share,
                        'probability': s.probability,
                        'wacc': s.wacc,
                        'cost_of_equity': s.cost_of_equity,
                        'terminal_value_pct': s.terminal_value_pct_of_ev,
                        'enterprise_value': s.enterprise_value,
                        'equity_value': s.equity_value,
                        'terminal_value': s.terminal_value,
                        'pv_terminal_value': s.pv_terminal_value,
                        'pv_fcfs': s.pv_fcfs,
                        'wacc_calculation': s.wacc_calculation,
                        # Detailed inputs used
                        'inputs_used': s.inputs_used if hasattr(s, 'inputs_used') else {},
                        # Yearly projections with all numbers
                        'yearly_projections': [
                            {
                                'year': p.year,
                                'revenue': p.revenue,
                                'revenue_growth': p.revenue_growth,
                                'ebit': p.ebit,
                                'ebit_margin': p.ebit_margin,
                                'nopat': p.nopat,
                                'da': p.da,
                                'capex': p.capex,
                                'wc_change': p.wc_change,
                                'fcf': p.fcf,
                                'discount_factor': p.discount_factor,
                                'pv_fcf': p.pv_fcf
                            }
                            for p in (s.yearly_projections if hasattr(s, 'yearly_projections') else [])
                        ]
                    }
                    for name, s in dcf.scenarios.items()
                },
                'pwv_calculation': dcf.pwv_calculation,
                'warnings': dcf.warnings
            },

            'comps': {
                'weighted_target': comps.weighted_target,
                'is_valid': comps.is_valid,
                'implied_upside': comps.implied_upside,
                'recommendation': comps.recommendation,
                'peers_used': comps.peers_used,
                'median_multiples': {
                    'pe': comps.median_pe,
                    'ev_ebitda': comps.median_ev_ebitda,
                    'ev_revenue': comps.median_ev_revenue,
                    'pb': comps.median_pb
                },
                'implied_values': {
                    'from_pe': comps.implied_from_pe,
                    'from_ev_ebitda': comps.implied_from_ev_ebitda,
                    'from_ev_revenue': comps.implied_from_ev_revenue,
                    'from_pb': comps.implied_from_pb
                },
                'warnings': comps.warnings
            },

            'ddm': {
                'fair_value': ddm.fair_value,
                'is_applicable': ddm.is_applicable,
                'implied_upside': ddm.implied_upside,
                'recommendation': ddm.recommendation,
                'dividend_yield': ddm.dividend_yield,
                'dividend_growth': ddm.dividend_growth_rate,
                'cost_of_equity': ddm.cost_of_equity,
                'calculation': ddm.calculation,
                'warnings': ddm.warnings
            },

            'reverse_dcf': {
                'implied_growth_rate': reverse_dcf.implied_growth_rate,
                'our_base_growth': reverse_dcf.our_base_growth,
                'growth_difference': reverse_dcf.growth_difference,
                'market_view': reverse_dcf.market_view,
                'description': reverse_dcf.implied_growth_description,
                'is_valid': reverse_dcf.is_valid,
                'warnings': reverse_dcf.warnings
            },

            # Cross-check validation
            'cross_check': {
                'convergence_level': cross_check.convergence_level,
                'is_converged': cross_check.is_converged,
                'value_spread': cross_check.value_spread,
                'method_values': cross_check.method_values,
                'median_value': cross_check.median_value,
                'mean_value': cross_check.mean_value,
                'market_alignment': cross_check.market_alignment,
                'market_alignment_pct': cross_check.market_alignment_pct,
                'issues_found': cross_check.issues_found,
                'recommendations': cross_check.recommendations
            },

            # Key insights
            'key_drivers': consensus.key_drivers,
            'key_risks': consensus.key_risks,
            'market_expectations': consensus.market_expectations,

            # Full summary
            'valuation_summary': consensus.valuation_summary,

            # Assumptions used
            'assumptions_used': {
                'scenarios': {
                    name: {
                        'probability': s.probability,
                        'revenue_growth_y1_3': s.revenue_growth_y1_3,
                        'revenue_growth_y4_5': s.revenue_growth_y4_5,
                        'terminal_growth': s.terminal_growth,
                        'target_margin': s.target_ebit_margin,
                        'wacc_adjustment': s.wacc_adjustment,
                        'rationale': s.rationale
                    }
                    for name, s in inputs.scenarios.items()
                },
                'wacc_inputs': {
                    'risk_free_rate': inputs.wacc_inputs.risk_free_rate,
                    'beta': inputs.wacc_inputs.beta,
                    'equity_risk_premium': inputs.wacc_inputs.equity_risk_premium,
                    'country_risk_premium': inputs.wacc_inputs.country_risk_premium,
                    'tax_rate': inputs.wacc_inputs.tax_rate
                }
            }
        }


def run_valuation_node(
    ticker: str,
    context: Dict[str, Any],
    prior_outputs: Dict[str, str],
    use_multi_ai: bool = True
) -> str:
    """
    Entry point for node_executor.py integration.

    Args:
        ticker: Stock ticker
        context: Context data including market_data
        prior_outputs: Dict with outputs from prior nodes
        use_multi_ai: Whether to use multi-AI extraction (default: True)

    Returns:
        JSON string of valuation results
    """
    orchestrator = ValuationOrchestrator(use_multi_ai=use_multi_ai)

    # Extract debate outputs from prior nodes
    debate_outputs = {
        'debate_critic': prior_outputs.get('Debate Critic', ''),
        'bull_r2': prior_outputs.get('Bull Advocate R2', ''),
        'bear_r2': prior_outputs.get('Bear Advocate R2', '')
    }

    # Get market data from context
    market_data = context.get('market_data', {})

    # Get additional outputs for multi-AI extraction
    industry_researcher_output = prior_outputs.get('Industry Deep Dive', '')
    business_model_output = prior_outputs.get('Company Deep Dive', '')
    company_name = context.get('company_name', ticker)

    # CRITICAL: Get Dot Connector output - this is PRIORITIZED for parameters
    # Dot Connector synthesizes parameters from research and may include REVISIONS
    dot_connector_output = prior_outputs.get('Dot Connector', '')
    if dot_connector_output:
        print(f"[run_valuation_node] Found Dot Connector output ({len(dot_connector_output)} chars)")
        # Check if this is a revision (contains REVISED markers)
        if '[REVISED]' in dot_connector_output or 'REVISION REQUESTED' in dot_connector_output:
            print(f"[run_valuation_node] DOT CONNECTOR CONTAINS REVISED PARAMETERS!")

    # Run valuation with multi-AI extraction
    result = orchestrator.run_valuation(
        ticker=ticker,
        debate_outputs=debate_outputs,
        market_data_raw=market_data,
        industry_researcher_output=industry_researcher_output,
        business_model_output=business_model_output,
        company_name=company_name,
        dot_connector_output=dot_connector_output
    )

    return json.dumps(result, indent=2, default=str)
