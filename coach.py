"""
Phase-1 coach: turns board events into short, friendly, jargon-free
messages. (Phase 2 replaces the wording layer with an LLM; the event
detection here stays the same.)
"""

import chess

PIECE_NAMES = {
    chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop",
    chess.ROOK: "rook", chess.QUEEN: "queen", chess.KING: "king",
}


def _sq(square):
    return chess.square_name(square)


def hanging_pieces(board: chess.Board, color):
    """Squares of `color` pieces that are attacked and not defended."""
    out = []
    for sq, piece in board.piece_map().items():
        if piece.color != color or piece.piece_type == chess.KING:
            continue
        if board.is_attacked_by(not color, sq) and not board.is_attacked_by(color, sq):
            out.append(sq)
    return out


def attacked_squares(board: chess.Board, color):
    """All squares of `color` pieces currently attacked by the opponent."""
    out = []
    for sq, piece in board.piece_map().items():
        if piece.color == color and board.is_attacked_by(not color, sq):
            out.append(sq)
    return out


class Coach:
    """Watches the game and produces one clear message at a time."""

    def __init__(self):
        self.message = (
            "Welcome to Shodan — in martial arts, the "
            "rank of first black belt. Let's earn yours. "
            "You're playing the white pieces. "
            "Click a piece to see everywhere it can go, "
            "then click a green dot to move it."
            )


    def on_user_move(self, board, move, eval_before, eval_after, captured, level=1):
        msgs = []
        important = False
        if captured:
            msgs.append(f"Nice — you captured their {PIECE_NAMES[captured]}!")
            important = True

        if board.is_checkmate():
            self.message = "Checkmate — you won! Their king is attacked and has no escape."
            return
        
        if board.is_stalemate():
            self.message = (
                "Stalemate — the game is a draw! They have no "
                "legal moves but aren't in check. When you're "
                "winning big, always leave the enemy king "
                "somewhere to go."
            )
            return
        
        if board.is_game_over():
            self.message = ("The game ends in a draw. Nobody wins, nobody loses — press New game for another round!")
            return
        
        if board.is_check():
            msgs.append("You're giving check: their king is under attack and they must deal with it right now.")

        # Eval drop = mistake (from White's perspective, user is White)
        if eval_before is not None and eval_after is not None:
            drop = eval_before - eval_after
            if drop >= 250:
                msgs.append("Careful — that move gave a lot away. Use 'Take back' and look for what you missed.")
                important = True
            elif drop >= 120:
                msgs.append("Hmm, there was a better option there. Try the Hint button to compare ideas.")
                important = True

        hang = hanging_pieces(board, chess.WHITE)
        if hang:
            names = ", ".join(
                f"{PIECE_NAMES[board.piece_at(s).piece_type]} on {_sq(s)}"
                for s in hang[:2]
            )
            msgs.append(f"Watch out: your {names} can be captured for free — nothing is defending it.")
            important = True

        if board.is_check():
            important = True

        # at higher levels the coach goes quiet on routine moves
        if level >= 3 and not important:
            self.message = None
            return
        if not msgs:
            msgs.append("Good. Now think about your opponent's reply: what is their best move against you?")
        self.message = " ".join(msgs)


    def on_ai_move(self, board, move, captured, level=1):
        piece = board.piece_at(move.to_square)
        name = PIECE_NAMES[piece.piece_type] if piece else "piece"
        msgs = [f"They moved their {name} to {_sq(move.to_square)}."]
        important = bool(captured)
        if captured:
            msgs.append(f"It captured your {PIECE_NAMES[captured]}.")

        if board.is_checkmate():
            self.message = ("Checkmate — they won this one. Every loss teaches something: start a new game and try again!")
            return
        
        if board.is_stalemate():
            self.message = (
                "Stalemate — a draw. You had no legal moves but "
                "weren't in check. Sometimes that's a great "
                "escape when you're losing!"
            )
            return
        
        if board.is_game_over():
            self.message = ("The game ends in a draw — press New game to play another.")
            return
        
        if board.is_check():
            msgs.append("Your king is in check — you must respond to the attack before doing anything else.")
        else:
            hang = hanging_pieces(board, chess.WHITE)
            if hang:
                s = hang[0]
                msgs.append(
                    f"It's threatening your "
                    f"{PIECE_NAMES[board.piece_at(s).piece_type]} on {_sq(s)}. "
                    "Defend it, move it, or find something better."
                )
                important = True

        if board.is_check():
            important = True
        if level >= 3 and not important:
            self.message = None
            return
        self.message = " ".join(msgs)


    def on_hint(self, board, move):
        piece = board.piece_at(move.from_square)
        name = PIECE_NAMES[piece.piece_type] if piece else "piece"
        reason = "it improves your position"
        temp = board.copy()
        captured = temp.piece_at(move.to_square)
        temp.push(move)
        if captured:
            reason = f"it wins their {PIECE_NAMES[captured.piece_type]}"
        elif temp.is_check():
            reason = "it attacks their king"
        elif move.to_square in (chess.D4, chess.E4, chess.D5, chess.E5):
            reason = "it fights for the center, where pieces are strongest"
        self.message = (
            f"Try moving your {name} from {_sq(move.from_square)} "
            f"to {_sq(move.to_square)} (green arrow) — {reason}."
        )


    def on_threats_toggle(self, on):
        if on:
            self.message = (
                "Red squares show every piece of yours that is "
                "currently attacked. Attacked isn't always bad — "
                "check if the piece is defended."
            )
        else:
            self.message = "Threat view off. Toggle it any time you feel unsure."
