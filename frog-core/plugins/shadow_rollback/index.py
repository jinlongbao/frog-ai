import logging
from typing import Dict, Any

def execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rollback or view changes made to the filesystem.
    """
    action = params.get("action")
    shadow_manager = context.get("shadow_manager")
    
    if not shadow_manager:
        return {"status": "error", "message": "Shadow Manager not found in context."}
        
    if action == "view_diff":
        diff = shadow_manager.get_diff()
        return {
            "status": "success",
            "message": "Current changes since last snapshot:",
            "diff": diff
        }
    
    elif action == "rollback":
        success = shadow_manager.rollback()
        if success:
            return {"status": "success", "message": "Workspace successfully reverted to last snapshot."}
        else:
            return {"status": "error", "message": "Rollback failed. Check logs for details."}
            
    else:
        return {"status": "error", "message": f"Unknown action: {action}"}
