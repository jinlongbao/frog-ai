import os
import subprocess

def execute(params, context):
    cmd = params.get("command")
    cwd = params.get("cwd", os.getcwd())

    if not cmd:
        return {"status": "error", "message": "Missing 'command' parameter"}

    try:
        # Run command securely with timeout limits
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120
        )

        output = result.stdout.strip()
        error = result.stderr.strip()

        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": f"STDOUT:\n{output}\n\nSTDERR:\n{error}",
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": f"Command '{cmd}' timed out after 120 seconds."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
