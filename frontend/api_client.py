"""Thin HTTP client for the Resume Analyzer backend."""
import os

import requests

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 120


class ApiError(Exception):
    """Human-readable error raised for any failed API interaction."""


def _request(method: str, path: str, **kwargs):
    try:
        resp = requests.request(method, f"{API_URL}{path}", timeout=TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        raise ApiError(f"Cannot reach the API at {API_URL}. Please make sure the backend is running.") from exc

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        if isinstance(detail, list):
            detail = "; ".join(str(d.get("msg", d)) for d in detail)
        raise ApiError(str(detail) or f"Request failed ({resp.status_code}).")
    return resp


def health() -> dict | None:
    try:
        return requests.get(f"{API_URL}/health", timeout=5).json()
    except (requests.RequestException, ValueError):
        return None


def analyze(filename: str, content: bytes, job_description: str, job_title: str = "") -> dict:
    resp = _request(
        "POST",
        "/api/analyze",
        files={"resume": (filename, content)},
        data={"job_description": job_description, "job_title": job_title},
    )
    return resp.json()


def history(limit: int = 50) -> list[dict]:
    return _request("GET", "/api/history", params={"limit": limit}).json()


def get_analysis(analysis_id: int) -> dict:
    return _request("GET", f"/api/history/{analysis_id}").json()


def delete_analysis(analysis_id: int) -> None:
    _request("DELETE", f"/api/history/{analysis_id}")
