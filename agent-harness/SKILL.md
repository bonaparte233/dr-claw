---
name: vibelab
description: VibeLab AI Research Workspace — manage research projects, query Claude sessions, and track experiment progress
---

# VibeLab Research Skill

VibeLab is a local AI research workspace. Use this skill when the user asks about their research projects, experiments, or wants to interact with their AI coding sessions.

## Setup check
Before using, verify VibeLab is running:
```bash
vibelab server status
```
If not running, start it: `vibelab server on`

## List research projects
```bash
vibelab --json projects list
```
Returns JSON list of projects. Each project has `id`, `name`, `path`, `provider`.

## Send a message to a research session
```bash
vibelab --json chat send --project <project-id> --message "<user message>"
```
This talks to the Claude agent in that project. Returns `{"reply": "...", "session_id": "..."}`.

## Check active sessions
```bash
vibelab --json chat sessions
```

## Switch the active project (user says /use <project-id>)
When the user says `/use <something>`, extract the project identifier, find it via `projects list`, and remember the project-id for subsequent messages in this conversation. Tell the user which project is now active.

## Workflow for user questions about research
1. If user hasn't specified a project, run `projects list` and ask which one (or pick the most recently accessed).
2. Send the message with `chat send --project <id> --message "<user's question>"`.
3. Return the reply as-is.

## Proactive progress updates
VibeLab can push updates to you. To enable: `vibelab openclaw configure --push-channel feishu:<chat_id>`

## Tips
- Project IDs look like encoded paths, e.g. `-Users-david-research-myproject`
- Session IDs are UUIDs
- If `chat send` times out, the Claude session may be processing — try again in a moment
- Use `--json` flag for all commands to get machine-readable output
