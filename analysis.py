"""
Post-game analysis.

Replays a finished (or abandoned) game, evaluates every position, and
turns the numbers into a beginner-friendly report:

- each of the student's moves is classified: great / good / inaccuracy /
  mistake / blunder
- an estimated accuracy score (based on average centipawn loss)
- the game's turning points (largest evaluation swings)
- a plain-language explanation for every flagged move, including what
  the engine would have played instead

Runs on a background thread; reports progress so the UI can show it.
"""

import math, threading, chess
from coach import hanging_pieces, PIECE_NAMES

# classification thresholds in centipawns lost
T_BLUNDER = 250
T_MISTAKE = 120
T_INACCURACY = 50

LABELS = {
    "great": "Great move",
    "good": "Good",
    "inaccuracy": "Inaccuracy",
    "mistake": "Mistake",
    "blunder": "Blunder",
}


class MoveReport:
    def __init__(self, ply, move, san, is_user, 
        eval_before, 
        eval_after, best_san, loss, 
        tag, note, fen_before=None, best_uci=None
    ):
        self.ply = ply                # 1-based ply index
        self.move = move
        self.san = san
        self.is_user = is_user        # True = White (the student)
        self.eval_before = eval_before
        self.eval_after = eval_after
        self.best_san = best_san
        self.loss = loss
        self.tag = tag                # key into LABELS, or None for AI moves
        self.note = note
        self.fen_before = fen_before  # position the student faced
        self.best_uci = best_uci      # engine's move in that position


class GameReport:
    def __init__(self, moves, accuracy, turning_points, summary):
        self.moves = moves                    # list[MoveReport]
        self.accuracy = accuracy
        self.turning_points = turning_points  # list of ply indices
        self.summary = summary

    def user_flagged(self):
        return [m.ply for m in self.moves
            if m.is_user and m.tag in ("inaccuracy", "mistake", "blunder")
        ]
    


def _classify(loss, played_best):
    if played_best and loss <= 20:
        return "great"
    if loss < T_INACCURACY:
        return "good"
    if loss < T_MISTAKE:
        return "inaccuracy"
    if loss < T_BLUNDER:
        return "mistake"
    return "blunder"


def _note_for(board_after, move, tag, best_san, captured, loss):
    """Plain-language explanation, one idea at a time."""
    bits = []
    if captured:
        bits.append(f"You captured their {PIECE_NAMES[captured]}.")
    if tag == "great":
        bits.append("This was the engine's top choice — excellent.")
    elif tag == "good":
        bits.append("A solid move that keeps your position healthy.")
    else:
        hang = hanging_pieces(board_after, chess.WHITE)
        if hang:
            sq = hang[0]
            p = board_after.piece_at(sq)
            bits.append(
                f"After this, your {PIECE_NAMES[p.piece_type]} on "
                f"{chess.square_name(sq)} could be captured for "
                "free — nothing defends it."
            )
        elif loss >= T_BLUNDER:
            bits.append("This move gave away a winning amount of material or position.")
        else:
            bits.append("This let some of your advantage slip.")
        if best_san:
            bits.append(f"The engine preferred {best_san}. Set up this position and ask the coach why!")
    return " ".join(bits)


class Analyzer:
    def __init__(self, engine):
        self.engine = engine
        self.progress = (0, 0)   # (done, total)
        self.busy = False

    def analyze_async(self, moves, callback):
        """moves: list of chess.Move from the start position."""
        if self.busy or not moves:
            return False
        self.busy = True
        moves = list(moves)

        def work():
            try:
                report = self._analyze(moves)
            except Exception:
                report = None
            finally:
                self.busy = False
            callback(report)

        threading.Thread(target=work, daemon=True).start()
        return True

    def _best_move(self, board):
        try:
            best = self.engine.hint_move(board)
            return (board.san(best), best.uci()) if best else (None, None)
        except Exception:
            return None, None

    def _analyze(self, moves):
        board = chess.Board()
        total = len(moves)
        self.progress = (0, total)

        evals = [self.engine.evaluate(board)]
        reports = []
        user_losses = []

        for i, move in enumerate(moves):
            is_user = board.turn == chess.WHITE
            san = board.san(move)
            captured_piece = board.piece_at(move.to_square)
            captured = captured_piece.piece_type if captured_piece else None

            best_san = best_uci = None
            fen_before = board.fen()
            if is_user:
                best_san, best_uci = self._best_move(board)

            board.push(move)
            ev = self.engine.evaluate(board)
            evals.append(ev)
            self.progress = (i + 1, total)

            tag = note = None
            loss = 0
            if is_user:
                loss = max(0, (evals[-2] or 0) - (ev or 0))
                played_best = best_san == san
                tag = _classify(loss, played_best)
                user_losses.append(loss)
                note = _note_for(
                    board, move, tag,
                    None if played_best else best_san,
                    captured, loss
                )
            reports.append(
                MoveReport(
                    i + 1, move, san, is_user,
                    evals[-2], ev, best_san, loss,
                    tag, note, fen_before, best_uci
                )
            )

        # accuracy: gentle exponential on average centipawn loss
        acpl = sum(user_losses) / max(len(user_losses), 1)
        accuracy = round(min(99, 103 * math.exp(-0.005 * acpl)))

        # turning points: 3 biggest eval swings anywhere in the game
        swings = sorted(
            range(1, len(evals)),
            key=lambda i: abs((evals[i] or 0) - (evals[i-1] or 0)),
            reverse=True
        )
        turning = sorted(swings[:3])

        counts = {}
        for r in reports:
            if r.is_user and r.tag:
                counts[r.tag] = counts.get(r.tag, 0) + 1

        nice = counts.get("great", 0) + counts.get("good", 0)
        rough = (counts.get("inaccuracy", 0) + counts.get("mistake", 0) + counts.get("blunder", 0))

        if rough == 0:
            summary = (
                f"Estimated accuracy {accuracy}%. A clean game — "
                "every move kept your position healthy!"
            )
        else:
            summary = (
                f"Estimated accuracy {accuracy}%. {nice} solid moves, "
                f"{rough} to learn from. Use 'Next mistake' to jump "
                "straight to the learning moments."
            )
        return GameReport(reports, accuracy, turning, summary)
