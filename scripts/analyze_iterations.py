"""
Iteration Analysis Tool - Diagnose feedback loops in workflow execution

This tool analyzes workflow result files to understand:
1. Why iterations keep repeating
2. What triggered each iteration
3. Whether quality is improving or stuck in a loop
4. Key outputs that caused routing decisions

Usage:
    python scripts/analyze_iterations.py context/6682_HK_workflow_result.json
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class IterationAnalyzer:
    """Analyzes workflow iterations to diagnose feedback loops"""

    # Nodes involved in the main feedback loop
    LOOP_NODES = [
        'Quality Supervisor',
        'Financial Modeler',
        'DCF Validator',
        'Dot Connector',
        'Pre-Model Validator',
        'Synthesizer'
    ]

    # Keywords that control routing
    ROUTING_KEYWORDS = {
        'Quality Supervisor': {
            'exit_to_synthesizer': 'ROUTE: Synthesizer',
            'loop_to_financial': 'ROUTE: Financial Modeler',
            'loop_to_dot_connector': 'ROUTE: Dot Connector',
            'loop_to_research': 'ROUTE: Research Supervisor',
            'loop_to_debate': 'ROUTE: Debate Moderator',
            'loop_to_data': 'ROUTE: Data Checkpoint',
        },
        'DCF Validator': {
            'validated': 'DCF: VALIDATED',
            'needs_revision': 'NEEDS_PARAMETER_REVISION',
        },
        'Pre-Model Validator': {
            'inputs_validated': 'INPUTS: VALIDATED',
            'inputs_invalid': 'INPUTS: INVALID',
        },
        'Data Checkpoint': {
            'data_verified': 'DATA: VERIFIED',
        }
    }

    # Quality metrics to extract
    QUALITY_PATTERNS = {
        'dcf_target': r'(?:PWV|target|fair value)[:\s]*(?:HKD|USD|CNY)?\s*([\d.]+)',
        'divergence': r'divergence[:\s]*([\d.]+)%',
        'wacc': r'WACC[:\s]*([\d.]+)%',
        'score': r'(?:score|rating)[:\s]*([\d.]+)',
        'recommendation': r'(BUY|SELL|HOLD|OVERVALUED|UNDERVALUED)',
    }

    def __init__(self, result_file: str):
        self.result_file = Path(result_file)
        self.data = None
        self.iterations = []
        self.node_outputs = {}
        self.execution_log = []

    def load_workflow_result(self):
        """Load the workflow result file"""
        with open(self.result_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

        self.node_outputs = self.data.get('node_outputs', {})
        self.execution_log = self.data.get('execution_log', [])
        self.ticker = self.data.get('ticker', 'UNKNOWN')
        self.verified_price = self.data.get('verified_price')
        self.total_iterations = self.data.get('iterations', 0)

    def extract_routing_keywords(self, content: str, node_name: str) -> dict:
        """Extract routing keywords from node output"""
        found = {}
        keywords = self.ROUTING_KEYWORDS.get(node_name, {})

        for key, keyword in keywords.items():
            if keyword in content:
                found[key] = True
            else:
                found[key] = False

        return found

    def extract_quality_metrics(self, content: str) -> dict:
        """Extract quality metrics from content"""
        metrics = {}
        for name, pattern in self.QUALITY_PATTERNS.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metrics[name] = match.group(1)
        return metrics

    def extract_key_snippet(self, content: str, max_len: int = 200) -> str:
        """Extract the most relevant snippet from content"""
        # Look for conclusion/decision sections
        markers = [
            'ROUTE:', 'DECISION:', 'RECOMMENDATION:', 'CONCLUSION:',
            'DCF:', 'VALIDATED', 'NEEDS_', 'PWV:', 'TARGET:'
        ]

        for marker in markers:
            idx = content.find(marker)
            if idx != -1:
                start = max(0, idx - 20)
                end = min(len(content), idx + max_len)
                return '...' + content[start:end].replace('\n', ' ').strip() + '...'

        # Fallback to last part of content (usually has conclusion)
        if len(content) > max_len:
            return '...' + content[-max_len:].replace('\n', ' ').strip()
        return content.replace('\n', ' ').strip()

    def analyze_node_progression(self, node_name: str) -> list:
        """Analyze how a node's output changed across iterations"""
        outputs = self.node_outputs.get(node_name, [])
        progression = []

        for i, output in enumerate(outputs):
            content = output.get('content', '')
            timestamp = output.get('timestamp', '')

            entry = {
                'execution': i + 1,
                'timestamp': timestamp,
                'length': len(content),
                'routing_keywords': self.extract_routing_keywords(content, node_name),
                'quality_metrics': self.extract_quality_metrics(content),
                'key_snippet': self.extract_key_snippet(content),
            }
            progression.append(entry)

        return progression

    def build_iteration_timeline(self) -> list:
        """Build a timeline of what happened in each iteration"""
        timeline = []
        current_iter = None
        iter_events = []

        for entry in self.execution_log:
            iteration = entry.get('iteration', 0)
            event = entry.get('event', '')
            node_id = entry.get('node_id', '')
            details = entry.get('details', {})

            if current_iter != iteration:
                if iter_events:
                    timeline.append({
                        'iteration': current_iter,
                        'events': iter_events
                    })
                current_iter = iteration
                iter_events = []

            # Only track relevant events
            if event in ['node_complete', 'node_triggered', 'edge_condition_failed']:
                iter_events.append({
                    'event': event,
                    'node': node_id,
                    'from': details.get('from', ''),
                    'to': details.get('to', ''),
                })

        if iter_events:
            timeline.append({
                'iteration': current_iter,
                'events': iter_events
            })

        return timeline

    def detect_loops(self) -> list:
        """Detect repeating patterns in the execution"""
        timeline = self.build_iteration_timeline()
        loops = []

        # Track sequence of completed nodes
        sequences = []
        for t in timeline:
            completed = [e['node'] for e in t['events'] if e['event'] == 'node_complete']
            sequences.append(tuple(completed))

        # Find repeating sequences
        seen = {}
        for i, seq in enumerate(sequences):
            if seq in seen:
                loops.append({
                    'first_occurrence': seen[seq] + 1,
                    'repeated_at': i + 1,
                    'nodes': list(seq)
                })
            else:
                seen[seq] = i

        return loops

    def generate_iteration_report(self) -> str:
        """Generate the iteration analysis report"""
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append(f"ITERATION ANALYSIS REPORT: {self.ticker}")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().isoformat()}")
        lines.append(f"Source: {self.result_file.name}")
        lines.append(f"Total Iterations: {self.total_iterations}")
        lines.append(f"Verified Price: {self.verified_price}")
        lines.append("")

        # Summary
        lines.append("-" * 80)
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)

        loops = self.detect_loops()
        if loops:
            lines.append(f"WARNING: Detected {len(loops)} repeating patterns!")
            lines.append("The workflow appears to be stuck in a loop.")
        else:
            lines.append("No obvious repeating patterns detected.")
        lines.append("")

        # Node execution counts
        lines.append("-" * 80)
        lines.append("NODE EXECUTION COUNTS")
        lines.append("-" * 80)
        for node_name in self.LOOP_NODES:
            outputs = self.node_outputs.get(node_name, [])
            count = len(outputs)
            status = "EXCESSIVE" if count > 5 else "NORMAL"
            lines.append(f"  {node_name:25} : {count:3} executions  [{status}]")
        lines.append("")

        # Quality Supervisor Analysis (most important for loop diagnosis)
        lines.append("=" * 80)
        lines.append("QUALITY SUPERVISOR ROUTING DECISIONS")
        lines.append("=" * 80)
        lines.append("This node controls whether to exit to Synthesizer or loop back.")
        lines.append("")

        qs_progression = self.analyze_node_progression('Quality Supervisor')
        for entry in qs_progression:
            lines.append(f"--- Execution #{entry['execution']} ---")

            # Routing decision
            routing = entry['routing_keywords']
            if routing.get('exit_to_synthesizer'):
                lines.append("  ROUTING: -> Synthesizer (EXIT LOOP)")
            elif routing.get('loop_to_financial'):
                lines.append("  ROUTING: -> Financial Modeler (CONTINUE LOOP)")
            elif routing.get('loop_to_dot_connector'):
                lines.append("  ROUTING: -> Dot Connector (CONTINUE LOOP)")
            elif routing.get('loop_to_research'):
                lines.append("  ROUTING: -> Research Supervisor (RESTART)")
            else:
                lines.append("  ROUTING: NO CLEAR ROUTING KEYWORD FOUND!")

            lines.append(f"  Key Output: {entry['key_snippet'][:150]}")
            lines.append("")

        # DCF Validator Analysis
        lines.append("=" * 80)
        lines.append("DCF VALIDATOR PROGRESSION")
        lines.append("=" * 80)
        lines.append("Shows whether DCF is being validated or triggering revisions.")
        lines.append("")

        dcf_progression = self.analyze_node_progression('DCF Validator')
        prev_metrics = {}
        for entry in dcf_progression:
            lines.append(f"--- Execution #{entry['execution']} ---")

            routing = entry['routing_keywords']
            if routing.get('validated'):
                lines.append("  STATUS: DCF VALIDATED")
            elif routing.get('needs_revision'):
                lines.append("  STATUS: NEEDS_PARAMETER_REVISION (triggers loop!)")
            else:
                lines.append("  STATUS: NO CLEAR STATUS")

            # Quality metrics comparison
            metrics = entry['quality_metrics']
            if metrics:
                lines.append(f"  Metrics: {metrics}")

                # Check if improving
                if prev_metrics:
                    improvements = []
                    regressions = []
                    for key in metrics:
                        if key in prev_metrics:
                            try:
                                curr = float(metrics[key])
                                prev = float(prev_metrics[key])
                                if curr != prev:
                                    if key == 'divergence':
                                        # Lower divergence is better
                                        if curr < prev:
                                            improvements.append(f"{key}: {prev}% -> {curr}%")
                                        else:
                                            regressions.append(f"{key}: {prev}% -> {curr}%")
                            except:
                                pass

                    if improvements:
                        lines.append(f"  IMPROVING: {', '.join(improvements)}")
                    if regressions:
                        lines.append(f"  REGRESSING: {', '.join(regressions)}")

                prev_metrics = metrics

            lines.append(f"  Key Output: {entry['key_snippet'][:150]}")
            lines.append("")

        # Financial Modeler Analysis
        lines.append("=" * 80)
        lines.append("FINANCIAL MODELER PROGRESSION")
        lines.append("=" * 80)
        lines.append("Shows how valuation targets changed across iterations.")
        lines.append("")

        fm_progression = self.analyze_node_progression('Financial Modeler')
        targets = []
        for entry in fm_progression:
            lines.append(f"--- Execution #{entry['execution']} ---")
            metrics = entry['quality_metrics']
            if metrics.get('dcf_target'):
                target = metrics['dcf_target']
                targets.append(float(target))
                lines.append(f"  DCF Target: {target}")
            if metrics.get('wacc'):
                lines.append(f"  WACC: {metrics['wacc']}%")
            lines.append(f"  Key Output: {entry['key_snippet'][:150]}")
            lines.append("")

        # Target convergence analysis
        if len(targets) > 1:
            lines.append("-" * 40)
            lines.append("TARGET CONVERGENCE ANALYSIS:")
            variance = max(targets) - min(targets)
            avg = sum(targets) / len(targets)
            lines.append(f"  Targets: {targets}")
            lines.append(f"  Range: {min(targets):.2f} - {max(targets):.2f} (spread: {variance:.2f})")
            lines.append(f"  Average: {avg:.2f}")
            if variance < 5:
                lines.append("  ASSESSMENT: Targets are converging (good)")
            elif variance < 20:
                lines.append("  ASSESSMENT: Targets have moderate variance")
            else:
                lines.append("  ASSESSMENT: Targets are NOT converging (stuck loop!)")
            lines.append("")

        # Loop Detection Details
        lines.append("=" * 80)
        lines.append("LOOP DETECTION DETAILS")
        lines.append("=" * 80)

        if loops:
            for loop in loops[:10]:  # Show first 10 loops
                lines.append(f"  Pattern from iteration {loop['first_occurrence']} "
                           f"repeated at iteration {loop['repeated_at']}")
                lines.append(f"    Nodes: {' -> '.join(loop['nodes'][:5])}")
        else:
            lines.append("  No exact repeating patterns found.")
        lines.append("")

        # Diagnosis
        lines.append("=" * 80)
        lines.append("DIAGNOSIS")
        lines.append("=" * 80)

        qs_count = len(self.node_outputs.get('Quality Supervisor', []))
        fm_count = len(self.node_outputs.get('Financial Modeler', []))
        dcf_count = len(self.node_outputs.get('DCF Validator', []))
        synth_count = len(self.node_outputs.get('Synthesizer', []))

        if synth_count == 0:
            lines.append("PROBLEM: Synthesizer was NEVER reached!")
            lines.append("  -> Quality Supervisor never output 'ROUTE: Synthesizer'")

        if qs_count > 5 and fm_count > 5:
            lines.append("PROBLEM: Quality Supervisor and Financial Modeler in feedback loop")
            lines.append("  -> Quality Supervisor keeps routing to Financial Modeler")
            lines.append("  -> Check if Quality Supervisor has clear exit criteria")

        # Check if improvements are happening
        if len(targets) > 2:
            first_half = targets[:len(targets)//2]
            second_half = targets[len(targets)//2:]
            first_variance = max(first_half) - min(first_half) if first_half else 0
            second_variance = max(second_half) - min(second_half) if second_half else 0

            if second_variance >= first_variance:
                lines.append("PROBLEM: Iterations are NOT improving convergence")
                lines.append("  -> Variance not decreasing: loop is UNPRODUCTIVE")
            else:
                lines.append("OK: Variance is decreasing, iterations may be productive")

        lines.append("")
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)

        return "\n".join(lines)


def run_iteration_analysis():
    """Entry point for iteration analysis CLI"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_iterations.py <workflow_result.json>")
        print("Example: python scripts/analyze_iterations.py context/6682_HK_workflow_result.json")
        sys.exit(1)

    result_file = sys.argv[1]

    if not Path(result_file).exists():
        print(f"Error: File not found: {result_file}")
        sys.exit(1)

    analyzer = IterationAnalyzer(result_file)
    analyzer.load_workflow_result()
    report = analyzer.generate_iteration_report()

    # Print to console
    print(report)

    # Also save to file
    output_file = Path(result_file).stem + "_iteration_analysis.txt"
    output_path = Path("context") / output_file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    run_iteration_analysis()
