"""
TaskMaster operations against the VibeLab REST API.

These helpers expose the task-state endpoints that OpenClaw can use to
inspect progress and generate compact status reports for mobile delivery.
"""

from typing import Any, Dict, List, Optional

from .session import VibeLab


def get_installation_status(client: VibeLab) -> Dict[str, Any]:
    """GET /api/taskmaster/installation-status."""
    resp = client.get("/api/taskmaster/installation-status")
    return resp.json()


def detect_taskmaster(client: VibeLab, project_name: str) -> Dict[str, Any]:
    """GET /api/taskmaster/detect/:projectName."""
    resp = client.get(f"/api/taskmaster/detect/{project_name}")
    return resp.json()


def detect_all(client: VibeLab) -> Dict[str, Any]:
    """GET /api/taskmaster/detect-all."""
    resp = client.get("/api/taskmaster/detect-all")
    return resp.json()


def initialize(client: VibeLab, project_name: str) -> Dict[str, Any]:
    """POST /api/taskmaster/initialize/:projectName."""
    resp = client.post(f"/api/taskmaster/initialize/{project_name}", {})
    return resp.json()


def list_tasks(client: VibeLab, project_name: str) -> Dict[str, Any]:
    """GET /api/taskmaster/tasks/:projectName."""
    resp = client.get(f"/api/taskmaster/tasks/{project_name}")
    return resp.json()


def get_next_task(client: VibeLab, project_name: str) -> Dict[str, Any]:
    """GET /api/taskmaster/next/:projectName."""
    resp = client.get(f"/api/taskmaster/next/{project_name}")
    return resp.json()


def get_next_guidance(client: VibeLab, project_name: str) -> Dict[str, Any]:
    """GET /api/taskmaster/next-guidance/:projectName."""
    resp = client.get(f"/api/taskmaster/next-guidance/{project_name}")
    return resp.json()


def get_summary(client: VibeLab, project_name: str) -> Dict[str, Any]:
    """GET /api/taskmaster/summary/:projectName."""
    resp = client.get(f"/api/taskmaster/summary/{project_name}")
    return resp.json()


def build_summary(client: VibeLab, project_name: str) -> Dict[str, Any]:
    """
    Build a compact TaskMaster summary for OpenClaw/mobile notifications.

    Response shape is intentionally stable and lightweight:
      {
        project,
        status,
        project_path,
        counts,
        next_task,
        guidance,
        updated_at,
      }
    """
    try:
        summary = get_summary(client, project_name)
        if isinstance(summary, dict) and summary.get("project"):
            return summary
    except Exception:
        pass

    detect_data = detect_taskmaster(client, project_name)
    tasks_data = list_tasks(client, project_name)
    next_data: Optional[Dict[str, Any]] = None
    guidance_data: Optional[Dict[str, Any]] = None

    try:
        next_data = get_next_task(client, project_name)
    except Exception:
        next_data = None

    try:
        guidance_data = get_next_guidance(client, project_name)
    except Exception:
        guidance_data = None

    tasks: List[Dict[str, Any]] = tasks_data.get("tasks") or []
    tasks_by_status = tasks_data.get("tasksByStatus") or {}

    status = detect_data.get("status") or "not-configured"
    next_task = None
    if isinstance(guidance_data, dict) and guidance_data.get("nextTask") is not None:
        next_task = guidance_data.get("nextTask")
    elif isinstance(next_data, dict):
        next_task = next_data.get("nextTask")

    guidance = guidance_data.get("guidance") if isinstance(guidance_data, dict) else None

    completed = tasks_by_status.get("done")
    if completed is None:
        completed = sum(1 for task in tasks if task.get("status") == "done")

    in_progress = tasks_by_status.get("in-progress")
    if in_progress is None:
        in_progress = sum(1 for task in tasks if task.get("status") == "in-progress")

    pending = tasks_by_status.get("pending")
    if pending is None:
        pending = sum(1 for task in tasks if task.get("status") == "pending")

    blocked = tasks_by_status.get("blocked")
    if blocked is None:
        blocked = sum(1 for task in tasks if task.get("status") == "blocked")

    total = tasks_data.get("totalTasks")
    if total is None:
        total = len(tasks)

    summary = {
        "project": project_name,
        "status": status,
        "project_path": detect_data.get("projectPath") or tasks_data.get("projectPath"),
        "counts": {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "blocked": blocked,
            "completion_rate": round((completed / total) * 100, 1) if total else 0.0,
        },
        "next_task": next_task,
        "guidance": guidance,
        "updated_at": tasks_data.get("timestamp")
        or detect_data.get("timestamp")
        or (guidance_data or {}).get("timestamp")
        or (next_data or {}).get("timestamp"),
    }

    return summary
