import httpx
import json

def execute(params, context):
    action = params.get("action", "send_webhook")
    webhook_url = params.get("webhook_url")
    message = params.get("message", "")
    bot_type = params.get("bot_type", "generic")
    custom_payload = params.get("custom_payload")

    # 0. Pull keys from context if missing
    wechat_key = context.get("wechat_work_key")
    tg_token = context.get("telegram_token")
    tg_chat_id = params.get("chat_id") or context.get("telegram_chat_id")

    if action != "send_webhook":
        return {"status": "error", "message": f"Unsupported action: {action}"}

    if not webhook_url:
        # Auto-construct URL if keys exist in context
        if bot_type == "wechat_work" and wechat_key:
            webhook_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={wechat_key}"
        elif bot_type == "telegram" and tg_token:
            webhook_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        
        if not webhook_url:
            return {"status": "error", "message": "Missing 'webhook_url' and no bot key found in settings."}

    # 1. Structure the Payload based on Bot Type
    payload = None
    if custom_payload:
        payload = custom_payload
    else:
        if bot_type == "wechat_work":
            # 企业微信机器人协议
            payload = {
                "msgtype": "text",
                "text": {"content": message}
            }
        elif bot_type == "discord":
            # Discord Webhook 协议
            payload = {"content": message}
            # Telegram Bot API 协议
            payload = {
                "text": message
            }
            if tg_chat_id:
                payload["chat_id"] = tg_chat_id
            else:
                return {"status": "error", "message": "Telegram requires a 'chat_id' (missing in params and settings)."}
        elif bot_type in ["feishu", "dingtalk"]:
            # 飞书/钉钉 通用文本协议
            payload = {
                "msgtype": "text",
                "text": {"content": message}
            }
        else:
            # 通用 JSON 格式 (fallback)
            payload = {"message": message, "text": message}

    # 2. Fire the Request
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(webhook_url, json=payload)
            response.raise_for_status()
            
            # WeChat Work and some bots return 200 even on logical errors
            # (e.g. wrong key), but raise_for_status covers network errors.
            return {
                "status": "success",
                "response_body": response.text,
                "message": "Message sent successfully via API."
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to send message via Bot API: {str(e)}",
            "payload_sent": payload
        }
