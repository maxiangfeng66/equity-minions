"""
Claude Minions - Smart Auto Visualizer
Automatically detects projects, Claude sessions, file activity, and git changes.
No configuration needed - just run it.
"""

import http.server
import socketserver
import json
import os
import webbrowser
import glob
import time
import subprocess
from http.server import SimpleHTTPRequestHandler
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta

PORT = 8080
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# Scan these locations
SEARCH_PATHS = [
    os.path.expanduser('~/Desktop'),
    os.path.expanduser('~/Documents'),
    os.path.expanduser('~/Projects'),
    os.path.expanduser('~/repos'),
    os.path.expanduser('~/code'),
]

# Track file modification times
file_activity = {}
last_scan = 0
SCAN_INTERVAL = 5  # seconds

def find_projects():
    """Auto-discover all projects"""
    projects = []
    seen = set()

    for search_path in SEARCH_PATHS:
        if not os.path.exists(search_path):
            continue

        # Find projects by various indicators
        for item in os.listdir(search_path):
            project_path = os.path.join(search_path, item)
            if not os.path.isdir(project_path):
                continue
            if item.startswith('.'):
                continue
            if project_path in seen:
                continue

            # Check if it's a real project
            indicators = [
                '.git', '.claude', 'package.json', 'requirements.txt',
                'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle',
                'minions.json', 'session_state.json', '.vscode'
            ]

            is_project = False
            for ind in indicators:
                if os.path.exists(os.path.join(project_path, ind)):
                    is_project = True
                    break
                # Check in context subfolder too
                if os.path.exists(os.path.join(project_path, 'context', ind)):
                    is_project = True
                    break

            if is_project:
                seen.add(project_path)
                projects.append({
                    'name': item,
                    'path': project_path
                })

    return sorted(projects, key=lambda p: get_project_activity_time(p['path']), reverse=True)


def get_project_activity_time(project_path):
    """Get the most recent file modification time in a project"""
    try:
        latest = 0
        for root, dirs, files in os.walk(project_path):
            # Skip hidden and node_modules
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
            for f in files[:20]:  # Limit files checked per folder
                try:
                    mtime = os.path.getmtime(os.path.join(root, f))
                    if mtime > latest:
                        latest = mtime
                except:
                    pass
            break  # Only check top level for speed
        return latest
    except:
        return 0


def analyze_project(project_path):
    """Smart analysis of a project - auto-generate agents and tasks"""
    project_name = os.path.basename(project_path)
    agents = []
    tasks = []

    # 1. Check for Claude Code session
    claude_info = detect_claude_session(project_path)

    # 2. Check for manual config files
    config_data = load_config_files(project_path)

    # 3. Detect project type
    project_type = detect_project_type(project_path)

    # 4. Get recent file activity
    recent_files = get_recent_files(project_path)

    # 5. Get git status
    git_info = get_git_info(project_path)

    # Build agents based on what we found
    agent_id = 0

    # Orchestrator - always present
    orchestrator_task = "Monitoring project"
    orchestrator_status = "idle"

    if claude_info['active']:
        orchestrator_task = claude_info.get('current_task', 'Claude Code session active')
        orchestrator_status = "active"
    elif recent_files:
        orchestrator_task = f"Watching {len(recent_files)} active files"
        orchestrator_status = "active"

    agents.append({
        'id': 'orchestrator',
        'name': 'Orchestrator',
        'type': 'orchestrator',
        'status': orchestrator_status,
        'task': orchestrator_task,
        'progress': calculate_progress(git_info, config_data),
        'tier': 0,
        'position': {'x': 0, 'z': -2},
        'connections': []
    })

    # File watcher agents - based on recent activity
    positions = [
        {'x': -4, 'z': 2}, {'x': 0, 'z': 2}, {'x': 4, 'z': 2},
        {'x': -4, 'z': 5}, {'x': 0, 'z': 5}, {'x': 4, 'z': 5},
    ]

    # Group files by type/purpose
    file_groups = categorize_files(recent_files)

    agent_types = {
        'code': ('researcher', 'Coder'),
        'test': ('critic', 'Tester'),
        'config': ('analyst', 'Config'),
        'docs': ('debater', 'Docs'),
        'style': ('analyst', 'Styler'),
        'data': ('researcher', 'Data'),
    }

    for category, files in file_groups.items():
        if agent_id >= 6:
            break
        if not files:
            continue

        agent_type, agent_label = agent_types.get(category, ('researcher', 'Worker'))
        most_recent = files[0]
        time_ago = format_time_ago(most_recent['mtime'])

        is_active = (time.time() - most_recent['mtime']) < 300  # Active if edited in last 5 min

        agent = {
            'id': f'{agent_type}-{agent_id + 1}',
            'name': f'{agent_label} {"Alpha Beta Gamma Delta Epsilon Zeta".split()[agent_id]}',
            'type': agent_type,
            'status': 'active' if is_active else 'idle',
            'task': f'{most_recent["name"]} ({time_ago})',
            'progress': 100 if not is_active else 50,
            'tier': 1 + (agent_id // 3),
            'position': positions[agent_id],
            'connections': []
        }

        agents[0]['connections'].append({'to': agent['id'], 'type': 'command'})
        agents.append(agent)
        agent_id += 1

    # Add idle agents if we don't have enough
    while agent_id < 3:
        agents.append({
            'id': f'worker-{agent_id + 1}',
            'name': f'Worker {"Alpha Beta Gamma".split()[agent_id]}',
            'type': 'researcher',
            'status': 'idle',
            'task': 'Standing by',
            'progress': 0,
            'tier': 1,
            'position': positions[agent_id],
            'connections': []
        })
        agent_id += 1

    # Build tasks from git and config
    if config_data.get('tasks'):
        tasks = config_data['tasks']
    elif config_data.get('equities'):
        # Legacy equity format
        for eq in config_data.get('equities', []):
            tasks.append({
                'ticker': eq.get('ticker', ''),
                'company': eq.get('company', ''),
                'status': eq.get('status', 'pending')
            })
        for eq in config_data.get('completed', []):
            tasks.append({
                'ticker': eq.get('ticker', ''),
                'company': eq.get('company', ''),
                'status': 'completed'
            })
    else:
        # Generate from git
        if git_info.get('uncommitted'):
            tasks.append({
                'ticker': 'UNCOMMITTED',
                'company': f"{git_info['uncommitted']} uncommitted changes",
                'status': 'active'
            })
        for commit in git_info.get('recent_commits', [])[:5]:
            tasks.append({
                'ticker': commit['hash'][:7],
                'company': commit['message'][:50],
                'status': 'completed'
            })

    return {
        'agents': agents,
        'tasks': tasks,
        'project': project_name,
        'type': project_type,
        'claude_active': claude_info['active']
    }


def detect_claude_session(project_path):
    """Check if Claude Code is active in this project"""
    claude_dir = os.path.join(project_path, '.claude')
    info = {'active': False}

    if not os.path.exists(claude_dir):
        return info

    # Check for recent session files
    try:
        for f in os.listdir(claude_dir):
            fpath = os.path.join(claude_dir, f)
            if os.path.isfile(fpath):
                mtime = os.path.getmtime(fpath)
                # Active if modified in last 5 minutes
                if time.time() - mtime < 300:
                    info['active'] = True
                    info['last_activity'] = mtime

                    # Try to read session info
                    if f.endswith('.json'):
                        try:
                            with open(fpath, 'r', encoding='utf-8') as jf:
                                data = json.load(jf)
                                if 'current_task' in data:
                                    info['current_task'] = data['current_task']
                        except:
                            pass
    except:
        pass

    return info


def load_config_files(project_path):
    """Load any config files (minions.json, session_state.json)"""
    data = {}

    for filename in ['minions.json', 'context/session_state.json', 'session_state.json']:
        filepath = os.path.join(project_path, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    break
            except:
                pass

    return data


def detect_project_type(project_path):
    """Detect what kind of project this is"""
    indicators = {
        'package.json': 'node',
        'requirements.txt': 'python',
        'Cargo.toml': 'rust',
        'go.mod': 'go',
        'pom.xml': 'java',
        'build.gradle': 'java',
        'Gemfile': 'ruby',
        'composer.json': 'php',
    }

    for filename, ptype in indicators.items():
        if os.path.exists(os.path.join(project_path, filename)):
            return ptype

    return 'unknown'


def get_recent_files(project_path, limit=20):
    """Get recently modified files"""
    files = []
    now = time.time()
    cutoff = now - 86400  # Last 24 hours

    try:
        for root, dirs, filenames in os.walk(project_path):
            # Skip hidden dirs, node_modules, etc.
            dirs[:] = [d for d in dirs if not d.startswith('.')
                      and d not in ('node_modules', '__pycache__', 'venv', 'dist', 'build', '.git')]

            for fname in filenames:
                if fname.startswith('.'):
                    continue

                fpath = os.path.join(root, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                    if mtime > cutoff:
                        files.append({
                            'name': fname,
                            'path': fpath,
                            'mtime': mtime,
                            'rel_path': os.path.relpath(fpath, project_path)
                        })
                except:
                    pass

            if len(files) > 100:  # Limit for performance
                break

    except:
        pass

    # Sort by most recent
    files.sort(key=lambda x: x['mtime'], reverse=True)
    return files[:limit]


def categorize_files(files):
    """Group files by type"""
    categories = {
        'code': [],
        'test': [],
        'config': [],
        'docs': [],
        'style': [],
        'data': [],
    }

    extensions = {
        'code': ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.c', '.cpp', '.rb', '.php'],
        'test': ['test.py', 'test.js', '.spec.', '_test.'],
        'config': ['.json', '.yaml', '.yml', '.toml', '.ini', '.env', '.config'],
        'docs': ['.md', '.txt', '.rst', '.doc'],
        'style': ['.css', '.scss', '.less', '.sass'],
        'data': ['.csv', '.sql', '.db'],
    }

    for f in files:
        name = f['name'].lower()
        categorized = False

        # Check test first (overrides code)
        for pattern in extensions['test']:
            if pattern in name:
                categories['test'].append(f)
                categorized = True
                break

        if categorized:
            continue

        # Check other categories
        for cat, exts in extensions.items():
            if cat == 'test':
                continue
            for ext in exts:
                if name.endswith(ext):
                    categories[cat].append(f)
                    categorized = True
                    break
            if categorized:
                break

        if not categorized:
            categories['code'].append(f)  # Default to code

    return categories


def get_git_info(project_path):
    """Get git status and recent commits"""
    info = {'uncommitted': 0, 'recent_commits': [], 'branch': 'unknown'}

    git_dir = os.path.join(project_path, '.git')
    if not os.path.exists(git_dir):
        return info

    try:
        # Get current branch
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info['branch'] = result.stdout.strip()

        # Get uncommitted changes count
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info['uncommitted'] = len([l for l in result.stdout.strip().split('\n') if l])

        # Get recent commits
        result = subprocess.run(
            ['git', 'log', '--oneline', '-10'],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(' ', 1)
                    if len(parts) == 2:
                        info['recent_commits'].append({
                            'hash': parts[0],
                            'message': parts[1]
                        })

    except:
        pass

    return info


def calculate_progress(git_info, config_data):
    """Calculate overall progress"""
    if config_data.get('completed') and config_data.get('equities'):
        total = len(config_data['completed']) + len(config_data['equities'])
        if total > 0:
            return int((len(config_data['completed']) / total) * 100)

    # Fallback: estimate from git
    if git_info.get('uncommitted', 0) > 0:
        return 50  # Work in progress
    return 0


def format_time_ago(timestamp):
    """Format timestamp as 'X ago'"""
    diff = time.time() - timestamp
    if diff < 60:
        return 'just now'
    elif diff < 3600:
        mins = int(diff / 60)
        return f'{mins}m ago'
    elif diff < 86400:
        hours = int(diff / 3600)
        return f'{hours}h ago'
    else:
        days = int(diff / 86400)
        return f'{days}d ago'


class SmartHandler(SimpleHTTPRequestHandler):
    """HTTP handler with smart auto-detection"""

    projects = []
    current_project = None
    state = {'agents': [], 'tasks': [], 'project': None}
    last_refresh = 0

    @classmethod
    def refresh_projects(cls):
        cls.projects = find_projects()
        if cls.projects and not cls.current_project:
            cls.current_project = cls.projects[0]

    @classmethod
    def refresh_state(cls):
        now = time.time()
        if now - cls.last_refresh < 2:  # Rate limit
            return
        cls.last_refresh = now

        if cls.current_project:
            cls.state = analyze_project(cls.current_project['path'])

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == '/':
            self.path = '/Claude%20Minions.html'
            return super().do_GET()

        elif parsed.path == '/api/projects':
            self.refresh_projects()
            self.send_json({
                'projects': [{'name': p['name'], 'path': p['path']} for p in self.projects],
                'current': self.current_project['name'] if self.current_project else None
            })

        elif parsed.path == '/api/state':
            self.refresh_state()
            self.send_json(self.state)

        elif parsed.path.startswith('/api/select/'):
            project_name = urllib.parse.unquote(parsed.path[12:])
            for p in self.projects:
                if p['name'] == project_name:
                    self.__class__.current_project = p
                    self.__class__.last_refresh = 0
                    self.refresh_state()
                    break
            self.send_json({'success': True, 'project': project_name})

        else:
            return super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def send_json(self, data):
        response = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        pass  # Quiet


def main():
    SmartHandler.refresh_projects()
    if SmartHandler.current_project:
        SmartHandler.refresh_state()

    print()
    print("  ==========================================")
    print("       Claude Minions - Smart Viewer")
    print("  ==========================================")
    print()
    print(f"  Server: http://localhost:{PORT}")
    print()
    print(f"  Projects found: {len(SmartHandler.projects)}")
    for i, p in enumerate(SmartHandler.projects[:5]):
        marker = " *" if SmartHandler.current_project and p['name'] == SmartHandler.current_project['name'] else ""
        print(f"    {p['name']}{marker}")
    if len(SmartHandler.projects) > 5:
        print(f"    ... and {len(SmartHandler.projects) - 5} more")
    print()
    print("  Auto-detects:")
    print("    - Claude Code sessions")
    print("    - File changes in real-time")
    print("    - Git commits and status")
    print()
    print("  Press Ctrl+C to stop")
    print()

    webbrowser.open(f'http://localhost:{PORT}')

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), SmartHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == '__main__':
    main()
