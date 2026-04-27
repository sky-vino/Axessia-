# scheduler.py
# Scheduled accessibility scanning with APScheduler
# Runs scans automatically and stores results for trend tracking

import logging
import threading
import requests
import os
from datetime import datetime

log = logging.getLogger(__name__)

_scheduler = None
_scheduler_lock = threading.Lock()


def _get_scheduler():
    global _scheduler
    with _scheduler_lock:
        if _scheduler is None:
            try:
                from apscheduler.schedulers.background import BackgroundScheduler
                _scheduler = BackgroundScheduler()
                _scheduler.start()
            except ImportError:
                log.warning("APScheduler not installed. pip install apscheduler")
                return None
    return _scheduler


def _run_scheduled_scan(url: str, api_url: str, api_key: str):
    """Execute a scheduled scan and save results."""
    from regression_tracker import save_snapshot, save_history
    from scoring import calculate_score
    from eaa_mapping import evaluate_eaa

    log.info(f"Scheduled scan starting: {url}")
    try:
        resp = requests.post(
            api_url,
            headers={"Content-Type": "application/json", "x-api-key": api_key},
            json={"url": url},
            timeout=120,
        )
        if resp.status_code == 200:
            result = resp.json()
            rules  = result.get("rules", [])
            score  = calculate_score(rules).get("score", 0)
            eaa    = evaluate_eaa(rules)
            fails  = len([r for r in rules if r.get("status") == "fail"])

            save_snapshot(url, result, score)
            save_history(url, score, fails, eaa.get("risk_level","—"))
            log.info(f"Scheduled scan complete: {url} | Score: {score}% | Failures: {fails}")
        else:
            log.error(f"Scheduled scan HTTP error {resp.status_code} for {url}")
    except Exception as e:
        log.error(f"Scheduled scan failed for {url}: {e}")


def schedule_url(
    url: str,
    frequency: str = "daily",
    api_url: str = None,
    api_key: str = None,
) -> bool:
    """
    Schedule a URL for automatic scanning.
    frequency: 'hourly' | 'daily' | 'weekly'
    """
    sched = _get_scheduler()
    if not sched:
        return False

    api_url = api_url or os.getenv("AXESSIA_API_URL", "http://127.0.0.1:8001/scan")
    api_key = api_key or os.getenv("AXESSIA_API_KEY", "super-secret-demo-key")

    job_id = f"scan_{url.replace('https://','').replace('/','_')[:50]}"

    # Remove existing job for this URL if present
    try:
        sched.remove_job(job_id)
    except Exception:
        pass

    trigger_map = {
        "hourly":  ("interval",  {"hours": 1}),
        "daily":   ("interval",  {"hours": 24}),
        "weekly":  ("interval",  {"weeks": 1}),
    }

    trigger_type, trigger_args = trigger_map.get(frequency, ("interval", {"hours": 24}))

    try:
        sched.add_job(
            _run_scheduled_scan,
            trigger=trigger_type,
            kwargs={"url": url, "api_url": api_url, "api_key": api_key},
            id=job_id,
            name=f"Axessia scan: {url[:50]}",
            replace_existing=True,
            **trigger_args,
        )
        log.info(f"Scheduled {frequency} scan for: {url}")
        return True
    except Exception as e:
        log.error(f"Failed to schedule scan for {url}: {e}")
        return False


def unschedule_url(url: str) -> bool:
    """Remove a scheduled scan for a URL."""
    sched = _get_scheduler()
    if not sched:
        return False
    job_id = f"scan_{url.replace('https://','').replace('/','_')[:50]}"
    try:
        sched.remove_job(job_id)
        return True
    except Exception:
        return False


def get_scheduled_jobs() -> list:
    """List all currently scheduled scans."""
    sched = _get_scheduler()
    if not sched:
        return []
    try:
        return [
            {
                "id":       job.id,
                "name":     job.name,
                "next_run": str(job.next_run_time),
                "trigger":  str(job.trigger),
            }
            for job in sched.get_jobs()
            if job.id.startswith("scan_")
        ]
    except Exception:
        return []


def run_now(url: str, api_url: str = None, api_key: str = None):
    """Trigger an immediate scan in a background thread."""
    api_url = api_url or os.getenv("AXESSIA_API_URL", "http://127.0.0.1:8001/scan")
    api_key = api_key or os.getenv("AXESSIA_API_KEY", "super-secret-demo-key")

    thread = threading.Thread(
        target=_run_scheduled_scan,
        kwargs={"url": url, "api_url": api_url, "api_key": api_key},
        daemon=True,
    )
    thread.start()
