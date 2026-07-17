"""
The conversational coach.

Answers free-form questions like a human instructor. Two modes:

1. LLM mode (best): if the ANTHROPIC_API_KEY environment variable is set,
   questions go to the Claude API together with a grounding package —
   the position, the engine's top moves with evaluations, hanging pieces,
   and the user's level — so answers are accurate AND friendly.

2. Offline mode: a rule-based tutor that answers the most common beginner
   questions ("why?", "what should I do?", "what's threatened?") directly
   from board analysis. No internet or key needed.

All calls run on a background thread so the UI never freezes.
"""

import os, json, chess, threading, urllib.request
from coach import hanging_pieces, PIECE_NAMES

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"


SYSTEM_PROMPT = """You are a warm, patient chess coach inside a desktop app,
teaching a complete beginner. Rules:
- Answer in 2-4 short sentences. Plain language only.
- If you use a chess term, define it in a few words the first time.
- Ground every claim in the ANALYSIS block you are given. Never suggest a
  move that is not listed there. Refer to squares by name (e4, f6).
- Be encouraging but honest. End with a short question or nudge that makes
  the student think, when natural.
- The student plays White.
"""



def top_moves(engine, board, n=3):
    """[(move, san, eval_after_cp), ...] best-first, from White's view."""
    results = []
    if engine.sf:
        try:
            import chess.engine as ce
            infos = engine.sf.analyse(board, ce.Limit(time=0.5), multipv=n)
            if isinstance(infos, dict):
                infos = [infos]
            for info in infos:
                pv = info.get("pv")
                if not pv:
                    continue
                move = pv[0]
                score = info["score"].white().score(mate_score=100000)
                results.append((move, board.san(move), score))
            if results:
                return results
        except Exception:
            pass
        
    # fallback: score each legal move with the built-in evaluator
    scored = []
    for move in board.legal_moves:
        board.push(move)
        scored.append((engine.evaluate(board), move))
        board.pop()
    scored.sort(key=lambda t: t[0], reverse=board.turn == chess.WHITE)
    return [(m, board.san(m), s) for s, m in scored[:n]]


def build_analysis(board, engine, last_move_san):
    tops = top_moves(engine, board, 3)
    ev = engine.evaluate(board)
    hang_w = hanging_pieces(board, chess.WHITE)
    hang_b = hanging_pieces(board, chess.BLACK)

    def name_at(sq):
        p = board.piece_at(sq)
        return f"{PIECE_NAMES[p.piece_type]} on {chess.square_name(sq)}"

    lines = [
        f"FEN: {board.fen()}",
        f"Side to move: {'White (the student)' if board.turn else 'Black (opponent)'}",
        f"Evaluation: {ev/100:+.1f} pawns for White" if ev is not None else "",
        f"Last move played: {last_move_san or 'none'}",
        "Engine's best moves for the side to move: " + "; ".join(f"{san} (eval {s/100:+.1f})" for _, san, s in tops),
    ]

    if hang_w:
        lines.append("White pieces that can be captured for free: " + ", ".join(name_at(s) for s in hang_w))
    if hang_b:
        lines.append("Black pieces that can be captured for free: " + ", ".join(name_at(s) for s in hang_b))
    if board.is_check():
        lines.append("The side to move is in check.")
    return "\n".join(l for l in lines if l), tops



class Tutor:
    def __init__(self, engine):
        self.engine = engine
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        self.busy = False

    @property
    def llm_available(self):
        return bool(self.api_key)

    def ask_async(self, question, board, last_move_san, history, callback, level=1):
        """Answer on a background thread; callback(text) on completion."""
        if self.busy:
            return False
        self.busy = True
        board_copy = board.copy()

        def work():
            try:
                analysis, tops = build_analysis(board_copy, self.engine, last_move_san)

                names = {
                    1: "complete beginner — define every term, keep it very simple",
                    2: "developing — use basic terms freely, guide with questions before giving answers",
                    3: "improving — be concise, talk plans and ideas, only explain advanced terms"
                }

                analysis += f"\nStudent level: {names.get(level, names[1])}"
                if self.llm_available:
                    text = self._ask_llm(question, analysis, history)
                    if text is None:
                        text = self._ask_offline(question, board_copy, tops)
                else:
                    text = self._ask_offline(question, board_copy, tops)

            except Exception:
                text = ("Sorry, I hit a snag answering that. Try asking again in a moment.")

            finally:
                self.busy = False
            callback(text)

        threading.Thread(target=work, daemon=True).start()
        return True


    def _ask_llm(self, question, analysis, history):
        messages = []
        for role, text in history[-6:]:  # short memory keeps it focused
            messages.append({"role": "user" if role == "user" else "assistant", "content": text})

        messages.append({
            "role": "user",
            "content": f"ANALYSIS (ground truth, trust this):\n{analysis}\n\n" f"Student's question: {question}"
        })
        
        payload = json.dumps({
            "model": MODEL,
            "max_tokens": 300,
            "system": SYSTEM_PROMPT,
            "messages": messages,
        }).encode()

        req = urllib.request.Request(API_URL, data=payload, headers={
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        })

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())
            parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
            text = " ".join(parts).strip()
            return text or None
        except Exception:
            return None


    def _ask_offline(self, question, board, tops):
        q = question.lower()
        best = tops[0] if tops else None

        def suggest():
            if not best:
                return "Look for a safe move that improves a piece."
            
            move, san, _ = best
            piece = board.piece_at(move.from_square)
            name = PIECE_NAMES[piece.piece_type] if piece else "piece"
            return (
                f"A strong idea here is {san} — moving your {name} from "
                f"{chess.square_name(move.from_square)} to "
                f"{chess.square_name(move.to_square)}."
            )

        if any(w in q for w in ("threat", "attack", "danger", "safe")):
            hang = hanging_pieces(board, chess.WHITE)
            if hang:
                s = hang[0]
                p = board.piece_at(s)
                return (
                    f"Right now your {PIECE_NAMES[p.piece_type]} on "
                    f"{chess.square_name(s)} can be captured for free — "
                    "nothing defends it. Move it, defend it, or find "
                    "something even better. Use 'Show threats' to see "
                    "every attacked piece in red."
                )
            
            return (
                "Nothing of yours can be taken for free right now. "
                "Still, before every move, ask: 'if I do this, what can "
                "they capture?' That habit alone wins many games."
            )

        if any(w in q for w in ("why", "reason", "explain")):
            if best:
                move, san, _ = best
                temp = board.copy()
                cap = temp.piece_at(move.to_square)
                temp.push(move)
                if cap:
                    why = f"it wins their {PIECE_NAMES[cap.piece_type]}"
                elif temp.is_check():
                    why = "it attacks their king, forcing them to react"
                elif move.to_square in (chess.D4, chess.E4, chess.D5, chess.E5):
                    why = ("it fights for the center — pieces control more "
                           "squares from there")
                else:
                    why = ("it improves the position: it develops a piece or creates a threat")
                return f"The engine likes {san} because {why}. {suggest()}"
            
            return "Ask me right after a move and I'll explain the idea behind it."

        if any(w in q for w in ("plan", "strategy", "goal", "idea", "think")):
            return (
                "A simple beginner plan in almost any position: 1) make "
                "sure none of your pieces can be taken for free, 2) get "
                "your knights and bishops off the back row, 3) castle to "
                "tuck your king safely in the corner. " + suggest()
            )

        if any(w in q for w in ("what should", "best move", "hint", "move should", "what do i", "next move", "suggest")):
            return suggest() + (" Before playing it, ask yourself what it attacks and what it leaves behind.")

        if any(w in q for w in ("castle", "castling")):
            return (
                "Castling is a special move where your king slides two "
                "squares toward a rook and the rook hops over it. It "
                "tucks your king into safety — usually a great idea in "
                "the first 10 moves, once the pieces between them have "
                "moved out of the way."
            )

        return (
            "Good question! I can help best with things like 'what "
            "should I do?', 'why is that the best move?', 'what is "
            "threatened?', or 'what's my plan?'. "
            "(Tip: set an ANTHROPIC_API_KEY to unlock the full "
            "conversational coach that can answer anything.) " + suggest()
        )
