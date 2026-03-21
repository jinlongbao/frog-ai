import json
import urllib.request
import urllib.error

def _fetch(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore').strip(), resp.getcode(), resp.headers.get_content_type()

def execute(params: dict, context: dict) -> dict:
    services = [
        ("https://api.ipify.org?format=json", "json_ipify"),
        ("https://ifconfig.me/ip", "text_ifconfig"),
        ("https://checkip.amazonaws.com/", "text_aws"),
        ("https://icanhazip.com/", "text_icanhazip")
    ]
    errors = []
    for url, mode in services:
        try:
            body, status, ctype = _fetch(url)
            if status != 200:
                errors.append(f"{url} status={status}")
                continue
            ip = None
            if mode == "json_ipify":
                data = json.loads(body)
                ip = data.get("ip")
            else:
                ip = body.strip()
            if ip:
                return {"success": True, "ip": ip, "source": url}
            errors.append(f"{url} empty response")
        except Exception as e:
            errors.append(f"{url} error={type(e).__name__}: {e}")
    return {"success": False, "error": "Failed to determine public IP", "details": errors}
