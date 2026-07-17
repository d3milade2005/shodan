"""
Opponent + analysis brain.

Uses Stockfish when it's installed (for a strong opponent and real
evaluations). If it isn't, falls back to a small built-in minimax AI so
the app runs out of the box with zero setup. The rest of the app never
needs to know which one is active.
"""

import chess, shutil, random
import chess.engine

PIECE_VALUES = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0,
}

# Small centralization bonus so the fallback AI plays sensible chess.
CENTER = {chess.D4, chess.E4, chess.D5, chess.E5}
NEAR_CENTER = {
    chess.C3, chess.D3, chess.E3, chess.F3,
    chess.C6, chess.D6, chess.E6, chess.F6,
    chess.C4, chess.F4, chess.C5, chess.F5
}


def _find_stockfish():
    for name in ("stockfish", "stockfish.exe"):
        path = shutil.which(name)
        if path:
            return path
    return None


class Engine:
    def __init__(self):
        self.sf = None
        path = _find_stockfish()
        if path:
            try:
                self.sf = chess.engine.SimpleEngine.popen_uci(path)
            except Exception:
                self.sf = None
        self.skill = 4  # default difficulty knob

    @property
    def using_stockfish(self):
        return self.sf is not None

    def set_difficulty(self, level):
        """level: 1..20-ish knob from config.DIFFICULTIES"""
        self.skill = level
        if self.sf:
            try:
                self.sf.configure({"Skill Level": min(level, 20)})
            except Exception:
                pass

    def best_move(self, board: chess.Board):
        """Opponent's move at current difficulty."""
        if self.sf:
            limit = chess.engine.Limit(time=0.15 + self.skill * 0.02)
            return self.sf.play(board, limit).move
        return self._fallback_move(board)

    def hint_move(self, board: chess.Board):
        """Best move for the user, always at full strength."""
        if self.sf:
            return self.sf.play(board, chess.engine.Limit(time=0.4)).move
        return self._minimax_root(board, depth=3)


    def evaluate(self, board: chess.Board):
        """Centipawns from White's point of view."""
        if board.is_checkmate():
            return -100000 if board.turn == chess.WHITE else 100000
        if self.sf:
            info = self.sf.analyse(board, chess.engine.Limit(time=0.12))
            return info["score"].white().score(mate_score=100000)
        return self._minimax(board, 2, -10**9, 10**9)


    def _material_eval(self, board):
        score = 0
        for sq, piece in board.piece_map().items():
            val = PIECE_VALUES[piece.piece_type]
            if piece.piece_type != chess.KING:
                if sq in CENTER:
                    val += 18
                elif sq in NEAR_CENTER:
                    val += 8
            score += val if piece.color == chess.WHITE else -val
        return score

    def _fallback_move(self, board):
        if self.skill <= 1:
            if random.random() < 0.5:
                return random.choice(list(board.legal_moves))
            return self._minimax_root(board, depth=1)
        if self.skill <= 4:
            return self._minimax_root(board, depth=2)
        return self._minimax_root(board, depth=3)

    def _minimax_root(self, board, depth):
        maximizing = board.turn == chess.WHITE
        best, best_score = None, None
        moves = list(board.legal_moves)
        random.shuffle(moves)
        for move in moves:
            board.push(move)
            score = self._minimax(board, depth - 1, -10**9, 10**9)
            board.pop()
            if best is None or (maximizing and score > best_score) \
                    or (not maximizing and score < best_score):
                best, best_score = move, score
        return best

    def _minimax(self, board, depth, alpha, beta):
        if depth == 0 or board.is_game_over():
            return self._material_eval(board) if not board.is_checkmate() \
                else (-100000 if board.turn == chess.WHITE else 100000)
        if board.turn == chess.WHITE:
            value = -10**9
            for move in board.legal_moves:
                board.push(move)
                value = max(value, self._minimax(board, depth - 1, alpha, beta))
                board.pop()
                alpha = max(alpha, value)
                if beta <= alpha:
                    break
            return value
        value = 10**9
        for move in board.legal_moves:
            board.push(move)
            value = min(value, self._minimax(board, depth - 1, alpha, beta))
            board.pop()
            beta = min(beta, value)
            if beta <= alpha:
                break
        return value

    def close(self):
        if self.sf:
            try:
                self.sf.quit()
            except Exception:
                pass
