"""Launch the local server and open the browser once it is ready."""
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8501"

def running():
    try:
        with urllib.request.urlopen(URL + "/_stcore/health", timeout=1) as response:
            return response.status == 200
    except Exception:
        return False

if running():
    webbrowser.open(URL)
    print("The local server is already running. Opened the browser.")
else:
    (ROOT/"work").mkdir(exist_ok=True)
    with (ROOT/"work/server.log").open("a") as log:
        process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("The server could not start. See work/server.log.")
            if running():
                webbrowser.open(URL)
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("The local server did not become ready within 30 seconds.")
        process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()
