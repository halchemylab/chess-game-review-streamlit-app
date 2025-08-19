import os
import io
import math
import platform
import textwrap
from typing import List, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import chess
import chess.pgn
import chess.svg
import chess.engine
from html import escape as html_escape

# ----------------------------
# Page setup
# ----------------------------
st.set_page_config(
    page_title="PGN Review (Chess.com-style) – Streamlit",
    layout="wide",
    page_icon="♟️",
)

# Small CSS to make it a bit sleeker
st.markdown("""
<style>
/* Tighten things up a bit, nicer tables, nicer sidebar spacing */
.reportview-container .main .block-container{padding-top:1rem;padding-bottom:2rem;}
.sidebar .sidebar-content {padding-top: 1rem;}
div[data-testid="stMetricValue"] { font-size: 1.8rem; }
.tag { display:inline-block; padding:2px 8px; border-radius:12px; font-size:0.85rem; margin-right:4px; }
.tag-best { background:#e1f7e7; color:#116530; border:1px solid #9fe3b2; }
.tag-excellent { background:#e5f0ff; color:#203a93; border:1px solid #9fb5ff; }
.tag-good { background:#f2f7ff; color:#1d4ed8; border:1px solid #bfdbfe; }
.tag-inaccuracy { background:#fff7e6; color:#92400e; border:1px solid #fed7aa; }
.tag-mistake { background:#ffefe6; color:#9a3412; border:1px solid #fdba74; }
.tag-blunder { background:#ffe4e6; color:#9f1239; border:1px solid #fda4af; }
.tag-brilliant { background:#f3e8ff; color:#6b21a8; border:1px solid #d8b4fe; }
.tag-missed { background:#fef3c7; color:#7c2d12; border:1px solid #fde68a; }
.small { opacity:0.8; font-size:0.9rem; }
.coach-bubble { background:#f6f7f9; border:1px solid #e6e7eb; border-radius:12px; padding:10px 12px; }
hr { border: none; border-top: 1px solid #eee; margin: 0.8rem 0; }
</style>
""", unsafe_allow_html=True)

# ----------------------------
# Helpers
# ----------------------------

def find_stockfish_binary() -> Optional[str]:
    """Try to find a usable Stockfish binary path."""
    # 1) Explicit env var (recommended)
    env_path = os.environ.get("STOCKFISH_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 2) PATH
    import shutil
    for name in ["stockfish", "stockfish.exe"]:
        p = shutil.which(name)
        if p:
            return p

    # 3) Streamlit secrets (if user added)
    try:
        secrets_path = st.secrets.get("stockfish_path")
        if secrets_path and os.path.isfile(secrets_path):
            return secrets_path
    except Exception:
        pass

    return None


def score_to_cp_white(score: chess.engine.PovScore) -> Optional[int]:
    """Convert a PovScore to a centipawn integer from White's perspective (mate -> huge)."""
    if score.is_mate():
        # Represent mate scores as very large +/- values.
        # positive -> mate for White; negative -> mate for Black
        sign = 1 if score.white().mate() and score.white().mate() > 0 else -1
        return sign * 100000
    return score.white().score()


def clamp_eval(cp: Optional[int], cap: int = 1000) -> Optional[int]:
    if cp is None:
        return None
    return max(-cap, min(cap, cp))


def material_count(board: chess.Board) -> int:
    """Rough material count (White minus Black in centipawns)."""
    vals = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
    }
    score = 0
    for piece_type, v in vals.items():
        score += v * (len(board.pieces(piece_type, chess.WHITE)) - len(board.pieces(piece_type, chess.BLACK)))
    return score


def classify_move(cp_loss: int, swing: int, before_cp: int, after_cp: int, mover_is_white: bool, sacrificed: bool, had_mate: bool, lost_mate: bool) -> str:
    """
    Simple, transparent tagger inspired by Chess.com categories.
    """
    # Special cases first
    if had_mate and lost_mate:
        return "Missed Mate"
    if not had_mate and (before_cp > 200 if mover_is_white else before_cp < -200) and (after_cp <= 50 and mover_is_white or after_cp >= -50 and not mover_is_white):
        return "Missed Win"
    if sacrificed and cp_loss <= 20 and ((after_cp >= before_cp) if mover_is_white else (after_cp <= before_cp)):
        return "Brilliant"

    # Baseline by CP loss
    if cp_loss <= 10:
        return "Best"
    if cp_loss <= 35:
        return "Excellent"
    if cp_loss <= 80:
        return "Good"
    if cp_loss <= 150:
        return "Inaccuracy"
    if cp_loss <= 350:
        return "Mistake"
    return "Blunder"


def accuracy_from_acpl(acpl: float) -> float:
    """
    Map Average Centipawn Loss to a 0–100 'accuracy' that feels school-grade-like.
    0 acpl -> ~100, 200 acpl -> 50, 50 acpl -> ~80, etc.
    """
    return 100.0 * (1.0 - (acpl / (acpl + 200.0)))


def comment_for_move(tag: str, cp_loss: int, swing: int, best_uci: Optional[str], pv_san: str, board_before: chess.Board, played_move: chess.Move, avatar: str) -> str:
    move_san = board_before.san(played_move)
    phrases = {
        "Best": [
            f"{avatar}: Nailed it — {move_san} keeps the edge.",
            f"{avatar}: Perfect. {move_san} was the engine’s top choice.",
        ],
        "Excellent": [
            f"{avatar}: Strong move. {move_san} keeps the plan on track.",
        ],
        "Good": [
            f"{avatar}: {move_san} is fine. There might be a cleaner line, but nothing major.",
        ],
        "Inaccuracy": [
            f"{avatar}: Slight slip. After {move_san}, you give up {abs(swing)} cp of eval. Consider {pv_san.split(' ',1)[0] if pv_san else best_uci}.",
        ],
        "Mistake": [
            f"{avatar}: That hurts. {move_san} drops ≈{abs(swing)} cp. The idea {pv_san if pv_san else best_uci} would score much better.",
        ],
        "Blunder": [
            f"{avatar}: Big miss. {move_san} swings the eval by ≈{abs(swing)} cp. Try {pv_san if pv_san else best_uci}.",
        ],
        "Brilliant": [
            f"{avatar}: Beautiful! {move_san} is a resourceful shot that keeps or improves the eval.",
        ],
        "Missed Win": [
            f"{avatar}: The win slipped away here. {move_san} lets the eval flatten; engine preferred {pv_san if pv_san else best_uci}.",
        ],
        "Missed Mate": [
            f"{avatar}: Mate was available! Look for forcing checks first. Engine line: {pv_san if pv_san else best_uci}.",
        ],
    }
    options = phrases.get(tag, [f"{avatar}: {move_san}"])
    return options[0]


def board_to_svg(board: chess.Board, last_move: Optional[chess.Move] = None, arrows: Optional[List[chess.svg.Arrow]] = None) -> str:
    highlight = {}
    if last_move:
        highlight = {
            last_move.from_square: "#f6f68a",
            last_move.to_square: "#f6f68a",
        }
    return chess.svg.board(board, lastmove=last_move, squares=highlight, arrows=arrows, size=520)


def svg_html(svg_str: str, height: int = 560) -> str:
    # Render raw SVG via HTML
    return f'<div style="width:100%; display:flex; justify-content:center;"><div>{svg_str}</div></div>'


def to_san_line(board: chess.Board, moves: List[chess.Move], max_len: int = 8) -> str:
    temp = board.copy()
    sans = []
    for i, mv in enumerate(moves[:max_len]):
        sans.append(temp.san(mv))
        temp.push(mv)
    return " ".join(sans)


# ----------------------------
# Sidebar controls
# ----------------------------
st.sidebar.title("⚙️ Review Settings")

avatar_name = st.sidebar.selectbox(
    "Coach avatar",
    options=["🧠 Coach", "🐴 Knight", "🦦 Capybara", "🤖 Engine Buddy"],
    index=0
)

analysis_preset = st.sidebar.radio(
    "Analysis preset",
    options=["Quick (0.25s/move)", "Balanced (0.6s/move)", "Deep (1.5s/move)"],
    index=1
)
preset_to_time = {
    "Quick (0.25s/move)": 0.25,
    "Balanced (0.6s/move)": 0.60,
    "Deep (1.5s/move)": 1.50,
}
time_per_move = preset_to_time[analysis_preset]

multipv = st.sidebar.slider("Candidate lines (MultiPV)", min_value=1, max_value=3, value=1, help="More lines = slower")

threads = st.sidebar.slider("Engine Threads", 1, max(1, os.cpu_count() or 2), value=min(4, max(1, os.cpu_count() or 2)))

stockfish_hint = """\
I couldn't find Stockfish automatically.

Install it and restart this app:
• macOS:  `brew install stockfish`
• Ubuntu/Debian:  `sudo apt-get install stockfish`
• Windows: Download from the official Stockfish site, then set the full path below.

Alternatively, set an env var before launching:
STOCKFISH_PATH=/full/path/to/stockfish
"""

stockfish_path_manual = st.sidebar.text_input("Stockfish path (optional override)", value=os.environ.get("STOCKFISH_PATH", ""))

# ----------------------------
# Sample PGN
# ----------------------------
SAMPLE_PGN = """\
[Event "Sample"]
[Site "?"]
[Date "2023.10.01"]
[Round "-"]
[White "WhitePlayer"]
[Black "BlackPlayer"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. b4 Bxb4 5. c3 Ba5 6. d4 exd4
7. O-O d3 8. Qb3 Qf6 9. e5 Qg6 10. Re1 Nge7 11. Ba3 O-O 12. Nbd2
Bb6 13. Re4 Na5 14. Qb4 Nxc4 15. Qxc4 Qe6 16. Qxd3 Re8 17. Rae1
Ng6 18. h4 Qf5 19. h5 Qxh5 20. g4 Qh3 21. Ng5 Qxd3 22. R1e3 Qxd2
23. Rh3 Qxf2+ 24. Kh1 Qg1# 0-1
"""

st.title("♟️ PGN Game Review (Streamlit)")

st.markdown(
    "Paste a PGN below and click **Analyze Game**. "
    "You’ll get an eval graph, per-move tags, a board scrubber, key moments with a Retry mode, and coach comments."
)

pgn_text = st.text_area("PGN", value=SAMPLE_PGN, height=220)


# ----------------------------
# Parse PGN
# ----------------------------
def parse_first_game(pgn_str: str) -> Optional[chess.pgn.Game]:
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_str))
        return game
    except Exception:
        return None

game = parse_first_game(pgn_text)

if not game:
    st.error("Could not parse a game from that PGN. Double-check the text.")
    st.stop()

# Basic headers
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("White", game.headers.get("White", "White"))
col_b.metric("Black", game.headers.get("Black", "Black"))
col_c.metric("Result", game.headers.get("Result", "*"))
col_d.metric("Event", game.headers.get("Event", "-"))

# ----------------------------
# Engine prep
# ----------------------------
sf_path = stockfish_path_manual.strip() or find_stockfish_binary()
engine_ready = sf_path is not None and os.path.exists(sf_path)

if not engine_ready:
    st.warning(stockfish_hint)

@st.cache_data(show_spinner=False, persist=False)
def analyze_game(
    pgn_text: str,
    engine_path: str,
    time_per_move: float,
    multipv: int,
    threads: int
) -> Dict:
    """Run engine analysis over all plies. Returns a rich dict of results."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    board = game.board()

    # Collect moves
    mainline_moves = [m for m in game.mainline_moves()]
    positions_before = []   # FEN before each move
    moves_san = []
    moves_uci = []

    b = board.copy()
    for mv in mainline_moves:
        positions_before.append(b.fen())
        moves_san.append(b.san(mv))
        moves_uci.append(mv.uci())
        b.push(mv)

    # Start engine
    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    engine.configure({"Threads": threads})
    results = []
    evals_after_each_move_white_cp = []

    b = board.copy()
    prev_eval_white_cp = None

    for ply_idx, mv in enumerate(mainline_moves):
        # Analysis before the move (best line from current position)
        info_before = engine.analyse(
            b,
            chess.engine.Limit(time=time_per_move),
            multipv=multipv
        )
        # info_before can be list if multipv > 1
        infos = info_before if isinstance(info_before, list) else [info_before]
        top = infos[0]
        score_before_white_cp = score_to_cp_white(top["score"])
        had_mate = top["score"].is_mate()
        best_move = top.get("pv", [None])[0]
        best_move_uci = best_move.uci() if isinstance(best_move, chess.Move) else None
        pv_moves = top.get("pv", [])
        pv_san = to_san_line(b, pv_moves, max_len=8)

        # We will also collect candidate lines if multipv > 1
        cand_lines = []
        if multipv > 1:
            for k, inf in enumerate(infos[:multipv]):
                pvk = inf.get("pv", [])
                cand_lines.append({
                    "rank": k+1,
                    "pv_san": to_san_line(b, pvk, max_len=8),
                    "score_white_cp": clamp_eval(score_to_cp_white(inf["score"]))
                })

        # Actual move
        material_before = material_count(b)
        mover_is_white = b.turn == chess.WHITE
        b.push(mv)  # play the actual move

        # Evaluation after actual move
        info_after = engine.analyse(
            b,
            chess.engine.Limit(time=time_per_move)
        )
        score_after_white_cp = score_to_cp_white(info_after["score"])
        is_mate_after = info_after["score"].is_mate()

        # Compute CP Loss for the mover
        # From White's POV; adjust for side to move:
        # For White's move: loss = best - after; For Black's move: loss = (after - best)
        cp_loss = 0
        if score_before_white_cp is not None and score_after_white_cp is not None:
            if mover_is_white:
                cp_loss = max(0, (score_before_white_cp - score_after_white_cp))
            else:
                cp_loss = max(0, (score_after_white_cp - score_before_white_cp))

        # Eval swing (White POV), between before and after
        swing = 0
        if score_before_white_cp is not None and score_after_white_cp is not None:
            swing = score_after_white_cp - score_before_white_cp

        # Sacrifice heuristic: immediate material drop for mover
        material_after = material_count(b)
        sacrificed = (material_after - material_before < -120) if mover_is_white else (material_after - material_before > 120)

        # Did we have a mate before, but now not (or worse)? -> "lost_mate"
        lost_mate = False
        if had_mate and not is_mate_after:
            lost_mate = True

        tag = classify_move(
            cp_loss=cp_loss,
            swing=swing,
            before_cp=score_before_white_cp or 0,
            after_cp=score_after_white_cp or 0,
            mover_is_white=mover_is_white,
            sacrificed=sacrificed,
            had_mate=had_mate,
            lost_mate=lost_mate
        )

        comment = comment_for_move(
            tag=tag,
            cp_loss=cp_loss,
            swing=swing,
            best_uci=best_move_uci,
            pv_san=pv_san,
            board_before=chess.Board(positions_before[ply_idx]),
            played_move=mv,
            avatar=avatar_name.split(" ")[0]
        )

        evals_after_each_move_white_cp.append(clamp_eval(score_after_white_cp))
        results.append({
            "ply": ply_idx + 1,
            "move_san": moves_san[ply_idx],
            "move_uci": moves_uci[ply_idx],
            "turn": "White" if mover_is_white else "Black",
            "score_before_white_cp": clamp_eval(score_before_white_cp),
            "score_after_white_cp": clamp_eval(score_after_white_cp),
            "cp_loss": cp_loss,
            "swing": swing,
            "tag": tag,
            "best_move_uci": best_move_uci,
            "pv_san": pv_san,
            "candidates": cand_lines,
            "fen_before": positions_before[ply_idx],
        })

    engine.quit()

    # Aggregate player stats
    df = pd.DataFrame(results)
    white_rows = df[df["turn"] == "White"]
    black_rows = df[df["turn"] == "Black"]

    white_acpl = float(white_rows["cp_loss"].mean()) if not white_rows.empty else 0.0
    black_acpl = float(black_rows["cp_loss"].mean()) if not black_rows.empty else 0.0

    white_acc = accuracy_from_acpl(white_acpl)
    black_acc = accuracy_from_acpl(black_acpl)

    # Key moments: top 5 absolute swings + anything tagged Mistake/Blunder
    df["abs_swing"] = df["swing"].abs()
    key_by_swing = df.sort_values("abs_swing", ascending=False).head(5)
    key_by_tag = df[df["tag"].isin(["Mistake", "Blunder", "Missed Win", "Missed Mate"])]
    key_moments = pd.concat([key_by_swing, key_by_tag]).drop_duplicates(subset=["ply"]).sort_values("ply")

    return {
        "df": df,
        "evals_after_each_move_white_cp": evals_after_each_move_white_cp,
        "white_acpl": white_acpl,
        "black_acpl": black_acpl,
        "white_acc": white_acc,
        "black_acc": black_acc,
        "key_moments": key_moments,
        "moves_san": moves_san,
        "positions_before": positions_before,
    }


# ----------------------------
# Analyze button
# ----------------------------
analyze_btn = st.button("🔍 Analyze Game", type="primary", disabled=not engine_ready)

if not analyze_btn and "analysis" not in st.session_state:
    st.info("Tip: Make sure Stockfish is installed and detected. Then click **Analyze Game**.")
    st.stop()

if analyze_btn:
    if not engine_ready:
        st.stop()
    with st.spinner("Analyzing with Stockfish…"):
        analysis = analyze_game(
            pgn_text=pgn_text,
            engine_path=sf_path,
            time_per_move=time_per_move,
            multipv=multipv,
            threads=threads
        )
        st.session_state["analysis"] = analysis

analysis = st.session_state.get("analysis")
if not analysis:
    st.stop()

df = analysis["df"]
positions_before = analysis["positions_before"]
moves_san = analysis["moves_san"]

# ----------------------------
# Top summary row (like Chess.com "Highlights")
# ----------------------------
c1, c2, c3, c4 = st.columns([1,1,1,2])

c1.metric("White Accuracy", f"{analysis['white_acc']:.1f}")
c2.metric("Black Accuracy", f"{analysis['black_acc']:.1f}")
c3.metric("Avg CPL (W/B)", f"{analysis['white_acpl']:.0f} / {analysis['black_acpl']:.0f}")

# Quick coach summary
w_acc, b_acc = analysis['white_acc'], analysis['black_acc']
if w_acc > b_acc + 5:
    summary = "White played more accurately overall."
elif b_acc > w_acc + 5:
    summary = "Black played more accurately overall."
else:
    summary = "Accuracy was fairly balanced."

c4.markdown(f"""
<div class="coach-bubble">
<b>{avatar_name.split(' ')[0]}:</b> {summary} Peak swings happened around key mistakes/blunders — check the <i>Key Moments</i> tab below.
</div>
""", unsafe_allow_html=True)

# ----------------------------
# Tabs UI
# ----------------------------
tab_review, tab_moments, tab_moves, tab_settings = st.tabs(["📈 Review", "⚡ Key Moments / Retry", "📜 Moves", "🔧 Settings"])

with tab_review:
    left, right = st.columns([1,1])

    # Eval graph
    with left:
        evals = analysis["evals_after_each_move_white_cp"]
        x = list(range(1, len(evals) + 1))
        fig = px.line(
            x=x, y=evals,
            labels={"x": "Ply", "y": "Evaluation (cp, White POV)"},
            title="Evaluation After Each Move"
        )
        # Add 0 line
        fig.add_hline(y=0, line_dash="dash")
        st.plotly_chart(fig, use_container_width=True)

    # Board + scrubber + coach
    with right:
        max_ply = len(moves_san)
        ply = st.slider("Scrub through the game", 1, max_ply, 1, key="ply_slider")
        fen = positions_before[ply-1]
        board = chess.Board(fen)
        last_move = chess.Move.from_uci(df.loc[df["ply"]==ply, "move_uci"].iloc[0])
        arrows = []
        best_uci = df.loc[df["ply"]==ply, "best_move_uci"].iloc[0]
        if best_uci:
            try:
                bm = chess.Move.from_uci(best_uci)
                arrows = [chess.svg.Arrow(bm.from_square, bm.to_square, color="#3b82f6")]
            except:
                arrows = []

        svg = board_to_svg(board, last_move=last_move, arrows=arrows if st.checkbox("Show best-move arrow", value=True) else None)
        st.components.v1.html(svg_html(svg), height=580)

        # Move tag + comment
        row = df[df["ply"] == ply].iloc[0]
        tag = row["tag"]
        tag_class = {
            "Best": "tag-best",
            "Excellent": "tag-excellent",
            "Good": "tag-good",
            "Inaccuracy": "tag-inaccuracy",
            "Mistake": "tag-mistake",
            "Blunder": "tag-blunder",
            "Brilliant": "tag-brilliant",
            "Missed Win": "tag-missed",
            "Missed Mate": "tag-missed",
        }.get(tag, "tag-good")

        st.markdown(
            f'<span class="tag {tag_class}">{html_escape(tag)}</span> '
            f'<span class="small">CP Loss: {int(row["cp_loss"])}, Swing: {int(row["swing"])} cp</span>',
            unsafe_allow_html=True
        )
        st.markdown(f'<div class="coach-bubble">{html_escape(row["pv_san"] and comment_for_move(tag, int(row["cp_loss"]), int(row["swing"]), row["best_move_uci"], row["pv_san"], chess.Board(fen), last_move, avatar_name.split(" ")[0]))}</div>', unsafe_allow_html=True)

with tab_moments:
    km = analysis["key_moments"]
    if km.empty:
        st.info("No big swings or critical mistakes detected.")
    else:
        st.dataframe(km[["ply", "turn", "move_san", "tag", "cp_loss", "swing", "pv_san"]].reset_index(drop=True))

        st.subheader("Retry a Key Position")
        idx = st.number_input("Choose a key moment by ply", min_value=int(km["ply"].min()), max_value=int(km["ply"].max()), value=int(km["ply"].iloc[0]))
        row = df[df["ply"] == idx].iloc[0]
        board_retry = chess.Board(row["fen_before"])
        svg_retry = board_to_svg(board_retry)
        st.components.v1.html(svg_html(svg_retry), height=580)

        st.write(f"Your move in the game was **{row['move_san']}** ({row['turn']} to move). Try a better move:")
        user_move_str = st.text_input("Enter a move (SAN or UCI), e.g. Nf3 or e2e4", key="retry_move")
        go = st.button("Check Move")
        if go and user_move_str.strip():
            # Parse move
            move_obj = None
            try:
                # Try SAN first
                move_obj = board_retry.parse_san(user_move_str.strip())
            except Exception:
                try:
                    move_obj = chess.Move.from_uci(user_move_str.strip())
                    if move_obj not in board_retry.legal_moves:
                        raise ValueError("Illegal UCI move")
                except Exception:
                    st.error("Couldn't parse that as a legal SAN/UCI move in this position.")
                    move_obj = None

            if move_obj:
                # Evaluate user's proposed move vs engine best
                try:
                    engine = chess.engine.SimpleEngine.popen_uci(sf_path)
                    engine.configure({"Threads": threads})

                    info_before = engine.analyse(board_retry, chess.engine.Limit(time=time_per_move))
                    sb = score_to_cp_white(info_before["score"])

                    board_retry.push(move_obj)
                    info_user = engine.analyse(board_retry, chess.engine.Limit(time=time_per_move))
                    su = score_to_cp_white(info_user["score"])

                    # Best line
                    board_retry.pop()
                    info_best = engine.analyse(board_retry, chess.engine.Limit(time=time_per_move))
                    pv = info_best.get("pv", [])
                    pv_san = to_san_line(board_retry, pv, max_len=6)

                    engine.quit()

                    if sb is not None and su is not None:
                        swing_user = su - sb
                        st.success(f"Engine says your try changes eval by {swing_user:+} cp (White POV).")
                        st.info(f"Engine suggestion: {pv_san or '(no PV)'}")
                except Exception as e:
                    st.error(f"Engine error: {e}")

with tab_moves:
    st.dataframe(df[["ply", "turn", "move_san", "tag", "cp_loss", "swing", "score_before_white_cp", "score_after_white_cp", "pv_san"]], use_container_width=True)

with tab_settings:
    st.markdown("### Engine Detection")
    if engine_ready:
        st.success(f"Found Stockfish at: `{sf_path}`")
    else:
        st.error("Stockfish not found.")
        st.code(stockfish_hint)

    st.markdown("### Notes")
    st.markdown(
        """
- **Accuracy** here is an approximation derived from Average Centipawn Loss, not Chess.com's CAPS2.
- Move tags are based on transparent CP thresholds and simple heuristics; they won’t exactly match Chess.com’s labels but feel similar.
- MultiPV > 1 shows extra candidate lines (slower).
- For “opening name” detection, consider adding an ECO book later (optional).
        """.strip()
    )
