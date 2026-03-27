import os
import json
from datetime import datetime
from typing import Dict, Any

def execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Manage persistent project memory using ChromaDB.
    params: { action: "save|get|list|search|clear", key: "...", value: "...", query: "..." }
    """
    action = params.get("action")
    key = params.get("key")
    value = params.get("value")
    query = params.get("query")
    
    memory_manager = context.get("memory_manager")
    if not memory_manager:
        return {"status": "error", "message": "MemoryManager not found in context."}
    
    collection = "project_memory"
    
    if action == "save":
        if not key or not value:
            return {"status": "error", "message": "'key' and 'value' are required for save."}
        
        memory_manager.add_memory(
            collection_name=collection,
            content=value,
            metadata={"key": key, "timestamp": datetime.now().isoformat()},
            doc_id=key
        )
        return {"status": "success", "message": f"Memory saved under key '{key}'"}
        
    elif action == "get":
        if not key:
            return {"status": "error", "message": "'key' is required for get."}
        
        memo = memory_manager.get_memory_by_id(collection, key)
        if not memo:
            return {"status": "error", "message": f"Key '{key}' not found."}
        return {"status": "success", "data": memo}
        
    elif action == "search":
        if not query:
            return {"status": "error", "message": "'query' is required for search."}
        
        results = memory_manager.search_memory(collection, query, n_results=params.get("n_results", 3))
        return {"status": "success", "results": results}
        
    elif action == "clear":
        if not key:
            return {"status": "error", "message": "'key' is required for clear."}
        
        memory_manager.delete_memory(collection, key)
        return {"status": "success", "message": f"Memory '{key}' cleared."}
        
    else:
        return {"status": "error", "message": f"Unknown or unsupported action: {action}"}
