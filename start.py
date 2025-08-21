#!/usr/bin/env python3
"""
Start script for setting Windows asyncio event loop policy then launching Streamlit.
Run with: python start.py
This script ensures the SelectorEventLoopPolicy is used on Windows (fixes some Streamlit asyncio issues),
then runs `python -m streamlit run app.py` in the same environment.
"""
import asyncio
import sys
import subprocess
import os

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main() -> int:
    this_dir = os.path.dirname(__file__)
    app_path = os.path.join(this_dir, "app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", app_path]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
