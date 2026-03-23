import os
import shutil

def execute(params, context):
    action = params.get("action")
    path = params.get("path")
    content = params.get("content", "")

    if not path:
        return {"status": "error", "message": "Missing 'path' parameter"}

    try:
        # Normalize path
        path = os.path.expanduser(path)
        abs_path = os.path.abspath(path)

        if action == "read":
            if not os.path.exists(abs_path):
                return {"status": "error", "message": f"File not found: {path}"}
            if os.path.isdir(abs_path):
                return {"status": "error", "message": f"{path} is a directory, use 'list' instead."}
            with open(abs_path, "r", encoding="utf-8") as f:
                return {"status": "success", "content": f.read()}

        elif action == "write":
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"status": "success", "message": f"File written to {path}"}

        elif action == "list":
            if not os.path.exists(abs_path):
                return {"status": "error", "message": f"Directory not found: {path}"}
            if not os.path.isdir(abs_path):
                return {"status": "error", "message": f"{path} is a file, use 'read' instead."}
            items = os.listdir(abs_path)
            results = []
            for item in items:
                item_path = os.path.join(abs_path, item)
                try:
                    results.append({
                        "name": item,
                        "type": "dir" if os.path.isdir(item_path) else "file",
                        "size": os.path.getsize(item_path) if os.path.isfile(item_path) else None
                    })
                except Exception:
                    continue
            return {"status": "success", "items": results}

        elif action == "delete":
            if not os.path.exists(abs_path):
                return {"status": "error", "message": f"Not found: {path}"}
            if os.path.isdir(abs_path):
                shutil.rmtree(abs_path)
            else:
                os.remove(abs_path)
            return {"status": "success", "message": f"Deleted {path}"}

        elif action == "exists":
            return {"status": "success", "exists": os.path.exists(abs_path)}

        elif action == "info":
            if not os.path.exists(abs_path):
                return {"status": "error", "message": f"Not found: {path}"}
            stat = os.stat(abs_path)
            return {
                "status": "success",
                "name": os.path.basename(abs_path),
                "type": "dir" if os.path.isdir(abs_path) else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime
            }

        else:
            return {"status": "error", "message": f"Unsupported action: {action}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
