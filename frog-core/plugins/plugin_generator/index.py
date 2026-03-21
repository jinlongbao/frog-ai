import sys
import os
import traceback

# Ensure frog-core is in the path to import tool_writer
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from tool_writer import tool_writer

def execute(params: dict, context: dict) -> dict:
    """
    Execute tool creation or healing.
    params: { "action": "create|fix", "tool_name": "...", "code": "...", "description": "...", "error_message": "..." }
    """
    action = params.get("action")
    tool_name = params.get("tool_name")
    code = params.get("code")
    
    if not action or not tool_name or not code:
        return {"status": "error", "message": "Missing required parameters: action, tool_name, and code"}
        
    try:
        if action == "create":
            description = params.get("description", f"Generated tool: {tool_name}")
            # Ensure safe parameters
            tool_params = params.get("parameters", {})
            if not isinstance(tool_params, dict):
                tool_params = {}
                
            result = tool_writer.write_tool(
                tool_name=tool_name,
                description=description,
                code=code,
                parameters=tool_params
            )
            result["installed"] = True
            result["message"] = f"Successfully created and installed plugin: {tool_name}"
            return result
            
        elif action == "fix":
            error_message = params.get("error_message", "Unknown error")
            result = tool_writer.fix_tool(
                tool_id=tool_name,
                error_message=error_message,  # Used by tool_writer for logging
                new_code=code
            )
            result["healed"] = True
            result["message"] = f"Successfully applied fix and hot-reloaded plugin: {tool_name}"
            return result
            
        else:
            return {"status": "error", "message": f"Unknown action: {action}. Use 'create' or 'fix'."}
            
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Autonomous Plugin Generator failed: {str(e)}",
            "traceback": traceback.format_exc()
        }
