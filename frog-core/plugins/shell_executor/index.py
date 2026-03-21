import subprocess
import os

def execute(params: dict, context: dict) -> dict:
    """
    Execute a shell command.
    params: { "command": "...", "cwd": "..." }
    """
    command = params.get("command")
    cwd = params.get("cwd") or os.getcwd()
    
    if not command:
        return {"status": "error", "message": "No command provided."}
        
    # Basic security blacklist for Windows and Unix
    blacklist = [
        "rd /s", "del /f /s /q c:", "format", "net user", "reg delete",
        "rm -rf /", "rm -rf /*", "mkfs", ":(){ :|:& };:"
    ]
    cmd_lower = command.lower()
    for item in blacklist:
        if item in cmd_lower:
            return {"status": "error", "message": f"Security violation: Command '{command}' contains blacklisted pattern '{item}'."}

    try:
        # On Windows, shell=True is often needed for built-in commands like 'dir'
        process = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30 # Safety timeout
        )
        
        return {
            "status": "success",
            "stdout": process.stdout,
            "stderr": process.stderr,
            "returncode": process.returncode,
            "message": f"Command executed with return code {process.returncode}"
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Command timed out after 30 seconds."}
    except Exception as e:
        return {"status": "error", "message": f"Execution failed: {str(e)}"}
