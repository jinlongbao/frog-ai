import subprocess
import os
import time
import sys

# Paths to executables
PYTHON_EXE = r"C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe"
NODE_DIR = r"C:\Program Files\nodejs"
ELECTRON_EXE = os.path.join(os.getcwd(), "frog-shell", "node_modules", "electron", "dist", "electron.exe")

def run_brain():
    print("Starting Frog AI Brain (Python)...")
    return subprocess.Popen([PYTHON_EXE, "frog-core/main.py"])

def run_shell():
    print("Starting Frog AI Shell (Electron)...")
    env = os.environ.copy()
    env["PATH"] = f"{NODE_DIR};{os.path.dirname(PYTHON_EXE)};{env.get('PATH', '')}"
    # Use the absolute path to the electron binary to avoid resolution issues
    return subprocess.Popen([ELECTRON_EXE, "frog-shell"], env=env)

if __name__ == "__main__":
    brain_proc = run_brain()
    time.sleep(2) # Wait for FastAPI to warm up
    shell_proc = run_shell()
    
    print("\nFrog AI Core is running!")
    print("Press Ctrl+C to stop all components.\n")
    
    try:
        shell_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        brain_proc.terminate()
        shell_proc.terminate()
