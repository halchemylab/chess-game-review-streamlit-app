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

The app will try to auto-detect Stockfish via:

1. `STOCKFISH_PATH` environment variable
2. Your system `PATH`
3. A Streamlit secret called `stockfish_path`
4. The **sidebar** “Stockfish path (optional override)” field

**Set an environment variable**

macOS/Linux:

```bash
export STOCKFISH_PATH="/full/path/to/stockfish"
# Example: export STOCKFISH_PATH="/opt/homebrew/bin/stockfish"
```

Windows (PowerShell):

```powershell
$env:STOCKFISH_PATH="C:\Tools\Stockfish\stockfish-windows-x86-64.exe"
```

Or just paste the full path into the app’s sidebar field.

### 5) Run the app

```bash
streamlit run app.py
```

Open the URL Streamlit prints (typically [http://localhost:8501](http://localhost:8501)). Paste a PGN, click **Analyze Game**.

---

## 🕹️ Using the app

* **PGN box**: Paste your game (single game per run). A sample PGN is prefilled so you can test immediately.
* **Analyze Game**: Runs engine analysis with your chosen preset / MultiPV / threads.
* **Review tab**:

  * **Eval chart** (left): Hover to see exact evals by ply.
  * **Board + scrubber** (right): Slide through moves and optionally show the engine’s recommended arrow.
  * **Move tag + coach**: Each move gets a classification and a short, helpful comment.
* **Key Moments / Retry**:

  * Table of biggest swings and critical errors.
  * Select a **ply** to revisit that position. Enter a SAN (e.g., `Nf3`) or UCI (`g1f3`) move and compare your idea vs. engine.
* **Moves tab**: Full per-move table (ply, turn, SAN, tag, CP loss/swing, eval before/after, engine PV).
* **Settings tab**: See engine detection status and notes.

**Sidebar controls**

* **Coach avatar**: Choose a persona (just for fun).
* **Analysis preset**: Quick / Balanced / Deep (time per move).
* **Candidate lines (MultiPV)**: Show 1–3 engine lines (slower with more).
* **Engine threads**: Use more CPU cores if you have them.
* **Stockfish path**: Manual override.

---

## 📐 How it works (high level)

1. **Parse PGN** via `python-chess` and build the mainline.
2. For each ply:

   * Ask Stockfish for evaluation and principal variation **before** the move.
   * Play the game’s actual move.
   * Ask Stockfish for evaluation **after** the move.
   * Compute **CP loss** (how far off from the best engine line the played move was) and **swing** (eval change).
   * Tag the move using transparent thresholds +
     heuristics for **Brilliant** (sacrifice that maintains/improves eval), **Missed Win**, and **Missed Mate**.
3. **Accuracy** is derived from **Average Centipawn Loss (ACPL)** using a simple monotone mapping to 0–100.
4. **Key Moments** pick the largest eval swings + any Mistake/Blunder/Missed Win/Missed Mate.
5. **Retry** lets you propose a move from a key position and compares its eval to the original.

---

## 🧪 Sample PGN

There’s a sample game preloaded in the app so you can test analysis immediately. Replace it with your own PGN when ready.

---

## ⚠️ Limitations / Notes

* Not CAPS2: **Accuracy** and **labels** are transparent approximations; they’ll feel similar but won’t match Chess.com exactly.
* Engine limits: Depth is governed by your **time per move**, **threads**, and CPU. For deep analysis, increase time/threads.
* Mate scores: Mating lines are represented internally as very large CP values for plotting.
* Single-game focus: The app analyzes one game per run; batch analysis is a future enhancement.

---

## 🧯 Troubleshooting

**“Stockfish not found.”**

* Run `stockfish -h` to confirm it’s on PATH.
* Set `STOCKFISH_PATH` (see above).
* On macOS with Homebrew, the path is often `/opt/homebrew/bin/stockfish` (Apple Silicon).
* On Windows, point to the full `.exe` path. If using backslashes in environment variables, PowerShell handles them fine.

**“Engine error” when retrying**

* Make sure the Stockfish path is valid and accessible.
* Try lowering MultiPV or using the **Quick** preset to reduce load.

**High CPU usage**

* Reduce threads and/or choose a lighter preset.
* MultiPV > 1 is costlier.

---

## 🔧 Configuration tips

* **Performance vs. quality**:

  * Quick ≈ 0.25s/move → very fast, surface-level tags
  * Balanced ≈ 0.6s/move → good for casual review
  * Deep ≈ 1.5s/move → better but slower
* **MultiPV**: Shows alternative engine lines; use with care on low-power machines.
* **Threads**: Start with a modest number (e.g., 4). More isn’t always faster if it causes thermal throttling.

---

## 🗺️ Roadmap (nice-to-haves)

* Opening names (ECO) and personal opening stats
* Audio text-to-speech for the coach
* Endgame tablebase lookups
* Batch analysis and export (PDF/CSV)
* Finer-grained tags (e.g., “Great”, “Book”, “Best Only Move”)

---

## 🤝 Acknowledgements

* **Stockfish** (GPLv3) — the engine doing the heavy lifting
* **python-chess** — parsing, board logic, and engine integration
* **Streamlit** — the app framework
* **Plotly** — charts

---

## 📄 License

MIT — do whatever you’d like; attribution appreciated. 