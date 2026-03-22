"""
Frog Plugin: Context Compressor
Compresses the current task's completed steps into a dense summary,
injected back into the orchestrator to prevent context window overflow.
"""
import sys
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)


def execute(params: dict, context: dict) -> dict:
    task_id = params.get("task_id", "").strip()
    preserve_last_n = int(params.get("preserve_last_n", 3))

    if not task_id:
        return {"status": "error", "message": "task_id is required"}

    try:
        from orchestrator import orchestrator
        task = orchestrator.get_task(task_id)
        if not task:
            return {"status": "error", "message": f"Task {task_id} not found"}

        steps = task.steps
        if len(steps) <= preserve_last_n:
            return {
                "status": "skipped",
                "message": f"Only {len(steps)} steps — compression not needed yet.",
                "total_steps": len(steps)
            }

        # Split into old (to compress) and recent (to keep)
        old_steps = steps[:-preserve_last_n] if preserve_last_n > 0 else steps
        recent_steps = steps[-preserve_last_n:] if preserve_last_n > 0 else []

        # Build a text summary of old steps
        summary_lines = [f"=== COMPRESSED HISTORY ({len(old_steps)} steps) ==="]
        for s in old_steps:
            p = s.get("parsed", {})
            if p.get("type") == "action":
                action = p.get("action", "?")
                thought = p.get("thought", "")[:120]
                obs = ""
                # Check if there's an observation in the step result
                result = s.get("result", "")
                summary_lines.append(f"- Step {s['step_number']}: [{action}] {thought}")
                if result and result != "Action to be executed":
                    summary_lines.append(f"  Result: {str(result)[:200]}")
            elif p.get("type") == "final_answer":
                summary_lines.append(f"- Step {s['step_number']}: [FINAL_ANSWER] {p.get('content','')[:200]}")

        compressed_summary = "\n".join(summary_lines)

        # Build a compression injection message
        compression_note = {
            "role": "system",
            "content": (
                "[CONTEXT COMPRESSION APPLIED]\n"
                "The following is a dense summary of completed task steps. "
                "The full history has been compressed to save context space.\n\n"
                + compressed_summary
                + "\n\n[END COMPRESSION — Continue from the most recent steps below]"
            )
        }

        # Replace old messages with the compression note + recent messages
        # Keep the original user message at position 0
        original_user_messages = [m for m in task.messages if m.get("role") == "user"]
        task.messages = original_user_messages[:1] + [compression_note]

        # Trim old steps, keep recent
        task.steps = recent_steps

        return {
            "status": "success",
            "message": f"Compressed {len(old_steps)} old steps into a summary. {preserve_last_n} recent steps preserved.",
            "compressed_steps": len(old_steps),
            "preserved_steps": len(recent_steps),
            "summary_preview": compressed_summary[:300] + "..."
        }

    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }
