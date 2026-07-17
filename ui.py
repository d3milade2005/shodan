"""
All drawing. Layout follows the spacing scale in config.py: wide outer
margins, cards separated by SPACE_MD/LG gaps, roomy padding inside every
card, and nothing touching anything else.
"""

import chess, pygame
import config as C


UNICODE_PIECES = {
    "P": "\u2659", "N": "\u2658", "B": "\u2657",
    "R": "\u2656", "Q": "\u2655", "K": "\u2654",
    "p": "\u265f", "n": "\u265e", "b": "\u265d",
    "r": "\u265c", "q": "\u265b", "k": "\u265a",
}


class UI:
    def __init__(self, screen):
        self.screen = screen
        pygame.font.init()
        self.f_title = pygame.font.SysFont(C.FONT_NAME, C.SIZE_TITLE, bold=True)
        self.f_body = pygame.font.SysFont(C.FONT_NAME, C.SIZE_BODY)
        self.f_small = pygame.font.SysFont(C.FONT_NAME, C.SIZE_SMALL)
        self.f_label = pygame.font.SysFont(C.FONT_NAME, C.SIZE_SMALL + 2, bold=True)
        self.f_piece = pygame.font.SysFont(C.PIECE_FONT, C.SIZE_PIECE)
        self.buttons = {}  # name -> rect (rebuilt every frame)


    def square_rect(self, square):
        f, r = chess.square_file(square), chess.square_rank(square)
        return pygame.Rect(
            C.BOARD_X + f * C.SQUARE,
            C.BOARD_Y + (7 - r) * C.SQUARE,
            C.SQUARE, C.SQUARE
        )
    

    def square_at(self, pos):
        x, y = pos
        if not (C.BOARD_X <= x < C.BOARD_X + C.BOARD_PX and C.BOARD_Y <= y < C.BOARD_Y + C.BOARD_PX):
            return None
        
        f = (x - C.BOARD_X) // C.SQUARE
        r = 7 - (y - C.BOARD_Y) // C.SQUARE
        return chess.square(f, r)

    def _card(self, rect, radius=14):
        pygame.draw.rect(self.screen, C.CARD_BG, rect, border_radius=radius)
        pygame.draw.rect(self.screen, C.CARD_BORDER, rect, 1, border_radius=radius)


    def _tint(self, rect, color, alpha):
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        s.fill((*color, alpha))
        self.screen.blit(s, rect.topleft)


    def _wrap(self, text, font, width):
        words, lines, line = text.split(), [], ""
        for w in words:
            test = (line + " " + w).strip()
            if font.size(test)[0] <= width:
                line = test
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
        return lines
    

    def _piece_at(self, piece, center):
        glyph = UNICODE_PIECES[piece.symbol()]
        white = piece.color == chess.WHITE
        color = C.PIECE_WHITE if white else C.PIECE_BLACK
        outline = self.f_piece.render(
            glyph, True, C.PIECE_OUTLINE_W if white else C.PIECE_OUTLINE_B)
        
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            self.screen.blit(outline, outline.get_rect(center=(center[0] + dx, center[1] + dy)))

        img = self.f_piece.render(glyph, True, color)
        self.screen.blit(img, img.get_rect(center=center))


    def _arrow(self, from_sq, to_sq, color):
        a = self.square_rect(from_sq).center
        b = self.square_rect(to_sq).center
        vec = pygame.math.Vector2(b) - pygame.math.Vector2(a)
        if vec.length() == 0:
            return
        d = vec.normalize()
        b_short = pygame.math.Vector2(b) - d * 22
        pygame.draw.line(self.screen, color, a, b_short, 7)
        left = b_short - d * 16 + d.rotate(90) * 11
        right = b_short - d * 16 + d.rotate(-90) * 11
        pygame.draw.polygon(self.screen, color, [b, left, right])


    def draw_board(self, board, state):
        # frame with a soft border, slightly larger than the board
        frame = pygame.Rect(C.BOARD_X - 10, C.BOARD_Y - 10, C.BOARD_PX + 20, C.BOARD_PX + 20)
        pygame.draw.rect(self.screen, C.BOARD_BORDER, frame, border_radius=12)

        for sq in chess.SQUARES:
            rect = self.square_rect(sq)
            light = (chess.square_file(sq) + chess.square_rank(sq)) % 2 == 1
            pygame.draw.rect(self.screen, C.BOARD_LIGHT if light else C.BOARD_DARK, rect)

        # highlight layers (consistent vocabulary)
        if state.last_move:
            for sq in (state.last_move.from_square, state.last_move.to_square):
                self._tint(self.square_rect(sq), C.HL_LAST_MOVE, 110)
        if state.show_threats:
            for sq in state.threat_squares:
                self._tint(self.square_rect(sq), C.HL_THREAT, 130)
        if state.selected is not None:
            self._tint(self.square_rect(state.selected), C.HL_SELECTED, 140)
        if state.hint_move:
            for sq in (state.hint_move.from_square, state.hint_move.to_square):
                self._tint(self.square_rect(sq), C.HL_SUGGEST, 120)

        # legal-move dots
        for move in state.legal_targets:
            rect = self.square_rect(move.to_square)
            center = rect.center
            if board.piece_at(move.to_square):
                pygame.draw.circle(self.screen, C.HL_LEGAL_DOT, center, C.SQUARE // 2 - 6, 5)
            else:
                pygame.draw.circle(self.screen, C.HL_LEGAL_DOT, center, 11)

        # pieces
        anim = getattr(state, "anim", None)
        anim_progress = None
        if anim:
            elapsed = pygame.time.get_ticks() - anim["start"]
            if elapsed >= anim["duration"]:
                state.anim = anim = None
            else:
                # ease-out for a natural glide
                t = elapsed / anim["duration"]
                anim_progress = 1 - (1 - t) ** 3

        for sq, piece in board.piece_map().items():
            if state.dragging and sq == state.selected:
                continue  # drawn at the cursor instead
            if anim and sq == anim["to"]:
                continue  # drawn interpolated below
            self._piece_at(piece, self.square_rect(sq).center)

        if anim and anim_progress is not None:
            a = self.square_rect(anim["from"]).center
            b = self.square_rect(anim["to"]).center
            pos = (a[0] + (b[0] - a[0]) * anim_progress, a[1] + (b[1] - a[1]) * anim_progress)
            piece = board.piece_at(anim["to"])
            if piece:
                self._piece_at(piece, pos)

        if state.dragging and state.selected is not None:
            piece = board.piece_at(state.selected)
            if piece:
                self._piece_at(piece, pygame.mouse.get_pos())

        if state.hint_move:
            self._arrow(state.hint_move.from_square, state.hint_move.to_square, C.ARROW_GOOD)

        # file/rank labels outside the board (top and left)
        for i in range(8):
            f = self.f_label.render("abcdefgh"[i], True, C.TEXT_MUTED)
            self.screen.blit(f, (C.BOARD_X + i * C.SQUARE + C.SQUARE // 2 - f.get_width() // 2, 
                                 C.BOARD_Y - C.SPACE_MD - 6))
            
            r = self.f_label.render(str(8 - i), True, C.TEXT_MUTED)
            self.screen.blit(r, (C.BOARD_X - C.SPACE_MD - 4, 
                                 C.BOARD_Y + i * C.SQUARE + C.SQUARE // 2 - r.get_height() // 2))


    def draw_eval_bar(self, evaluation):
        x = C.BOARD_X - 10 - C.EVAL_BAR_GAP - C.EVAL_BAR_W
        rect = pygame.Rect(x, C.BOARD_Y, C.EVAL_BAR_W, C.BOARD_PX)
        pygame.draw.rect(self.screen, C.EVAL_BLACK, rect, border_radius=7)
        # map centipawns to a 0..1 share for White (clamped, gentle curve)
        cp = max(-800, min(800, evaluation or 0))
        share = 0.5 + cp / 1600
        white_h = int(rect.height * share)
        wrect = pygame.Rect(rect.x, rect.bottom - white_h, rect.width, white_h)
        pygame.draw.rect(self.screen, C.EVAL_WHITE, wrect, border_radius=7)
        pygame.draw.rect(self.screen, C.CARD_BORDER, rect, 1, border_radius=7)



    def _bubble(self, text, width, is_user):
        """Pre-render one chat bubble; returns (surface, height)."""
        font = self.f_body
        pad = C.CHAT_BUBBLE_PAD
        inner_w = width - pad * 2
        lines = self._wrap(text, font, inner_w)
        line_h = font.get_height() + 4
        h = pad * 2 + len(lines) * line_h
        surf = pygame.Surface((width, h), pygame.SRCALPHA)
        bg = C.USER_BUBBLE if is_user else C.COACH_BUBBLE
        fg = C.USER_TEXT if is_user else C.TEXT_PRIMARY
        pygame.draw.rect(surf, bg, surf.get_rect(), border_radius=12)
        ty = pad
        for ln in lines:
            surf.blit(font.render(ln, True, fg), (pad, ty))
            ty += line_h
        return surf, h
    

    def draw_sidebar(self, state):
        self.buttons = {}
        if getattr(state, "sidebar_minimized", False):
            return
        x, w = C.SIDEBAR_X, C.SIDEBAR_W
        top = self.draw_tabs("tab_play")
        bottom = C.WINDOW_H - C.MARGIN

        # header
        title = self.f_title.render("Shodan", True, C.TEXT_PRIMARY)
        self.screen.blit(title, (x, top))
        sub = self.f_small.render(state.engine_label, True, C.TEXT_SECOND)
        self.screen.blit(sub, (x, top + title.get_height() + 6))
        y = top + title.get_height() + sub.get_height() + C.SPACE_MD


        # action buttons
        btn_h = 44
        names = [("Hint", "hint"), ("Take back", "takeback"), ("Show threats", "threats"), ("New game", "new")]
        btn_w = (w - C.SPACE_SM) // 2
        for i, (label_text, key) in enumerate(names):
            bx = x + (i % 2) * (btn_w + C.SPACE_SM)
            by = y + (i // 2) * (btn_h + C.SPACE_SM)
            rect = pygame.Rect(bx, by, btn_w, btn_h)
            hover = rect.collidepoint(pygame.mouse.get_pos())
            active = key == "threats" and state.show_threats
            bg = C.BTN_BG_HOVER if (hover or active) else C.BTN_BG
            pygame.draw.rect(self.screen, bg, rect, border_radius=12)
            pygame.draw.rect(self.screen, C.BTN_BORDER, rect, 1, border_radius=12)
            img = self.f_body.render(label_text, True, C.TEXT_PRIMARY)
            self.screen.blit(img, img.get_rect(center=rect.center))
            self.buttons[key] = rect
        y += btn_h * 2 + C.SPACE_SM + C.SPACE_MD


        # difficulty pills, one row
        pill_w = (w - C.SPACE_XS * 3) // 4
        for i, (name, _lvl) in enumerate(C.DIFFICULTIES):
            rect = pygame.Rect(x + i * (pill_w + C.SPACE_XS), y, pill_w, 40)
            selected = i == state.difficulty_idx
            hover = rect.collidepoint(pygame.mouse.get_pos())
            bg = C.COACH_BUBBLE if selected else (C.BTN_BG_HOVER if hover else C.BTN_BG)
            pygame.draw.rect(self.screen, bg, rect, border_radius=12)
            border = C.HL_LEGAL_DOT if selected else C.BTN_BORDER
            pygame.draw.rect(self.screen, border, rect, 1, border_radius=12)
            short = name if self.f_small.size(name)[0] <= pill_w - 12 else \
                name.split()[0]
            img = self.f_small.render(short, True, C.TEXT_PRIMARY)
            self.screen.blit(img, img.get_rect(center=rect.center))
            self.buttons[f"diff{i}"] = rect
        y += 40 + C.SPACE_SM

        # review game (full width)
        rect = pygame.Rect(x, y, w, 44)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, C.BTN_BG_HOVER if hover else C.BTN_BG, rect, border_radius=12)
        pygame.draw.rect(self.screen, C.BTN_BORDER, rect, 1, border_radius=12)
        img = self.f_body.render("Review game", True, C.TEXT_PRIMARY)
        self.screen.blit(img, img.get_rect(center=rect.center))
        self.buttons["review"] = rect
        y += 44 + C.SPACE_SM

        # status line
        status = self.f_small.render(state.status_text, True, C.TEXT_SECOND)
        self.screen.blit(status, (x, y))



    def _badge(self, tag, pos):
        from analysis import LABELS
        bg, fg = C.BADGE_COLORS[tag]
        img = self.f_small.render(LABELS[tag], True, fg)
        rect = pygame.Rect(pos[0], pos[1], img.get_width() + 20, 26)
        pygame.draw.rect(self.screen, bg, rect, border_radius=13)
        self.screen.blit(img, img.get_rect(center=rect.center))
        return rect

    def draw_eval_graph(self, rect, evals, current_ply):
        """evals[i] = eval after ply i (evals[0] = start)."""
        pygame.draw.rect(self.screen, C.CARD_BG, rect, border_radius=14)
        pygame.draw.rect(self.screen, C.CARD_BORDER, rect, 1, border_radius=14)
        inner = rect.inflate(-C.SPACE_SM * 2, -C.SPACE_SM * 2)
        mid = inner.centery
        pygame.draw.line(self.screen, C.CARD_BORDER, (inner.left, mid), (inner.right, mid), 1)
        if len(evals) < 2:
            return
        
        n = len(evals) - 1
        pts = []
        for i, ev in enumerate(evals):
            cp = max(-600, min(600, ev or 0))
            x = inner.left + inner.w * i / n
            y = mid - (cp / 600) * (inner.h / 2)
            pts.append((x, y))

        # soft fill for White's advantage
        fill_pts = [(inner.left, mid)] + pts + [(inner.right, mid)]
        pygame.draw.polygon(self.screen, C.GRAPH_FILL, fill_pts)
        pygame.draw.lines(self.screen, C.GRAPH_LINE, False, pts, 2)

        # marker at the ply being viewed
        cx, cy = pts[max(0, min(current_ply, n))]
        pygame.draw.circle(self.screen, C.GRAPH_MARKER, (int(cx), int(cy)), 6)
        label = self.f_small.render("you're winning", True, C.TEXT_MUTED)
        self.screen.blit(label, (inner.left, inner.top - 2))
        label = self.f_small.render("opponent is winning", True, C.TEXT_MUTED)
        self.screen.blit(label, (inner.left, inner.bottom - label.get_height() + 2))

    def draw_review_sidebar(self, state):
        self.buttons = {}
        if getattr(state, "sidebar_minimized", False):
            return
        x, w = C.SIDEBAR_X, C.SIDEBAR_W
        top, bottom = C.MARGIN, C.WINDOW_H - C.MARGIN

        title = self.f_title.render("Game review", True, C.TEXT_PRIMARY)
        self.screen.blit(title, (x, top))
        report = state.report
        sub_text = (f"Estimated accuracy: {report.accuracy}%" if report else "Analyzing your game...")
        sub = self.f_small.render(sub_text, True, C.TEXT_SECOND)
        self.screen.blit(sub, (x, top + title.get_height() + 6))
        y = top + title.get_height() + sub.get_height() + C.SPACE_MD

        if not report:
            done, total = state.analyze_progress
            bar = pygame.Rect(x, y + C.SPACE_LG, w, 14)
            pygame.draw.rect(self.screen, C.CARD_BG, bar, border_radius=7)
            pygame.draw.rect(self.screen, C.CARD_BORDER, bar, 1, border_radius=7)
            if total:
                fill = pygame.Rect(bar.x, bar.y, int(bar.w * done / total), bar.h)
                pygame.draw.rect(self.screen, C.HL_SUGGEST, fill, border_radius=7)
            msg = self.f_body.render(f"Looking at every move... {done}/{total}", True, C.TEXT_SECOND)
            self.screen.blit(msg, (x, y + C.SPACE_LG + 28))
            return

        # eval graph
        graph = pygame.Rect(x, y, w, 130)
        self.draw_eval_graph(graph, state.review_evals, state.review_ply)
        self.buttons["graph"] = graph
        y += 130 + C.SPACE_MD

        # current move card (flexible height)
        pad = C.SPACE_SM
        if state.review_ply == 0:
            header = "Starting position"
            note_lines = self._wrap(report.summary, self.f_body, w - pad * 2)
            tag = None
        else:
            mr = report.moves[state.review_ply - 1]
            who = "You played" if mr.is_user else "Opponent played"
            moveno = (mr.ply + 1) // 2
            header = f"Move {moveno}: {who} {mr.san}"
            note = mr.note or "A normal move by your opponent."
            note_lines = self._wrap(note, self.f_body, w - pad * 2)
            tag = mr.tag
        line_h = self.f_body.get_height() + 4
        card_h = (
            pad + self.f_body.get_height() + C.SPACE_XS +
            (30 if tag else 0) +
            len(note_lines) * line_h + pad
        )

        card = pygame.Rect(x, y, w, card_h)
        self._card(card)
        img = self.f_body.render(header, True, C.TEXT_PRIMARY)
        self.screen.blit(img, (x + pad, y + pad))
        ty = y + pad + self.f_body.get_height() + C.SPACE_XS
        if tag:
            self._badge(tag, (x + pad, ty))
            ty += 30
        for ln in note_lines:
            self.screen.blit(self.f_body.render(ln, True, C.TEXT_SECOND), (x + pad, ty))
            ty += line_h
        y += card_h + C.SPACE_MD

        # navigation
        labels = [("|<", "rev_start"), ("<", "rev_prev"), (">", "rev_next"), (">|", "rev_end")]
        nav_w = (w - C.SPACE_XS * 3) // 4
        for i, (t, key) in enumerate(labels):
            rect = pygame.Rect(x + i * (nav_w + C.SPACE_XS), y, nav_w, 48)
            hover = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(self.screen,C.BTN_BG_HOVER if hover else C.BTN_BG, rect, border_radius=12)
            pygame.draw.rect(self.screen, C.BTN_BORDER, rect, 1, border_radius=12)
            img = self.f_body.render(t, True, C.TEXT_PRIMARY)
            self.screen.blit(img, img.get_rect(center=rect.center))
            self.buttons[key] = rect
        y += 48 + C.SPACE_SM

        pos = self.f_small.render(
            f"Position {state.review_ply} of {len(report.moves)}  ·  "
            "use arrow keys or click the graph",
            True, C.TEXT_MUTED
        )

        self.screen.blit(pos, (x, y))
        y += pos.get_height() + C.SPACE_MD

        # next mistake + back
        flagged = report.user_flagged()
        rows = [
            ("Next mistake" + (f" ({len(flagged)})" if flagged else ""),
            "rev_mistake"),
            ("Back to the game", "rev_back")
        ]

        for label_text, key in rows:
            rect = pygame.Rect(x, y, w, 48)
            hover = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(
                self.screen,
                C.BTN_BG_HOVER if hover else C.BTN_BG,
                rect, border_radius=12
            )
            pygame.draw.rect(self.screen, C.BTN_BORDER, rect, 1, border_radius=12)
            img = self.f_body.render(label_text, True, C.TEXT_PRIMARY)
            self.screen.blit(img, img.get_rect(center=rect.center))
            self.buttons[key] = rect
            y += 48 + C.SPACE_SM

    def draw_review_board(self, board, state):
        """Board during review: last move highlighted; mistakes tinted red."""
        frame = pygame.Rect(C.BOARD_X - 10, C.BOARD_Y - 10, C.BOARD_PX + 20, C.BOARD_PX + 20)
        pygame.draw.rect(self.screen, C.BOARD_BORDER, frame, border_radius=12)
        for sq in chess.SQUARES:
            rect = self.square_rect(sq)
            light = (chess.square_file(sq) + chess.square_rank(sq)) % 2 == 1
            pygame.draw.rect(self.screen, C.BOARD_LIGHT if light else C.BOARD_DARK, rect)

        report = state.report
        if report and state.review_ply > 0:
            mr = report.moves[state.review_ply - 1]
            bad = mr.tag in ("mistake", "blunder")
            color = C.HL_THREAT if bad else C.HL_LAST_MOVE
            for sq in (mr.move.from_square, mr.move.to_square):
                self._tint(self.square_rect(sq), color, 120)

        for sq, piece in board.piece_map().items():
            self._piece_at(piece, self.square_rect(sq).center)

        for i in range(8):
            f = self.f_small.render("abcdefgh"[i], True, C.TEXT_MUTED)
            self.screen.blit(f, (C.BOARD_X + i * C.SQUARE + C.SQUARE // 2 - 4, C.BOARD_Y + C.BOARD_PX + C.SPACE_SM))
            r = self.f_small.render(str(8 - i), True, C.TEXT_MUTED)
            self.screen.blit(r, (C.BOARD_X + C.BOARD_PX + C.SPACE_SM + 2, C.BOARD_Y + i * C.SQUARE + C.SQUARE // 2 - 8))


    # tabs
    def draw_tabs(self, active):
        """Play / Practice / Lessons tab bar. Returns the y below it."""
        x, w = C.SIDEBAR_X, C.SIDEBAR_W
        tabs = [("Play", "tab_play"), ("Practice", "tab_puzzle"), ("Lessons", "tab_lessons"), ("Stats", "tab_stats"), ("Guide", "tab_guide")]
        tab_w = (w - C.SPACE_XS * 4) // 5
        for i, (label, key) in enumerate(tabs):
            rect = pygame.Rect(x + i * (tab_w + C.SPACE_XS), C.MARGIN, tab_w, 40)
            is_active = key == active
            hover = rect.collidepoint(pygame.mouse.get_pos())
            bg = C.TAB_ACTIVE_BG if is_active else (C.BTN_BG_HOVER if hover else C.BTN_BG)
            fg = C.TAB_ACTIVE_FG if is_active else C.TEXT_PRIMARY
            pygame.draw.rect(self.screen, bg, rect, border_radius=12)

            if not is_active:
                pygame.draw.rect(self.screen, C.BTN_BORDER, rect, 1, border_radius=12)

            img = self.f_small.render(label, True, fg)
            if img.get_width() > tab_w - 4:
                img = pygame.transform.smoothscale(img, (tab_w - 4, int(img.get_height() * (tab_w - 4) / img.get_width())))
            self.screen.blit(img, img.get_rect(center=rect.center))
            self.buttons[key] = rect
        return C.MARGIN + 40 + C.SPACE_MD

    def _wide_button(self, y, label, key, height=48):
        x, w = C.SIDEBAR_X, C.SIDEBAR_W
        rect = pygame.Rect(x, y, w, height)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, C.BTN_BG_HOVER if hover else C.BTN_BG, rect, border_radius=12)
        pygame.draw.rect(self.screen, C.BTN_BORDER, rect, 1, border_radius=12)
        img = self.f_body.render(label, True, C.TEXT_PRIMARY)
        self.screen.blit(img, img.get_rect(center=rect.center))
        self.buttons[key] = rect
        return y + height + C.SPACE_SM
    

    def _text_card(self, y, label, text, extra_h=0):
        """Card with a small caption and wrapped body. Returns new y."""
        x, w = C.SIDEBAR_X, C.SIDEBAR_W
        pad = C.SPACE_SM
        lines = self._wrap(text, self.f_body, w - pad * 2)
        line_h = self.f_body.get_height() + 4
        h = (pad + self.f_small.get_height() + C.SPACE_XS + len(lines) * line_h + pad + extra_h)
        card = pygame.Rect(x, y, w, h)
        self._card(card)
        cap = self.f_small.render(label, True, C.TEXT_MUTED)
        self.screen.blit(cap, (x + pad, y + pad))
        ty = y + pad + cap.get_height() + C.SPACE_XS
        for ln in lines:
            self.screen.blit(self.f_body.render(ln, True, C.TEXT_PRIMARY), (x + pad, ty))
            ty += line_h
        return y + h + C.SPACE_MD

    # practice mode
    def draw_practice_sidebar(self, state):
        self.buttons = {}
        if getattr(state, "sidebar_minimized", False):
            return
        y = self.draw_tabs("tab_puzzle")
        x, w = C.SIDEBAR_X, C.SIDEBAR_W

        title = self.f_title.render("Practice", True, C.TEXT_PRIMARY)
        self.screen.blit(title, (x, y))
        due, total, mine = state.puzzle_counts
        sub = self.f_small.render(
            f"{due} due today  ·  {total} total  ·  {mine} from your games",
            True, C.TEXT_SECOND)
        self.screen.blit(sub, (x, y + title.get_height() + 6))
        y += title.get_height() + sub.get_height() + C.SPACE_MD

        p = state.current_puzzle
        if p is None:
            y = self._text_card(
                y, "ALL DONE",
                "Nothing due right now — brilliant! New puzzles appear "
                "here when spaced repetition brings old ones back, and "
                "whenever a game review finds a mistake worth practicing. "
                "Go play a game!"
            )
            return

        source = ("Starter puzzle" if p["source"] == "starter" else "From one of your games")
        y = self._text_card(
            y, source.upper(),
            f"{state.puzzle_side} to move. Find the best "
            "move on the board!" if not state.puzzle_feedback
            else state.puzzle_feedback
        )

        if state.puzzle_solved:
            y = self._wide_button(y, "Next puzzle", "pz_next")
        else:
            y = self._wide_button(y, "Show me the answer", "pz_reveal")
            y = self._wide_button(y, "Skip for now", "pz_skip")

        streak = p.get("streak", 0)
        info = self.f_small.render(
            f"Solve streak for this puzzle: {streak}  ·  correct answers "
            "push it further into the future", True, C.TEXT_MUTED
        )
        self.screen.blit(info, (x, y))

    # lessons mode
    def draw_lessons_sidebar(self, state):
        import storage
        from content import LESSONS
        self.buttons = {}
        if getattr(state, "sidebar_minimized", False):
            return
        y = self.draw_tabs("tab_lessons")
        x, w = C.SIDEBAR_X, C.SIDEBAR_W

        if state.lesson is None:
            title = self.f_title.render("Lessons", True, C.TEXT_PRIMARY)
            self.screen.blit(title, (x, y))
            sub = self.f_small.render(
                "A step-by-step path from beginner to strong player.",
                True, C.TEXT_SECOND
            )
            self.screen.blit(sub, (x, y + title.get_height() + 6))
            y += title.get_height() + sub.get_height() + C.SPACE_MD
            for i, lesson in enumerate(LESSONS):
                done = storage.lesson_done_count(lesson["id"])
                n = len(lesson["exercises"])
                rect = pygame.Rect(x, y, w, 62)
                hover = rect.collidepoint(pygame.mouse.get_pos())
                pygame.draw.rect(
                    self.screen,
                    C.BTN_BG_HOVER if hover else C.CARD_BG,
                    rect, border_radius=14
                )
                pygame.draw.rect(
                    self.screen, C.CARD_BORDER, rect, 1,
                    border_radius=14
                )
                name = self.f_body.render(f"{i + 1}. {lesson['title']}", True, C.TEXT_PRIMARY)
                self.screen.blit(name, (x + C.SPACE_SM, rect.y + 10))
                prog_color = (C.HL_LEGAL_DOT if done >= n else C.TEXT_MUTED)
                prog = self.f_small.render(
                    "Completed!" if done >= n else f"{done} of {n} exercises",
                    True, prog_color
                )
                self.screen.blit(prog, (x + C.SPACE_SM, rect.y + 36))
                self.buttons[f"lesson{i}"] = rect
                y += 62 + C.SPACE_SM
            return

        lesson = state.lesson
        ex = lesson["exercises"][state.exercise_idx]
        title = self.f_title.render(lesson["title"], True, C.TEXT_PRIMARY)
        self.screen.blit(title, (x, y))
        sub = self.f_small.render(
            f"Exercise {state.exercise_idx + 1} of {len(lesson['exercises'])}",
            True, C.TEXT_SECOND
        )

        self.screen.blit(sub, (x, y + title.get_height() + 6))
        y += title.get_height() + sub.get_height() + C.SPACE_MD

        y = self._text_card(y, "THE IDEA", lesson["intro"])
        y = self._text_card(y, "YOUR TASK", state.lesson_feedback or ex["prompt"])

        if state.exercise_solved:
            last = state.exercise_idx == len(lesson["exercises"]) - 1
            y = self._wide_button(y, "Finish lesson" if last else "Next exercise", "lx_next")
        else:
            y = self._wide_button(y, "Show me the answer", "lx_reveal")
        y = self._wide_button(y, "Back to all lessons", "lx_back")


    # stats mode
    def _stat_row(self, y, label, value):
        x, w = C.SIDEBAR_X, C.SIDEBAR_W
        pad = C.SPACE_SM
        img_l = self.f_body.render(label, True, C.TEXT_SECOND)
        img_v = self.f_body.render(str(value), True, C.TEXT_PRIMARY)
        self.screen.blit(img_l, (x + pad, y))
        self.screen.blit(img_v, (x + w - pad - img_v.get_width(), y))
        return y + img_l.get_height() + C.SPACE_XS

    def draw_stats_sidebar(self, state):
        import storage
        from content import LESSONS
        self.buttons = {}
        if getattr(state, "sidebar_minimized", False):
            return
        y = self.draw_tabs("tab_stats")
        x, w = C.SIDEBAR_X, C.SIDEBAR_W

        title = self.f_title.render("Your progress", True, C.TEXT_PRIMARY)
        self.screen.blit(title, (x, y))
        level = state.skill
        names = {
            1: "Brand new — everything explained",
            2: "Developing — the coach asks you questions first",
            3: "Improving — the coach speaks only when it matters"
        }

        sub = self.f_small.render(f"Coaching level {level}: {names[level]}", True, C.TEXT_SECOND)
        self.screen.blit(sub, (x, y + title.get_height() + 6))
        y += title.get_height() + sub.get_height() + C.SPACE_MD

        accs, avg, best, total = storage.game_stats()

        # accuracy trend card
        card = pygame.Rect(x, y, w, 150)
        self._card(card)
        cap = self.f_small.render("ACCURACY TREND (LAST 20 GAMES)", True, C.TEXT_MUTED)
        self.screen.blit(cap, (x + C.SPACE_SM, y + C.SPACE_SM))

        inner = pygame.Rect(
            x + C.SPACE_SM,
            y + C.SPACE_SM + cap.get_height() + C.SPACE_XS,
            w - C.SPACE_SM * 2,
            150 - C.SPACE_SM * 2 - cap.get_height() -
            C.SPACE_XS
        )

        if len(accs) >= 2:
            pts = []
            for i, a in enumerate(accs):
                px = inner.left + inner.w * i / (len(accs) - 1)
                py = inner.bottom - inner.h * a / 100
                pts.append((px, py))

            fill = [(inner.left, inner.bottom)] + pts + \
                   [(inner.right, inner.bottom)]
            
            pygame.draw.polygon(self.screen, C.GRAPH_FILL, fill)
            pygame.draw.lines(self.screen, C.GRAPH_LINE, False, pts, 2)

            for p in pts:
                pygame.draw.circle(self.screen, C.GRAPH_MARKER, (int(p[0]), int(p[1])), 4)
        else:
            msg = self.f_body.render(
                "Review a couple of games to see your trend.", True,
                C.TEXT_MUTED
            )
            self.screen.blit(msg, msg.get_rect(center=inner.center))
        y += 150 + C.SPACE_MD

        # numbers card
        attempts, rate = storage.puzzle_stats()
        mistakes, blunders = storage.mistake_totals()
        due, ptotal, mine = storage.counts()

        rows = [
            ("Games reviewed", total),
            ("Average accuracy", f"{avg}%" if total else "—"),
            ("Best accuracy", f"{best}%" if total else "—"),
            ("Mistakes + blunders, last 10 games", mistakes + blunders if total else "—"),
            ("Puzzles solved first try", f"{round(rate * 100)}%" if attempts else "—"),
            ("Puzzles from your own games", mine),
            ("Puzzles due today", due)
        ]

        row_h = self.f_body.get_height() + C.SPACE_XS
        card_h = C.SPACE_SM * 2 + len(rows) * row_h
        card = pygame.Rect(x, y, w, card_h)
        self._card(card)
        ry = y + C.SPACE_SM
        for label, value in rows:
            ry = self._stat_row(ry, label, value)
        y += card_h + C.SPACE_MD

        # lessons card
        done = sum(storage.lesson_done_count(l["id"]) for l in LESSONS)
        total_ex = sum(len(l["exercises"]) for l in LESSONS)
        card_h = C.SPACE_SM * 2 + row_h
        card = pygame.Rect(x, y, w, card_h)
        self._card(card)
        self._stat_row(y + C.SPACE_SM, "Lesson exercises completed", f"{done} of {total_ex}")


    def draw_chat_sidebar(self, state):
        if getattr(state, "sidebar_minimized", False):
            return
        x, w = C.CHAT_X, C.CHAT_W
        y = C.MARGIN

        chips_h = C.CHIP_H
        input_h = C.CHAT_INPUT_H
        reserved = C.SPACE_SM + chips_h + C.SPACE_SM + input_h + C.SPACE_MD
        bottom = C.WINDOW_H - C.MARGIN
        chat_h = bottom - y - reserved

        card = pygame.Rect(x, y, w, chat_h)
        self._card(card)
        pad = C.SPACE_SM
        label = self.f_small.render("YOUR COACH", True, C.TEXT_MUTED)
        self.screen.blit(label, (x + pad, y + pad))
        inner = pygame.Rect(
            x + pad, y + pad + label.get_height() + C.SPACE_XS, w - pad * 2,
            chat_h - pad * 2 - label.get_height() - C.SPACE_XS
        )
        self.chat_rect = inner

        bubbles = []
        bubble_w = inner.w - 36
        for role, text in state.chat:
            bubbles.append((role, *self._bubble(text, bubble_w, role == "user")))

        if state.coach_thinking:
            bubbles.append(("coach", *self._bubble("Coach is thinking...", bubble_w, False)))

        total = sum(h for _, _, h in bubbles) + C.SPACE_XS * max(len(bubbles) - 1, 0)
        max_scroll = max(0, total - inner.h)
        state.chat_scroll = max(0, min(state.chat_scroll, max_scroll))
        state.chat_max_scroll = max_scroll

        clip = self.screen.get_clip()
        self.screen.set_clip(inner)
        by = inner.bottom + state.chat_scroll
        for role, surf, h in reversed(bubbles):
            by -= h
            bx = inner.x + (inner.w - bubble_w if role == "user" else 0)
            self.screen.blit(surf, (bx, by))
            by -= C.SPACE_XS
        self.screen.set_clip(clip)
        y += chat_h + C.SPACE_SM

        cx = x
        for i, (label_text, _payload) in enumerate(state.chips):
            img = self.f_small.render(label_text, True, C.TEXT_PRIMARY)
            cw = img.get_width() + 28
            rect = pygame.Rect(cx, y, cw, C.CHIP_H)
            hover = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(self.screen, C.BTN_BG_HOVER if hover else C.BTN_BG, rect, border_radius=17)
            pygame.draw.rect(self.screen, C.BTN_BORDER, rect, 1, border_radius=17)
            self.screen.blit(img, img.get_rect(center=rect.center))
            self.buttons[f"chip{i}"] = rect
            cx += cw + C.SPACE_XS

        y += C.CHIP_H + C.SPACE_SM

        send_w = 76
        in_rect = pygame.Rect(x, y, w - send_w - C.SPACE_XS, C.CHAT_INPUT_H)
        pygame.draw.rect(self.screen, C.CARD_BG, in_rect, border_radius=12)
        border = C.HL_LAST_MOVE if state.input_focus else C.BTN_BORDER
        pygame.draw.rect(self.screen, border, in_rect, 2, border_radius=12)
        self.buttons["input"] = in_rect
        text = state.input_text
        placeholder = not text and not state.input_focus
        shown = "Ask your coach anything..." if placeholder else text
        color = C.TEXT_MUTED if placeholder else C.TEXT_PRIMARY
        img = self.f_body.render(shown, True, color)

        max_w = in_rect.w - 28
        if img.get_width() > max_w:
            img = img.subsurface((img.get_width() - max_w, 0, max_w, img.get_height()))

        self.screen.blit(img, (in_rect.x + 14, in_rect.centery - img.get_height() // 2))

        if state.input_focus and (pygame.time.get_ticks() // 500) % 2 == 0:
            cx2 = in_rect.x + 14 + min(self.f_body.size(text)[0], max_w)
            pygame.draw.line(self.screen, C.TEXT_PRIMARY, (cx2 + 2, in_rect.y + 12), (cx2 + 2, in_rect.bottom - 12), 2)
            
        send = pygame.Rect(in_rect.right + C.SPACE_XS, y, send_w, C.CHAT_INPUT_H)
        hover = send.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, C.BTN_BG_HOVER if hover else C.BTN_BG, send, border_radius=12)
        pygame.draw.rect(self.screen, C.BTN_BORDER, send, 1, border_radius=12)
        img = self.f_body.render("Ask", True, C.TEXT_PRIMARY)
        self.screen.blit(img, img.get_rect(center=send.center))
        self.buttons["send"] = send


    def draw_guide_sidebar(self, state):
        self.buttons = {}
        if getattr(state, "sidebar_minimized", False):
            return
        y = self.draw_tabs("tab_guide")
        x, w = C.SIDEBAR_X, C.SIDEBAR_W

        title = self.f_title.render("Pieces Guide", True, C.TEXT_PRIMARY)
        self.screen.blit(title, (x, y))
        sub = self.f_small.render("What they do and how they move.", True, C.TEXT_SECOND)
        self.screen.blit(sub, (x, y + title.get_height() + 6))
        y += title.get_height() + sub.get_height() + C.SPACE_MD

        pieces_info = [
            ("King", "\u2654", "Moves one square in any direction. The most important piece - if it's trapped, you lose!"),
            ("Queen", "\u2655", "Moves any number of squares in any direction. Extremely powerful."),
            ("Rook", "\u2656", "Moves straight along rows and columns. Great for open files and back ranks."),
            ("Bishop", "\u2657", "Moves diagonally any number of squares. Stays on one color its whole life."),
            ("Knight", "\u2658", "Moves in an 'L' shape (two steps one way, one step side). Can jump over pieces."),
            ("Pawn", "\u2659", "Moves forward one square (two on its first move). Captures diagonally.")
        ]

        if not hasattr(state, "guide_scroll"):
            state.guide_scroll = 0

        total_h = 0
        pieces_data = []
        for name, glyph, desc in pieces_info:
            name_img = self.f_body.render(name, True, C.TEXT_PRIMARY)
            lines = self._wrap(desc, self.f_small, w - 90)
            text_h = 14 + name_img.get_height() + len(lines) * (self.f_small.get_height() + 2) + 14
            h = max(80, text_h)
            pieces_data.append((name, glyph, desc, name_img, lines, h))
            total_h += h + C.SPACE_SM
            
        clip_rect = pygame.Rect(x, y, w, C.WINDOW_H - y - C.MARGIN)
        self.guide_rect = clip_rect
        
        max_scroll = max(0, total_h - clip_rect.h)
        state.guide_scroll = max(0, min(state.guide_scroll, max_scroll))

        clip = self.screen.get_clip()
        self.screen.set_clip(clip_rect)

        by = y - state.guide_scroll
        for name, glyph, desc, name_img, lines, h in pieces_data:
            rect = pygame.Rect(x, by, w, h)
            self._card(rect)
            
            # Draw piece icon centered vertically in the card
            pygame.draw.circle(self.screen, C.COACH_BUBBLE, (x + 40, by + h // 2), 24)
            img = self.f_piece.render(glyph, True, C.PIECE_WHITE)
            outl = self.f_piece.render(glyph, True, C.PIECE_OUTLINE_W)
            for dx, dy in ((-2,0), (2,0), (0,-2), (0,2)):
                self.screen.blit(outl, outl.get_rect(center=(x + 40 + dx, by + h // 2 + dy)))
            self.screen.blit(img, img.get_rect(center=(x + 40, by + h // 2)))
            
            # Text
            self.screen.blit(name_img, (x + 80, by + 12))
            
            ty = by + 14 + name_img.get_height()
            for ln in lines:
                self.screen.blit(self.f_small.render(ln, True, C.TEXT_SECOND), (x + 80, ty))
                ty += self.f_small.get_height() + 2

            by += h + C.SPACE_SM

        self.screen.set_clip(clip)


    # theme toggle
    def draw_theme_toggle(self, state=None):
        """Small sun/moon button floating right of the sidebar."""
        size = 40
        if getattr(state, "sidebar_minimized", False):
            x = C.WINDOW_W - C.MARGIN + (C.MARGIN - size) // 2
            y = C.MARGIN
            rect = pygame.Rect(x, y, size, size)
            rect.right = min(rect.right, C.WINDOW_W - 8)
        else:
            x = min(C.SIDEBAR_X + C.SIDEBAR_W - size, C.WINDOW_W - size - 8)
            y = C.MARGIN + 40 + C.SPACE_MD
            rect = pygame.Rect(x, y, size, size)

        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, C.BTN_BG_HOVER if hover else C.BTN_BG, rect, border_radius=20)
        pygame.draw.rect(self.screen, C.BTN_BORDER, rect, 1, border_radius=20)
        cx, cy = rect.center

        if C.THEME == "light":
            # moon: circle with a bite taken out
            pygame.draw.circle(self.screen, C.TEXT_SECOND, (cx, cy), 9)
            pygame.draw.circle(
                self.screen,
                C.BTN_BG_HOVER if hover else C.BTN_BG,
                (cx + 5, cy - 4), 8
            )
        else:
            # sun: circle with rays
            pygame.draw.circle(self.screen, C.TEXT_SECOND, (cx, cy), 6)
            for dx, dy in (
                (1, 0), (-1, 0), (0, 1), (0, -1),
                (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7),
                (-0.7, -0.7)
            ):
                pygame.draw.line(
                    self.screen, C.TEXT_SECOND,
                    (cx + dx * 9, cy + dy * 9),
                    (cx + dx * 13, cy + dy * 13), 2
                )

        if state is not None:
            if getattr(state, "sidebar_minimized", False):
                rect2 = pygame.Rect(rect.x, rect.bottom + C.SPACE_SM, size, size)
            else:
                rect2 = pygame.Rect(rect.x - size - C.SPACE_XS, rect.y, size, size)
                
            hover2 = rect2.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(self.screen, C.BTN_BG_HOVER if hover2 else C.BTN_BG, rect2, border_radius=12)
            pygame.draw.rect(self.screen, C.BTN_BORDER, rect2, 1, border_radius=12)
            icon = "<" if state.sidebar_minimized else ">"
            img2 = self.f_body.render(icon, True, C.TEXT_PRIMARY)
            self.screen.blit(img2, img2.get_rect(center=rect2.center))
            self.buttons["toggle_sidebar"] = rect2
        self.buttons["theme"] = rect