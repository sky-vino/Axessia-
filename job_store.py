# job_store.py
# Date: 2026-02-03

import uuid

_JOBS = {}


def create_job(payload: dict) -> str:
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {
        "status": "pending",
        "payload": payload,
        "result": None,
        "error": None,
    }
    return job_id


def set_running(job_id: str):
    _JOBS[job_id]["status"] = "running"


def set_result(job_id: str, result: dict):
    _JOBS[job_id]["status"] = "done"
    _JOBS[job_id]["result"] = result


def set_error(job_id: str, error: str):
    _JOBS[job_id]["status"] = "error"
    _JOBS[job_id]["error"] = error


def get_job(job_id: str) -> dict | None:
    return _JOBS.get(job_id)
