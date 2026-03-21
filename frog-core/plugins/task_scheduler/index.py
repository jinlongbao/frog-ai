"""
Frog Plugin: Task Scheduler
Schedule a task prompt to run after a delay, at a specific time delay,
or on a recurring interval. Dispatches to the orchestrator's /task/create endpoint.
"""
import os
import sys
import time
import json
import threading
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

API_BASE = "http://127.0.0.1:8000"

# Registry of active scheduled tasks  {label: thread}
_scheduled_tasks: dict = {}


def _dispatch_task(prompt: str, config: dict, label: str, repeat_interval: int, max_repeats: int):
    """Background thread: create and run the scheduled task."""
    run_count = 0
    while True:
        run_count += 1
        print(f"[task_scheduler] 🕐 Dispatching scheduled task: '{label}' (run #{run_count})")
        
        try:
            res = requests.post(f"{API_BASE}/task/create", json={
                "messages": [{"role": "user", "content": prompt}],
                "api_key":  config.get("api_key", ""),
                "base_url": config.get("base_url", ""),
                "model":    config.get("model", "gpt-4o-mini"),
                "reasoning_effort": config.get("reasoning_effort", "medium"),
                "provider": config.get("provider", "openai")
            }, timeout=10)
            
            if res.ok:
                task_id = res.json().get("task_id", "")
                print(f"[task_scheduler] ✅ Task created: {task_id}")
                
                # Auto-run the task steps
                for _ in range(15):
                    step_res = requests.post(f"{API_BASE}/task/{task_id}/step", timeout=60)
                    if not step_res.ok:
                        break
                    status = step_res.json().get("status", "")
                    if status in ("COMPLETED", "FAILED"):
                        print(f"[task_scheduler] Task {task_id} finished with status: {status}")
                        break
                    time.sleep(2)
            else:
                print(f"[task_scheduler] ❌ Failed to create task: {res.text[:200]}")
                
        except Exception as e:
            print(f"[task_scheduler] ❌ Error dispatching task: {e}")

        # Check repeat
        if repeat_interval <= 0:
            break
        if max_repeats > 0 and run_count >= max_repeats:
            print(f"[task_scheduler] Reached max_repeats ({max_repeats}). Stopping.")
            break
        
        print(f"[task_scheduler] ⏳ Next run in {repeat_interval}s...")
        time.sleep(repeat_interval)

    if label in _scheduled_tasks:
        del _scheduled_tasks[label]
    print(f"[task_scheduler] 🏁 Scheduled task '{label}' completed all runs.")


def execute(params: dict, context: dict) -> dict:
    prompt           = params.get("prompt", "").strip()
    delay_seconds    = int(params.get("delay_seconds", 0))
    repeat_interval  = int(params.get("repeat_interval_seconds", 0))
    max_repeats      = int(params.get("max_repeats", 0))
    label            = params.get("label", f"task_{datetime.now().strftime('%H%M%S')}")

    if not prompt:
        return {"status": "error", "message": "prompt is required"}

    if label in _scheduled_tasks and _scheduled_tasks[label].is_alive():
        return {
            "status": "error",
            "message": f"A scheduled task with label '{label}' is already running. Use a different label."
        }

    # Load LLM config from env as fallback
    from dotenv import load_dotenv
    load_dotenv()
    config = {
        "api_key":          context.get("api_key") or os.getenv("OPENAI_API_KEY", ""),
        "base_url":         context.get("base_url") or os.getenv("OPENAI_BASE_URL", ""),
        "model":            context.get("model") or os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
        "reasoning_effort": context.get("reasoning_effort", "medium"),
        "provider":         context.get("provider", "openai")
    }

    def _runner():
        if delay_seconds > 0:
            print(f"[task_scheduler] ⏳ Waiting {delay_seconds}s before '{label}'...")
            time.sleep(delay_seconds)
        _dispatch_task(prompt, config, label, repeat_interval, max_repeats)

    t = threading.Thread(target=_runner, daemon=True, name=f"sched_{label}")
    t.start()
    _scheduled_tasks[label] = t

    schedule_desc = []
    if delay_seconds > 0:
        schedule_desc.append(f"starts in {delay_seconds}s")
    else:
        schedule_desc.append("starts immediately")
    if repeat_interval > 0:
        rpt = f"repeats every {repeat_interval}s"
        if max_repeats > 0:
            rpt += f" (max {max_repeats}x)"
        else:
            rpt += " (unlimited)"
        schedule_desc.append(rpt)

    return {
        "status": "success",
        "label": label,
        "prompt_preview": prompt[:100],
        "schedule": ", ".join(schedule_desc),
        "message": f"Task '{label}' scheduled: {', '.join(schedule_desc)}"
    }
