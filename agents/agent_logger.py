"""
Agent Logger - Comprehensive logging for agent lifecycle and AI provider usage

Creates detailed logs for each research run including:
- Agent creation/termination events
- Tier-based hierarchy visualization
- AI provider (OpenAI, Grok, Qwen, Gemini, Claude, DeepSeek) usage statistics
- Agent spawn chains and parent-child relationships
- Detailed API calling methods for each provider

USAGE:
    from agents.agent_logger import get_logger, log_spawn, log_ai_call

    # Start session
    logger = get_logger()
    logger.start_session("Research Run")

    # Log agent creation
    log_spawn("agent_001", "AnalystAgent", tier=2, provider="openai")

    # Log AI API calls
    log_ai_call("openai", "gpt-4o", "agent_001", "AnalystAgent", "analysis", 500, 1000)

    # End and save
    logger.end_session()
    logger.save_log()
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from pathlib import Path


# ==============================================================================
# AI PROVIDER DETAILS - HOW EACH PROVIDER IS CALLED
# ==============================================================================
AI_PROVIDER_DETAILS = {
    "openai": {
        "display_name": "OpenAI (GPT)",
        "model": "gpt-4o",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "rate_limit": "28,000 TPM (Tokens Per Minute)",
        "env_key": "OPENAI_API_KEY",
        "call_method": {
            "type": "POST",
            "auth": "Authorization: Bearer {API_KEY}",
            "payload_format": "OpenAI Chat Completions format",
            "example": {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "..."},
                    {"role": "user", "content": "..."}
                ],
                "temperature": 0.7,
                "max_tokens": 4096
            }
        },
        "source_file": "agents/ai_providers.py:180-229"
    },
    "gemini": {
        "display_name": "Google (Gemini)",
        "model": "gemini-2.0-flash",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "rate_limit": "15 RPM (Requests Per Minute) - Free Tier",
        "env_key": "GOOGLE_API_KEY",
        "call_method": {
            "type": "POST",
            "auth": "Query parameter: ?key={API_KEY}",
            "payload_format": "Gemini GenerateContent format",
            "example": {
                "contents": [{"parts": [{"text": "..."}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 4096
                }
            }
        },
        "source_file": "agents/ai_providers.py:232-273"
    },
    "grok": {
        "display_name": "xAI (Grok)",
        "model": "grok-3",
        "endpoint": "https://api.x.ai/v1/chat/completions",
        "rate_limit": "100,000 TPM (Tokens Per Minute)",
        "env_key": "XAI_API_KEY",
        "call_method": {
            "type": "POST",
            "auth": "Authorization: Bearer {API_KEY}",
            "payload_format": "OpenAI-compatible Chat Completions format",
            "example": {
                "model": "grok-3",
                "messages": [
                    {"role": "system", "content": "..."},
                    {"role": "user", "content": "..."}
                ],
                "temperature": 0.7,
                "max_tokens": 4096
            }
        },
        "source_file": "agents/ai_providers.py:276-321"
    },
    "qwen": {
        "display_name": "Alibaba (Qwen)",
        "model": "qwen-turbo",
        "endpoint": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        "rate_limit": "Standard (international endpoint)",
        "env_key": "DASHSCOPE_API_KEY",
        "call_method": {
            "type": "POST",
            "auth": "Authorization: Bearer {API_KEY}",
            "payload_format": "OpenAI-compatible Chat Completions format",
            "example": {
                "model": "qwen-turbo",
                "messages": [
                    {"role": "system", "content": "..."},
                    {"role": "user", "content": "..."}
                ],
                "temperature": 0.7,
                "max_tokens": 4096
            }
        },
        "source_file": "agents/ai_providers.py:364-406"
    },
    "claude": {
        "display_name": "Anthropic (Claude)",
        "model": "claude-3-opus / claude-3-sonnet",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "rate_limit": "Varies by tier",
        "env_key": "ANTHROPIC_API_KEY",
        "call_method": {
            "type": "POST",
            "auth": "x-api-key: {API_KEY}, anthropic-version: 2023-06-01",
            "payload_format": "Anthropic Messages API format",
            "example": {
                "model": "claude-3-opus-20240229",
                "max_tokens": 4096,
                "messages": [
                    {"role": "user", "content": "..."}
                ]
            }
        },
        "source_file": "N/A - Reserved for future integration"
    }
}


# ==============================================================================
# AGENT TIER DEFINITIONS
# ==============================================================================
AGENT_TIER_INFO = {
    0: {
        "name": "Architect",
        "description": "Strategic Planning Layer",
        "responsibilities": [
            "System-wide strategy coordination",
            "Research pool creation",
            "Quality threshold management",
            "Resource allocation"
        ],
        "agents": ["ChiefArchitectAgent", "PriorityManager", "ResourceAllocator"],
        "source_files": ["agents/architects/chief_architect.py", "agents/architects/priority_manager.py"]
    },
    1: {
        "name": "Supervisor",
        "description": "Orchestration Layer",
        "responsibilities": [
            "Research lifecycle management",
            "Worker agent spawning",
            "Debate orchestration",
            "Quality coordination"
        ],
        "agents": ["ResearchSupervisor", "DebateModerator"],
        "source_files": ["agents/supervisors/research_supervisor.py", "agents/supervisors/debate_moderator.py"]
    },
    2: {
        "name": "Worker",
        "description": "Execution Layer",
        "responsibilities": [
            "Research analysis execution",
            "Bull/Bear debate arguments",
            "Critical analysis",
            "Synthesis of findings",
            "Domain specialization"
        ],
        "agents": [
            "AnalystAgent", "BullAgent", "BearAgent", "CriticAgent", "SynthesizerAgent",
            "EnhancedAnalystAgent", "EnhancedBullAgent", "EnhancedBearAgent",
            "EnhancedCriticAgent", "EnhancedSynthesizerAgent",
            "SpecialistAgent", "DevilsAdvocateAgent"
        ],
        "source_files": [
            "agents/analyst_agent.py", "agents/workers/enhanced_workers.py",
            "agents/workers/specialist.py", "agents/workers/devils_advocate.py"
        ]
    },
    3: {
        "name": "Goalkeeper",
        "description": "Quality Gate Layer",
        "responsibilities": [
            "Final publication approval",
            "Logical consistency validation",
            "Fact-checking",
            "Consensus verification",
            "Due diligence for high-conviction calls"
        ],
        "agents": [
            "PublishGatekeeperAgent", "LogicAuditorAgent",
            "FactCheckerAgent", "ConsensusValidatorAgent", "DueDiligenceAgent"
        ],
        "source_files": [
            "agents/goalkeepers/publish_gatekeeper.py",
            "agents/goalkeepers/logic_auditor.py",
            "agents/goalkeepers/fact_checker_gate.py"
        ]
    }
}


@dataclass
class AgentEvent:
    """Single agent lifecycle event"""
    timestamp: str
    event_type: str  # 'spawn', 'terminate', 'activate', 'deactivate', 'task_start', 'task_complete'
    agent_id: str
    agent_role: str
    tier: int
    parent_id: Optional[str]
    ai_provider: Optional[str]
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIProviderCall:
    """Single AI provider API call"""
    timestamp: str
    provider: str  # 'openai', 'gemini', 'grok', 'qwen', 'claude'
    model: str
    agent_id: str
    agent_role: str
    call_type: str  # 'analysis', 'debate', 'synthesis', 'validation'
    tokens_in: int
    tokens_out: int
    success: bool
    error: Optional[str] = None


class AgentLogger:
    """
    Singleton logger for tracking all agent activity across a research session.

    Usage:
        logger = AgentLogger.get_instance()
        logger.start_session("Full research run")

        # In agents:
        logger.log_agent_spawn(agent_id, role, tier, parent_id, provider)
        logger.log_ai_call(provider, model, agent_id, role, call_type, tokens_in, tokens_out)

        # At end:
        logger.end_session()
        logger.save_log()
    """

    _instance = None

    # AI Provider name mappings (multiple aliases for flexibility)
    PROVIDER_NAMES = {
        'openai': 'OpenAI (GPT-4)',
        'gpt': 'OpenAI (GPT-4)',
        'google': 'Google (Gemini)',
        'gemini': 'Google (Gemini)',
        'xai': 'xAI (Grok)',
        'grok': 'xAI (Grok)',
        'dashscope': 'Alibaba (Qwen)',
        'qwen': 'Alibaba (Qwen)',
        'anthropic': 'Anthropic (Claude)',
        'claude': 'Anthropic (Claude)'
    }

    # Provider key normalization
    PROVIDER_KEY_MAP = {
        'openai': 'openai', 'gpt': 'openai',
        'google': 'gemini', 'gemini': 'gemini',
        'xai': 'grok', 'grok': 'grok',
        'dashscope': 'qwen', 'qwen': 'qwen',
        'anthropic': 'claude', 'claude': 'claude'
    }

    # Tier names
    TIER_NAMES = {
        0: 'Architect (Strategy)',
        1: 'Supervisor (Oversight)',
        2: 'Worker (Execution)',
        3: 'Goalkeeper (Quality)'
    }

    # Reference to global provider details
    PROVIDER_DETAILS = AI_PROVIDER_DETAILS
    TIER_INFO = AGENT_TIER_INFO

    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = AgentLogger()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)"""
        cls._instance = None

    def __init__(self):
        self.log_dir = Path("agents/logs")
        self.log_dir.mkdir(exist_ok=True)

        # Session info
        self.session_id: str = None
        self.session_name: str = None
        self.session_start: datetime = None
        self.session_end: datetime = None

        # Event tracking
        self.agent_events: List[AgentEvent] = []
        self.ai_calls: List[AIProviderCall] = []

        # Live statistics
        self.active_agents: Dict[str, Dict] = {}  # agent_id -> info
        self.agent_counts_by_tier: Dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}
        self.agent_counts_by_role: Dict[str, int] = {}
        self.total_spawned: int = 0
        self.total_terminated: int = 0

        # AI provider stats
        self.provider_call_counts: Dict[str, int] = {}
        self.provider_token_usage: Dict[str, Dict[str, int]] = {}  # provider -> {in, out}
        self.provider_errors: Dict[str, int] = {}

    def start_session(self, name: str = "Research Session"):
        """Start a new logging session"""
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_name = name
        self.session_start = datetime.now()

        # Reset statistics
        self.agent_events = []
        self.ai_calls = []
        self.active_agents = {}
        self.agent_counts_by_tier = {0: 0, 1: 0, 2: 0, 3: 0}
        self.agent_counts_by_role = {}
        self.total_spawned = 0
        self.total_terminated = 0
        self.provider_call_counts = {}
        self.provider_token_usage = {}
        self.provider_errors = {}

        print(f"\n[AgentLogger] Session started: {self.session_id}")
        print(f"[AgentLogger] Log will be saved to: {self.log_dir / f'session_{self.session_id}.json'}")

    def end_session(self):
        """End the current session"""
        self.session_end = datetime.now()
        print(f"\n[AgentLogger] Session ended. Duration: {self.session_end - self.session_start}")

    # ==========================================
    # Agent Lifecycle Logging
    # ==========================================

    def log_agent_spawn(
        self,
        agent_id: str,
        role: str,
        tier: int,
        parent_id: Optional[str] = None,
        ai_provider: Optional[str] = None,
        config: Dict = None
    ):
        """Log agent spawn event"""
        event = AgentEvent(
            timestamp=datetime.now().isoformat(),
            event_type='spawn',
            agent_id=agent_id,
            agent_role=role,
            tier=tier,
            parent_id=parent_id,
            ai_provider=ai_provider,
            details={
                'config': config or {},
                'provider_name': self.PROVIDER_NAMES.get(ai_provider, ai_provider)
            }
        )
        self.agent_events.append(event)

        # Update stats
        self.active_agents[agent_id] = {
            'role': role,
            'tier': tier,
            'parent_id': parent_id,
            'provider': ai_provider,
            'spawned_at': event.timestamp
        }
        self.agent_counts_by_tier[tier] = self.agent_counts_by_tier.get(tier, 0) + 1
        self.agent_counts_by_role[role] = self.agent_counts_by_role.get(role, 0) + 1
        self.total_spawned += 1

        tier_name = self.TIER_NAMES.get(tier, f'Tier {tier}')
        provider_name = self.PROVIDER_NAMES.get(ai_provider, ai_provider or 'None')
        parent_info = f" (parent: {parent_id})" if parent_id else " (root)"
        print(f"[AgentLogger] SPAWN: {role} [{tier_name}] using {provider_name}{parent_info}")

    def log_agent_terminate(
        self,
        agent_id: str,
        reason: str = "normal"
    ):
        """Log agent termination event"""
        agent_info = self.active_agents.get(agent_id, {})

        event = AgentEvent(
            timestamp=datetime.now().isoformat(),
            event_type='terminate',
            agent_id=agent_id,
            agent_role=agent_info.get('role', 'unknown'),
            tier=agent_info.get('tier', -1),
            parent_id=agent_info.get('parent_id'),
            ai_provider=agent_info.get('provider'),
            details={'reason': reason}
        )
        self.agent_events.append(event)

        # Update stats
        if agent_id in self.active_agents:
            del self.active_agents[agent_id]
        self.total_terminated += 1

        print(f"[AgentLogger] TERMINATE: {agent_info.get('role', agent_id)} (reason: {reason})")

    def log_agent_task(
        self,
        agent_id: str,
        task: str,
        status: str = "started"  # 'started', 'completed', 'failed'
    ):
        """Log agent task events"""
        agent_info = self.active_agents.get(agent_id, {})

        event = AgentEvent(
            timestamp=datetime.now().isoformat(),
            event_type=f'task_{status}',
            agent_id=agent_id,
            agent_role=agent_info.get('role', 'unknown'),
            tier=agent_info.get('tier', -1),
            parent_id=agent_info.get('parent_id'),
            ai_provider=agent_info.get('provider'),
            details={'task': task, 'status': status}
        )
        self.agent_events.append(event)

    # ==========================================
    # AI Provider Call Logging
    # ==========================================

    def log_ai_call(
        self,
        provider: str,
        model: str,
        agent_id: str,
        agent_role: str,
        call_type: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        success: bool = True,
        error: str = None
    ):
        """Log an AI provider API call"""
        call = AIProviderCall(
            timestamp=datetime.now().isoformat(),
            provider=provider,
            model=model,
            agent_id=agent_id,
            agent_role=agent_role,
            call_type=call_type,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            success=success,
            error=error
        )
        self.ai_calls.append(call)

        # Update provider stats
        self.provider_call_counts[provider] = self.provider_call_counts.get(provider, 0) + 1

        if provider not in self.provider_token_usage:
            self.provider_token_usage[provider] = {'in': 0, 'out': 0}
        self.provider_token_usage[provider]['in'] += tokens_in
        self.provider_token_usage[provider]['out'] += tokens_out

        if not success:
            self.provider_errors[provider] = self.provider_errors.get(provider, 0) + 1

    # ==========================================
    # Statistics & Reporting
    # ==========================================

    def get_summary(self) -> Dict:
        """Get session summary statistics"""
        # Normalize provider keys
        normalized_provider_stats = {}
        for provider in set(list(self.provider_call_counts.keys()) + list(self.provider_token_usage.keys())):
            norm_key = self.PROVIDER_KEY_MAP.get(provider.lower(), provider.lower())
            details = self.PROVIDER_DETAILS.get(norm_key, {})

            normalized_provider_stats[norm_key] = {
                'display_name': details.get('display_name', self.PROVIDER_NAMES.get(provider, provider)),
                'model': details.get('model', 'unknown'),
                'endpoint': details.get('endpoint', 'unknown'),
                'rate_limit': details.get('rate_limit', 'unknown'),
                'call_method': details.get('call_method', {}),
                'total_calls': self.provider_call_counts.get(provider, 0),
                'tokens_in': self.provider_token_usage.get(provider, {}).get('in', 0),
                'tokens_out': self.provider_token_usage.get(provider, {}).get('out', 0),
                'errors': self.provider_errors.get(provider, 0)
            }

        return {
            'session_id': self.session_id,
            'session_name': self.session_name,
            'session_start': self.session_start.isoformat() if self.session_start else None,
            'session_end': self.session_end.isoformat() if self.session_end else None,
            'duration_seconds': (self.session_end - self.session_start).total_seconds() if self.session_end else None,

            'architecture': {
                'total_tiers': 4,
                'tier_details': {
                    f'tier_{tier}': info
                    for tier, info in self.TIER_INFO.items()
                }
            },

            'agents': {
                'total_spawned': self.total_spawned,
                'total_terminated': self.total_terminated,
                'currently_active': len(self.active_agents),
                'by_tier': {
                    self.TIER_NAMES.get(tier, f'Tier {tier}'): count
                    for tier, count in sorted(self.agent_counts_by_tier.items())
                },
                'by_role': dict(sorted(self.agent_counts_by_role.items(), key=lambda x: -x[1]))
            },

            'ai_providers': normalized_provider_stats,

            'ai_provider_reference': {
                k: {
                    'display_name': v['display_name'],
                    'model': v['model'],
                    'endpoint': v['endpoint'],
                    'rate_limit': v['rate_limit'],
                    'auth_method': v['call_method'].get('auth', 'N/A'),
                    'payload_format': v['call_method'].get('payload_format', 'N/A')
                }
                for k, v in self.PROVIDER_DETAILS.items()
            },

            'total_ai_calls': sum(self.provider_call_counts.values()),
            'total_tokens': {
                'in': sum(p.get('in', 0) for p in self.provider_token_usage.values()),
                'out': sum(p.get('out', 0) for p in self.provider_token_usage.values())
            }
        }

    def get_hierarchy_tree(self) -> Dict:
        """Build a tree visualization of agent hierarchy"""
        # Build tree from events
        tree = {'root_agents': [], 'all_agents': {}}

        for event in self.agent_events:
            if event.event_type == 'spawn':
                agent_info = {
                    'id': event.agent_id,
                    'role': event.agent_role,
                    'tier': event.tier,
                    'tier_name': self.TIER_NAMES.get(event.tier, f'Tier {event.tier}'),
                    'provider': event.ai_provider,
                    'provider_name': self.PROVIDER_NAMES.get(event.ai_provider, event.ai_provider),
                    'parent_id': event.parent_id,
                    'children': []
                }
                tree['all_agents'][event.agent_id] = agent_info

                if event.parent_id and event.parent_id in tree['all_agents']:
                    tree['all_agents'][event.parent_id]['children'].append(event.agent_id)
                elif not event.parent_id:
                    tree['root_agents'].append(event.agent_id)

        return tree

    def print_hierarchy(self):
        """Print ASCII visualization of agent hierarchy"""
        tree = self.get_hierarchy_tree()

        print("\n" + "=" * 70)
        print("AGENT HIERARCHY")
        print("=" * 70)

        def print_agent(agent_id: str, indent: int = 0):
            agent = tree['all_agents'].get(agent_id)
            if not agent:
                return

            prefix = "  " * indent + ("├── " if indent > 0 else "")
            provider = agent['provider_name'] or 'No AI'
            print(f"{prefix}{agent['role']} [{agent['tier_name']}] - {provider}")

            for child_id in agent['children']:
                print_agent(child_id, indent + 1)

        for root_id in tree['root_agents']:
            print_agent(root_id)

        print("=" * 70)

    def print_provider_stats(self):
        """Print AI provider usage statistics"""
        print("\n" + "=" * 70)
        print("AI PROVIDER USAGE")
        print("=" * 70)

        for provider, count in sorted(self.provider_call_counts.items(), key=lambda x: -x[1]):
            name = self.PROVIDER_NAMES.get(provider, provider)
            tokens = self.provider_token_usage.get(provider, {})
            errors = self.provider_errors.get(provider, 0)

            print(f"\n{name}:")
            print(f"  API Calls: {count}")
            print(f"  Tokens In: {tokens.get('in', 0):,}")
            print(f"  Tokens Out: {tokens.get('out', 0):,}")
            print(f"  Errors: {errors}")

        print("\n" + "=" * 70)

    # ==========================================
    # Save/Load
    # ==========================================

    def save_log(self, filename: str = None):
        """Save complete log to JSON file"""
        if not filename:
            filename = f"session_{self.session_id}.json"

        filepath = self.log_dir / filename

        log_data = {
            'summary': self.get_summary(),
            'hierarchy': self.get_hierarchy_tree(),
            'events': [asdict(e) for e in self.agent_events],
            'ai_calls': [asdict(c) for c in self.ai_calls]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, default=str)

        print(f"\n[AgentLogger] Log saved to: {filepath}")
        return filepath

    def save_readable_log(self, filename: str = None):
        """Save comprehensive human-readable log with all details"""
        if not filename:
            filename = f"session_{self.session_id}_readable.txt"

        filepath = self.log_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("EQUITY MINIONS - AGENT SESSION LOG\n")
            f.write("=" * 80 + "\n\n")

            # Summary
            summary = self.get_summary()
            f.write(f"Session: {summary['session_name']}\n")
            f.write(f"ID: {summary['session_id']}\n")
            f.write(f"Start: {summary['session_start']}\n")
            f.write(f"End: {summary['session_end']}\n")
            if summary['duration_seconds']:
                f.write(f"Duration: {summary['duration_seconds']:.1f} seconds\n")
            f.write("\n")

            # =================================================================
            # ARCHITECTURE OVERVIEW
            # =================================================================
            f.write("=" * 80 + "\n")
            f.write("SYSTEM ARCHITECTURE - 4-TIER HIERARCHICAL AGENT SYSTEM\n")
            f.write("=" * 80 + "\n\n")

            for tier_num, tier_info in self.TIER_INFO.items():
                f.write(f"TIER {tier_num}: {tier_info['name'].upper()} - {tier_info['description']}\n")
                f.write("-" * 60 + "\n")
                f.write("Responsibilities:\n")
                for resp in tier_info['responsibilities']:
                    f.write(f"  - {resp}\n")
                f.write("Agent Types:\n")
                for agent in tier_info['agents']:
                    f.write(f"  - {agent}\n")
                f.write("Source Files:\n")
                for src in tier_info['source_files']:
                    f.write(f"  - {src}\n")
                f.write("\n")

            # =================================================================
            # AGENT STATISTICS
            # =================================================================
            f.write("=" * 80 + "\n")
            f.write("AGENT STATISTICS\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Total Agents Spawned: {summary['agents']['total_spawned']}\n")
            f.write(f"Total Agents Terminated: {summary['agents']['total_terminated']}\n")
            f.write(f"Currently Active: {summary['agents']['currently_active']}\n\n")

            f.write("AGENTS BY TIER:\n")
            f.write("-" * 40 + "\n")
            for tier, count in summary['agents']['by_tier'].items():
                f.write(f"  {tier}: {count}\n")
            f.write("\n")

            f.write("AGENTS BY ROLE:\n")
            f.write("-" * 40 + "\n")
            for role, count in summary['agents']['by_role'].items():
                f.write(f"  {role}: {count}\n")
            f.write("\n")

            # =================================================================
            # AI PROVIDER DETAILS - HOW EACH IS CALLED
            # =================================================================
            f.write("=" * 80 + "\n")
            f.write("AI PROVIDER DETAILS - HOW EACH PROVIDER IS CALLED\n")
            f.write("=" * 80 + "\n\n")

            for provider_key, details in self.PROVIDER_DETAILS.items():
                f.write(f"{'='*60}\n")
                f.write(f"{details['display_name'].upper()}\n")
                f.write(f"{'='*60}\n")
                f.write(f"Model: {details['model']}\n")
                f.write(f"Endpoint: {details['endpoint']}\n")
                f.write(f"Rate Limit: {details['rate_limit']}\n")
                f.write(f"Environment Variable: {details['env_key']}\n")
                f.write(f"Source File: {details['source_file']}\n\n")

                call_method = details['call_method']
                f.write("API Call Method:\n")
                f.write(f"  HTTP Method: {call_method['type']}\n")
                f.write(f"  Authentication: {call_method['auth']}\n")
                f.write(f"  Payload Format: {call_method['payload_format']}\n")
                f.write("  Example Payload:\n")
                f.write(f"    {json.dumps(call_method['example'], indent=4).replace(chr(10), chr(10) + '    ')}\n")
                f.write("\n")

            # =================================================================
            # AI PROVIDER USAGE STATISTICS
            # =================================================================
            f.write("=" * 80 + "\n")
            f.write("AI PROVIDER USAGE - THIS SESSION\n")
            f.write("=" * 80 + "\n\n")

            for provider, stats in summary['ai_providers'].items():
                f.write(f"{stats['display_name']}:\n")
                f.write(f"  API Calls Made: {stats['total_calls']}\n")
                f.write(f"  Input Tokens: {stats['tokens_in']:,}\n")
                f.write(f"  Output Tokens: {stats['tokens_out']:,}\n")
                f.write(f"  Total Tokens: {stats['tokens_in'] + stats['tokens_out']:,}\n")
                f.write(f"  Errors: {stats['errors']}\n\n")

            f.write(f"TOTAL API CALLS: {summary['total_ai_calls']}\n")
            f.write(f"TOTAL TOKENS USED: {summary['total_tokens']['in'] + summary['total_tokens']['out']:,}\n")
            f.write(f"  - Input: {summary['total_tokens']['in']:,}\n")
            f.write(f"  - Output: {summary['total_tokens']['out']:,}\n\n")

            # =================================================================
            # AGENT HIERARCHY
            # =================================================================
            f.write("=" * 80 + "\n")
            f.write("AGENT HIERARCHY TREE\n")
            f.write("=" * 80 + "\n\n")

            tree = self.get_hierarchy_tree()

            def write_agent_tree(agent_id: str, indent: int = 0):
                agent = tree['all_agents'].get(agent_id)
                if not agent:
                    return
                prefix = "  " * indent + ("├── " if indent > 0 else "")
                provider = agent['provider_name'] or 'No AI Provider'
                f.write(f"{prefix}{agent['role']} [{agent['tier_name']}] - {provider}\n")
                for child_id in agent['children']:
                    write_agent_tree(child_id, indent + 1)

            for root_id in tree['root_agents']:
                write_agent_tree(root_id)

            if not tree['root_agents']:
                f.write("  (No agents spawned in this session)\n")
            f.write("\n")

            # =================================================================
            # EVENT TIMELINE
            # =================================================================
            f.write("=" * 80 + "\n")
            f.write("EVENT TIMELINE\n")
            f.write("=" * 80 + "\n\n")

            for event in self.agent_events:
                f.write(f"{event.timestamp} | {event.event_type.upper():12} | ")
                f.write(f"{event.agent_role} (Tier {event.tier})")
                if event.ai_provider:
                    f.write(f" [Provider: {self.PROVIDER_NAMES.get(event.ai_provider, event.ai_provider)}]")
                if event.parent_id:
                    f.write(f" <- parent:{event.parent_id[:20]}")
                f.write("\n")

            if not self.agent_events:
                f.write("  (No events recorded)\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("END OF LOG\n")
            f.write("=" * 80 + "\n")

        print(f"[AgentLogger] Readable log saved to: {filepath}")
        return filepath


# Global convenience functions
def get_logger() -> AgentLogger:
    """Get the global agent logger instance"""
    return AgentLogger.get_instance()


def log_spawn(agent_id: str, role: str, tier: int, parent_id: str = None, provider: str = None, config: Dict = None):
    """Log agent spawn (convenience function)"""
    get_logger().log_agent_spawn(agent_id, role, tier, parent_id, provider, config)


def log_terminate(agent_id: str, reason: str = "normal"):
    """Log agent termination (convenience function)"""
    get_logger().log_agent_terminate(agent_id, reason)


def log_ai_call(provider: str, model: str, agent_id: str, role: str, call_type: str,
                tokens_in: int = 0, tokens_out: int = 0, success: bool = True, error: str = None):
    """Log AI call (convenience function)"""
    get_logger().log_ai_call(provider, model, agent_id, role, call_type, tokens_in, tokens_out, success, error)


def print_architecture_info():
    """Print comprehensive architecture information"""
    print("=" * 80)
    print("EQUITY MINIONS - MULTI-AI AGENT SYSTEM ARCHITECTURE")
    print("=" * 80)
    print()

    # Count totals
    total_agent_types = sum(len(info['agents']) for info in AGENT_TIER_INFO.values())
    total_providers = len(AI_PROVIDER_DETAILS)

    print(f"SUMMARY:")
    print(f"  Total Agent Types: {total_agent_types}")
    print(f"  Total Tiers: 4 (Hierarchical)")
    print(f"  AI Providers Supported: {total_providers}")
    print()

    # Tier breakdown
    print("=" * 80)
    print("4-TIER HIERARCHICAL ARCHITECTURE")
    print("=" * 80)
    print()

    for tier_num, tier_info in AGENT_TIER_INFO.items():
        print(f"TIER {tier_num}: {tier_info['name'].upper()} - {tier_info['description']}")
        print("-" * 60)
        print("Responsibilities:")
        for resp in tier_info['responsibilities']:
            print(f"  - {resp}")
        print(f"Agent Types ({len(tier_info['agents'])}):")
        for agent in tier_info['agents']:
            print(f"  - {agent}")
        print()

    # AI Provider details
    print("=" * 80)
    print("AI PROVIDER INTEGRATION DETAILS")
    print("=" * 80)
    print()

    for provider_key, details in AI_PROVIDER_DETAILS.items():
        print(f"{'='*60}")
        print(f"{details['display_name'].upper()}")
        print(f"{'='*60}")
        print(f"  Model: {details['model']}")
        print(f"  Endpoint: {details['endpoint']}")
        print(f"  Rate Limit: {details['rate_limit']}")
        print(f"  Env Variable: {details['env_key']}")
        print(f"  Source: {details['source_file']}")
        print()
        print("  API Call Method:")
        call_method = details['call_method']
        print(f"    HTTP: {call_method['type']}")
        print(f"    Auth: {call_method['auth']}")
        print(f"    Format: {call_method['payload_format']}")
        print()

    print("=" * 80)


# ==============================================================================
# MAIN - Demo and Architecture Info
# ==============================================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        # Run a demo session
        print("Running demo session...")
        print()

        logger = get_logger()
        logger.start_session("Demo Research Session")

        # Simulate agent spawns
        log_spawn("arch_001", "ChiefArchitectAgent", tier=0, provider="openai")
        log_spawn("sup_001", "ResearchSupervisor", tier=1, parent_id="arch_001", provider="gemini")
        log_spawn("analyst_001", "AnalystAgent", tier=2, parent_id="sup_001", provider="openai")
        log_spawn("bull_001", "BullAgent", tier=2, parent_id="sup_001", provider="grok")
        log_spawn("bear_001", "BearAgent", tier=2, parent_id="sup_001", provider="qwen")
        log_spawn("critic_001", "CriticAgent", tier=2, parent_id="sup_001", provider="openai")
        log_spawn("gate_001", "PublishGatekeeperAgent", tier=3, parent_id="sup_001", provider="gemini")

        # Simulate AI calls
        log_ai_call("openai", "gpt-4o", "analyst_001", "AnalystAgent", "analysis", 1500, 2000)
        log_ai_call("grok", "grok-3", "bull_001", "BullAgent", "debate", 1200, 1800)
        log_ai_call("qwen", "qwen-turbo", "bear_001", "BearAgent", "debate", 1300, 1700)
        log_ai_call("openai", "gpt-4o", "critic_001", "CriticAgent", "critique", 1000, 1500)
        log_ai_call("gemini", "gemini-2.0-flash", "gate_001", "PublishGatekeeperAgent", "validation", 800, 500)

        logger.end_session()
        logger.print_hierarchy()
        logger.print_provider_stats()

        # Save logs
        json_path = logger.save_log()
        txt_path = logger.save_readable_log()

        print()
        print(f"Demo complete! Logs saved to:")
        print(f"  JSON: {json_path}")
        print(f"  TXT:  {txt_path}")

    else:
        # Print architecture info
        print_architecture_info()

        print()
        print("USAGE:")
        print("-" * 40)
        print("  python agent_logger.py         # Show architecture info")
        print("  python agent_logger.py --demo  # Run demo session")
        print()
        print("In your code:")
        print("-" * 40)
        print("""
from agents.agent_logger import (
    get_logger, log_spawn, log_ai_call, log_terminate
)

# Start session
logger = get_logger()
logger.start_session("My Research Run")

# Log agent creation
log_spawn("agent_001", "AnalystAgent", tier=2, provider="openai")

# Log AI API calls
log_ai_call("openai", "gpt-4o", "agent_001", "AnalystAgent", "analysis", 500, 1000)

# End and save
logger.end_session()
logger.save_log()          # JSON
logger.save_readable_log() # Human-readable TXT
""")
