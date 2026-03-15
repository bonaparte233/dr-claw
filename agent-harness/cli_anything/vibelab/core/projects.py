"""
Project-level operations against the VibeLab REST API.

All functions accept a `VibeLab` client instance as their first argument so
that callers control authentication and URL resolution.
"""

from typing import Any, Dict, List

from .session import VibeLab


def list_projects(client: VibeLab) -> List[Dict[str, Any]]:
    """
    GET /api/projects

    Returns a list of project dicts as returned by the server.  Each dict
    typically includes keys such as ``id``, ``display_name``, ``path``, and
    ``provider``.
    """
    resp = client.get("/api/projects")
    data = resp.json()
    # The server may return a bare list or a dict with a "projects" key.
    if isinstance(data, list):
        return data
    return data.get("projects", data)


def rename_project(client: VibeLab, project_id: str, new_name: str) -> bool:
    """
    PATCH /api/projects/:id/rename

    Returns True on success, raises on HTTP error.
    """
    resp = client.patch(f"/api/projects/{project_id}/rename", {"newName": new_name})
    return resp.json().get("success", True)


def delete_project(client: VibeLab, project_id: str) -> bool:
    """
    DELETE /api/projects/:id

    Returns True on success, raises on HTTP error.
    """
    resp = client.delete(f"/api/projects/{project_id}")
    data = resp.json()
    return data.get("success", True)


def add_project_manual(client: VibeLab, path: str) -> Dict[str, Any]:
    """
    POST /api/projects  (manual path addition)

    Registers a filesystem path as a new project and returns the created
    project dict.
    """
    resp = client.post("/api/projects", {"path": path})
    return resp.json()
