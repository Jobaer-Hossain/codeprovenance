"""
CodeProvenance Server Launcher
"""

import sys
import io
import argparse
import uvicorn
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    parser = argparse.ArgumentParser(description="CodeProvenance Web Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=8001, help="Port number")
    args = parser.parse_args()

    print("=" * 65)
    print("🔍 CodeProvenance — Architecture Drift & Evolution Detector")
    print(f"📡 Serving Web Dashboard at http://{args.host}:{args.port}")
    print("=" * 65)

    uvicorn.run("codeprovenance.api.server:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
