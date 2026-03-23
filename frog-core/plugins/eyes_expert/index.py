import os
import time
import base64
import httpx

def execute(params, context):
    question = params.get("question", "Please describe what is currently happening on this screen.")
    
    try:
        import pyautogui
    except ImportError:
        return {"status": "error", "message": "Missing dependency. Run `pip install pyautogui` first."}
         
    try:
        # 1. Take a clean screenshot
        temp_img = os.path.abspath(f"temp_vision_screenshot_{int(time.time())}.png")
        pyautogui.screenshot(temp_img)
        
        # 2. Encode to base64
        with open(temp_img, "rb") as f:
            b64_image = base64.b64encode(f.read()).decode("utf-8")
            
        # Clean up
        try:
            os.remove(temp_img)
        except Exception:
            pass
            
        # 3. Pull user API credentials gracefully (prioritizing dynamic context from Setup Wizard)
        api_key = context.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        base_url = context.get("api_base_url") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip('/')
        model = context.get("model") or os.environ.get("DEFAULT_MODEL", "gpt-4o")
        
        if not api_key:
            return {"status": "error", "message": "Missing OPENAI_API_KEY in environment variables. Setup wizard must be completed."}
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{question} (Respond specifically and concisely to the prompt based ONLY on the image provided.)"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                    ]
                }
            ],
            "max_tokens": 1000
        }
        
        # 4. Proxy to Vision Endpoint
        response = httpx.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=60.0)
        
        if response.status_code != 200:
            return {
                "status": "error", 
                "message": f"Vision API rejected the request. Does your model '{model}' support Vision payloads? Error: {response.text}"
            }
            
        data = response.json()
        vision_result = data['choices'][0]['message']['content']
        
        return {
            "status": "success",
            "vision_analysis": vision_result
        }

    except Exception as e:
        return {"status": "error", "message": f"Screen Vision Expert failed: {str(e)}"}
