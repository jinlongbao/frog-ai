"""
Frog Plugin: Multi-Agent Spawner
Runs multiple sub-task prompts in parallel using background threads,
each dispatching to the orchestrator's /task/create and /task/{id}/step endpoints.
Returns a merged result from all sub-agents.
"""
import sys
import os
import time
import threading
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

API_BASE = "http://127.0.0.1:8000"


def _run_sub_agent(label: str, prompt: str, config: dict, result_store: dict, idx: int):
    """Thread worker: create + run a sub-agent task, store result in result_store."""
    try:
        # Create sub-task
        res = requests.post(f"{API_BASE}/task/create", json={
            "messages": [{"role": "user", "content": prompt}],
            "api_key":  config.get("api_key", ""),
            "base_url": config.get("base_url", ""),
            "model":    config.get("model", "gpt-4o-mini"),
            "reasoning_effort": config.get("reasoning_effort", "medium"),
            "provider": config.get("provider", "openai")
        }, timeout=15)

        if not res.ok:
            result_store[idx] = {
                "label": label,
                "status": "error",
                "result": f"Failed to create sub-task: {res.text[:200]}"
            }
            return

        task_id = res.json().get("task_id", "")
        print(f"[multi_agent] 🚀 Sub-agent '{label}' started (task_id: {task_id})")

        # Poll task to completion (max 15 steps)
        final_result = None
        for step_num in range(15):
            try:
                step_res = requests.post(f"{API_BASE}/task/{task_id}/step", timeout=90)
                if not step_res.ok:
                    break
                status_data = step_res.json()
                status = status_data.get("status", "")
                if status == "COMPLETED":
                    final_result = status_data.get("final_result") or status_data.get("final_answer", "")
                    print(f"[multi_agent] ✅ Sub-agent '{label}' COMPLETED (step {step_num+1})")
                    break
                elif status == "FAILED":
                    final_result = f"Sub-agent failed: {status_data.get('error', 'unknown error')}"
                    break
            except requests.exceptions.Timeout:
                print(f"[multi_agent] ⚠️  Sub-agent '{label}' step timeout, retrying...")
                continue
            time.sleep(1)

        result_store[idx] = {
            "label": label,
            "status": "success" if final_result else "timeout",
            "result": final_result or "Sub-agent did not complete within step limit."
        }

    except Exception as e:
        result_store[idx] = {
            "label": label,
            "status": "error",
            "result": str(e)
        }


def execute(params: dict, context: dict) -> dict:
    tasks = params.get("tasks", [])
    timeout_seconds = int(params.get("timeout_seconds", 120))

    if not tasks:
        return {"status": "error", "message": "No tasks provided. Pass a 'tasks' list with label+prompt items."}

    if len(tasks) > 8:
        return {"status": "error", "message": "Maximum 8 parallel sub-agents allowed."}

    # Load config from context or env
    from dotenv import load_dotenv
    load_dotenv()
    config = {
        "api_key":          context.get("api_key") or os.getenv("OPENAI_API_KEY", ""),
        "base_url":         context.get("base_url") or os.getenv("OPENAI_BASE_URL", ""),
        "model":            context.get("model") or os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
        "reasoning_effort": context.get("reasoning_effort", "medium"),
        "provider":         context.get("provider", "openai")
    }

    result_store = {}
    threads = []

    print(f"[multi_agent] 🌐 Spawning {len(tasks)} parallel sub-agents...")

    for i, task in enumerate(tasks):
        label  = task.get("label", f"sub_agent_{i+1}")
        prompt = task.get("prompt", "")
        if not prompt:
            result_store[i] = {"label": label, "status": "error", "result": "Empty prompt"}
            continue

        t = threading.Thread(
            target=_run_sub_agent,
            args=(label, prompt, config, result_store, i),
            daemon=True,
            name=f"agent_{label}"
        )
        threads.append(t)
        t.start()

    # Wait for all threads with timeout
    deadline = time.time() + timeout_seconds
    for t in threads:
        remaining = max(0, deadline - time.time())
        t.join(timeout=remaining)

    # Collect and format results
    results = [result_store.get(i, {"label": f"task_{i}", "status": "timeout", "result": "Did not complete"})
               for i in range(len(tasks))]

    success_count = sum(1 for r in results if r["status"] == "success")
    
    # Build merged summary
    summary_parts = []
    for r in results:
        summary_parts.append(f"### [{r['label']}]\n{r['result']}")
    merged = "\n\n".join(summary_parts)

    return {
        "status": "success",
        "total_agents": len(tasks),
        "completed": success_count,
        "results": results,
        "merged_summary": merged
    }
