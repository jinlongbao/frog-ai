import os
import json
import threading
from datetime import datetime

# Shared lock for thread safety since FastAPI runs in a thread pool
_memory_lock = threading.Lock()

def get_memory_file(context: dict) -> str:
    # Use the knowledge directory provided by context or fallback to a default
    base_dir = context.get("knowledge_dir", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "project_memory.json")

def _load_memory(filepath: str) -> dict:
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_memory_file(filepath: str, data: dict):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def execute(params: dict, context: dict) -> dict:
    """
    Manage persistent project memory.
    params: { action: "save|get|list|clear", key: "...", value: "..." }
    """
    action = params.get("action")
    key = params.get("key")
    value = params.get("value")
    
    memory_file = get_memory_file(context)
    
    if action not in ["save", "get", "list", "clear"]:
        return {"status": "error", "message": f"Unknown action: {action}"}
        
    with _memory_lock:
        memory = _load_memory(memory_file)
        
        if action == "save":
            if not key or not value:
                return {"status": "error", "message": "'key' and 'value' are required for save."}
            memory[key] = {
                "content": value,
                "timestamp": datetime.now().isoformat()
            }
            _save_memory_file(memory_file, memory)
            return {"status": "success", "message": f"Memory saved under key '{key}'"}
            
        elif action == "get":
            if not key:
                return {"status": "error", "message": "'key' is required for get."}
            if key not in memory:
                return {"status": "error", "message": f"Key '{key}' not found in memory."}
            return {"status": "success", "data": memory[key]}
            
        elif action == "list":
            keys = list(memory.keys())
            summary = {k: v["timestamp"] for k, v in memory.items()}
            return {"status": "success", "keys": keys, "summary": summary}
            
        elif action == "clear":
            if not key:
                return {"status": "error", "message": "'key' is required for clear."}
            if key in memory:
                del memory[key]
                _save_memory_file(memory_file, memory)
                return {"status": "success", "message": f"Memory '{key}' cleared."}
            return {"status": "success", "message": f"Key '{key}' not found, nothing to clear."}
