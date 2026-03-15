# cli-anything-vibelab

A stateful Python CLI harness for the [VibeLab](https://github.com/OpenLAIR/VibeLab)
AI research workspace.

## Installation

```bash
pip install -e /path/to/agent-harness
# or from PyPI once published:
pip install cli-anything-vibelab
```

## Quick start

```bash
# Check server status (no login required)
cli-anything-vibelab auth status

# Log in — token is stored in ~/.vibelab_session.json
cli-anything-vibelab auth login --username admin --password secret

# List all projects
cli-anything-vibelab projects list

# Pipe JSON output to jq
cli-anything-vibelab --json projects list | jq '.[].display_name'

# List sessions for a project
cli-anything-vibelab sessions list <project-id>

# Read messages from a session
cli-anything-vibelab sessions messages <session-id>

# Manage API keys
cli-anything-vibelab settings api-keys list
cli-anything-vibelab settings api-keys create "my-key"
cli-anything-vibelab settings api-keys delete 42

# Rename / delete a project
cli-anything-vibelab projects rename <project-id> "New Name"
cli-anything-vibelab projects delete <project-id>

# Log out
cli-anything-vibelab auth logout
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `VIBELAB_URL` | Server base URL | `http://localhost:3001` |
| `VIBELAB_TOKEN` | Inject token without session file | *(session file)* |

The `--url URL` flag overrides `VIBELAB_URL` for a single invocation.

## Running tests

```bash
# Unit tests only (no server required)
pytest cli_anything/vibelab/tests/test_core.py -v

# Full E2E tests (requires running server)
VIBELAB_E2E=1 VIBELAB_USER=admin VIBELAB_PASS=secret \
    pytest cli_anything/vibelab/tests/ -v
```
