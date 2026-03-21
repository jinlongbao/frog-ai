"""
post_task_hooks.py
Triggered automatically when the orchestrator completes a task.
Implements:
  1. Self-Evaluation — LLM grades the task and logs reflection
  2. Knowledge Auto-Enrichment — extracts key insights into knowledge base
  3. Plugin Quality Scoring — tracks tool success/failure rates
"""
import os
import json
import threading
from datetime import datetime
from typing import Dict, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")
GROWTH_LOG_FILE = os.path.join(KNOWLEDGE_DIR, "growth_log.json")
QUALITY_SCORES_FILE = os.path.join(KNOWLEDGE_DIR, "plugin_quality_scores.json")
AUTO_KNOWLEDGE_DIR = os.path.join(KNOWLEDGE_DIR, "auto_enriched")


# ════════════════════════════════════════════════════════════
# 1. Plugin Quality Scoring
# ════════════════════════════════════════════════════════════

def record_tool_usage(tool_name: str, success: bool):
    """Called after each tool execution to track success/failure rate."""
    try:
        scores = {}
        if os.path.exists(QUALITY_SCORES_FILE):
            with open(QUALITY_SCORES_FILE, "r", encoding="utf-8") as f:
                scores = json.load(f)

        if tool_name not in scores:
            scores[tool_name] = {"success": 0, "failure": 0, "last_used": ""}

        if success:
            scores[tool_name]["success"] += 1
        else:
            scores[tool_name]["failure"] += 1
        scores[tool_name]["last_used"] = datetime.now().isoformat()

        # Calculate success rate
        total = scores[tool_name]["success"] + scores[tool_name]["failure"]
        scores[tool_name]["success_rate"] = round(scores[tool_name]["success"] / total, 2) if total > 0 else 1.0

        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        with open(QUALITY_SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)

    except Exception:
        pass  # Never block the main flow


def get_low_quality_plugins(threshold: float = 0.4) -> List[Dict]:
    """Returns plugins with success rate below threshold."""
    if not os.path.exists(QUALITY_SCORES_FILE):
        return []
    try:
        with open(QUALITY_SCORES_FILE, "r", encoding="utf-8") as f:
            scores = json.load(f)
        return [
            {"name": name, **data}
            for name, data in scores.items()
            if data.get("success_rate", 1.0) < threshold
            and (data["success"] + data["failure"]) >= 3  # Min 3 uses before judging
        ]
    except Exception:
        return []


# ════════════════════════════════════════════════════════════
# 2. Self-Evaluation
# ════════════════════════════════════════════════════════════

def _run_self_evaluation(task_summary: str, steps_summary: str, final_answer: str, config: dict):
    """Background: ask LLM to grade the task performance."""
    try:
        import httpx
        from openai import OpenAI
        from dotenv import load_dotenv
        load_dotenv()

        api_key  = config.get("api_key") or os.getenv("OPENAI_API_KEY", "")
        base_url = config.get("base_url") or os.getenv("OPENAI_BASE_URL", "")
        model    = config.get("model") or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

        if not api_key:
            return

        prompt = f"""You are evaluating your own task performance. Be honest and brief.

TASK: {task_summary[:300]}

STEPS TAKEN:
{steps_summary[:600]}

FINAL ANSWER:
{final_answer[:400]}

Rate this execution on these dimensions (1-5 stars each):
- Efficiency: Were steps minimal and direct?
- Accuracy: Was the answer correct and complete?
- Autonomy: Did the AI handle obstacles independently?

Output format (JSON only):
{{"efficiency": 3, "accuracy": 4, "autonomy": 5, "overall": 4, "reflection": "One sentence on what to improve next time."}}"""

        http_client = httpx.Client(follow_redirects=True, timeout=30.0)
        client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url else None,
            http_client=http_client
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.split("```")[0].strip()

        evaluation = json.loads(raw)
        evaluation["task_preview"] = task_summary[:100]
        evaluation["timestamp"] = datetime.now().isoformat()

        # Append to growth log
        growth_log = []
        if os.path.exists(GROWTH_LOG_FILE):
            with open(GROWTH_LOG_FILE, "r", encoding="utf-8") as f:
                growth_log = json.load(f)

        growth_log.append(evaluation)
        # Keep last 100 entries
        if len(growth_log) > 100:
            growth_log = growth_log[-100:]

        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        with open(GROWTH_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(growth_log, f, ensure_ascii=False, indent=2)

        print(f"[self_eval] ⭐ Task rated {evaluation.get('overall', '?')}/5 — {evaluation.get('reflection', '')}")

    except Exception as e:
        print(f"[self_eval] ⚠️  Self-evaluation failed: {e}")


# ════════════════════════════════════════════════════════════
# 3. Knowledge Auto-Enrichment
# ════════════════════════════════════════════════════════════

def _run_knowledge_enrichment(task_summary: str, final_answer: str, config: dict):
    """Background: if the task produced useful knowledge, extract and save it."""
    try:
        import httpx
        from openai import OpenAI
        from dotenv import load_dotenv
        load_dotenv()

        api_key  = config.get("api_key") or os.getenv("OPENAI_API_KEY", "")
        base_url = config.get("base_url") or os.getenv("OPENAI_BASE_URL", "")
        model    = config.get("model") or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

        if not api_key:
            return

        prompt = f"""Analyze this AI task result. Does the final answer contain reusable knowledge, facts, or insights worth storing?

TASK: {task_summary[:200]}
ANSWER: {final_answer[:500]}

If YES: extract a concise knowledge entry.
If NO (e.g. simple greeting, unclear, personal data): respond with exactly: SKIP

If YES, output JSON only:
{{"title": "Short descriptive title", "content": "The actual knowledge in 2-5 sentences", "tags": ["tag1", "tag2"]}}"""

        http_client = httpx.Client(follow_redirects=True, timeout=30.0)
        client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url else None,
            http_client=http_client
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.2
        )

        raw = response.choices[0].message.content.strip()
        if raw.upper() == "SKIP" or "SKIP" in raw[:10]:
            print("[knowledge_enrich] ⏭️  No reusable knowledge extracted (SKIP)")
            return

        # Strip markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.split("```")[0].strip()

        entry = json.loads(raw)
        title = entry.get("title", "Auto-enriched knowledge")
        content = entry.get("content", "")
        tags = entry.get("tags", ["auto"])

        if not content:
            return

        # Save to auto_enriched knowledge directory
        os.makedirs(AUTO_KNOWLEDGE_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:40].strip()
        filename = f"{timestamp}_{safe_title}.json"

        with open(os.path.join(AUTO_KNOWLEDGE_DIR, filename), "w", encoding="utf-8") as f:
            json.dump({
                "title": title,
                "content": content,
                "tags": tags + ["auto_enriched"],
                "source": "auto_enrichment",
                "created_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

        print(f"[knowledge_enrich] 💾 Auto-saved: '{title}'")

    except Exception as e:
        print(f"[knowledge_enrich] ⚠️  Enrichment failed: {e}")


# ════════════════════════════════════════════════════════════
# Main hook — called by orchestrator on task completion
# ════════════════════════════════════════════════════════════

def run_post_task_hooks(task, config: dict):
    """
    Non-blocking: fire all post-task hooks in background threads.
    Called when a task reaches COMPLETED status.
    """
    try:
        steps = task.steps or []
        final_answer = task.final_result or ""

        # Build steps summary for eval
        user_msgs = [m for m in task.messages if m.get("role") == "user"]
        task_summary = user_msgs[0]["content"] if user_msgs else "Unknown task"

        steps_lines = []
        for s in steps[-10:]:  # Last 10 steps only
            p = s.get("parsed", {})
            if p.get("type") == "action":
                steps_lines.append(f"- Action: {p.get('action', '?')} | Thought: {p.get('thought', '')[:80]}")
        steps_summary = "\n".join(steps_lines) if steps_lines else "(no steps recorded)"

        # Record tool quality scores
        for s in steps:
            p = s.get("parsed", {})
            if p.get("type") == "action" and p.get("action") not in ("none", ""):
                tool = p.get("action", "")
                result = s.get("result", "")
                success = "error" not in str(result).lower() and "failed" not in str(result).lower()
                record_tool_usage(tool, success)

        # Fire self-eval and knowledge enrichment in background
        if final_answer and len(steps) >= 2:
            threading.Thread(
                target=_run_self_evaluation,
                args=(task_summary, steps_summary, final_answer, config),
                daemon=True
            ).start()

            threading.Thread(
                target=_run_knowledge_enrichment,
                args=(task_summary, final_answer, config),
                daemon=True
            ).start()

        # Check for low-quality plugins and log warning
        low_quality = get_low_quality_plugins(threshold=0.4)
        if low_quality:
            names = [p["name"] for p in low_quality]
            print(f"[quality_score] ⚠️  Low-quality plugins detected: {names} — consider regenerating them.")

    except Exception as e:
        print(f"[post_task_hooks] ⚠️  Hook error (non-fatal): {e}")
