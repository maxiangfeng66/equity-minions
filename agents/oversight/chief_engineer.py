"""
Chief Engineer Agent - Master Oversight Agent for the Equity Minions Project.

The Chief Engineer is the autonomous guardian of the entire system.
It continuously monitors, validates, and maintains all project components.

Responsibilities:
1. Understand project architecture, idea, and execution
2. Monitor health of all agents and components
3. Spawn sub-agents for specific inspection tasks
4. Detect and report issues before they cause failures
5. Suggest and implement improvements
6. Maintain project documentation and state
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import traceback

from ..core.spawnable_agent import SpawnableAgent
from ..core.lifecycle import AgentLifecycleState
from ..core.agent_registry import AgentRegistry


class ComponentStatus(Enum):
    """Status of a system component"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    UNKNOWN = "unknown"


class InspectionPriority(Enum):
    """Priority levels for inspection tasks"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    ROUTINE = 5


@dataclass
class ComponentHealth:
    """Health status of a system component"""
    component_name: str
    status: ComponentStatus
    last_checked: datetime
    issues: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class InspectionTask:
    """A task for a sub-agent to execute"""
    task_id: str
    component: str
    task_type: str
    priority: InspectionPriority
    description: str
    assigned_agent: Optional[str] = None
    status: str = "pending"
    result: Optional[Dict] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class ProjectKnowledge:
    """Chief Engineer's understanding of the project"""
    project_name: str = "Equity Minions"
    project_purpose: str = ""
    architecture_summary: str = ""
    key_components: List[str] = field(default_factory=list)
    critical_paths: List[str] = field(default_factory=list)
    known_issues: List[str] = field(default_factory=list)
    improvement_backlog: List[str] = field(default_factory=list)
    last_full_inspection: Optional[datetime] = None


class ChiefEngineerAgent(SpawnableAgent):
    """
    Chief Engineer - Master Oversight Agent.

    The Chief Engineer maintains a comprehensive understanding of the project
    and continuously monitors all components for health and correctness.

    Key Capabilities:
    - Project understanding (reads and comprehends project docs)
    - Component health monitoring
    - Sub-agent spawning for specialized inspections
    - Issue detection and escalation
    - Improvement suggestions
    - State persistence across sessions
    """

    # Component registry - what to monitor
    MONITORED_COMPONENTS = {
        'workflow_engine': {
            'files': ['workflow/graph_executor.py', 'workflow/node_executor.py'],
            'check_interval': timedelta(hours=1),
            'inspector': 'WorkflowAuditorAgent'
        },
        'yaml_workflow': {
            'files': ['workflow/definitions/equity_research_v4.yaml'],
            'check_interval': timedelta(hours=2),
            'inspector': 'WorkflowAuditorAgent'
        },
        'ai_providers': {
            'files': ['agents/ai_providers.py'],
            'check_interval': timedelta(hours=4),
            'inspector': 'ComponentInspectorAgent'
        },
        'dcf_calculator': {
            'files': ['agents/tools/financial_calculator.py'],
            'check_interval': timedelta(minutes=30),
            'inspector': 'DCFQualityController'
        },
        'market_data_api': {
            'files': ['agents/tools/market_data_api.py'],
            'check_interval': timedelta(hours=1),
            'inspector': 'ComponentInspectorAgent'
        },
        'debate_system': {
            'files': ['agents/debate_system.py', 'agents/multi_ai_debate.py'],
            'check_interval': timedelta(hours=2),
            'inspector': 'ComponentInspectorAgent'
        },
        'goalkeeper_agents': {
            'files': ['agents/goalkeepers/publish_gatekeeper.py', 'agents/goalkeepers/due_diligence_agent.py'],
            'check_interval': timedelta(hours=4),
            'inspector': 'ComponentInspectorAgent'
        },
        'report_generation': {
            'files': ['utils/html_generator.py', 'generate_workflow_report.py'],
            'check_interval': timedelta(hours=6),
            'inspector': 'ComponentInspectorAgent'
        }
    }

    def __init__(
        self,
        project_root: str,
        ai_provider: Optional[Any] = None,
        state_file: str = "context/chief_engineer_state.json"
    ):
        super().__init__(
            name="ChiefEngineer",
            role="Master Oversight Agent",
            tier=0
        )

        self.project_root = Path(project_root)
        self.state_file = self.project_root / state_file
        self.ai_provider = ai_provider

        # State
        self.knowledge = ProjectKnowledge()
        self.component_health: Dict[str, ComponentHealth] = {}
        self.active_inspections: Dict[str, InspectionTask] = {}
        self.inspection_history: List[InspectionTask] = []
        self.spawned_inspectors: Dict[str, SpawnableAgent] = {}

        # Load persisted state
        self._load_state()

    def _load_state(self):
        """Load persisted state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)

                self.knowledge.project_purpose = state.get('project_purpose', '')
                self.knowledge.architecture_summary = state.get('architecture_summary', '')
                self.knowledge.key_components = state.get('key_components', [])
                self.knowledge.known_issues = state.get('known_issues', [])
                self.knowledge.improvement_backlog = state.get('improvement_backlog', [])

                if state.get('last_full_inspection'):
                    self.knowledge.last_full_inspection = datetime.fromisoformat(
                        state['last_full_inspection']
                    )

                print(f"[ChiefEngineer] Loaded state from {self.state_file}")

            except Exception as e:
                print(f"[ChiefEngineer] Could not load state: {e}")

    def _save_state(self):
        """Persist state to file"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = {
                'project_purpose': self.knowledge.project_purpose,
                'architecture_summary': self.knowledge.architecture_summary,
                'key_components': self.knowledge.key_components,
                'known_issues': self.knowledge.known_issues,
                'improvement_backlog': self.knowledge.improvement_backlog,
                'last_full_inspection': self.knowledge.last_full_inspection.isoformat()
                    if self.knowledge.last_full_inspection else None,
                'component_health': {
                    name: {
                        'status': health.status.value,
                        'last_checked': health.last_checked.isoformat(),
                        'issues': health.issues,
                        'recommendations': health.recommendations
                    }
                    for name, health in self.component_health.items()
                },
                'saved_at': datetime.now().isoformat()
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            print(f"[ChiefEngineer] Could not save state: {e}")

    async def initialize(self):
        """Initialize the Chief Engineer - understand the project"""
        print("[ChiefEngineer] Initializing and understanding project...")

        # Read and understand project documentation
        await self._understand_project()

        # Initialize component health tracking
        for component_name in self.MONITORED_COMPONENTS:
            if component_name not in self.component_health:
                self.component_health[component_name] = ComponentHealth(
                    component_name=component_name,
                    status=ComponentStatus.UNKNOWN,
                    last_checked=datetime.min
                )

        self._save_state()
        print("[ChiefEngineer] Initialization complete.")

    async def _understand_project(self):
        """Read and comprehend project documentation"""
        brain_path = self.project_root / "brain"

        # Key documents to understand
        docs_to_read = [
            "blueprint.md",
            "idea.txt",
            "system_flowchart.md",
            "investigation_summary.md"
        ]

        project_docs = {}

        for doc in docs_to_read:
            doc_path = brain_path / doc
            if doc_path.exists():
                try:
                    with open(doc_path, 'r', encoding='utf-8') as f:
                        project_docs[doc] = f.read()
                except Exception as e:
                    print(f"[ChiefEngineer] Could not read {doc}: {e}")

        # Extract key understanding
        if "idea.txt" in project_docs:
            self.knowledge.project_purpose = self._extract_purpose(project_docs["idea.txt"])

        if "blueprint.md" in project_docs:
            self.knowledge.architecture_summary = self._extract_architecture(project_docs["blueprint.md"])
            self.knowledge.key_components = self._extract_components(project_docs["blueprint.md"])

        if "investigation_summary.md" in project_docs:
            self.knowledge.known_issues = self._extract_issues(project_docs["investigation_summary.md"])

        # Identify critical paths
        self.knowledge.critical_paths = [
            "START -> Research Supervisor -> Data Collection -> Data Checkpoint",
            "Debate Moderator -> Bull/Bear Advocates -> Devils Advocate -> Debate Critic",
            "Pre-Model Validator -> Financial Modeler -> Valuation Committee",
            "Quality Gates -> Synthesizer -> Final Report"
        ]

    def _extract_purpose(self, content: str) -> str:
        """Extract project purpose from idea.txt"""
        lines = content.split('\n')[:20]  # First 20 lines
        return ' '.join(lines).strip()[:500]

    def _extract_architecture(self, content: str) -> str:
        """Extract architecture summary from blueprint"""
        # Find architecture section
        if "## Architecture" in content:
            start = content.find("## Architecture")
            end = content.find("##", start + 1)
            if end == -1:
                end = start + 2000
            return content[start:end].strip()[:1000]
        return content[:1000]

    def _extract_components(self, content: str) -> List[str]:
        """Extract key components from blueprint"""
        components = []
        for line in content.split('\n'):
            if line.strip().startswith('- **') and '**' in line[4:]:
                component = line.split('**')[1]
                components.append(component)
        return components[:20]

    def _extract_issues(self, content: str) -> List[str]:
        """Extract known issues from investigation summary"""
        issues = []
        for line in content.split('\n'):
            if 'CRITICAL' in line or 'issue' in line.lower() or 'problem' in line.lower():
                issues.append(line.strip())
        return issues[:10]

    async def run_health_check(self) -> Dict[str, ComponentHealth]:
        """Run health check on all components"""
        print("[ChiefEngineer] Running system health check...")

        for component_name, config in self.MONITORED_COMPONENTS.items():
            health = self.component_health.get(component_name)

            # Check if inspection is needed
            if health and health.last_checked:
                time_since_check = datetime.now() - health.last_checked
                if time_since_check < config['check_interval']:
                    continue  # Skip, recently checked

            # Create inspection task
            task = InspectionTask(
                task_id=f"{component_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                component=component_name,
                task_type="health_check",
                priority=InspectionPriority.ROUTINE,
                description=f"Routine health check for {component_name}"
            )

            await self._execute_inspection(task, config)

        self._save_state()
        return self.component_health

    async def _execute_inspection(self, task: InspectionTask, config: Dict):
        """Execute an inspection task"""
        component_name = task.component
        print(f"[ChiefEngineer] Inspecting {component_name}...")

        issues = []
        recommendations = []
        status = ComponentStatus.HEALTHY

        # Check if files exist
        for file_path in config.get('files', []):
            full_path = self.project_root / file_path
            if not full_path.exists():
                issues.append(f"Missing file: {file_path}")
                status = ComponentStatus.FAILING

        # Run component-specific checks
        try:
            if component_name == 'workflow_engine':
                check_result = await self._check_workflow_engine()
            elif component_name == 'yaml_workflow':
                check_result = await self._check_yaml_workflow()
            elif component_name == 'dcf_calculator':
                check_result = await self._check_dcf_calculator()
            elif component_name == 'ai_providers':
                check_result = await self._check_ai_providers()
            else:
                check_result = await self._generic_component_check(component_name, config)

            issues.extend(check_result.get('issues', []))
            recommendations.extend(check_result.get('recommendations', []))

            if check_result.get('status'):
                status = check_result['status']

        except Exception as e:
            issues.append(f"Inspection error: {str(e)}")
            status = ComponentStatus.DEGRADED

        # Update component health
        self.component_health[component_name] = ComponentHealth(
            component_name=component_name,
            status=status,
            last_checked=datetime.now(),
            issues=issues,
            recommendations=recommendations
        )

        # Complete task
        task.status = "completed"
        task.completed_at = datetime.now()
        task.result = {
            'status': status.value,
            'issues': issues,
            'recommendations': recommendations
        }

        self.inspection_history.append(task)

    async def _check_workflow_engine(self) -> Dict:
        """Check workflow engine health"""
        issues = []
        recommendations = []

        # Check graph_executor.py
        executor_path = self.project_root / "workflow" / "graph_executor.py"
        if executor_path.exists():
            content = executor_path.read_text()

            # Check for error handling
            if "except Exception" not in content:
                issues.append("graph_executor.py may lack comprehensive error handling")

            # Check for MAX_ITERATIONS
            if "MAX_ITERATIONS" in content:
                import re
                match = re.search(r'MAX_ITERATIONS\s*=\s*(\d+)', content)
                if match:
                    max_iter = int(match.group(1))
                    if max_iter < 25:
                        issues.append(f"MAX_ITERATIONS ({max_iter}) may be too low for complex workflows")

        return {
            'issues': issues,
            'recommendations': recommendations,
            'status': ComponentStatus.HEALTHY if not issues else ComponentStatus.DEGRADED
        }

    async def _check_yaml_workflow(self) -> Dict:
        """Check YAML workflow definition"""
        issues = []
        recommendations = []

        workflow_path = self.project_root / "workflows" / "equity_research_v4.yaml"
        if workflow_path.exists():
            try:
                import yaml
                with open(workflow_path, 'r') as f:
                    workflow = yaml.safe_load(f)

                # Count nodes and edges
                nodes = workflow.get('graph', {}).get('nodes', [])
                edges = workflow.get('graph', {}).get('edges', [])

                if len(nodes) < 10:
                    issues.append(f"Workflow has only {len(nodes)} nodes - may be incomplete")

                if len(edges) < len(nodes):
                    issues.append("Some nodes may be unreachable (fewer edges than nodes)")

                # Check for required nodes
                node_ids = [n.get('id') for n in nodes]
                required = ['START', 'Research Supervisor', 'Financial Modeler', 'Synthesizer']
                for req in required:
                    if req not in node_ids:
                        issues.append(f"Missing required node: {req}")

            except Exception as e:
                issues.append(f"Could not parse workflow YAML: {e}")

        return {
            'issues': issues,
            'recommendations': recommendations,
            'status': ComponentStatus.HEALTHY if not issues else ComponentStatus.DEGRADED
        }

    async def _check_dcf_calculator(self) -> Dict:
        """Check DCF calculator functionality"""
        issues = []
        recommendations = []

        calc_path = self.project_root / "agents" / "tools" / "financial_calculator.py"
        if calc_path.exists():
            content = calc_path.read_text()

            # Check for key functions
            required_functions = ['calculate_wacc', 'calculate_fcf', 'calculate_terminal_value']
            for func in required_functions:
                if f"def {func}" not in content:
                    issues.append(f"Missing function: {func}")

            # Check for validation
            if "validate" not in content.lower():
                recommendations.append("Consider adding input validation to DCF calculator")

        else:
            issues.append("DCF calculator not found - need to create agents/tools/financial_calculator.py")

        return {
            'issues': issues,
            'recommendations': recommendations,
            'status': ComponentStatus.HEALTHY if not issues else ComponentStatus.DEGRADED
        }

    async def _check_ai_providers(self) -> Dict:
        """Check AI providers configuration"""
        issues = []
        recommendations = []

        providers_path = self.project_root / "agents" / "ai_providers.py"
        if providers_path.exists():
            content = providers_path.read_text()

            # Check for rate limiting
            if "rate" not in content.lower() and "limit" not in content.lower():
                recommendations.append("Consider adding rate limiting to AI providers")

            # Check for retry logic
            if "retry" not in content.lower():
                recommendations.append("Consider adding retry logic for API failures")

            # Check for all expected providers
            providers = ['openai', 'google', 'xai', 'deepseek', 'dashscope']
            for provider in providers:
                if provider.lower() not in content.lower():
                    issues.append(f"Missing provider configuration: {provider}")

        return {
            'issues': issues,
            'recommendations': recommendations,
            'status': ComponentStatus.HEALTHY if not issues else ComponentStatus.DEGRADED
        }

    async def _generic_component_check(self, component_name: str, config: Dict) -> Dict:
        """Generic component check"""
        issues = []

        for file_path in config.get('files', []):
            full_path = self.project_root / file_path
            if not full_path.exists():
                issues.append(f"Missing file: {file_path}")
            else:
                # Check file size
                size = full_path.stat().st_size
                if size < 100:
                    issues.append(f"File {file_path} is very small ({size} bytes) - may be incomplete")

        return {
            'issues': issues,
            'recommendations': [],
            'status': ComponentStatus.HEALTHY if not issues else ComponentStatus.DEGRADED
        }

    async def spawn_inspector(
        self,
        inspector_type: str,
        target_component: str,
        task_description: str
    ) -> Optional[str]:
        """
        Spawn a specialized inspector sub-agent.

        Args:
            inspector_type: Type of inspector to spawn
            target_component: Component to inspect
            task_description: What to inspect

        Returns:
            Inspector agent ID if spawned successfully
        """
        from .component_inspector import ComponentInspectorAgent
        from .workflow_auditor import WorkflowAuditorAgent
        from .dcf_quality_controller import DCFQualityController

        inspector_classes = {
            'ComponentInspectorAgent': ComponentInspectorAgent,
            'WorkflowAuditorAgent': WorkflowAuditorAgent,
            'DCFQualityController': DCFQualityController
        }

        if inspector_type not in inspector_classes:
            print(f"[ChiefEngineer] Unknown inspector type: {inspector_type}")
            return None

        inspector_class = inspector_classes[inspector_type]

        try:
            inspector = inspector_class(
                name=f"{inspector_type}_{target_component}",
                project_root=str(self.project_root),
                parent_agent=self
            )

            # Register as child
            await self.spawn_child(inspector)

            # Store reference
            inspector_id = inspector.agent_id
            self.spawned_inspectors[inspector_id] = inspector

            print(f"[ChiefEngineer] Spawned {inspector_type} for {target_component}")

            return inspector_id

        except Exception as e:
            print(f"[ChiefEngineer] Failed to spawn inspector: {e}")
            traceback.print_exc()
            return None

    async def get_system_report(self) -> Dict:
        """Generate comprehensive system health report"""
        # Ensure health check is recent
        await self.run_health_check()

        healthy_count = sum(1 for h in self.component_health.values()
                           if h.status == ComponentStatus.HEALTHY)
        total_count = len(self.component_health)

        all_issues = []
        all_recommendations = []

        for health in self.component_health.values():
            all_issues.extend(health.issues)
            all_recommendations.extend(health.recommendations)

        return {
            'generated_at': datetime.now().isoformat(),
            'overall_health': 'HEALTHY' if healthy_count == total_count else
                            'DEGRADED' if healthy_count > total_count / 2 else 'CRITICAL',
            'healthy_components': healthy_count,
            'total_components': total_count,
            'component_details': {
                name: {
                    'status': health.status.value,
                    'last_checked': health.last_checked.isoformat(),
                    'issues': health.issues,
                    'recommendations': health.recommendations
                }
                for name, health in self.component_health.items()
            },
            'all_issues': all_issues,
            'all_recommendations': all_recommendations,
            'known_project_issues': self.knowledge.known_issues,
            'improvement_backlog': self.knowledge.improvement_backlog,
            'project_understanding': {
                'purpose': self.knowledge.project_purpose[:200],
                'key_components': self.knowledge.key_components,
                'critical_paths': self.knowledge.critical_paths
            }
        }

    async def continuous_monitoring(self, interval_seconds: int = 300):
        """
        Run continuous monitoring loop.

        Args:
            interval_seconds: How often to check (default 5 minutes)
        """
        print(f"[ChiefEngineer] Starting continuous monitoring (interval: {interval_seconds}s)")

        while self.lifecycle_state == AgentLifecycleState.ACTIVE:
            try:
                # Run health check
                await self.run_health_check()

                # Check for critical issues
                critical_components = [
                    name for name, health in self.component_health.items()
                    if health.status == ComponentStatus.FAILING
                ]

                if critical_components:
                    print(f"[ChiefEngineer] ALERT: Critical issues in: {critical_components}")

                # Generate and save report
                report = await self.get_system_report()

                report_path = self.project_root / "context" / "system_health_report.json"
                with open(report_path, 'w') as f:
                    json.dump(report, f, indent=2)

                # Wait for next cycle
                await asyncio.sleep(interval_seconds)

            except asyncio.CancelledError:
                print("[ChiefEngineer] Monitoring stopped")
                break
            except Exception as e:
                print(f"[ChiefEngineer] Monitoring error: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    def add_to_improvement_backlog(self, improvement: str):
        """Add an improvement suggestion to the backlog"""
        if improvement not in self.knowledge.improvement_backlog:
            self.knowledge.improvement_backlog.append(improvement)
            self._save_state()

    def report_issue(self, issue: str, component: str = "unknown"):
        """Report a new issue"""
        issue_entry = f"[{datetime.now().isoformat()}] [{component}] {issue}"
        if issue_entry not in self.knowledge.known_issues:
            self.knowledge.known_issues.append(issue_entry)
            self._save_state()


# Convenience function for standalone execution
async def run_chief_engineer(project_root: str):
    """Run the Chief Engineer in standalone mode"""
    engineer = ChiefEngineerAgent(project_root)
    await engineer.initialize()

    # Run initial health check
    await engineer.run_health_check()

    # Generate and print report
    report = await engineer.get_system_report()
    print("\n" + "="*60)
    print("SYSTEM HEALTH REPORT")
    print("="*60)
    print(json.dumps(report, indent=2))

    return engineer


if __name__ == "__main__":
    import sys
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    asyncio.run(run_chief_engineer(project_root))
