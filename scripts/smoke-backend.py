import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_DIR = ROOT / "build" / "backend" / "smp-workbench-backend"
EXECUTABLE = BUNDLE_DIR / (
    "smp-workbench-backend.exe" if sys.platform.startswith("win") else "smp-workbench-backend"
)


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(port: int, timeout_seconds: int = 120) -> None:
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as error:  # noqa: BLE001 - report the last startup failure.
            last_error = error
        time.sleep(0.25)

    raise RuntimeError(f"Backend health check failed: {last_error}")


def main() -> None:
    if not EXECUTABLE.exists():
        raise FileNotFoundError(f"Packaged backend not found: {EXECUTABLE}")

    port = get_free_port()
    process = subprocess.Popen(
        [str(EXECUTABLE), "--port", str(port)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    error: Exception | None = None
    output = ""
    try:
        wait_for_health(port)
    except Exception as exc:  # noqa: BLE001 - re-raised after process output is captured.
        error = exc
    finally:
        process.terminate()
        try:
            output, _ = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate(timeout=5)

    if error is not None:
        if output:
            print(output)
        raise error

    print(f"Packaged backend responded on http://127.0.0.1:{port}/api/health")


if __name__ == "__main__":
    main()
