import httpx
import os
import sys
import json

def execute(params: dict, context: dict) -> dict:
    file_path = params.get("file_path", "").strip()
    caption = params.get("caption", "")

    # 从 context 获取 Telegram 凭证
    token = context.get("telegram_token", "")
    chat_id = context.get("telegram_chat_id", "")

    if not token or not chat_id:
        return {"status": "error", "message": "Missing telegram_token or telegram_chat_id in context. Make sure the task was triggered via Telegram remote control."}

    if not file_path:
        return {"status": "error", "message": "Missing required parameter: file_path"}

    # --- START SMART PATH RESOLUTION ---
    search_paths = []
    
    # 1. Try original path
    search_paths.append(file_path)
    
    # 2. Try expanded home path
    if file_path.startswith("~"):
        search_paths.append(os.path.expanduser(file_path))
        
    # 3. If it's just a filename, look in common 'Hero' spots
    if not os.path.dirname(file_path):
        from pathlib import Path
        # Built-in system paths
        search_paths.append(str(Path.home() / "Desktop" / file_path))
        search_paths.append(str(Path.home() / "Downloads" / file_path))
        # Current workspace
        search_paths.append(os.path.join(os.getcwd(), file_path))
        # LOCALIZED / REDIRECTED checks (D:\桌面 etc)
        for drive in ['C', 'D', 'E']:
            for localized_name in ['桌面', 'Desktop']:
                redirect_path = f"{drive}:\\{localized_name}\\{file_path}"
                search_paths.append(redirect_path)

    # Find first existing path
    final_path = None
    for p in search_paths:
        if os.path.exists(p):
            final_path = p
            break
            
    if not final_path:
        return {
            "status": "error", 
            "message": f"File not found: {file_path}. I checked {len(search_paths)} potential locations including Desktop and Downloads.",
            "searched_locations": search_paths[:5] # Show a few for debugging
        }
        
    file_path = final_path
    # --- END SMART PATH RESOLUTION ---

    # 判断文件类型
    ext = os.path.splitext(file_path)[1].lower()
    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    is_image = ext in image_exts

    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        file_name = os.path.basename(file_path)

        if is_image:
            # 发送图片
            api_url = f"https://api.telegram.org/bot{token}/sendPhoto"
            files = {"photo": (file_name, file_bytes)}
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption
        else:
            # 发送文件
            api_url = f"https://api.telegram.org/bot{token}/sendDocument"
            files = {"document": (file_name, file_bytes)}
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption

        response = httpx.post(api_url, data=data, files=files, timeout=60)

        if response.status_code == 200 and response.json().get("ok"):
            return {
                "status": "success",
                "message": f"File '{file_name}' sent successfully to Telegram chat {chat_id}.",
                "file_type": "photo" if is_image else "document"
            }
        else:
            return {
                "status": "error",
                "message": f"Telegram API error: {response.text}"
            }

    except Exception as e:
        return {"status": "error", "message": str(e)}
