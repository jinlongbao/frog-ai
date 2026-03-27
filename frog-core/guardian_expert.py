import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("frog-guardian")

# Known destructive patterns that require human oversight
DESTRUCTIVE_PATTERNS = [
    "rm ", "rmdir ", "del ", "erase ", 
    "format ", "mkfs ", "fdisk ",
    "drop database", "drop table", "truncate table", "delete from",
    "chmod 777", "chown ",
    "shutdown ", "reboot ", "kill -9",
    "pip uninstall ", "npm uninstall ",
    "git push --force", "git remote add", "git remote set-url"
]

def audit_tool_call(tool_name: str, params: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Audits a tool call for potentially destructive or dangerous actions.
    Returns (is_safe, warning_message).
    """
    param_str = str(params).lower()
    
    # Check for direct destructive commands in strings
    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern in param_str:
            return False, f"Potentially destructive pattern '{pattern}' detected in parameters."
            
    # Check for specific suspicious tool usage
    if tool_name == "fs_expert" and params.get("action") == "delete":
        return False, "File deletion requested via fs_expert."
        
    if tool_name == "bash_expert" or tool_name == "powershell_expert":
         command = params.get("command", "").lower()
         for pattern in DESTRUCTIVE_PATTERNS:
             if pattern in command:
                 return False, f"Dangerous command pattern '{pattern}' detected in shell script."

    return True, ""
