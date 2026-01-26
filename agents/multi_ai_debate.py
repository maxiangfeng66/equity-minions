"""
Multi-AI Debate System
5 AI providers (GPT, Gemini, Grok, Qwen, Claude) debate and challenge each other
on equity valuations to produce rigorous, stress-tested investment theses.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Import AI providers
from agents.ai_providers import AIProviderManager

class DebateRole(Enum):
    ANALYST = "analyst"      # Primary research and valuation
    BULL = "bull"            # Optimistic case advocate
    BEAR = "bear"            # Pessimistic case advocate
    CRITIC = "critic"        # Challenges all assumptions
    SYNTHESIZER = "synthesizer"  # Reconciles views into final thesis

@dataclass
class DebateMessage:
    """Single message in a debate round"""
    round_num: int
    role: str
    ai_provider: str
    content: str
    timestamp: str
    challenges: List[str] = None

    def to_dict(self):
        return asdict(self)

@dataclass
class DebateRound:
    """One complete round of debate"""
    round_num: int
    messages: List[DebateMessage]
    key_disagreements: List[str]
    consensus_points: List[str]

    def to_dict(self):
        return {
            "round_num": self.round_num,
            "messages": [m.to_dict() for m in self.messages],
            "key_disagreements": self.key_disagreements,
            "consensus_points": self.consensus_points
        }

@dataclass
class DebateResult:
    """Final output from multi-AI debate"""
    ticker: str
    company: str
    sector: str
    debate_rounds: List[DebateRound]
    final_thesis: Dict[str, Any]
    valuation_range: Dict[str, float]
    probability_weighted_price: float
    confidence_level: str
    key_risks: List[str]
    key_catalysts: List[str]
    ai_consensus: Dict[str, str]
    timestamp: str

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "company": self.company,
            "sector": self.sector,
            "debate_rounds": [r.to_dict() for r in self.debate_rounds],
            "final_thesis": self.final_thesis,
            "valuation_range": self.valuation_range,
            "probability_weighted_price": self.probability_weighted_price,
            "confidence_level": self.confidence_level,
            "key_risks": self.key_risks,
            "key_catalysts": self.key_catalysts,
            "ai_consensus": self.ai_consensus,
            "timestamp": self.timestamp
        }


class MultiAIDebateOrchestrator:
    """
    Orchestrates debates between multiple AI providers.
    Each AI takes on different roles and challenges others' assumptions.
    """

    def __init__(self, api_keys: Dict[str, str], num_rounds: int = 10):
        self.provider_manager = AIProviderManager(api_keys)
        self.num_rounds = num_rounds
        self.debate_log: List[DebateRound] = []

    def _get_role_system_prompt(self, role: DebateRole, equity_context: str) -> str:
        """Generate system prompt for each debate role"""

        base_context = f"""You are participating in a rigorous multi-AI equity research debate.

EQUITY CONTEXT:
{equity_context}

Your responses should be:
- Data-driven and specific
- Challenging of weak assumptions
- Quantitative where possible
- Honest about uncertainties
"""

        role_prompts = {
            DebateRole.ANALYST: base_context + """
YOUR ROLE: PRIMARY ANALYST
- Provide comprehensive fundamental analysis
- Build DCF valuation models with clear assumptions
- Identify key value drivers and risks
- Present balanced view but take a position
- Defend your valuation against challenges""",

            DebateRole.BULL: base_context + """
YOUR ROLE: BULL ADVOCATE
- Argue for the optimistic case
- Identify upside catalysts others may miss
- Challenge pessimistic assumptions
- Quantify potential upside scenarios
- Be aggressive but grounded in facts""",

            DebateRole.BEAR: base_context + """
YOUR ROLE: BEAR ADVOCATE
- Argue for the pessimistic case
- Identify risks others may underestimate
- Challenge optimistic assumptions
- Quantify potential downside scenarios
- Be skeptical but fair""",

            DebateRole.CRITIC: base_context + """
YOUR ROLE: CRITICAL EXAMINER
- Challenge ALL assumptions from every side
- Ask probing questions
- Identify logical inconsistencies
- Demand evidence for claims
- Stress-test valuation models
- Point out what could go wrong with any thesis""",

            DebateRole.SYNTHESIZER: base_context + """
YOUR ROLE: SYNTHESIZER
- Reconcile different viewpoints
- Identify where the truth likely lies
- Assign probability weights to scenarios
- Produce final probability-weighted valuation
- Summarize key agreements and disagreements
- Provide actionable investment recommendation"""
        }

        return role_prompts[role]

    async def _get_ai_response(self, provider_name: str, role: DebateRole,
                                prompt: str, equity_context: str) -> Optional[str]:
        """Get response from specific AI provider with role"""
        provider = self.provider_manager.get_provider(provider_name)
        if not provider:
            return None

        system_prompt = self._get_role_system_prompt(role, equity_context)

        try:
            response = await provider.generate(prompt, system_prompt)
            return response
        except Exception as e:
            print(f"Error from {provider_name}: {e}")
            return None

    async def run_debate_round(self, round_num: int, equity_data: Dict,
                               previous_messages: List[DebateMessage]) -> DebateRound:
        """Run a single round of debate across all AIs"""

        # Reduced context size to avoid token limits (30K TPM for OpenAI)
        equity_context = f"""
Ticker: {equity_data.get('ticker')}
Company: {equity_data.get('company')}
Sector: {equity_data.get('sector')}
Research Summary: {json.dumps(equity_data.get('executive_summary', ''), indent=2)[:800]}
Key Financials: {json.dumps(equity_data.get('financial_data', {}), indent=2)[:400]}
"""

        # Build context from previous messages (reduced from 10 to 5, 500 to 300 chars)
        prev_context = ""
        if previous_messages:
            prev_context = "\n\nPREVIOUS DEBATE:\n"
            for msg in previous_messages[-5:]:  # Last 5 messages only
                prev_context += f"\n[{msg.ai_provider}/{msg.role}]: {msg.content[:300]}...\n"

        messages = []

        # Assign roles to different AIs for this round using BALANCED distribution
        # Use get_diversified_providers to ensure no single LLM dominates
        providers = self.provider_manager.get_diversified_providers(4)
        provider_names = [p.name for p in providers]

        # Role assignments - each role gets a DIFFERENT provider
        # Shuffle based on round to ensure variety across rounds
        if len(provider_names) >= 4:
            # Full diversity: each role gets unique provider
            offset = (round_num - 1) % len(provider_names)
            role_assignments = {
                DebateRole.ANALYST: provider_names[(0 + offset) % len(provider_names)],
                DebateRole.BULL: provider_names[(1 + offset) % len(provider_names)],
                DebateRole.BEAR: provider_names[(2 + offset) % len(provider_names)],
                DebateRole.CRITIC: provider_names[(3 + offset) % len(provider_names)],
            }
        else:
            # Fallback for fewer providers - still rotate
            role_assignments = {
                DebateRole.ANALYST: provider_names[round_num % len(provider_names)] if provider_names else "GPT",
                DebateRole.BULL: provider_names[(round_num + 1) % len(provider_names)] if provider_names else "Gemini",
                DebateRole.BEAR: provider_names[(round_num + 2) % len(provider_names)] if provider_names else "Grok",
                DebateRole.CRITIC: provider_names[(round_num + 3) % len(provider_names)] if provider_names else "Qwen",
            }

        # Phase-specific prompts
        if round_num <= 3:
            phase = "INITIAL POSITIONS"
            phase_instruction = "Establish your initial position with clear arguments and evidence."
        elif round_num <= 6:
            phase = "CROSS-EXAMINATION"
            phase_instruction = "Challenge the positions taken by others. Point out weaknesses in their arguments."
        elif round_num <= 9:
            phase = "REFINEMENT"
            phase_instruction = "Refine your position based on valid critiques. Acknowledge good points from others."
        else:
            phase = "FINAL SYNTHESIS"
            phase_instruction = "Provide your final view incorporating all debate insights."

        # Get responses from each AI in their roles (in parallel)
        tasks = []
        role_provider_pairs = []

        for role, provider_name in role_assignments.items():
            prompt = f"""
DEBATE ROUND {round_num}/10 - PHASE: {phase}

{phase_instruction}

{prev_context}

As the {role.value.upper()}, provide your analysis and arguments.
Be specific, quantitative, and challenge weak assumptions.
"""
            tasks.append(self._get_ai_response(provider_name, role, prompt, equity_context))
            role_provider_pairs.append((role, provider_name))

        # Run all AI calls in parallel
        responses = await asyncio.gather(*tasks)

        # Collect messages
        for (role, provider_name), response in zip(role_provider_pairs, responses):
            if response:
                messages.append(DebateMessage(
                    round_num=round_num,
                    role=role.value,
                    ai_provider=provider_name,
                    content=response,
                    timestamp=datetime.now().isoformat(),
                    challenges=[]
                ))

        # Identify disagreements and consensus
        disagreements = self._extract_disagreements(messages)
        consensus = self._extract_consensus(messages)

        return DebateRound(
            round_num=round_num,
            messages=messages,
            key_disagreements=disagreements,
            consensus_points=consensus
        )

    def _extract_disagreements(self, messages: List[DebateMessage]) -> List[str]:
        """Extract key points of disagreement from messages"""
        # Simple extraction - in production would use NLP
        disagreements = []
        for msg in messages:
            if any(word in msg.content.lower() for word in ['disagree', 'however', 'but', 'challenge', 'incorrect', 'overestimate', 'underestimate']):
                # Extract first sentence after disagreement indicator
                sentences = msg.content.split('.')
                for i, sent in enumerate(sentences):
                    if any(word in sent.lower() for word in ['disagree', 'challenge', 'incorrect']):
                        if i + 1 < len(sentences):
                            disagreements.append(f"{msg.ai_provider} ({msg.role}): {sentences[i+1].strip()[:200]}")
                        break
        return disagreements[:5]  # Top 5 disagreements

    def _extract_consensus(self, messages: List[DebateMessage]) -> List[str]:
        """Extract points of consensus from messages"""
        consensus = []
        for msg in messages:
            if any(word in msg.content.lower() for word in ['agree', 'consensus', 'clearly', 'undoubtedly', 'certainly']):
                sentences = msg.content.split('.')
                for sent in sentences:
                    if any(word in sent.lower() for word in ['agree', 'consensus', 'clearly']):
                        consensus.append(f"{msg.ai_provider}: {sent.strip()[:200]}")
                        break
        return consensus[:5]

    async def run_full_debate(self, equity_data: Dict, progress_callback=None) -> DebateResult:
        """Run complete multi-round debate for one equity

        Args:
            equity_data: Dict with ticker, company, research data
            progress_callback: Optional callback(round_num, total_rounds, ticker) for progress updates
        """

        ticker = equity_data.get('ticker', '')
        print(f"\n{'='*60}")
        print(f"Starting Multi-AI Debate: {ticker} - {equity_data.get('company')}")
        print(f"{'='*60}")

        all_messages = []
        debate_rounds = []

        for round_num in range(1, self.num_rounds + 1):
            print(f"  Round {round_num}/{self.num_rounds}...")

            # Call progress callback for visualizer updates
            if progress_callback:
                progress_callback(round_num, self.num_rounds, ticker)

            round_result = await self.run_debate_round(round_num, equity_data, all_messages)
            debate_rounds.append(round_result)
            all_messages.extend(round_result.messages)

            # Brief pause to avoid rate limiting
            await asyncio.sleep(1)

        # Final synthesis
        final_thesis = await self._generate_final_synthesis(equity_data, debate_rounds)

        result = DebateResult(
            ticker=equity_data.get('ticker', ''),
            company=equity_data.get('company', ''),
            sector=equity_data.get('sector', ''),
            debate_rounds=debate_rounds,
            final_thesis=final_thesis,
            valuation_range=final_thesis.get('valuation_range', {}),
            probability_weighted_price=final_thesis.get('probability_weighted_price', 0),
            confidence_level=final_thesis.get('confidence_level', 'Medium'),
            key_risks=final_thesis.get('key_risks', []),
            key_catalysts=final_thesis.get('key_catalysts', []),
            ai_consensus=final_thesis.get('ai_consensus', {}),
            timestamp=datetime.now().isoformat()
        )

        print(f"  Debate complete. Probability-weighted price: {result.probability_weighted_price}")

        # Print provider usage stats to show distribution
        stats = self.provider_manager.get_usage_stats()
        if stats["total_requests"] > 0:
            print(f"\n  Provider Usage Distribution:")
            for name, data in stats["providers"].items():
                print(f"    {name}: {data['actual_pct']}% (target: {data['target_pct']}%, {data['requests']} calls)")

        return result

    async def _generate_final_synthesis(self, equity_data: Dict,
                                        debate_rounds: List[DebateRound]) -> Dict[str, Any]:
        """Generate final synthesis from all debate rounds"""

        # Collect all key points
        all_disagreements = []
        all_consensus = []
        for round_obj in debate_rounds:
            all_disagreements.extend(round_obj.key_disagreements)
            all_consensus.extend(round_obj.consensus_points)

        # Get synthesis from first available provider
        providers = self.provider_manager.get_all_providers()
        if not providers:
            return self._default_synthesis(equity_data)

        # Reduced prompt size to avoid token limits
        synthesis_prompt = f"""
Debate for {equity_data.get('ticker')} - {equity_data.get('company')}:

DISAGREEMENTS:
{json.dumps(all_disagreements[:5], indent=2)}

CONSENSUS:
{json.dumps(all_consensus[:5], indent=2)}

RESEARCH:
{json.dumps(equity_data.get('executive_summary', ''), indent=2)[:600]}

Provide investment synthesis in JSON:
{{
    "recommendation": "BUY/HOLD/SELL",
    "conviction": "HIGH/MEDIUM/LOW",
    "valuation_range": {{
        "bear_case": <number>,
        "base_case": <number>,
        "bull_case": <number>
    }},
    "probability_weighted_price": <number>,
    "confidence_level": "High/Medium/Low",
    "key_risks": ["risk1", "risk2", "risk3"],
    "key_catalysts": ["catalyst1", "catalyst2", "catalyst3"],
    "ai_consensus": {{
        "agreed": "Points all AIs agreed on",
        "disputed": "Points still disputed"
    }},
    "investment_thesis": "2-3 sentence summary"
}}

Return ONLY valid JSON.
"""

        try:
            response = await providers[0].generate(synthesis_prompt,
                "You are a senior investment analyst synthesizing a multi-AI debate into a final investment recommendation.")

            # Try to parse JSON from response
            # Handle case where response might have markdown code blocks
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            return json.loads(json_str)
        except Exception as e:
            print(f"Error generating synthesis: {e}")
            return self._default_synthesis(equity_data)

    def _default_synthesis(self, equity_data: Dict) -> Dict[str, Any]:
        """Default synthesis if AI synthesis fails"""
        return {
            "recommendation": "HOLD",
            "conviction": "LOW",
            "valuation_range": {
                "bear_case": 0,
                "base_case": 0,
                "bull_case": 0
            },
            "probability_weighted_price": equity_data.get('probability_weighted_price', 0),
            "confidence_level": "Low",
            "key_risks": equity_data.get('risks', [])[:3] if isinstance(equity_data.get('risks'), list) else [],
            "key_catalysts": [],
            "ai_consensus": {"agreed": "Insufficient data", "disputed": "N/A"},
            "investment_thesis": "Insufficient debate data for strong thesis."
        }


async def run_debates_for_all_equities(context_dir: str, api_keys: Dict[str, str],
                                       output_dir: str, num_rounds: int = 10):
    """Run debates for all equities with research data"""

    orchestrator = MultiAIDebateOrchestrator(api_keys, num_rounds)

    # Find all research JSON files
    research_files = [f for f in os.listdir(context_dir) if f.endswith('.json') and f != 'session_state.json']

    results = []

    for research_file in research_files:
        filepath = os.path.join(context_dir, research_file)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                equity_data = json.load(f)

            # Run debate
            debate_result = await orchestrator.run_full_debate(equity_data)

            # Save debate result
            output_file = os.path.join(output_dir, f"debate_{research_file}")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(debate_result.to_dict(), f, indent=2, ensure_ascii=False)

            results.append(debate_result)

        except Exception as e:
            print(f"Error processing {research_file}: {e}")
            continue

    return results


if __name__ == "__main__":
    # Test run
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import API_KEYS

    async def main():
        context_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "context")
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "context", "debates")
        os.makedirs(output_dir, exist_ok=True)

        results = await run_debates_for_all_equities(context_dir, API_KEYS, output_dir, num_rounds=5)
        print(f"\nCompleted {len(results)} debates")

    asyncio.run(main())
