"""
Shodan — a chess trainer that takes you from your first move
toward your black belt.
A spacious chess trainer for complete beginners, now with a
conversational coach: ask any question and get an answer grounded in
real engine analysis.

Run:  python main.py
Optional: install Stockfish (stronger opponent, real evaluations).
Optional: set ANTHROPIC_API_KEY to unlock the full LLM coach; without
it, a built-in rule-based tutor answers common questions offline.
"""

import sys, pygame, chess, queue
import config as C
from engine_ai import Engine
from coach import Coach, attacked_squares
from tutor_llm import Tutor
from analysis import Analyzer
import storage
from content import STARTER_PUZZLES, LESSONS

DEFAULT_CHIPS = [
    ("Why?", "Why is that the best move?"),
    ("Any threats?", "What is threatened right now?"),
    ("What's the plan?", "What should my plan be?")
]
RETRY_CHIPS = [
    ("Yes, take it back", "__takeback__"),
    ("No, keep going", "__keepgoing__")
]


class State:
    """Everything the UI needs to draw a frame."""

    def __init__(self):
        self.selected = None
        self.legal_targets = []
        self.last_move = None
        self.last_move_san = None
        self.hint_move = None
        self.show_threats = False
        self.threat_squares = []
        self.difficulty_idx = 0
        self.engine_label = ""
        self.status_text = "Your move — you play White."
        self.evaluation = 0
        # chat
        self.chat = []            # list of (role, text)
        self.chips = list(DEFAULT_CHIPS)
        self.input_text = ""
        self.input_focus = False
        self.chat_scroll = 0
        self.chat_max_scroll = 0
        self.coach_thinking = False
        self.dragging = False
        self.anim = None
        # review mode
        self.mode = "play"   # 'play' | 'review' | 'puzzle' | 'lessons'
        self.report = None
        self.review_ply = 0
        self.review_evals = []
        self.analyze_progress = (0, 0)
        # practice mode
        self.current_puzzle = None
        self.puzzle_counts = (0, 0, 0)
        self.puzzle_feedback = None
        self.puzzle_solved = False
        self.puzzle_first_try = True
        # lessons mode
        self.lesson = None
        self.exercise_idx = 0
        self.lesson_feedback = None
        self.exercise_solved = False
        self.puzzle_side = "White"
        self.skill = 1
        self.hint_stage = 0


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((C.WINDOW_W, C.WINDOW_H), pygame.RESIZABLE)
        pygame.display.set_caption("Shodan")
        self.clock = pygame.time.Clock()

        from ui import UI  # after pygame.init
        self.ui = UI(self.screen)

        self.board = chess.Board()
        self.engine = Engine()
        self.coach = Coach()
        self.tutor = Tutor(self.engine)
        self.analyzer = Analyzer(self.engine)
        self.state = State()
        self.answers = queue.Queue()
        self.reports = queue.Queue()
        self.review_board = chess.Board()
        self.puzzle_board = chess.Board()
        storage.seed_starters(STARTER_PUZZLES)
        C.set_theme(storage.get_setting("theme", "light"))
        self.state.skill = storage.skill_level()

        self.say(self.coach.message)
        if self.tutor.llm_available:
            self.say(
                "I'm your personal coach — ask me anything, any time. Try the quick buttons below, or type your own question."
            )
        else:
            self.say(
                "Ask me things like 'what should I do?' or 'any threats?' using the box below. (Set an "
                "ANTHROPIC_API_KEY to unlock my full conversational mode.)"
            )
            
        self.state.engine_label = (
            "Opponent: Stockfish engine" if self.engine.using_stockfish
            else "Opponent: built-in AI (install Stockfish for full strength)"
        )
        self.engine.set_difficulty(C.DIFFICULTIES[0][1])
        self.ai_pending = False
        self.ai_due_at = 0



    def say(self, text):
        self.state.chat.append(("coach", text))
        self.state.chat_scroll = 0  # snap to newest

    def user_says(self, text):
        self.state.chat.append(("user", text))
        self.state.chat_scroll = 0

    def ask_tutor(self, question):
        if self.state.coach_thinking:
            return
        self.user_says(question)
        self.state.coach_thinking = True
        ok = self.tutor.ask_async(
            question, self.board, self.state.last_move_san,
            self.state.chat[:-1], self.answers.put,
            level=self.state.skill)
        if not ok:
            self.state.coach_thinking = False


    def handle_click(self, pos):
        if self.state.mode == "review":
            for key, rect in self.ui.buttons.items():
                if rect.collidepoint(pos):
                    self.on_button(key)
                    return
            return
        
        if self.state.mode in ("puzzle", "lessons", "stats"):
            for key, rect in self.ui.buttons.items():
                if rect.collidepoint(pos):
                    self.on_button(key)
                    return
            if self.state.mode != "stats":
                self.practice_board_click(pos)
            return
        
        self.state.input_focus = (
            "input" in self.ui.buttons and
            self.ui.buttons["input"].collidepoint(pos)
        )
        
        for key, rect in self.ui.buttons.items():
            if rect.collidepoint(pos):
                self.on_button(key)
                return
            
        if self.ai_pending or self.board.is_game_over():
            return
        
        self.board_press(pos, self.board, self.user_move, chess.WHITE)

    def practice_board_click(self, pos):
        s = self.state
        if s.mode == "puzzle" and (not s.current_puzzle or s.puzzle_solved):
            return
        if s.mode == "lessons" and (s.lesson is None or s.exercise_solved):
            return
        
        board = self.puzzle_board
        attempt = (self.puzzle_attempt if s.mode == "puzzle" else self.lesson_attempt)
        self.board_press(pos, board, attempt, board.turn)



    def board_press(self, pos, board, on_move, color):
        """Mouse down on the board: complete click-click, or begin drag."""
        s = self.state
        sq = self.ui.square_at(pos)
        if sq is None:
            return
        
        for move in s.legal_targets:
            if move.to_square == sq:
                on_move(move)
                return
            
        piece = board.piece_at(sq)
        if piece and piece.color == color:
            s.selected = sq
            s.legal_targets = [m for m in board.legal_moves if m.from_square == sq]
            s.dragging = True
        else:
            s.selected, s.legal_targets = None, []


    def board_release(self, pos):
        """Mouse up: drop the dragged piece if over a legal square."""
        s = self.state
        if not s.dragging:
            return
        s.dragging = False
        sq = self.ui.square_at(pos)
        if sq is None or sq == s.selected:
            return  # keep selection: acts like a click
        
        for move in list(s.legal_targets):
            if move.to_square == sq:
                if s.mode == "play":
                    if not self.ai_pending and not self.board.is_game_over():
                        self.user_move(move)
                elif s.mode == "puzzle":
                    self.puzzle_attempt(move)
                elif s.mode == "lessons":
                    self.lesson_attempt(move)
                return
            
        s.selected, s.legal_targets = None, []


    def handle_key(self, event):
        if self.state.mode == "review":
            if event.key in (pygame.K_LEFT, pygame.K_UP):
                self.review_button("rev_prev")
            elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                self.review_button("rev_next")
            elif event.key == pygame.K_HOME:
                self.review_button("rev_start")
            elif event.key == pygame.K_END:
                self.review_button("rev_end")
            elif event.key == pygame.K_ESCAPE:
                self.review_button("rev_back")
            return
        
        if not self.state.input_focus:
            if event.key == pygame.K_ESCAPE:
                self.state.selected = None
                self.state.legal_targets = []
                self.state.dragging = False
            return
        
        if event.key == pygame.K_RETURN:
            self.submit_input()
        elif event.key == pygame.K_BACKSPACE:
            self.state.input_text = self.state.input_text[:-1]
        elif event.key == pygame.K_ESCAPE:
            self.state.input_focus = False


    def submit_input(self):
        text = self.state.input_text.strip()
        if text:
            self.state.input_text = ""
            self.ask_tutor(text)



    def start_review(self):
        if self.ai_pending:
            self.ai_move()  # let the opponent finish before we analyze
        if len(self.board.move_stack) < 2:
            self.say("Play a few moves first, then I can review the game with you!")
            return
        
        if self.analyzer.busy:
            return
        
        # same game, nothing new played? reuse the report instantly
        key = (len(self.board.move_stack), self.board.fen())
        if self.state.report and getattr(self, "report_key", None) == key:
            self.state.mode = "review"
            self.set_review_ply(0)
            return
        
        self.report_key = key
        self.state.mode = "review"
        self.state.report = None
        self.state.review_ply = 0
        self.review_board = chess.Board()
        self.puzzle_board = chess.Board()
        storage.seed_starters(STARTER_PUZZLES)
        C.set_theme(storage.get_setting("theme", "light"))
        self.state.skill = storage.skill_level()
        moves = list(self.board.move_stack)
        self.analyzer.analyze_async(moves, self.reports.put)

    def set_review_ply(self, ply):
        report = self.state.report
        if not report:
            return
        ply = max(0, min(ply, len(report.moves)))
        self.state.review_ply = ply
        self.review_board = chess.Board()
        self.puzzle_board = chess.Board()
        storage.seed_starters(STARTER_PUZZLES)
        C.set_theme(storage.get_setting("theme", "light"))
        self.state.skill = storage.skill_level()
        for mr in report.moves[:ply]:
            self.review_board.push(mr.move)

    def review_button(self, key):
        report = self.state.report
        if key == "rev_back":
            self.state.mode = "play"
            if report:
                self.say(report.summary + " Great work reviewing — that's how players improve fastest.")
            return
        
        if not report:
            return
        
        if key == "rev_start":
            self.set_review_ply(0)
        elif key == "rev_prev":
            self.set_review_ply(self.state.review_ply - 1)
        elif key == "rev_next":
            self.set_review_ply(self.state.review_ply + 1)
        elif key == "rev_end":
            self.set_review_ply(len(report.moves))
        elif key == "rev_mistake":
            flagged = report.user_flagged()
            nxt = [p for p in flagged if p > self.state.review_ply]
            self.set_review_ply(nxt[0] if nxt else (flagged[0] if flagged else 0))
        elif key == "graph":
            mx = pygame.mouse.get_pos()[0]
            rect = self.ui.buttons["graph"]
            frac = (mx - rect.x - 16) / max(rect.w - 32, 1)
            self.set_review_ply(round(frac * len(report.moves)))


    def open_practice(self):
        self.state.mode = "puzzle"
        self.state.selected = None
        self.state.legal_targets = []
        self.state.hint_move = None
        self.load_next_puzzle()


    def load_next_puzzle(self):
        s = self.state
        s.puzzle_counts = storage.counts()
        due = storage.due_puzzles()
        s.current_puzzle = due[0] if due else None
        s.puzzle_feedback = None
        s.puzzle_solved = False
        s.puzzle_first_try = True
        s.selected, s.legal_targets, s.hint_move, s.last_move = \
            None, [], None, None
        if s.current_puzzle:
            self.puzzle_board = chess.Board(s.current_puzzle["fen"])
            s.puzzle_side = ("White" if self.puzzle_board.turn else "Black")


    def puzzle_attempt(self, move):
        s = self.state
        p = s.current_puzzle
        if not p or s.puzzle_solved:
            return
        
        if move.uci() == p["solution"] or \
                move.uci()[:4] == p["solution"][:4]:
            days = storage.record_result(p["id"], s.puzzle_first_try)
            storage.log_puzzle_attempt(s.puzzle_first_try)
            self.puzzle_board.push(chess.Move.from_uci(p["solution"] if len(p["solution"]) > 4 else move.uci()))
            s.last_move = move
            s.puzzle_solved = True
            fb = p["note"] or "That's the move!"

            if s.puzzle_first_try:
                fb += (
                    f" Solved first try — this puzzle returns in "
                    f"{days} day{'s' if days != 1 else ''}."
                )
            else:
                fb += " You got there — it'll come back tomorrow to stick."

            s.puzzle_feedback = fb

        else:
            s.puzzle_first_try = False
            s.puzzle_feedback = (
                "Not quite — that's a legal move, but there's something stronger. Look for checks, captures, and threats first."
            )

        s.selected, s.legal_targets = None, []

    def puzzle_button(self, key):
        s = self.state
        if key == "pz_next":
            self.load_next_puzzle()
        elif key == "pz_skip":
            if s.current_puzzle:
                storage.record_result(s.current_puzzle["id"], False)
            self.load_next_puzzle()
        elif key == "pz_reveal" and s.current_puzzle:
            sol = chess.Move.from_uci(s.current_puzzle["solution"])
            s.hint_move = sol
            storage.record_result(s.current_puzzle["id"], False)
            storage.log_puzzle_attempt(False)
            self.puzzle_board.push(sol)
            s.anim = dict(start=pygame.time.get_ticks(), duration=260, **{"from": sol.from_square, "to": sol.to_square})
            s.last_move = sol
            s.puzzle_solved = True
            s.puzzle_feedback = (
                (s.current_puzzle["note"] or "") + " No worries — seeing the answer is learning too. It'll return tomorrow."
            )


    def open_lessons(self):
        s = self.state
        s.mode = "lessons"
        s.lesson = None
        s.selected, s.legal_targets, s.hint_move, s.last_move = \
            None, [], None, None

    def open_lesson(self, idx):
        s = self.state
        s.lesson = LESSONS[idx]
        done = storage.lesson_done_count(s.lesson["id"])
        n = len(s.lesson["exercises"])
        s.exercise_idx = 0 if done >= n else min(done, n - 1)
        self.load_exercise()


    def load_exercise(self):
        s = self.state
        ex = s.lesson["exercises"][s.exercise_idx]
        self.puzzle_board = chess.Board(ex["fen"])
        s.lesson_feedback = None
        s.exercise_solved = False
        s.selected, s.legal_targets, s.hint_move, s.last_move = \
            None, [], None, None


    def lesson_attempt(self, move):
        s = self.state
        ex = s.lesson["exercises"][s.exercise_idx]
        if s.exercise_solved:
            return
        if move.uci() == ex["solution"] or \
                move.uci()[:4] == ex["solution"][:4]:
            self.puzzle_board.push(move)
            s.last_move = move
            s.exercise_solved = True
            s.lesson_feedback = ex["success"]
            storage.complete_exercise(s.lesson["id"], s.exercise_idx)
        else:
            s.lesson_feedback = ("Not that one — re-read the task above and try again. You've got this!")
        s.selected, s.legal_targets = None, []


    def lesson_button(self, key):
        s = self.state
        if key == "lx_back":
            s.lesson = None
        elif key == "lx_reveal" and not s.exercise_solved:
            ex = s.lesson["exercises"][s.exercise_idx]
            sol = chess.Move.from_uci(ex["solution"])
            s.hint_move = sol
            self.puzzle_board.push(sol)
            s.last_move = sol
            s.exercise_solved = True
            s.lesson_feedback = (ex["success"] + " (Shown for you this time — it still counts!)")
            storage.complete_exercise(s.lesson["id"], s.exercise_idx)
        elif key == "lx_next":
            if s.exercise_idx < len(s.lesson["exercises"]) - 1:
                s.exercise_idx += 1
                self.load_exercise()
            else:
                s.lesson = None


    def switch_tab(self, key):
        if key == "tab_play":
            self.state.mode = "play"
            s = self.state
            s.selected, s.legal_targets, s.hint_move = None, [], None
            s.last_move = (self.board.peek() if self.board.move_stack else None)
            self.refresh_threats()
        elif key == "tab_puzzle":
            self.open_practice()
        elif key == "tab_lessons":
            self.open_lessons()
        elif key == "tab_stats":
            self.state.mode = "stats"
            self.state.skill = storage.skill_level()


    def on_button(self, key):
        if key == "theme":
            C.set_theme("dark" if C.THEME == "light" else "light")
            storage.set_setting("theme", C.THEME)
            return
        if key.startswith("tab_"):
            self.switch_tab(key)
            return
        if self.state.mode == "puzzle":
            self.puzzle_button(key)
            return
        if self.state.mode == "lessons":
            if key.startswith("lesson"):
                self.open_lesson(int(key[6:]))
            else:
                self.lesson_button(key)
            return
        if self.state.mode == "review":
            self.review_button(key)
            return
        if key == "review":
            self.start_review()
            self.submit_input()
        elif key == "input":
            pass  # focus handled in handle_click
        elif key.startswith("chip"):
            label, payload = self.state.chips[int(key[4:])]
            if payload == "__takeback__":
                self.state.chips = list(DEFAULT_CHIPS)
                self.user_says(label)
                self.do_takeback()
                self.say("Good call. Look at the whole board this time — what was your opponent threatening?")
            elif payload == "__keepgoing__":
                self.state.chips = list(DEFAULT_CHIPS)
                self.user_says(label)
                self.say("That's the spirit — playing on from tough spots is great practice. Let's find the best defense.")
            else:
                self.ask_tutor(payload)
        elif key == "new":
            self.board.reset()
            s = self.state
            s.selected, s.legal_targets = None, []
            s.last_move, s.last_move_san, s.hint_move = None, None, None
            s.evaluation = 0
            s.chips = list(DEFAULT_CHIPS)
            s.hint_stage = 0
            s.status_text = "New game — your move."
            self.ai_pending = False
            self.say("Fresh board! Remember: control the center, develop your pieces, keep your king safe.")
            self.refresh_threats()
        elif key == "takeback":
            self.do_takeback()
        elif key == "hint":
            if not self.ai_pending and not self.board.is_game_over():
                move = self.engine.hint_move(self.board)
                if move:
                    if self.state.skill >= 2 and self.state.hint_stage == 0:
                        # Socratic first: a nudge, not the answer
                        piece = self.board.piece_at(move.from_square)
                        from coach import PIECE_NAMES
                        name = (PIECE_NAMES[piece.piece_type]
                                if piece else "piece")
                        self.say(f"Before I show you: look at your {name} "
                                 f"on {chess.square_name(move.from_square)}."
                                 " What could it do this move? Press Hint "
                                 "again if you want the answer.")
                        self.state.hint_stage = 1
                    else:
                        self.state.hint_move = move
                        self.coach.on_hint(self.board, move)
                        self.say(self.coach.message)
                        self.state.hint_stage = 0
        elif key == "threats":
            self.state.show_threats = not self.state.show_threats
            self.refresh_threats()
            self.coach.on_threats_toggle(self.state.show_threats)
            self.say(self.coach.message)
        elif key.startswith("diff"):
            idx = int(key[4:])
            self.state.difficulty_idx = idx
            self.engine.set_difficulty(C.DIFFICULTIES[idx][1])
            self.say(f"Opponent set to '{C.DIFFICULTIES[idx][0]}'. It applies from their next move.")

    def do_takeback(self):
        if len(self.board.move_stack) >= 2 and not self.ai_pending:
            self.board.pop()
            self.board.pop()
            self.state.last_move = (self.board.peek() if self.board.move_stack else None)
            self.state.last_move_san = None
            self.state.selected = None
            self.state.legal_targets = []
            self.state.hint_move = None
            self.state.hint_stage = 0
            self.state.evaluation = self.engine.evaluate(self.board)
            self.state.status_text = "Your move."
            self.refresh_threats()


    def user_move(self, move):
        piece = self.board.piece_at(move.from_square)
        if piece and piece.piece_type == chess.PAWN and \
                chess.square_rank(move.to_square) == 7:
            move = chess.Move(move.from_square, move.to_square, promotion=chess.QUEEN)

        eval_before = self.state.evaluation
        captured = self.board.piece_at(move.to_square)
        captured_type = captured.piece_type if captured else None
        san = self.board.san(move)
        self.board.push(move)
        self.state.last_move = move
        self.state.last_move_san = san
        self.state.selected = []
        self.state.selected = None
        self.state.legal_targets = []
        self.state.hint_move = None
        self.state.evaluation = self.engine.evaluate(self.board)
        self.state.hint_stage = 0
        self.coach.on_user_move(
            self.board, move, eval_before,
            self.state.evaluation, captured_type,
            level=self.state.skill
        )

        if self.coach.message:
            self.say(self.coach.message)

        if eval_before is not None and self.state.evaluation is not None and \
                eval_before - self.state.evaluation >= 250 and \
                not self.board.is_game_over():
            self.say("Want to take that back and try a different idea?")
            self.state.chips = list(RETRY_CHIPS)

        self.refresh_threats()
        if not self.board.is_game_over():
            self.ai_pending = True
            self.ai_due_at = pygame.time.get_ticks() + 450
            self.state.status_text = "Opponent is thinking..."
        else:
            self.state.status_text = "Game over — press New game to play again."


    def ai_move(self):
        move = self.engine.best_move(self.board)
        if move is None:
            self.ai_pending = False
            return
        captured = self.board.piece_at(move.to_square)
        captured_type = captured.piece_type if captured else None
        san = self.board.san(move)
        self.board.push(move)
        self.state.anim = dict(
            start=pygame.time.get_ticks(), duration=260,
            **{"from": move.from_square, "to": move.to_square}
        )
        self.state.last_move = move
        self.state.last_move_san = san
        self.state.evaluation = self.engine.evaluate(self.board)
        self.coach.on_ai_move(self.board, move, captured_type, level=self.state.skill)

        if self.coach.message:
            self.say(self.coach.message)

        self.refresh_threats()
        self.ai_pending = False
        self.state.status_text = ("Game over — press New game to play again." if self.board.is_game_over() else "Your move.")

    def refresh_threats(self):
        self.state.threat_squares = (
            attacked_squares(self.board, chess.WHITE)
            if self.state.show_threats else [])



    def run(self):
        pygame.key.set_repeat(400, 35)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.engine.close()
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.board_release(event.pos)
                elif event.type == pygame.MOUSEWHEEL:
                    if hasattr(self.ui, "chat_rect") and \
                            self.ui.chat_rect.collidepoint(pygame.mouse.get_pos()):
                        self.state.chat_scroll += event.y * 30
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event)
                elif event.type == pygame.TEXTINPUT and self.state.input_focus:
                    self.state.input_text += event.text
                elif event.type == pygame.VIDEORESIZE:
                    C.update_layout(event.w, event.h)
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    from ui import UI
                    self.ui = UI(self.screen)

            # answers arriving from the tutor thread
            try:
                while True:
                    text = self.answers.get_nowait()
                    self.state.coach_thinking = False
                    self.say(text)
            except queue.Empty:
                pass

            # analysis finishing
            try:
                report = self.reports.get_nowait()
                if report is None:
                    self.state.mode = "play"
                    self.say("Sorry, the analysis hit a snag. Try again?")
                else:
                    self.state.report = report
                    self.state.review_evals = (
                        [report.moves[0].eval_before] + [m.eval_after for m in report.moves]
                    )
                    self.set_review_ply(0)

                    # your mistakes become tomorrow's puzzles
                    saved = 0
                    for m in report.moves:
                        if m.is_user and m.tag in ("mistake", "blunder") \
                                and m.best_uci and m.fen_before:
                            storage.add_puzzle(
                                m.fen_before, m.best_uci,
                                f"From your own game — instead of "
                                f"{m.san}, the strong move was "
                                f"{m.best_san}. " + (m.note or ""),
                                "your game"
                            )
                            saved += 1

                    if saved:
                        report.summary += (
                            f" I've saved {saved} position"
                            f"{'s' if saved > 1 else ''} "
                            "to your Practice tab."
                        )
                    n_mist = sum(1 for m in report.moves if m.is_user and m.tag == "mistake")
                    n_blun = sum(1 for m in report.moves if m.is_user and m.tag == "blunder")
                    storage.record_game(report.accuracy, n_mist, n_blun)
                    self.state.skill = storage.skill_level()
            except queue.Empty:
                pass
            if self.state.mode == "review":
                self.state.analyze_progress = self.analyzer.progress

            if self.state.mode == "play" and self.ai_pending and \
                    pygame.time.get_ticks() >= self.ai_due_at:
                self.ai_move()

            self.screen.fill(C.BG)
            if self.state.mode == "stats":
                self.ui.draw_board(self.board, self.state)
                self.ui.draw_stats_sidebar(self.state)
            elif self.state.mode in ("puzzle", "lessons"):
                show_board = (self.state.mode == "puzzle" and
                              self.state.current_puzzle) or \
                             (self.state.mode == "lessons" and self.state.lesson)
                if show_board:
                    self.ui.draw_board(self.puzzle_board, self.state)
                else:
                    self.ui.draw_board(chess.Board(), self.state)
                if self.state.mode == "puzzle":
                    self.ui.draw_practice_sidebar(self.state)
                else:
                    self.ui.draw_lessons_sidebar(self.state)
            elif self.state.mode == "review":
                self.ui.draw_review_board(self.review_board, self.state)
                report = self.state.report
                if report and self.state.review_evals:
                    idx = min(self.state.review_ply, len(self.state.review_evals) - 1)
                    self.ui.draw_eval_bar(self.state.review_evals[idx])
                self.ui.draw_review_sidebar(self.state)
            else:
                self.ui.draw_board(self.board, self.state)
                self.ui.draw_eval_bar(self.state.evaluation)
                self.ui.draw_sidebar(self.state)
            self.ui.draw_theme_toggle()
            pygame.display.flip()
            self.clock.tick(C.FPS)


if __name__ == "__main__":
    Game().run()