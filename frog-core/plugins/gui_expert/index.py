import time

def execute(params, context):
    action = params.get("action")
    
    try:
        import pyautogui
    except ImportError:
        return {
            "status": "error", 
            "message": "Missing dependencies. Run `pip install pyautogui pyperclip` via shell_executor first."
        }

    try:
        if action == "click":
            x, y = params.get("x"), params.get("y")
            if x is not None and y is not None:
                pyautogui.click(x=x, y=y)
                msg = f"Clicked at ({x}, {y})"
            else:
                pyautogui.click()
                msg = "Clicked at current location"
            return {"status": "success", "message": msg}
            
        elif action == "double_click":
            x, y = params.get("x"), params.get("y")
            if x is not None and y is not None:
                pyautogui.doubleClick(x=x, y=y)
            else:
                pyautogui.doubleClick()
            return {"status": "success", "message": "Double clicked"}

        elif action == "mouse_move":
            x, y = params.get("x"), params.get("y")
            if x is None or y is None:
                return {"status": "error", "message": "Missing x or y for mouse_move"}
            pyautogui.moveTo(x, y, duration=0.2)
            return {"status": "success", "message": f"Moved mouse to ({x}, {y})"}

        elif action == "type":
            text = params.get("text")
            if not text:
                return {"status": "error", "message": "Missing 'text' parameter"}
            
            # Use pyperclip to bypass PyAutoGUI's inability to type non-ASCII (e.g. Chinese)
            try:
                import pyperclip
                pyperclip.copy(str(text))
                time.sleep(0.1)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.1)
                return {"status": "success", "message": f"Typed text natively (via clipboard): {text}"}
            except ImportError:
                return {"status": "error", "message": "Missing dependency. Please `pip install pyperclip`."}
            
        elif action == "press":
            keys = params.get("keys", [])
            if not keys:
                return {"status": "error", "message": "Missing 'keys' array"}
            for k in keys:
                pyautogui.press(str(k).lower())
                time.sleep(0.05)
            return {"status": "success", "message": f"Pressed sequential keys: {keys}"}
            
        elif action == "hotkey":
            keys = params.get("keys", [])
            if len(keys) < 2:
                return {"status": "error", "message": "Hotkey requires at least 2 keys (e.g., ['ctrl', 'c'])"}
            pyautogui.hotkey(*[str(k).lower() for k in keys])
            return {"status": "success", "message": f"Executed hotkey combo: {keys}"}
            
        elif action == "sleep":
            duration = params.get("duration", 1.0)
            time.sleep(float(duration))
            return {"status": "success", "message": f"Slept for {duration} seconds. Ready for next action."}
            
        else:
            return {"status": "error", "message": f"Unknown GUI action: {action}"}
            
    except Exception as e:
        return {"status": "error", "message": f"GUI RPA failed: {str(e)}"}
