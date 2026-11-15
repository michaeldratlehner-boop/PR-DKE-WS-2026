"""Startet Backend (FastAPI) und Frontend (Vite) gemeinsam.

    python start.py

Beenden mit Strg+C: beide Prozesse werden dann gestoppt.
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"


def beenden(prozess: subprocess.Popen) -> None:
    """Stoppt einen Prozess samt Kindprozessen (unter Windows startet npm weitere)."""
    if prozess.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(prozess.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        prozess.terminate()


def main() -> int:
    npm = shutil.which("npm")
    if npm is None:
        print("FEHLER: npm nicht gefunden. Node.js installieren: https://nodejs.org/")
        return 1

    # Beim ersten Start fehlen die Pakete des Frontends noch.
    if not (FRONTEND / "node_modules").exists():
        print("Installiere Frontend-Abhängigkeiten (einmalig) ...")
        subprocess.run([npm, "install"], cwd=FRONTEND, check=True)

    print("Starte Backend   -> http://127.0.0.1:8000/docs")
    print("Starte Frontend  -> http://localhost:5173")
    print("Beenden mit Strg+C\n")

    # sys.executable = genau der Python-Interpreter, mit dem start.py läuft
    # (also die .venv, wenn sie aktiv ist).
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--app-dir", "harness", "--reload"],
        cwd=ROOT,
    )
    frontend = subprocess.Popen([npm, "run", "dev"], cwd=FRONTEND)
    prozesse = [backend, frontend]

    try:
        # Läuft, solange beide Prozesse leben. Stürzt einer ab, wird alles beendet.
        while all(p.poll() is None for p in prozesse):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for p in prozesse:
            beenden(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())