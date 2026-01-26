"""
Debate System - Orchestrates multi-agent debates for equity research
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_agent import BaseAgent, ResearchContext, AgentMessage
from .analyst_agent import AnalystAgent, BullAgent, BearAgent
from .critic_agent import CriticAgent, SynthesizerAgent
from .ai_providers import AIProviderManager

# Import visualizer bridge for real-time updates
try:
    from visualizer.visualizer_bridge import VisualizerBridge
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False
    VisualizerBridge = None


class DebateSystem:
    """Orchestrates multi-agent debates for thorough equity research"""

    def __init__(self, ai_manager: AIProviderManager, debate_rounds: int = 10, visualizer=None):
        self.ai_manager = ai_manager
        self.debate_rounds = debate_rounds

        # Auto-create visualizer if not provided
        if visualizer is None and VISUALIZER_AVAILABLE:
            self.visualizer = VisualizerBridge("context")
        else:
            self.visualizer = visualizer

        # Initialize agents with DIVERSIFIED AI providers
        # Use get_diversified_providers to ensure balanced distribution
        providers = ai_manager.get_diversified_providers(5)

        # Assign different providers to different agents for diverse perspectives
        # Each agent gets a different provider to avoid over-reliance on any single LLM
        if len(providers) >= 4:
            self.analyst = AnalystAgent(providers[0])      # Primary research
            self.bull = BullAgent(providers[1])            # Optimistic view
            self.bear = BearAgent(providers[2])            # Pessimistic view
            self.critic = CriticAgent(providers[3])        # Critical analysis
            self.synthesizer = SynthesizerAgent(providers[0])  # Synthesis (can reuse analyst's)
        else:
            # Fallback for fewer providers - still distribute as much as possible
            self.analyst = AnalystAgent(providers[0] if providers else None)
            self.bull = BullAgent(providers[1 % len(providers)] if providers else None)
            self.bear = BearAgent(providers[2 % len(providers)] if providers else None)
            self.critic = CriticAgent(providers[-1] if providers else None)  # Use last available
            self.synthesizer = SynthesizerAgent(providers[0] if providers else None)

        # Store manager for dynamic provider rotation in debates
        self._rotate_providers_each_round = True

    async def run_full_research(self, context: ResearchContext,
                                 progress_callback=None) -> ResearchContext:
        """Run complete research process with multi-agent debate"""

        ticker = context.ticker
        company = context.company_name

        # Start visualizer tracking
        if self.visualizer:
            self.visualizer.start_research(ticker, company)

        # Phase 1: Initial Research
        if progress_callback:
            progress_callback(f"Phase 1: Initial research for {ticker}")
        if self.visualizer:
            self.visualizer.update_phase(ticker, 'data_gathering', 10)

        await self._phase1_initial_research(context)

        # Phase 2: Multi-agent debate (10 rounds)
        if progress_callback:
            progress_callback(f"Phase 2: Running {self.debate_rounds} debate rounds")
        if self.visualizer:
            self.visualizer.start_debate(ticker, company)

        await self._phase2_debate(context, progress_callback)

        if self.visualizer:
            self.visualizer.complete_debate(ticker)

        # Phase 3: External research comparison
        if progress_callback:
            progress_callback("Phase 3: Comparing with external research")
        if self.visualizer:
            self.visualizer.update_phase(ticker, 'industry_analysis', 85)

        await self._phase3_external_research(context)

        # Phase 4: Final synthesis
        if progress_callback:
            progress_callback("Phase 4: Final synthesis and valuation")
        if self.visualizer:
            self.visualizer.update_phase(ticker, 'synthesis', 95)

        await self._phase4_synthesis(context)

        # Complete visualizer tracking
        if self.visualizer:
            self.visualizer.complete_research(ticker)

        return context

    async def _phase1_initial_research(self, context: ResearchContext):
        """
        Phase 1: Analyst performs initial research

        Optimized execution order:
        1. Industry + Governance in parallel (independent)
        2. Company analysis (needs industry context)
        3. DCF (needs company analysis)

        This reduces Phase 1 from ~4 serial calls to ~3 serial calls,
        saving approximately 25-30% time on this phase.
        """

        # Step 1: Run industry and governance analysis in PARALLEL
        # These are independent - governance doesn't need industry context
        industry_task = self.analyst.analyze(context, analysis_type="industry")
        governance_task = self.analyst.analyze(context, analysis_type="governance")

        industry_result, governance_result = await asyncio.gather(
            industry_task,
            governance_task
        )

        # Update context with parallel results
        context.industry_analysis = industry_result
        context.governance_analysis = governance_result

        # Log industry analysis
        context.debate_log.append(self.analyst.create_message(
            f"Industry Analysis:\n{industry_result}",
            {"phase": 1, "type": "industry"}
        ))

        # Log governance analysis
        context.debate_log.append(self.analyst.create_message(
            f"Governance Analysis:\n{governance_result}",
            {"phase": 1, "type": "governance"}
        ))

        # Step 2: Company analysis (depends on industry for better context)
        company_result = await self.analyst.analyze(context, analysis_type="company")
        context.company_analysis = company_result
        context.debate_log.append(self.analyst.create_message(
            f"Company Analysis:\n{company_result}",
            {"phase": 1, "type": "company"}
        ))

        # Step 3: Initial DCF (depends on company analysis)
        dcf_result = await self.analyst.analyze(context, analysis_type="dcf")
        context.debate_log.append(self.analyst.create_message(
            f"Initial DCF Valuation:\n{dcf_result}",
            {"phase": 1, "type": "dcf"}
        ))

    async def _phase2_debate(self, context: ResearchContext, progress_callback=None):
        """Phase 2: Multi-agent debate with ROTATING providers for diversity"""

        ticker = context.ticker

        for round_num in range(1, self.debate_rounds + 1):
            if progress_callback:
                progress_callback(f"  Debate round {round_num}/{self.debate_rounds}")

            # Update visualizer with debate round progress
            if self.visualizer:
                self.visualizer.update_debate_round(ticker, round_num, self.debate_rounds)

            # ROTATE PROVIDERS each round to ensure diversity
            # This prevents any single LLM from dominating the debate
            if self._rotate_providers_each_round and len(self.ai_manager.providers) >= 3:
                providers = self.ai_manager.get_diversified_providers(4)
                # Rotate based on round number for variety
                offset = (round_num - 1) % len(providers)
                self.bull.provider = providers[(0 + offset) % len(providers)]
                self.bear.provider = providers[(1 + offset) % len(providers)]
                self.critic.provider = providers[(2 + offset) % len(providers)]

            # Get the latest analyst/synthesizer view
            latest_view = self._get_latest_view(context)

            # Run bull and bear challenges in parallel
            bull_task = self.bull.analyze(context, analyst_view=latest_view)
            bear_task = self.bear.analyze(context, analyst_view=latest_view)

            bull_result, bear_result = await asyncio.gather(bull_task, bear_task)

            # Include provider info in metadata for tracking
            context.debate_log.append(self.bull.create_message(
                bull_result, {"round": round_num, "provider": self.bull.provider.name if self.bull.provider else "N/A"}
            ))
            context.debate_log.append(self.bear.create_message(
                bear_result, {"round": round_num, "provider": self.bear.provider.name if self.bear.provider else "N/A"}
            ))

            # Critic evaluates the debate
            combined_view = f"Bull Case:\n{bull_result}\n\nBear Case:\n{bear_result}"
            critic_result = await self.critic.analyze(
                context,
                analysis=combined_view,
                focus="assumptions"
            )
            context.debate_log.append(self.critic.create_message(
                critic_result, {"round": round_num}
            ))

            # Every 3 rounds, synthesizer provides interim summary
            if round_num % 3 == 0:
                interim_synthesis = await self.synthesizer.analyze(context)
                context.debate_log.append(self.synthesizer.create_message(
                    f"Interim Synthesis (Round {round_num}):\n{interim_synthesis}",
                    {"round": round_num, "type": "interim"}
                ))

    async def _phase3_external_research(self, context: ResearchContext):
        """Phase 3: Compare with external research sources"""

        prompt = f"""For {context.company_name} ({context.ticker}), search for and analyze:

1. Recent analyst reports and their price targets
2. Key research from major investment banks
3. Industry reports and market analysis
4. News and recent developments

Compare these external views with our analysis:
{self._get_latest_view(context)[:2000]}

Identify:
- Key differences in assumptions
- Different methodologies used
- Unique insights from external sources
- How our view should be adjusted based on external research"""

        external_result = await self.analyst.respond(prompt)
        context.debate_log.append(self.analyst.create_message(
            f"External Research Comparison:\n{external_result}",
            {"phase": 3, "type": "external"}
        ))

    async def _phase4_synthesis(self, context: ResearchContext):
        """Phase 4: Final synthesis and valuation table"""

        # First, create a condensed summary of the debate to reduce tokens
        debate_summary = await self._summarize_debate(context)
        context.debate_summary = debate_summary

        # Final synthesis using the condensed summary
        final_synthesis = await self.synthesizer.analyze(context, use_summary=True)
        context.debate_log.append(self.synthesizer.create_message(
            f"Final Synthesis:\n{final_synthesis}",
            {"phase": 4, "type": "final"}
        ))

        # Generate final valuation table
        final_table = await self.synthesizer.create_final_table(context)
        context.scenario_analysis = final_table

        # Extract intrinsic values
        if "intrinsic_values" in final_table:
            context.intrinsic_values = final_table["intrinsic_values"]

    async def _summarize_debate(self, context: ResearchContext) -> str:
        """Summarize the debate log to reduce tokens for final synthesis"""

        # Collect key points from each round
        bull_points = []
        bear_points = []
        critic_points = []

        for msg in context.debate_log:
            if msg.role == "bull" and len(bull_points) < 3:
                # Extract first 500 chars of key bull arguments
                bull_points.append(msg.content[:500])
            elif msg.role == "bear" and len(bear_points) < 3:
                bear_points.append(msg.content[:500])
            elif msg.role == "critic" and len(critic_points) < 2:
                critic_points.append(msg.content[:400])

        summary = f"""
DEBATE SUMMARY for {context.ticker}:

KEY BULL ARGUMENTS:
{chr(10).join(f'- {p[:300]}...' for p in bull_points[:2])}

KEY BEAR ARGUMENTS:
{chr(10).join(f'- {p[:300]}...' for p in bear_points[:2])}

CRITIC OBSERVATIONS:
{chr(10).join(f'- {p[:250]}...' for p in critic_points[:2])}

INITIAL ANALYSIS SUMMARY:
- Industry: {context.industry_analysis[:400] if context.industry_analysis else 'N/A'}...
- Company: {context.company_analysis[:400] if context.company_analysis else 'N/A'}...
- Governance: {context.governance_analysis[:300] if context.governance_analysis else 'N/A'}...
"""
        return summary

    def _get_latest_view(self, context: ResearchContext) -> str:
        """Get the most recent comprehensive view from debate log"""
        # Look for the latest synthesizer or analyst message
        for msg in reversed(context.debate_log):
            if msg.role in ["synthesizer", "analyst"]:
                return msg.content

        # Fallback to combined initial analysis
        return f"""
Industry: {context.industry_analysis[:1000]}
Company: {context.company_analysis[:1000]}
Governance: {context.governance_analysis[:500]}
"""


class ParallelDebateRunner:
    """Runs debates for multiple equities in parallel"""

    def __init__(self, ai_manager: AIProviderManager, max_concurrent: int = 3):
        self.ai_manager = ai_manager
        self.max_concurrent = max_concurrent

    async def run_all(self, equities: Dict[str, Dict[str, str]],
                      progress_callback=None) -> Dict[str, ResearchContext]:
        """Run research for all equities with controlled concurrency"""

        results = {}
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def research_with_semaphore(ticker: str, info: Dict[str, str]):
            async with semaphore:
                context = ResearchContext(
                    ticker=ticker,
                    company_name=info["name"],
                    sector=info["sector"],
                    industry=info["industry"]
                )

                debate_system = DebateSystem(self.ai_manager)

                def callback(msg):
                    if progress_callback:
                        progress_callback(f"[{ticker}] {msg}")

                return await debate_system.run_full_research(context, callback)

        # Create tasks for all equities
        tasks = [
            research_with_semaphore(ticker, info)
            for ticker, info in equities.items()
        ]

        # Run all with gather
        contexts = await asyncio.gather(*tasks, return_exceptions=True)

        # Map results
        for (ticker, _), ctx in zip(equities.items(), contexts):
            if isinstance(ctx, Exception):
                print(f"Error researching {ticker}: {ctx}")
            else:
                results[ticker] = ctx

        return results
