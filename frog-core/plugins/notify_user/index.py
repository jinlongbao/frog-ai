"""
Frog Plugin: Notify User
Sends a desktop system notification to alert the user.
Works on Windows (via win10toast / Windows-native), macOS (osascript), and Linux (notify-send).
"""
import os
import sys
import platform
import subprocess


def _notify_windows(title: str, message: str, urgency: str):
    """Try multiple Windows notification methods."""
    # Method 1: win10toast (if installed)
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(
            title,
            message,
            duration=8 if urgency == "critical" else 5,
            threaded=True
        )
        return True
    except ImportError:
        pass

    # Method 2: PowerShell toast notification (no extra deps)
    try:
        ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.Visible = $true
$notify.ShowBalloonTip(5000, '{title.replace("'", "")}', '{message.replace("'", "")}', [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Seconds 6
$notify.Dispose()
"""
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except Exception:
        pass

    return False


def _notify_macos(title: str, message: str):
    """macOS notification via osascript."""
    try:
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=True, timeout=5)
        return True
    except Exception:
        return False


def _notify_linux(title: str, message: str, urgency: str):
    """Linux notification via notify-send."""
    try:
        level = "critical" if urgency == "critical" else "normal"
        subprocess.run(
            ["notify-send", "-u", level, title, message],
            check=True, timeout=5
        )
        return True
    except Exception:
        return False


def execute(params: dict, context: dict) -> dict:
    title   = params.get("title", "Frog AI")[:50]
    message = params.get("message", "")[:200]
    urgency = params.get("urgency", "normal")

    if not message:
        return {"status": "error", "message": "message is required"}

    system = platform.system()
    success = False

    try:
        if system == "Windows":
            success = _notify_windows(title, message, urgency)
        elif system == "Darwin":
            success = _notify_macos(title, message)
        elif system == "Linux":
            success = _notify_linux(title, message, urgency)
        else:
            return {"status": "error", "message": f"Unsupported OS: {system}"}
    except Exception as e:
        return {"status": "error", "message": f"Notification failed: {str(e)}"}

    if success:
        print(f"[notify_user] 🔔 {title}: {message}")
        return {
            "status": "success",
            "message": f"Desktop notification sent: '{title}'",
            "platform": system
        }
    else:
        # Fallback: at minimum print to console
        print(f"\n{'='*50}\n🔔 FROG AI NOTIFICATION\n{title}\n{message}\n{'='*50}\n")
        return {
            "status": "success",
            "message": "Notification sent via console fallback (no OS notification library installed)",
            "fallback": True
        }
