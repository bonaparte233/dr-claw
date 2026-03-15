# vibelab

A stateful Python CLI harness for the VibeLab / Dr. Claw AI research workspace.

## Installation

```bash
pip install -e /path/to/agent-harness
```

The console entrypoint is `vibelab`.

## Quick start

```bash
# Check server status (no login required)
vibelab auth status

# Log in; token is stored in ~/.vibelab_session.json
vibelab auth login --username admin --password secret

# List all projects
vibelab projects list

# Add a local project path
vibelab projects add /path/to/project --name "Demo Project"

# Pipe JSON output to jq
vibelab --json projects list | jq '.[].displayName'

# List Claude sessions for a project
vibelab sessions list <project-ref>

# List Cursor sessions for a project
vibelab sessions list <project-ref> --provider cursor

# Read messages from a session
vibelab sessions messages <project-ref> <session-id> --provider claude

# Send a Claude message into a project
vibelab chat send --project <project-ref> --message "Summarize current progress"

# Show TaskMaster progress
vibelab taskmaster summary <project-ref>
vibelab taskmaster next-guidance <project-ref>

# Generate a mobile/OpenClaw report without sending
vibelab openclaw report --project <project-ref> --dry-run

# Configure and send through OpenClaw
vibelab openclaw configure --push-channel feishu:<chat_id>
vibelab openclaw report --project <project-ref>
```

## Project references

Anywhere the CLI accepts `<project-ref>`, you can pass one of:

- the project `name`
- the project `displayName`
- the project filesystem `path` / `fullPath`

For `chat send`, a real filesystem path is always resolved before sending the WebSocket command.

## TaskMaster commands

```bash
vibelab taskmaster status
vibelab taskmaster detect <project-ref>
vibelab taskmaster detect-all
vibelab taskmaster init <project-ref>
vibelab taskmaster tasks <project-ref>
vibelab taskmaster next <project-ref>
vibelab taskmaster next-guidance <project-ref>
vibelab taskmaster summary <project-ref>
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `VIBELAB_URL` | Server base URL | `http://localhost:3001` |
| `VIBELAB_TOKEN` | Inject token without session file | session file |

The `--url URL` flag overrides `VIBELAB_URL` for a single invocation.

## Running tests

```bash
python3 -m pytest agent-harness/cli_anything/vibelab/tests/test_core.py -q
PYTHONPATH=agent-harness python3 -m cli_anything.vibelab.vibelab_cli --help
PYTHONPATH=agent-harness python3 -m cli_anything.vibelab.vibelab_cli taskmaster --help
PYTHONPATH=agent-harness python3 -m cli_anything.vibelab.vibelab_cli openclaw report --help
```
