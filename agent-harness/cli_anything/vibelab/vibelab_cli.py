"""
vibelab - CLI harness for the VibeLab / Dr. Claw research workspace.

Entry point: cli_anything.vibelab.vibelab_cli:cli

Usage overview:
  vibelab [--json] [--url URL] <command> [<subcommand>] [options]

Global flags (must come before the command):
  --json        Output all results as JSON to stdout.
  --url URL     Override the VibeLab server URL for this invocation.

Sub-command tree:
  auth
    login       Authenticate and store token in ~/.vibelab_session.json
    logout      Remove the local session file
    status      Check server auth status (no token required)
  projects
    list        List all projects
    add         Register a project by filesystem path
    rename      Rename a project display name
    delete      Delete a project
  sessions
    list        List sessions for a project
    messages    Retrieve messages for a session
  taskmaster
    status          Show TaskMaster installation status
    detect          Detect TaskMaster state for a project
    detect-all      Detect TaskMaster state across all projects
    init            Initialize .pipeline files for a project
    tasks           List project tasks
    next            Show the next task
    next-guidance   Show next-task guidance metadata
    summary         Show a compact progress summary
  settings
    api-keys
      list      List API keys
      create    Create an API key
      delete    Delete an API key
  skills
    list        List global skills
  chat
    send        Send a Claude message over WebSocket
    sessions    List active sessions across projects
  openclaw
    install     Install the VibeLab skill into OpenClaw
    configure   Save the default push channel
    push        Send a raw message through OpenClaw
    report      Send a TaskMaster status report through OpenClaw
"""

import json
import os
import shutil
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

warnings.filterwarnings("ignore")

import click
import requests

from .core import chat as chat_mod
from .core import conversations as conversations_mod
from .core import daemon as daemon_mod
from .core import projects as projects_mod
from .core import settings as settings_mod
from .core import taskmaster as taskmaster_mod
from .core.session import (
    SESSION_FILE,
    NotLoggedInError,
    VibeLab,
    _load_session_file,
    _save_session_file,
)
from .utils.output import error, info, output, success


_SESSION_COLLECTIONS = {
    "claude": "sessions",
    "cursor": "cursorSessions",
    "codex": "codexSessions",
    "gemini": "geminiSessions",
}
_PROVIDER_CHOICES = ["claude", "cursor", "codex", "gemini"]
_OPENCLAW_SKILL_DIR_NAME = "vibelab"
_SKILL_MD_FILENAME = "SKILL.md"
_HARNESS_ROOT = Path(__file__).parent.parent.parent
_OWN_SKILL_MD = _HARNESS_ROOT / _SKILL_MD_FILENAME


class Context:
    def __init__(self, json_mode: bool, client: VibeLab) -> None:
        self.json_mode = json_mode
        self.client = client


pass_context = click.make_pass_decorator(Context)


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


def _normalize_path(value: str) -> str:
    return os.path.abspath(os.path.expanduser(value))


def _project_label(project: Dict[str, Any]) -> str:
    return (
        project.get("displayName")
        or project.get("display_name")
        or project.get("name")
        or project.get("fullPath")
        or project.get("path")
        or "unknown"
    )


def _project_identity(project: Dict[str, Any]) -> str:
    return project.get("name") or project.get("fullPath") or project.get("path") or repr(project)


def _resolve_project_ref(
    client: VibeLab,
    project_ref: str,
    allow_path_fallback: bool = False,
) -> Dict[str, Any]:
    """Resolve a project name, display name, or filesystem path to a project."""
    ref = (project_ref or "").strip()
    if not ref:
        raise ValueError("Project reference is required.")

    projects = projects_mod.list_projects(client)
    if not isinstance(projects, list):
        raise ValueError("Failed to load VibeLab projects.")

    ref_lower = ref.lower()
    maybe_path = None
    if os.path.isabs(ref) or ref.startswith("~") or ref.startswith(".") or "/" in ref:
        maybe_path = _normalize_path(ref)

    matches: List[tuple[int, Dict[str, Any]]] = []
    for project in projects:
        if not isinstance(project, dict):
            continue

        score = -1
        project_name = str(project.get("name") or "").strip()
        display_name = str(project.get("displayName") or project.get("display_name") or "").strip()
        project_paths = [
            str(project.get("path") or "").strip(),
            str(project.get("fullPath") or "").strip(),
        ]

        if project_name and ref == project_name:
            score = max(score, 100)
        elif project_name and ref_lower == project_name.lower():
            score = max(score, 90)

        if display_name and ref == display_name:
            score = max(score, 80)
        elif display_name and ref_lower == display_name.lower():
            score = max(score, 70)

        for candidate_path in project_paths:
            if not candidate_path:
                continue
            if ref == candidate_path:
                score = max(score, 60)
            if maybe_path and _normalize_path(candidate_path) == maybe_path:
                score = max(score, 95)

        if score >= 0:
            matches.append((score, project))

    if matches:
        matches.sort(key=lambda item: item[0], reverse=True)
        top_score = matches[0][0]
        top_projects: List[Dict[str, Any]] = []
        seen = set()
        for score, project in matches:
            if score != top_score:
                continue
            identity = _project_identity(project)
            if identity in seen:
                continue
            seen.add(identity)
            top_projects.append(project)

        if len(top_projects) == 1:
            return top_projects[0]

        labels = ", ".join(sorted(_project_label(project) for project in top_projects))
        raise ValueError(f"Project reference '{project_ref}' is ambiguous. Matches: {labels}")

    if allow_path_fallback and maybe_path and os.path.exists(maybe_path):
        return {
            "name": None,
            "displayName": os.path.basename(maybe_path) or maybe_path,
            "path": maybe_path,
            "fullPath": maybe_path,
            "_unlisted_path": True,
        }

    sample_refs = ", ".join(_project_label(project) for project in projects[:6] if isinstance(project, dict))
    if sample_refs:
        raise ValueError(
            f"Project '{project_ref}' was not found. Try a project name, display name, or path from: {sample_refs}"
        )
    raise ValueError("No VibeLab projects are available.")


def _require_project_name(project: Dict[str, Any], project_ref: str) -> str:
    project_name = project.get("name")
    if not project_name:
        raise ValueError(
            f"Project '{project_ref}' is not registered in VibeLab. Add it first, or choose a project from `vibelab projects list`."
        )
    return str(project_name)


def _project_rows(projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        taskmaster = project.get("taskmaster") or {}
        rows.append(
            {
                "name": project.get("name", ""),
                "display_name": _project_label(project),
                "path": project.get("fullPath") or project.get("path") or "",
                "claude": len(project.get("sessions") or []),
                "cursor": len(project.get("cursorSessions") or []),
                "codex": len(project.get("codexSessions") or []),
                "gemini": len(project.get("geminiSessions") or []),
                "taskmaster": taskmaster.get("status") or "",
            }
        )
    return rows


def _emit_collection(
    ctx: Context,
    page: Dict[str, Any],
    item_key: str,
    title: str,
) -> None:
    if ctx.json_mode:
        output(page, json_mode=True)
        return

    items = page.get(item_key) or []
    output(items, json_mode=False, title=title)

    meta_parts: List[str] = []
    if page.get("total") is not None:
        meta_parts.append(f"total={page['total']}")
    if page.get("offset") is not None:
        meta_parts.append(f"offset={page['offset']}")
    if page.get("limit") is not None:
        meta_parts.append(f"limit={page['limit']}")
    if meta_parts:
        info("  " + "  ".join(meta_parts))
    if page.get("hasMore"):
        info("  More items are available. Increase --limit or use --offset.")


def _normalize_provider(provider: Optional[str]) -> Optional[str]:
    if provider is None:
        return None
    return provider.lower().strip()


def _session_timestamp(session: Dict[str, Any]) -> str:
    for key in ("lastActivity", "lastModified", "updatedAt", "createdAt", "timestamp"):
        value = session.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _list_provider_sessions_from_project(
    project: Dict[str, Any],
    provider: str,
    limit: Optional[int],
    offset: int,
) -> Dict[str, Any]:
    field_name = _SESSION_COLLECTIONS[provider]
    raw_sessions = project.get(field_name) or []
    if not isinstance(raw_sessions, list):
        raw_sessions = []

    normalized: List[Dict[str, Any]] = []
    for session in raw_sessions:
        if not isinstance(session, dict):
            continue
        row = dict(session)
        row.setdefault("provider", provider)
        row.setdefault("project_id", project.get("name"))
        row.setdefault("project_name", project.get("name"))
        row.setdefault("project_display_name", _project_label(project))
        row.setdefault("summary", row.get("summary") or row.get("title") or row.get("name") or "")
        normalized.append(row)

    normalized.sort(key=_session_timestamp, reverse=True)
    safe_offset = max(offset, 0)
    total = len(normalized)

    if limit is None:
        page_items = normalized[safe_offset:]
    else:
        page_items = normalized[safe_offset : safe_offset + max(limit, 0)]

    return {
        "sessions": page_items,
        "total": total,
        "offset": safe_offset,
        "limit": limit,
        "hasMore": safe_offset + len(page_items) < total,
    }


def _resolve_push_channel(channel: Optional[str]) -> Optional[str]:
    if channel:
        return channel
    session_data = _load_session_file()
    return session_data.get("openclaw_push_channel")


def _send_openclaw_message(message_text: str, channel: str) -> str:
    cmd = ["openclaw", "message", "send", "--to", channel, "--message", message_text]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        err_output = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"openclaw exited with code {result.returncode}: {err_output}")
    return result.stdout.strip()


def _truncate_text(value: Any, max_len: int = 220) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _build_openclaw_report(
    project: Dict[str, Any],
    summary: Dict[str, Any],
    include_prompt: bool = False,
) -> str:
    counts = summary.get("counts") or {}
    next_task = summary.get("next_task") or {}
    guidance = summary.get("guidance") or {}

    lines = [f"[VibeLab] {_project_label(project)}"]
    lines.append(f"Status: {summary.get('status', 'unknown')}")
    lines.append(
        "Progress: "
        f"{counts.get('completed', 0)}/{counts.get('total', 0)} done "
        f"({counts.get('completion_rate', 0)}%), "
        f"in-progress {counts.get('in_progress', 0)}, pending {counts.get('pending', 0)}"
    )

    if next_task:
        next_bits = [f"#{next_task.get('id', '?')}", next_task.get("title") or "Untitled task"]
        if next_task.get("stage"):
            next_bits.append(f"stage={next_task['stage']}")
        if next_task.get("status"):
            next_bits.append(f"status={next_task['status']}")
        lines.append("Next: " + " | ".join(str(bit) for bit in next_bits if bit))
    else:
        lines.append("Next: no pending task")

    why_next = guidance.get("whyNext")
    if why_next:
        lines.append(f"Why next: {_truncate_text(why_next, 180)}")

    required_inputs = guidance.get("requiredInputs") or []
    if required_inputs:
        lines.append("Inputs: " + ", ".join(str(item) for item in required_inputs[:4]))

    suggested_skills = guidance.get("suggestedSkills") or []
    if suggested_skills:
        lines.append("Skills: " + ", ".join(str(item) for item in suggested_skills[:4]))

    if include_prompt and guidance.get("nextActionPrompt"):
        lines.append(f"Prompt: {_truncate_text(guidance['nextActionPrompt'], 320)}")

    updated_at = summary.get("updated_at")
    if updated_at:
        lines.append(f"Updated: {updated_at}")

    return "\n".join(lines)


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output results as JSON.")
@click.option("--url", "url_override", default=None, metavar="URL", help="Override the VibeLab server URL.")
@click.pass_context
def cli(ctx: click.Context, json_mode: bool, url_override: Optional[str]) -> None:
    """VibeLab CLI harness - manage projects, sessions, TaskMaster, and OpenClaw integration."""
    client = VibeLab(url_override=url_override)
    ctx.obj = Context(json_mode=json_mode, client=client)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.group()
def auth() -> None:
    """Authentication commands."""


@auth.command("login")
@click.option("--username", "-u", prompt="Username", help="VibeLab username.")
@click.option("--password", "-p", prompt="Password", hide_input=True, help="VibeLab password.")
@pass_context
def auth_login(ctx: Context, username: str, password: str) -> None:
    """Log in and store the JWT token locally."""
    try:
        data = ctx.client.login(username, password)
        user = data.get("user", {})
        success(
            f"Logged in as '{user.get('username', username)}'. Token stored in {SESSION_FILE}",
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
        data["has_local_token"] = ctx.client.get_token() is not None
        output(data, json_mode=ctx.json_mode, title="Auth Status")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@cli.group()
def projects() -> None:
    """Project management commands."""


@projects.command("list")
@pass_context
def projects_list(ctx: Context) -> None:
    """List all projects."""
    try:
        items = projects_mod.list_projects(ctx.client)
        if ctx.json_mode:
            output(items, json_mode=True)
        else:
            output(_project_rows(items), json_mode=False, title="Projects")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@projects.command("add")
@click.argument("project_path")
@click.option("--name", "display_name", default=None, metavar="DISPLAY_NAME", help="Optional display name to save for the project.")
@pass_context
def projects_add(ctx: Context, project_path: str, display_name: Optional[str]) -> None:
    """Register PROJECT_PATH as a VibeLab project."""
    try:
        project = projects_mod.add_project_manual(
            ctx.client,
            _normalize_path(project_path),
            display_name=display_name,
        )
        if ctx.json_mode:
            output(project, json_mode=True)
        else:
            success(f"Project '{_project_label(project)}' added.", json_mode=False)
            info(f"  name : {project.get('name', '')}")
            info(f"  path : {project.get('fullPath') or project.get('path') or ''}")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@projects.command("rename")
@click.argument("project_ref")
@click.argument("new_name")
@pass_context
def projects_rename(ctx: Context, project_ref: str, new_name: str) -> None:
    """Rename PROJECT_REF to NEW_NAME."""
    try:
        project = _resolve_project_ref(ctx.client, project_ref)
        project_name = _require_project_name(project, project_ref)
        projects_mod.rename_project(ctx.client, project_name, new_name)
        success(
            f"Project '{_project_label(project)}' renamed to '{new_name}'.",
            json_mode=ctx.json_mode,
        )
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@projects.command("delete")
@click.argument("project_ref")
@click.confirmation_option(prompt="Are you sure you want to delete this project?")
@pass_context
def projects_delete(ctx: Context, project_ref: str) -> None:
    """Delete PROJECT_REF."""
    try:
        project = _resolve_project_ref(ctx.client, project_ref)
        project_name = _require_project_name(project, project_ref)
        projects_mod.delete_project(ctx.client, project_name)
        success(f"Project '{_project_label(project)}' deleted.", json_mode=ctx.json_mode)
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@cli.group()
def sessions() -> None:
    """Conversation session commands."""


@sessions.command("list")
@click.argument("project_ref")
@click.option("--provider", type=click.Choice(_PROVIDER_CHOICES, case_sensitive=False), default="claude", show_default=True, help="Session provider to list.")
@click.option("--limit", type=int, default=20, show_default=True, metavar="N", help="Maximum number of sessions to fetch.")
@click.option("--offset", type=int, default=0, show_default=True, metavar="N", help="Number of newest sessions to skip.")
@pass_context
def sessions_list(ctx: Context, project_ref: str, provider: str, limit: int, offset: int) -> None:
    """List sessions for PROJECT_REF."""
    try:
        normalized_provider = _normalize_provider(provider) or "claude"
        project = _resolve_project_ref(ctx.client, project_ref)
        project_name = _require_project_name(project, project_ref)

        if normalized_provider == "claude":
            page = conversations_mod.list_sessions(
                ctx.client,
                project_name,
                limit=limit,
                offset=offset,
                include_meta=True,
            )
        else:
            page = _list_provider_sessions_from_project(project, normalized_provider, limit=limit, offset=offset)

        title = f"Sessions for {_project_label(project)} ({normalized_provider})"
        _emit_collection(ctx, page, "sessions", title)
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@sessions.command("messages")
@click.argument("project_ref")
@click.argument("session_id")
@click.option("--provider", type=click.Choice(_PROVIDER_CHOICES, case_sensitive=False), default=None, help="Session provider for message lookup.")
@click.option("--limit", type=int, default=None, metavar="N", help="Maximum number of messages to fetch. Omit to fetch all available messages.")
@click.option("--offset", type=int, default=0, show_default=True, metavar="N", help="Number of newest messages to skip when pagination is enabled.")
@pass_context
def sessions_messages(
    ctx: Context,
    project_ref: str,
    session_id: str,
    provider: Optional[str],
    limit: Optional[int],
    offset: int,
) -> None:
    """Get messages for SESSION_ID within PROJECT_REF."""
    try:
        normalized_provider = _normalize_provider(provider)
        project = _resolve_project_ref(ctx.client, project_ref)
        project_name = _require_project_name(project, project_ref)
        page = conversations_mod.get_session_messages(
            ctx.client,
            project_name,
            session_id,
            limit=limit,
            offset=offset,
            provider=normalized_provider,
            include_meta=True,
        )
        title = f"Messages for {session_id} in {_project_label(project)}"
        _emit_collection(ctx, page, "messages", title)
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@cli.group()
def taskmaster() -> None:
    """TaskMaster / pipeline status commands."""


@taskmaster.command("status")
@pass_context
def taskmaster_status(ctx: Context) -> None:
    """Show global TaskMaster installation status."""
    try:
        data = taskmaster_mod.get_installation_status(ctx.client)
        output(data, json_mode=ctx.json_mode, title="TaskMaster Status")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@taskmaster.command("detect")
@click.argument("project_ref")
@pass_context
def taskmaster_detect(ctx: Context, project_ref: str) -> None:
    """Detect TaskMaster configuration for PROJECT_REF."""
    try:
        project = _resolve_project_ref(ctx.client, project_ref)
        project_name = _require_project_name(project, project_ref)
        data = taskmaster_mod.detect_taskmaster(ctx.client, project_name)
        output(data, json_mode=ctx.json_mode, title=f"TaskMaster detect: {_project_label(project)}")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@taskmaster.command("detect-all")
@pass_context
def taskmaster_detect_all(ctx: Context) -> None:
    """Detect TaskMaster state for all known projects."""
    try:
        data = taskmaster_mod.detect_all(ctx.client)
        output(data, json_mode=ctx.json_mode, title="TaskMaster Detect All")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@taskmaster.command("init")
@click.argument("project_ref")
@pass_context
def taskmaster_init(ctx: Context, project_ref: str) -> None:
    """Initialize .pipeline files for PROJECT_REF."""
    try:
        project = _resolve_project_ref(ctx.client, project_ref)
        project_name = _require_project_name(project, project_ref)
        data = taskmaster_mod.initialize(ctx.client, project_name)
        if ctx.json_mode:
            output(data, json_mode=True)
        else:
            success(f"TaskMaster initialized for {_project_label(project)}.", json_mode=False)
            info(f"  pipeline : {data.get('pipelinePath', '')}")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@taskmaster.command("tasks")
@click.argument("project_ref")
@pass_context
def taskmaster_tasks(ctx: Context, project_ref: str) -> None:
    """List TaskMaster tasks for PROJECT_REF."""
    try:
        project = _resolve_project_ref(ctx.client, project_ref)
        project_name = _require_project_name(project, project_ref)
        data = taskmaster_mod.list_tasks(ctx.client, project_name)
        if ctx.json_mode:
            output(data, json_mode=True)
        else:
            output(data.get("tasks") or [], json_mode=False, title=f"Tasks for {_project_label(project)}")
            counts = data.get("tasksByStatus") or {}
            if counts:
                info(
                    "  "
                    + "  ".join(
                        [
                            f"pending={counts.get('pending', 0)}",
                            f"in-progress={counts.get('in-progress', 0)}",
                            f"done={counts.get('done', 0)}",
                            f"review={counts.get('review', 0)}",
                        ]
                    )
                )
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@taskmaster.command("next")
@click.argument("project_ref")
@pass_context
def taskmaster_next(ctx: Context, project_ref: str) -> None:
    """Show the next task for PROJECT_REF."""
    try:
        project = _resolve_project_ref(ctx.client, project_ref)
        project_name = _require_project_name(project, project_ref)
        data = taskmaster_mod.get_next_task(ctx.client, project_name)
        output(data, json_mode=ctx.json_mode, title=f"Next task: {_project_label(project)}")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@taskmaster.command("next-guidance")
@click.argument("project_ref")
@pass_context
def taskmaster_next_guidance(ctx: Context, project_ref: str) -> None:
    """Show next-task guidance metadata for PROJECT_REF."""
    try:
        project = _resolve_project_ref(ctx.client, project_ref)
        project_name = _require_project_name(project, project_ref)
        data = taskmaster_mod.get_next_guidance(ctx.client, project_name)
        output(data, json_mode=ctx.json_mode, title=f"Next guidance: {_project_label(project)}")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@taskmaster.command("summary")
@click.argument("project_ref")
@click.option("--include-prompt", is_flag=True, default=False, help="Include the next action prompt in pretty output.")
@pass_context
def taskmaster_summary(ctx: Context, project_ref: str, include_prompt: bool) -> None:
    """Show a compact TaskMaster summary for PROJECT_REF."""
    try:
        project = _resolve_project_ref(ctx.client, project_ref)
        project_name = _require_project_name(project, project_ref)
        summary = taskmaster_mod.build_summary(ctx.client, project_name)
        if ctx.json_mode:
            output(summary, json_mode=True)
        else:
            click.echo(_build_openclaw_report(project, summary, include_prompt=include_prompt))
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


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
        if isinstance(data, list):
            display = [
                {
                    "name": item.get("name", ""),
                    "type": item.get("type", ""),
                    "path": item.get("path", ""),
                }
                for item in data
                if isinstance(item, dict)
            ]
        else:
            display = data
        output(display, json_mode=ctx.json_mode, title="Skills")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@cli.group()
def server() -> None:
    """Start / stop the VibeLab Node.js server as a background daemon."""


@server.command("on")
@click.option("--path", "server_path", default=None, metavar="PATH", help="Path to the VibeLab installation directory (saved for future use).")
@click.option("--port", default=None, type=int, metavar="PORT", help="Port to listen on (default: 3001).")
@pass_context
def server_on(ctx: Context, server_path: Optional[str], port: Optional[int]) -> None:
    """Start the VibeLab server as a daemon. Logs -> ~/.vibelab/logs/server.log"""
    try:
        result = daemon_mod.server_start(path_override=server_path, port=port)
        if ctx.json_mode:
            output(result, json_mode=True)
        else:
            success(f"Server started (PID {result['pid']}). Logs: {result['log_file']}", json_mode=False)
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
        elif result["stopped"]:
            success(result["message"], json_mode=False)
        else:
            info(result["message"])
    except Exception as exc:
        error(str(exc))
        sys.exit(1)


@server.command("status")
@click.option("--logs", "show_logs", is_flag=True, default=False, help="Print the last 20 lines of the server log.")
@pass_context
def server_status(ctx: Context, show_logs: bool) -> None:
    """Show whether the daemon is running."""
    try:
        st = daemon_mod.server_status()
        if ctx.json_mode:
            output(st, json_mode=True)
            return

        state = "RUNNING" if st["running"] else "STOPPED"
        state_text = click.style(state, fg="green" if st["running"] else "red", bold=True)
        click.echo(f"  status : {state_text}")
        if st.get("pid"):
            click.echo(f"  pid    : {st['pid']}")
        click.echo(f"  logs   : {st['log_file']}")
        if show_logs and st.get("log_tail"):
            click.echo("\n--- last 20 log lines ---")
            click.echo(st["log_tail"])
    except Exception as exc:
        error(str(exc))
        sys.exit(1)


@server.command("logs")
@click.option("-n", "lines", default=50, show_default=True, help="Number of lines to show.")
@click.option("-f", "follow", is_flag=True, default=False, help="Follow the log (like tail -f).")
@pass_context
def server_logs(ctx: Context, lines: int, follow: bool) -> None:
    """Tail the server log file."""
    if not daemon_mod.LOG_FILE.exists():
        info("No log file yet. Start the server first.")
        return
    if follow:
        try:
            subprocess.run(["tail", f"-{lines}", "-f", str(daemon_mod.LOG_FILE)], check=False)
        except KeyboardInterrupt:
            pass
    else:
        subprocess.run(["tail", f"-{lines}", str(daemon_mod.LOG_FILE)], check=False)


@cli.group()
def chat() -> None:
    """Chat with Claude sessions via WebSocket."""


@chat.command("send")
@click.option("--project", "project_ref", required=True, metavar="PROJECT", help="Project name, display name, or filesystem path.")
@click.option("--message", "message", "-m", required=True, metavar="TEXT", help="Message to send to the Claude session.")
@click.option("--session", "session_id", default=None, metavar="SESSION_ID", help="Session ID to resume (omit to start a new session).")
@click.option("--timeout", type=int, default=180, show_default=True, metavar="SECONDS", help="Maximum seconds to wait for completion.")
@pass_context
def chat_send(
    ctx: Context,
    project_ref: str,
    message: str,
    session_id: Optional[str],
    timeout: int,
) -> None:
    """Send a message to a Claude session and print the reply."""
    try:
        project = _resolve_project_ref(ctx.client, project_ref, allow_path_fallback=True)
        project_path = project.get("fullPath") or project.get("path") or project_ref
        result = chat_mod.send_message(
            ctx.client,
            project_path=str(project_path),
            message=message,
            session_id=session_id or None,
            timeout=timeout,
        )
        payload = {
            "project": project.get("name") or project.get("fullPath") or project.get("path"),
            "project_path": result.get("project_path"),
            "session_id": result.get("session_id"),
            "reply": result.get("reply", ""),
        }
        if ctx.json_mode:
            output(payload, json_mode=True)
        else:
            click.echo(result.get("reply", ""))
            info(f"Session: {result.get('session_id', '')}")
            info(f"Project: {payload['project_path']}")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@chat.command("sessions")
@click.option("--project", "project_ref", default=None, metavar="PROJECT", help="Optional project name, display name, or path filter.")
@click.option("--provider", type=click.Choice(_PROVIDER_CHOICES, case_sensitive=False), default=None, help="Optional provider filter.")
@pass_context
def chat_sessions(ctx: Context, project_ref: Optional[str], provider: Optional[str]) -> None:
    """List active sessions across all projects."""
    try:
        sessions = chat_mod.get_active_sessions(ctx.client)
        normalized_provider = _normalize_provider(provider)
        if project_ref:
            project = _resolve_project_ref(ctx.client, project_ref)
            project_name = project.get("name")
            project_path = project.get("fullPath") or project.get("path")
            sessions = [
                session
                for session in sessions
                if session.get("project_name") == project_name or session.get("project_path") == project_path
            ]
        if normalized_provider:
            sessions = [session for session in sessions if session.get("provider") == normalized_provider]
        output(sessions, json_mode=ctx.json_mode, title="Active Sessions")
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@cli.group()
def openclaw() -> None:
    """OpenClaw integration commands."""


@openclaw.command("install")
@click.option("--openclaw-dir", "openclaw_dir", default=None, metavar="DIR", help="Path to the OpenClaw workspace root (default: ~/.openclaw).")
@pass_context
def openclaw_install(ctx: Context, openclaw_dir: Optional[str]) -> None:
    """Install the VibeLab skill into the OpenClaw workspace."""
    base = Path(openclaw_dir).expanduser() if openclaw_dir else Path.home() / ".openclaw"
    skills_dir = base / "workspace" / "skills" / _OPENCLAW_SKILL_DIR_NAME
    dest = skills_dir / _SKILL_MD_FILENAME

    if not _OWN_SKILL_MD.exists():
        error(f"SKILL.md not found at {_OWN_SKILL_MD}. Run this command from the agent-harness repo.")
        sys.exit(1)

    skills_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(_OWN_SKILL_MD), str(dest))

    if ctx.json_mode:
        output({"installed": str(dest), "source": str(_OWN_SKILL_MD)}, json_mode=True)
    else:
        success(f"VibeLab skill installed to {dest}", json_mode=False)


@openclaw.command("push")
@click.argument("message_text")
@click.option("--to", "channel", default=None, metavar="CHANNEL", help="Destination channel (for example feishu:<chat_id>). Falls back to saved openclaw_push_channel in ~/.vibelab_session.json.")
@pass_context
def openclaw_push(ctx: Context, message_text: str, channel: Optional[str]) -> None:
    """Send a message via the OpenClaw CLI."""
    resolved_channel = _resolve_push_channel(channel)
    if not resolved_channel:
        error("No channel specified. Use --to <channel> or run `vibelab openclaw configure --push-channel <channel>` first.")
        sys.exit(1)

    try:
        cmd_output = _send_openclaw_message(message_text, resolved_channel)
        if ctx.json_mode:
            output({"sent": True, "channel": resolved_channel, "output": cmd_output}, json_mode=True)
        else:
            success(f"Message sent to {resolved_channel}", json_mode=False)
            if cmd_output:
                click.echo(cmd_output)
    except FileNotFoundError:
        error("'openclaw' command not found. Is OpenClaw installed and on your PATH?")
        sys.exit(1)
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


@openclaw.command("configure")
@click.option("--push-channel", "push_channel", required=True, metavar="CHANNEL", help="Default channel for `openclaw push` and `openclaw report`.")
@pass_context
def openclaw_configure(ctx: Context, push_channel: str) -> None:
    """Save OpenClaw integration settings to ~/.vibelab_session.json."""
    session_data = _load_session_file()
    session_data["openclaw_push_channel"] = push_channel
    _save_session_file(session_data)
    if ctx.json_mode:
        output({"openclaw_push_channel": push_channel}, json_mode=True)
    else:
        success(f"Default OpenClaw push channel set to: {push_channel}", json_mode=False)


@openclaw.command("report")
@click.option("--project", "project_ref", required=True, metavar="PROJECT", help="Project name, display name, or path.")
@click.option("--to", "channel", default=None, metavar="CHANNEL", help="Destination channel. Falls back to the configured default channel.")
@click.option("--dry-run", is_flag=True, default=False, help="Print the report without sending it to OpenClaw.")
@click.option("--include-prompt", is_flag=True, default=False, help="Include the next action prompt in the generated report text.")
@pass_context
def openclaw_report(
    ctx: Context,
    project_ref: str,
    channel: Optional[str],
    dry_run: bool,
    include_prompt: bool,
) -> None:
    """Generate a TaskMaster status report for OpenClaw / mobile delivery."""
    try:
        project = _resolve_project_ref(ctx.client, project_ref)
        project_name = _require_project_name(project, project_ref)
        summary = taskmaster_mod.build_summary(ctx.client, project_name)
        report_text = _build_openclaw_report(project, summary, include_prompt=include_prompt)

        resolved_channel = _resolve_push_channel(channel)
        sent = False
        cmd_output = ""
        if not dry_run:
            if not resolved_channel:
                raise ValueError(
                    "No channel specified. Use --to <channel>, run `vibelab openclaw configure --push-channel <channel>`, or pass --dry-run."
                )
            cmd_output = _send_openclaw_message(report_text, resolved_channel)
            sent = True

        payload = {
            "project": project_name,
            "channel": resolved_channel,
            "sent": sent,
            "report": report_text,
            "summary": summary,
            "openclaw_output": cmd_output,
        }
        if ctx.json_mode:
            output(payload, json_mode=True)
        else:
            click.echo(report_text)
            if sent:
                success(f"Report sent to {resolved_channel}", json_mode=False)
                if cmd_output:
                    click.echo(cmd_output)
            else:
                info("Dry run only; report was not sent.")
    except FileNotFoundError:
        error("'openclaw' command not found. Is OpenClaw installed and on your PATH?")
        sys.exit(1)
    except Exception as exc:
        _handle_error(exc, ctx.json_mode)


if __name__ == "__main__":
    cli()
