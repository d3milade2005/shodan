"""
Design system for Chess Master.
All spacing, color, and layout decisions live here so the UI stays
consistent and easy to tune. The layout is built around generous
whitespace: a spacing scale, wide outer margins, and roomy cards.
"""

# ---------------------------------------------------------------- spacing
# A simple 4px-based scale. Use these instead of magic numbers.
SPACE_XS = 8
SPACE_SM = 16
SPACE_MD = 24
SPACE_LG = 36
SPACE_XL = 48

# ---------------------------------------------------------------- window
WINDOW_W = 1240
WINDOW_H = 820
FPS = 60

MARGIN = SPACE_XL          # breathing room around everything
SIDEBAR_W = 400            # right-hand panel
PANEL_GAP = SPACE_XL + 32  # gap between board area and sidebar (increased)

# chat panel
CHAT_BUBBLE_PAD = 12
CHAT_INPUT_H = 48
CHIP_H = 34
USER_BUBBLE = (230, 241, 251)   # soft blue for the student's messages
USER_TEXT = (12, 68, 124)

# ---------------------------------------------------------------- board
SQUARE = 80
BOARD_PX = SQUARE * 8      # 640
EVAL_BAR_W = 14
EVAL_BAR_GAP = SPACE_SM
BOARD_X = MARGIN + EVAL_BAR_W + EVAL_BAR_GAP + 10   # room for eval bar
BOARD_Y = (WINDOW_H - BOARD_PX) // 2

SIDEBAR_X = BOARD_X + BOARD_PX + PANEL_GAP

def update_layout(w, h):
    global WINDOW_W, WINDOW_H, BOARD_Y
    WINDOW_W = w
    WINDOW_H = h
    BOARD_Y = (WINDOW_H - BOARD_PX) // 2

# ---------------------------------------------------------------- palette
# Two complete palettes. All drawing code reads module attributes at
# render time, so set_theme() switches the whole app instantly.

LIGHT = dict(
    BG=(246, 244, 239),
    BOARD_LIGHT=(238, 233, 223), BOARD_DARK=(181, 166, 140),
    BOARD_BORDER=(160, 148, 126),
    CARD_BG=(255, 255, 255), CARD_BORDER=(226, 222, 214),
    TEXT_PRIMARY=(44, 44, 42), TEXT_SECOND=(120, 118, 112),
    TEXT_MUTED=(168, 165, 158),
    HL_LAST_MOVE=(133, 183, 235), HL_SELECTED=(250, 199, 117),
    HL_LEGAL_DOT=(99, 153, 34), HL_SUGGEST=(151, 196, 89),
    HL_THREAT=(240, 149, 149),
    ARROW_GOOD=(59, 109, 17), ARROW_BAD=(163, 45, 45),
    BTN_BG=(255, 255, 255), BTN_BG_HOVER=(241, 239, 232),
    BTN_BORDER=(200, 196, 188),
    COACH_BUBBLE=(241, 239, 232),
    USER_BUBBLE=(230, 241, 251), USER_TEXT=(12, 68, 124),
    EVAL_WHITE=(250, 249, 246), EVAL_BLACK=(70, 68, 64),
    PIECE_WHITE=(250, 249, 246), PIECE_BLACK=(40, 39, 37),
    PIECE_OUTLINE_W=(96, 90, 80), PIECE_OUTLINE_B=(120, 114, 104),
    BADGE_COLORS={
        "great":      ((225, 245, 238), (8, 80, 65)),
        "good":       ((234, 243, 222), (39, 80, 10)),
        "inaccuracy": ((250, 238, 218), (99, 56, 6)),
        "mistake":    ((250, 231, 214), (113, 43, 19)),
        "blunder":    ((252, 235, 235), (121, 31, 31)),
    },
    GRAPH_LINE=(95, 94, 90), GRAPH_FILL=(223, 219, 210),
    GRAPH_MARKER=(216, 90, 48),
    TAB_ACTIVE_BG=(44, 44, 42), TAB_ACTIVE_FG=(255, 255, 255),
)

DARK = dict(
    BG=(26, 26, 29),
    BOARD_LIGHT=(142, 133, 116), BOARD_DARK=(88, 81, 69),
    BOARD_BORDER=(56, 52, 46),
    CARD_BG=(38, 38, 43), CARD_BORDER=(60, 60, 66),
    TEXT_PRIMARY=(233, 231, 226), TEXT_SECOND=(163, 161, 155),
    TEXT_MUTED=(122, 120, 115),
    HL_LAST_MOVE=(96, 150, 205), HL_SELECTED=(222, 172, 92),
    HL_LEGAL_DOT=(140, 190, 80), HL_SUGGEST=(120, 165, 66),
    HL_THREAT=(205, 105, 105),
    ARROW_GOOD=(150, 205, 95), ARROW_BAD=(224, 108, 108),
    BTN_BG=(38, 38, 43), BTN_BG_HOVER=(54, 54, 61),
    BTN_BORDER=(74, 74, 82),
    COACH_BUBBLE=(50, 50, 57),
    USER_BUBBLE=(32, 58, 86), USER_TEXT=(168, 205, 240),
    EVAL_WHITE=(236, 234, 229), EVAL_BLACK=(18, 18, 20),
    PIECE_WHITE=(245, 243, 238), PIECE_BLACK=(30, 29, 27),
    PIECE_OUTLINE_W=(44, 42, 38), PIECE_OUTLINE_B=(186, 180, 168),
    BADGE_COLORS={
        "great":      ((24, 62, 52), (146, 220, 192)),
        "good":       ((38, 58, 26), (176, 216, 138)),
        "inaccuracy": ((70, 52, 22), (232, 190, 128)),
        "mistake":    ((76, 42, 24), (238, 170, 128)),
        "blunder":    ((80, 30, 30), (240, 150, 150)),
    },
    GRAPH_LINE=(168, 166, 158), GRAPH_FILL=(52, 51, 48),
    GRAPH_MARKER=(230, 110, 66),
    TAB_ACTIVE_BG=(233, 231, 226), TAB_ACTIVE_FG=(30, 30, 34),
)

THEME = "light"


def set_theme(name):
    """Switch every color the app draws with. Safe to call any time."""
    global THEME
    THEME = "dark" if name == "dark" else "light"
    globals().update(DARK if THEME == "dark" else LIGHT)


set_theme("light")

# ---------------------------------------------------------------- type
FONT_NAME     = "segoeui,arial"
PIECE_FONT    = "segoeuisymbol,segoeui,arial"  # needs chess glyphs
SIZE_TITLE    = 26
SIZE_BODY     = 17
SIZE_SMALL    = 14
SIZE_PIECE    = 58

# ---------------------------------------------------------------- game
# Friendly difficulty tiers -> approximate engine strength.
DIFFICULTIES = [
    ("Just learning", 1),    # fallback AI depth / stockfish skill 1
    ("Casual",        4),
    ("Club player",   9),
    ("Strong",        15),
]
