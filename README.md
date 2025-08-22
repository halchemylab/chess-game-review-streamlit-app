# ♟️ PGN Game Review (Streamlit)

A lightweight, local, Chess.com-style game review tool. Paste a PGN, hit **Analyze**, and get:

* An **interactive board** with a scrubber and optional best-move arrows
* An **evaluation graph** (centipawns, White POV) across the game
* **Per-move classifications** (Best / Excellent / Good / Inaccuracy / Mistake / Blunder + a few special tags)
* **Key Moments** detection and a **Retry** trainer (try a better move and compare vs. engine)
* A friendly **coach avatar** that comments on each move
* Adjustable **engine settings** (time per move, MultiPV, threads)

> ⚠️ This project is unaffiliated with Chess.com. Accuracy scoring and labels are transparent approximations (not CAPS2), so results won’t exactly match Chess.com’s Game Review.

---

## ✨ Features

* **PGN In, Insights Out** – Paste any single-game PGN; headers are extracted automatically (players, result, event).
* **Local Stockfish Analysis** – Uses your local Stockfish engine (no internet required after install).
* **Move Tags** – CP-loss/swing–based labels + simple heuristics for “Brilliant”, “Missed Win”, “Missed Mate”.
* **Eval Graph** – White-centric centipawn chart after each move; quick feel for where things swung.
* **Key Moments** – Auto-picks the biggest eval swings and critical errors (Mistake/Blunder/Missed Win/Missed Mate).
* **Retry Trainer** – Rewind to a key moment, try your own move (SAN or UCI), and compare to engine’s suggestion.
* **Coach Avatar** – Choose a persona; get concise, plain-English commentary for every move.
* **Configurable Depth** – Choose Quick/Balanced/Deep presets, MultiPV (1–3), and Threads.

---

## 🧰 What’s inside

```
.
├── app.py              # Streamlit app (UI + engine logic)
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

**Key libraries**

* [Streamlit] for the UI
* [python-chess] for PGN parsing, board/engine integration, and SVG rendering
* [Plotly] for the evaluation chart
* **Stockfish** (binary on your machine) for actual chess analysis

[Streamlit]: https://streamlit.io
[python-chess]: https://python-chess.readthedocs.io
[Plotly]: https://plotly.com/python/
[Stockfish official site]: https://stockfishchess.org/

---

## 🚀 Quickstart

### Prereqs

* Python **3.9+** recommended
* A local **Stockfish** engine (see install steps below)

### 1) Clone or create a folder, then add files

Save `app.py`, `requirements.txt`, and this `README.md` into the same folder.

### 2) Install Python deps

```bash
pip install -r requirements.txt
```

### 3) Install Stockfish

**macOS (Homebrew)**

```bash
brew install stockfish
```

The binary is typically at `/opt/homebrew/bin/stockfish` (Apple Silicon) or `/usr/local/bin/stockfish` (Intel).

**Ubuntu/Debian**

```bash
sudo apt-get update
sudo apt-get install -y stockfish
```

**Windows**

1. Download the latest Windows build from the [Stockfish official site].
2. Unzip somewhere like: `C:\Tools\Stockfish\stockfish-windows-x86-64.exe`
3. (Optional) Add that directory to your system **PATH**.

> Tip (any OS): Verify it’s on your PATH
>
> ```bash
> stockfish -h
> ```
>
> If you see usage text, you’re good.

### 4) Point the app to Stockfish (if needed)

# ♟️ PGN Game Review (Streamlit)

A lightweight, local, Chess.com-style game review tool built with Streamlit + python-chess. Paste a PGN, click Analyze, and get:

- Interactive board with a scrubber and optional best-move arrows
- Evaluation graph (centipawns, White POV)
- Per-move classifications (Best / Excellent / Good / Inaccuracy / Mistake / Blunder, plus special tags)
- Key moments detection and a Retry trainer (enter a move and compare to the engine)
- A friendly coach avatar that produces short comments
- Configurable engine settings (time per move, MultiPV, threads)

> ⚠️ This project is unaffiliated with Chess.com. The accuracy score and tags are transparent approximations (not CAPS2) and will not exactly match their Game Review.

## Quick summary of the repo

Files you care about:

- `app.py` — the Streamlit app (UI + engine analysis logic)
- `start.py` — convenience starter for Windows that sets the asyncio policy and launches Streamlit
- `requirements.txt` — Python dependencies
- `README.md` — this file

Key libraries:

- Streamlit — UI
- python-chess — PGN parsing, board, engine integration, SVG rendering
- Plotly — evaluation chart
- Stockfish — an external engine binary (installed on your machine)

## Requirements

- Python 3.9+ recommended
- See `requirements.txt` (Streamlit, python-chess, plotly, pandas, numpy)
- A local Stockfish binary (any modern build)

## Install and run

1. Create and activate a virtual environment (recommended)

PowerShell (recommended on Windows):

```pwsh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux (bash/zsh):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Install Stockfish

- macOS (Homebrew): `brew install stockfish`
- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y stockfish`
- Windows: download a release from https://stockfishchess.org/ and unzip somewhere (e.g. `C:\Tools\Stockfish\stockfish.exe`).

3. Point the app to Stockfish (app auto-detects in this order):

1. `STOCKFISH_PATH` environment variable
2. system `PATH` (i.e. `stockfish` is runnable)
3. Streamlit secrets (optional)
4. Sidebar field in the app (manual override)

Set `STOCKFISH_PATH` (PowerShell example):

```pwsh
$env:STOCKFISH_PATH = 'C:\Tools\Stockfish\stockfish-windows-x86-64.exe'
```

Or in macOS/Linux (bash/zsh):

```bash
export STOCKFISH_PATH="/full/path/to/stockfish"
```

4. Run the app

On Windows, the supplied `start.py` sets a compatible asyncio policy and launches Streamlit (useful on some Windows setups):

```pwsh
python start.py
```

You can also run Streamlit directly:

```bash
streamlit run app.py
```

Then open the URL Streamlit prints (typically http://localhost:8501).

## Notes about `start.py`

`start.py` simply sets `asyncio.WindowsSelectorEventLoopPolicy()` when running on `win32` and then calls `python -m streamlit run app.py` using the current interpreter. If you encounter asyncio-related warnings or Streamlit behaves oddly on Windows, use `python start.py` instead of `streamlit run app.py`.

## Using the app (brief)

- Paste a single-game PGN into the PGN box (a sample game is preloaded).
- Use the sidebar to choose an avatar, analysis preset (Quick/Balanced/Deep), MultiPV (1–3), threads, and optionally override Stockfish path.
- Click Analyze Game to run analysis (requires a valid Stockfish binary).
- Tabs:
  - Review: Eval graph and board scrubber with tagged moves and coach comments.
  - Key Moments / Retry: Table of big swings/critical errors, and a position trainer to try your moves.
  - Moves: Full per-move table with evals and engine PV.
  - Settings: Engine detection status and notes.

## Troubleshooting

- "Stockfish not found":
  - Run `stockfish -h` in a terminal to confirm it is on your PATH.
  - Or set `STOCKFISH_PATH` and/or paste the full path into the app sidebar.

- Engine errors while retrying:
  - Verify the `stockfish` binary is correct and accessible by the user running Streamlit.
  - Lower MultiPV or use the Quick preset if the machine is low-powered.

- High CPU usage:
  - Reduce threads and/or lower preset time per move. MultiPV > 1 increases load.

## How the analysis works (high level)

1. Parse the PGN mainline with `python-chess`.
2. For each ply: query Stockfish for a PV before the move, play the game's move, then query again.
3. Compute CP loss (how far from best) and swing (eval change), tag the move using transparent thresholds, and collect candidate lines if MultiPV > 1.
4. Accuracy is approximated from Average Centipawn Loss (ACPL).

## License

MIT — see the repository for details.

---

If you'd like, I can also:

- Add a short CONTRIBUTING section or a one-line Docker run example
- Create a small `launch.ps1` that sets `STOCKFISH_PATH` and starts `start.py` on Windows

Status: README cleaned and updated to reflect `app.py` and `start.py` behavior.