import os
import shutil
from pathlib import Path

def execute(params, context):
    action = params.get("action")
    path = params.get("path")
    content = params.get("content", "")

    if not path:
        return {"status": "error", "message": "Missing 'path' parameter"}

    try:
        abs_path = os.path.abspath(path)
        target = Path(abs_path)

        if action == "read":
            if not target.exists():
                return {"status": "error", "message": f"File not found: {path}"}
            if target.is_dir():
                return {"status": "error", "message": f"{path} is a directory, use 'list' instead."}
            return {"status": "success", "content": target.read_text(encoding="utf-8")}

        elif action == "write":
            parent = target.parent
            if parent and not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {"status": "success", "message": f"File written to {path}"}

        elif action == "list":
            if not target.exists():
                return {"status": "error", "message": f"Directory not found: {path}"}
            if not target.is_dir():
                return {"status": "error", "message": f"{path} is a file, use 'read' instead."}
            results = []
            for item in target.iterdir():
                try:
                    results.append({
                        "name": item.name,
                        "type": "dir" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None
                    })
                except Exception:
                    continue
            return {"status": "success", "items": results}

        elif action == "delete":
            if not target.exists():
                return {"status": "error", "message": f"Not found: {path}"}
            if target.is_dir():
                shutil.rmtree(str(target))
            else:
                target.unlink()
            return {"status": "success", "message": f"Deleted {path}"}

        elif action == "exists":
            return {"status": "success", "exists": target.exists()}

        elif action == "info":
            if not target.exists():
                return {"status": "error", "message": f"Not found: {path}"}
            stat = target.stat()
            return {
                "status": "success",
                "name": target.name,
                "type": "dir" if target.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "path": str(target)
            }

        else:
            return {"status": "error", "message": f"Unsupported action: {action}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
