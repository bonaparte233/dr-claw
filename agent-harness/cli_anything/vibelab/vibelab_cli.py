"""
cli-anything-vibelab — CLI harness for the VibeLab AI research workspace.

Entry point: cli_anything.vibelab.vibelab_cli:cli

Usage overview:
  cli-anything-vibelab [--json] [--url URL] <command> [<subcommand>] [options]

Global flags (must come before the command):
  --json        Output all results as JSON to stdout.
  --url URL     Override the VibeLab server URL for this invocation.

Sub-command tree:
  auth
    login     Authenticate and store token in ~/.vibelab_session.json
    logout    Remove the local session file
    status    Check server auth status (no token required)
  projects
    list      List all projects
    rename    Rename a project
    delete    Delete a project
  sessions
    list      List sessions for a project
    messages  Retrieve messages for a session
  settings
    api-keys
      list    List API keys
      create  Create an API key
      delete  Delete an API key
  skills
    list      List global skills
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import warnings
warnings.filterwarnings("ignore")   # suppress urllib3 LibreSSL warning on macOS

import click
import requests

from .core.session import VibeLab, NotLoggedInError, SESSION_FILE, _load_session_file, _save_session_file
from .core import projects as projects_mod
from .core import conversations as conversations_mod
from .core import settings as settings_mod
from .core import daemon as daemon_mod
from .core import chat as chat_mod
from .utils.output import output, success, error, info


# ---------------------------------------------------------------------------
# Shared context object
# ---------------------------------------------------------------------------

class Context:
    def __init__(self, json_mode: bool, client: VibeLab) -> None:
        self.json_mode = json_mode
        self.client = client


pass_context = click.make_pass_decorator(Context)


# ---------------------------------------------------------------------------
# Error handling helper
# ---------------------------------------------------------------------------

def _handle_error(exc: Exception, json_mode: bool) -> None:
    """Print a tidy error message and exit with code 1."""
    if isinstance(exc, NotLoggedInError):
        error(str(exc))
    elif isinstance(exc, requests.HTTPError):
        try:
            detail = exc.response.json().get("error", exc.response.text)
        except Exception:
            detail = str(exc)
        error(f"HTTP {exc.response.status_code}: {detail}")
    elif isinstance(exc, requests.ConnectionError):
        error(f"Could not connect to the VibeLab server. Is it running?  ({exc})")
    elif isinstance(exc, requests.Timeout):
        error("Request timed out.")
    else:
        error(str(exc))
    sys.exit(1)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.option("--json", "json_mode", is_flag=True, default=False,
              help="Output results as JSON.")
@click.option("--url", "url_override", default=None, metavar="URL",
              help="Override the VibeLab server URL.")
@click.pass_context
def cli(ctx: click.Context, json_mode: bool, url_override: str) -> None:
    """VibeLab CLI harness — manage projects, sessions and settings."""
    ctx.ensure_object(dict)
    client = VibeLab(url_override=url_override)
    ctx.obj = Context(json_mode=json_mode, client=client)


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------

@cli.group()
def auth() -> None:
    """Authentication commands."""


@auth.command("login")
@click.option("--username", "-u", prompt="Username", help="VibeLab username.")
@click.option("--password", "-p", prompt="Password", hide_input=True,
              help="VibeLab password.")
@pass_context
def auth_login(ctx: Context, username: str, password: str) -> None:
    """Log in and store the JWT token locally."""
    try:
        data = ctx.client.login(username, password)
        user = data.get("user", {})
        success(
            f"Logged in as '{user.get('username', username)}'. "
            f"Token stored in ~/.vibelab_session.json",
            json_mode=ctx.json_mode,
        )
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@auth.command("logout")
@pass_context
def auth_logout(ctx: Context) -> None:
    """Remove the local session file (token is not revoked server-side)."""
    ctx.client.logout()
    success("Logged out. Session file removed.", json_mode=ctx.json_mode)


@auth.command("status")
@pass_context
def auth_status(ctx: Context) -> None:
    """Check whether the server needs initial setup."""
    try:
        resp = ctx.client.get_unauthenticated("/api/auth/status")
        data = resp.json()
        token = ctx.client.get_token()
        data["has_local_token"] = token is not None
        output(data, json_mode=ctx.json_mode, title="Auth Status")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


# ---------------------------------------------------------------------------
# projects
# ---------------------------------------------------------------------------

@cli.group()
def projects() -> None:
    """Project management commands."""


@projects.command("list")
@pass_context
def projects_list(ctx: Context) -> None:
    """List all projects."""
    try:
        items = projects_mod.list_projects(ctx.client)
        output(items, json_mode=ctx.json_mode, title="Projects")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@projects.command("rename")
@click.argument("project_id")
@click.argument("new_name")
@pass_context
def projects_rename(ctx: Context, project_id: str, new_name: str) -> None:
    """Rename PROJECT_ID to NEW_NAME."""
    try:
        projects_mod.rename_project(ctx.client, project_id, new_name)
        success(f"Project '{project_id}' renamed to '{new_name}'.", json_mode=ctx.json_mode)
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@projects.command("delete")
@click.argument("project_id")
@click.confirmation_option(prompt="Are you sure you want to delete this project?")
@pass_context
def projects_delete(ctx: Context, project_id: str) -> None:
    """Delete project PROJECT_ID."""
    try:
        projects_mod.delete_project(ctx.client, project_id)
        success(f"Project '{project_id}' deleted.", json_mode=ctx.json_mode)
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


# ---------------------------------------------------------------------------
# sessions
# ---------------------------------------------------------------------------

@cli.group()
def sessions() -> None:
    """Conversation session commands."""


@sessions.command("list")
@click.argument("project_id")
@pass_context
def sessions_list(ctx: Context, project_id: str) -> None:
    """List sessions for PROJECT_ID."""
    try:
        items = conversations_mod.list_sessions(ctx.client, project_id)
        output(items, json_mode=ctx.json_mode, title=f"Sessions for project {project_id}")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@sessions.command("messages")
@click.argument("session_id")
@pass_context
def sessions_messages(ctx: Context, session_id: str) -> None:
    """Get all messages for SESSION_ID."""
    try:
        items = conversations_mod.get_session_messages(ctx.client, session_id)
        output(items, json_mode=ctx.json_mode, title=f"Messages for session {session_id}")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------

@cli.group()
def settings() -> None:
    """Settings management commands."""


@settings.group("api-keys")
def settings_api_keys() -> None:
    """API key management."""


@settings_api_keys.command("list")
@pass_context
def api_keys_list(ctx: Context) -> None:
    """List all API keys."""
    try:
        items = settings_mod.list_api_keys(ctx.client)
        output(items, json_mode=ctx.json_mode, title="API Keys")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@settings_api_keys.command("create")
@click.argument("key_name")
@pass_context
def api_keys_create(ctx: Context, key_name: str) -> None:
    """Create a new API key named KEY_NAME."""
    try:
        key = settings_mod.create_api_key(ctx.client, key_name)
        output(key, json_mode=ctx.json_mode, title="New API Key")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@settings_api_keys.command("delete")
@click.argument("key_id")
@click.confirmation_option(prompt="Are you sure you want to delete this API key?")
@pass_context
def api_keys_delete(ctx: Context, key_id: str) -> None:
    """Delete API key KEY_ID."""
    try:
        settings_mod.delete_api_key(ctx.client, key_id)
        success(f"API key '{key_id}' deleted.", json_mode=ctx.json_mode)
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


# ---------------------------------------------------------------------------
# skills
# ---------------------------------------------------------------------------

@cli.group()
def skills() -> None:
    """Skill management commands."""


@skills.command("list")
@pass_context
def skills_list(ctx: Context) -> None:
    """List global skills."""
    try:
        resp = ctx.client.get("/api/skills")
        data = resp.json()
        # Skills endpoint returns a file tree; flatten top-level names for display
        if isinstance(data, list):
            # Each item may be a tree node with 'name', 'type', 'children'
            display = [
                {
                    "name": item.get("name", ""),
                    "type": item.get("type", ""),
                    "path": item.get("path", ""),
                }
                for item in data
            ]
        elif isinstance(data, dict):
            display = data
        else:
            display = data
        output(display, json_mode=ctx.json_mode, title="Skills")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


# ---------------------------------------------------------------------------
# server (daemon)
# ---------------------------------------------------------------------------

@cli.group()
def server() -> None:
    """Start / stop the VibeLab Node.js server as a background daemon."""


@server.command("on")
@click.option("--path", "server_path", default=None, metavar="PATH",
              help="Path to the VibeLab installation directory (saved for future use).")
@click.option("--port", default=None, type=int, metavar="PORT",
              help="Port to listen on (default: 3001).")
@pass_context
def server_on(ctx: Context, server_path: str, port: int) -> None:
    """Start the VibeLab server as a daemon. Logs → ~/.vibelab/logs/server.log"""
    try:
        result = daemon_mod.server_start(path_override=server_path, port=port)
        msg = f"Server started (PID {result['pid']}). Logs: {result['log_file']}"
        if ctx.json_mode:
            output(result, json_mode=True)
        else:
            success(msg, json_mode=False)
            info(f"  logs : {result['log_file']}")
            info(f"  path : {result['server_path']}")
    except Exception as exc:
        error(str(exc))
        sys.exit(1)


@server.command("off")
@pass_context
def server_off(ctx: Context) -> None:
    """Stop the running VibeLab daemon."""
    try:
        result = daemon_mod.server_stop()
        if ctx.json_mode:
            output(result, json_mode=True)
        else:
            if result["stopped"]:
                success(result["message"], json_mode=False)
            else:
                info(result["message"])
    except Exception as exc:
        error(str(exc))
        sys.exit(1)


@server.command("status")
@click.option("--logs", "show_logs", is_flag=True, default=False,
              help="Print the last 20 lines of the server log.")
@pass_context
def server_status(ctx: Context, show_logs: bool) -> None:
    """Show whether the daemon is running."""
    try:
        st = daemon_mod.server_status()
        if ctx.json_mode:
            output(st, json_mode=True)
        else:
            state = "RUNNING" if st["running"] else "STOPPED"
            color = "\033[32m" if st["running"] else "\033[31m"
            reset = "\033[0m"
            click.echo(f"  status : {color}{state}{reset}")
            if st["pid"]:
                click.echo(f"  pid    : {st['pid']}")
            click.echo(f"  logs   : {st['log_file']}")
            if show_logs and st["log_tail"]:
                click.echo("\n--- last 20 log lines ---")
                click.echo(st["log_tail"])
    except Exception as exc:
        error(str(exc))
        sys.exit(1)


@server.command("logs")
@click.option("-n", "lines", default=50, show_default=True,
              help="Number of lines to show.")
@click.option("-f", "follow", is_flag=True, default=False,
              help="Follow the log (like tail -f).")
@pass_context
def server_logs(ctx: Context, lines: int, follow: bool) -> None:
    """Tail the server log file."""
    import subprocess as sp
    log_file = str(daemon_mod.LOG_FILE)
    if not daemon_mod.LOG_FILE.exists():
        info("No log file yet. Start the server first.")
        return
    if follow:
        try:
            sp.run(["tail", f"-{lines}", "-f", log_file])
        except KeyboardInterrupt:
            pass
    else:
        sp.run(["tail", f"-{lines}", log_file])


# ---------------------------------------------------------------------------
# chat
# ---------------------------------------------------------------------------

@cli.group()
def chat() -> None:
    """Chat with Claude sessions via WebSocket."""


@chat.command("send")
@click.option("--project", "project_id", required=True, metavar="PROJECT",
              help="Project ID or path to send the message to.")
@click.option("--message", "-m", "message", required=True, metavar="TEXT",
              help="Message to send to the Claude session.")
@click.option("--session", "session_id", default=None, metavar="SESSION_ID",
              help="Session ID to resume (omit to start a new session).")
@pass_context
def chat_send(ctx: Context, project_id: str, message: str, session_id: str) -> None:
    """Send a message to a Claude session and print the reply."""
    try:
        result = chat_mod.send_message(
            ctx.client,
            project_path=project_id,
            message=message,
            session_id=session_id or None,
        )
        if ctx.json_mode:
            output(
                {"reply": result["reply"], "session_id": result["session_id"]},
                json_mode=True,
            )
        else:
            click.echo(result["reply"])
            info(f"Session: {result['session_id']}")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@chat.command("sessions")
@pass_context
def chat_sessions(ctx: Context) -> None:
    """List active sessions across all projects."""
    try:
        sessions = chat_mod.get_active_sessions(ctx.client)
        output(sessions, json_mode=ctx.json_mode, title="Active Sessions")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


# ---------------------------------------------------------------------------
# openclaw
# ---------------------------------------------------------------------------

# Path where OpenClaw skill definition will be installed
_OPENCLAW_SKILL_DIR_NAME = "vibelab"
_SKILL_MD_FILENAME = "SKILL.md"

# Path to our own SKILL.md, stored next to this package
import pathlib as _pathlib
_HARNESS_ROOT = _pathlib.Path(__file__).parent.parent.parent  # agent-harness/
_OWN_SKILL_MD = _HARNESS_ROOT / _SKILL_MD_FILENAME


@cli.group()
def openclaw() -> None:
    """OpenClaw integration commands."""


@openclaw.command("install")
@click.option(
    "--openclaw-dir",
    "openclaw_dir",
    default=None,
    metavar="DIR",
    help="Path to the OpenClaw workspace root (default: ~/.openclaw).",
)
@pass_context
def openclaw_install(ctx: Context, openclaw_dir: str) -> None:
    """Install the VibeLab skill into the OpenClaw workspace."""
    if openclaw_dir:
        base = _pathlib.Path(openclaw_dir).expanduser()
    else:
        base = _pathlib.Path.home() / ".openclaw"

    skills_dir = base / "workspace" / "skills" / _OPENCLAW_SKILL_DIR_NAME
    dest = skills_dir / _SKILL_MD_FILENAME

    # Determine source: prefer the SKILL.md from this repo; fall back to generating
    # it inline so the command works even when the repo SKILL.md is absent.
    if _OWN_SKILL_MD.exists():
        source = _OWN_SKILL_MD
    else:
        error(f"SKILL.md not found at {_OWN_SKILL_MD}. Run from the agent-harness repo.")
        sys.exit(1)

    skills_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source), str(dest))

    if ctx.json_mode:
        output({"installed": str(dest), "source": str(source)}, json_mode=True)
    else:
        success(f"VibeLab skill installed to {dest}", json_mode=False)


@openclaw.command("push")
@click.argument("message_text")
@click.option("--to", "channel", default=None, metavar="CHANNEL",
              help="Destination channel (e.g. feishu:<chat_id>). "
                   "Falls back to saved openclaw_push_channel in ~/.vibelab_session.json.")
@pass_context
def openclaw_push(ctx: Context, message_text: str, channel: str) -> None:
    """Send a message via the OpenClaw CLI."""
    if not channel:
        session_data = _load_session_file()
        channel = session_data.get("openclaw_push_channel")
    if not channel:
        error(
            "No channel specified. Use --to <channel> or run "
            "`vibelab openclaw configure --push-channel <channel>` first."
        )
        sys.exit(1)

    cmd = ["openclaw", "message", "send", "--to", channel, "--message", message_text]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            err_output = result.stderr.strip() or result.stdout.strip()
            error(f"openclaw exited with code {result.returncode}: {err_output}")
            sys.exit(result.returncode)
        out = result.stdout.strip()
        if ctx.json_mode:
            output({"sent": True, "channel": channel, "output": out}, json_mode=True)
        else:
            success(f"Message sent to {channel}", json_mode=False)
            if out:
                click.echo(out)
    except FileNotFoundError:
        error("'openclaw' command not found. Is OpenClaw installed and on your PATH?")
        sys.exit(1)
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@openclaw.command("configure")
@click.option("--push-channel", "push_channel", required=True, metavar="CHANNEL",
              help="Default channel for `openclaw push` (e.g. feishu:<chat_id>).")
@pass_context
def openclaw_configure(ctx: Context, push_channel: str) -> None:
    """Save OpenClaw integration settings to ~/.vibelab_session.json."""
    session_data = _load_session_file()
    session_data["openclaw_push_channel"] = push_channel
    _save_session_file(session_data)
    if ctx.json_mode:
        output({"openclaw_push_channel": push_channel}, json_mode=True)
    else:
        success(
            f"Default OpenClaw push channel set to: {push_channel}",
            json_mode=False,
        )


# ---------------------------------------------------------------------------
# Entry point guard
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
