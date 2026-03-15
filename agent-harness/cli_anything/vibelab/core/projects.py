"""
Project-level operations against the VibeLab REST API.

All functions accept a `VibeLab` client instance as their first argument so
that callers control authentication and URL resolution.
"""

from typing import Any, Dict, List, Optional

from .session import VibeLab


def list_projects(client: VibeLab) -> List[Dict[str, Any]]:
    """
    GET /api/projects

    Returns a list of project dicts as returned by the server. Each dict
    typically includes keys such as ``name``, ``displayName``, ``path``, and
    provider-specific session metadata.
    """
    resp = client.get("/api/projects")
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("projects", data)


def rename_project(client: VibeLab, project_name: str, new_name: str) -> bool:
    """
    PUT /api/projects/:projectName/rename

    Returns True on success, raises on HTTP error.
    """
    resp = client.put(
        f"/api/projects/{project_name}/rename",
        {"displayName": new_name},
    )
    return resp.json().get("success", True)


def delete_project(client: VibeLab, project_id: str) -> bool:
    """
    DELETE /api/projects/:id

    Returns True on success, raises on HTTP error.
    """
    resp = client.delete(f"/api/projects/{project_id}")
    data = resp.json()
    return data.get("success", True)


def add_project_manual(
    client: VibeLab,
    path: str,
    display_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    POST /api/projects

    Registers a filesystem path as a new project and returns the created
    project dict.
    """
    body: Dict[str, Any] = {"path": path}
    if display_name is not None:
        body["displayName"] = display_name

    resp = client.post("/api/projects", body)
    data = resp.json()
    if isinstance(data, dict) and isinstance(data.get("project"), dict):
        return data["project"]
    return data
