"""
Frog Plugin: Goal Tracker
Persists long-term goals across sessions. The AI can add goals, update progress,
mark them complete, list them, and delete them. Goals are stored in knowledge/goals.json.
The AI should review active goals periodically and work toward them autonomously.
"""
import os
import json
import uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOALS_FILE = os.path.join(BASE_DIR, "knowledge", "goals.json")


def _load_goals() -> list:
    if not os.path.exists(GOALS_FILE):
        return []
    try:
        with open(GOALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_goals(goals: list):
    os.makedirs(os.path.dirname(GOALS_FILE), exist_ok=True)
    with open(GOALS_FILE, "w", encoding="utf-8") as f:
        json.dump(goals, f, ensure_ascii=False, indent=2)


def execute(params: dict, context: dict) -> dict:
    action = params.get("action", "").strip().lower()
    goal_id = params.get("goal_id", "").strip()

    goals = _load_goals()

    # ── ADD ──────────────────────────────────────────────────────────────────
    if action == "add":
        title = params.get("title", "").strip()
        description = params.get("description", "").strip()
        deadline = params.get("deadline", "").strip()

        if not title:
            return {"status": "error", "message": "title is required to add a goal"}

        new_goal = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "description": description,
            "deadline": deadline,
            "status": "active",
            "progress_log": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        goals.append(new_goal)
        _save_goals(goals)

        return {
            "status": "success",
            "message": f"Goal added: '{title}'",
            "goal": new_goal
        }

    # ── LIST ─────────────────────────────────────────────────────────────────
    elif action == "list":
        active = [g for g in goals if g.get("status") == "active"]
        completed = [g for g in goals if g.get("status") == "completed"]

        summary_lines = [f"📋 Active Goals ({len(active)}):"]
        for g in active:
            deadline_str = f" [Deadline: {g['deadline']}]" if g.get("deadline") else ""
            last_progress = g["progress_log"][-1]["note"] if g.get("progress_log") else "No progress yet"
            summary_lines.append(
                f"  [{g['id']}] {g['title']}{deadline_str}\n"
                f"         Last update: {last_progress}"
            )

        if completed:
            summary_lines.append(f"\n✅ Completed Goals ({len(completed)}):")
            for g in completed[-3:]:  # Show last 3 completed
                summary_lines.append(f"  [{g['id']}] {g['title']}")

        return {
            "status": "success",
            "total_goals": len(goals),
            "active_count": len(active),
            "completed_count": len(completed),
            "goals": goals,
            "summary": "\n".join(summary_lines)
        }

    # ── UPDATE_PROGRESS ───────────────────────────────────────────────────────
    elif action == "update_progress":
        note = params.get("progress_note", "").strip()
        if not goal_id:
            return {"status": "error", "message": "goal_id is required"}
        if not note:
            return {"status": "error", "message": "progress_note is required"}

        for goal in goals:
            if goal["id"] == goal_id:
                goal.setdefault("progress_log", []).append({
                    "note": note,
                    "timestamp": datetime.now().isoformat()
                })
                goal["updated_at"] = datetime.now().isoformat()
                _save_goals(goals)
                return {
                    "status": "success",
                    "message": f"Progress updated for goal '{goal['title']}'",
                    "goal": goal
                }
        return {"status": "error", "message": f"Goal '{goal_id}' not found"}

    # ── COMPLETE ─────────────────────────────────────────────────────────────
    elif action == "complete":
        if not goal_id:
            return {"status": "error", "message": "goal_id is required"}

        for goal in goals:
            if goal["id"] == goal_id:
                goal["status"] = "completed"
                goal["completed_at"] = datetime.now().isoformat()
                goal["updated_at"] = datetime.now().isoformat()
                _save_goals(goals)
                return {
                    "status": "success",
                    "message": f"🎉 Goal '{goal['title']}' marked as COMPLETED!",
                    "goal": goal
                }
        return {"status": "error", "message": f"Goal '{goal_id}' not found"}

    # ── DELETE ────────────────────────────────────────────────────────────────
    elif action == "delete":
        if not goal_id:
            return {"status": "error", "message": "goal_id is required"}

        original_len = len(goals)
        goals = [g for g in goals if g["id"] != goal_id]
        if len(goals) < original_len:
            _save_goals(goals)
            return {"status": "success", "message": f"Goal '{goal_id}' deleted"}
        return {"status": "error", "message": f"Goal '{goal_id}' not found"}

    else:
        return {
            "status": "error",
            "message": f"Unknown action '{action}'. Valid actions: add, list, update_progress, complete, delete"
        }
