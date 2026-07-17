"""
Persistent progress, stored in progress.db next to the app.

- puzzles: every position worth practicing. Some ship with the app
  ("starter" source); the rest are created automatically from mistakes
  found in your game reviews ("your game" source).
- spaced repetition: each puzzle has a due date. Solve it on the first
  try and the interval grows (1 -> 3 -> 7 -> 14 -> 30 days); miss it and
  it comes back tomorrow. This is how the app makes sure you never
  repeat the same kind of mistake for long.
- lesson progress: which curriculum exercises you've completed.
"""

import os, sqlite3, datetime as dt

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "progress.db")
INTERVALS = [1, 3, 7, 14, 30]


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS puzzles (
        id INTEGER PRIMARY KEY,
        fen TEXT NOT NULL,
        solution TEXT NOT NULL,
        note TEXT,
        source TEXT,
        created TEXT,
        due TEXT,
        streak INTEGER DEFAULT 0,
        UNIQUE(fen, solution))"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS lesson_progress (
        lesson_id TEXT,
        exercise_idx INTEGER,
        PRIMARY KEY (lesson_id, exercise_idx))"""
    )
    return conn


def _today():
    return dt.date.today().isoformat()


def add_puzzle(fen, solution_uci, note, source):
    """Insert if new; new puzzles are due immediately."""
    with _conn() as c:
        c.execute(
            """INSERT OR IGNORE INTO puzzles
            (fen, solution, note, source, created, due, streak)
            VALUES (?,?,?,?,?,?,0)""",
            (fen, solution_uci, note, source, _today(), _today())
        )


def seed_starters(starters):
    """starters: list of dicts with fen/solution/note. Runs once."""
    with _conn() as c:
        for s in starters:
            c.execute(
                """INSERT OR IGNORE INTO puzzles
                (fen, solution, note, source, created, due, streak)
                VALUES (?,?,?,?,?,?,0)""",
                (s["fen"], s["solution"], s["note"], "starter",
                _today(), _today())
            )


def due_puzzles():
    """All puzzles due today or earlier, oldest-due first."""
    with _conn() as c:
        rows = c.execute(
            """SELECT id, fen, solution, note, source, streak
            FROM puzzles WHERE due <= ?
            ORDER BY due, id""", (_today(),)
            ).fetchall()
        
    return [dict(zip(("id", "fen", "solution", "note", "source", "streak"), r)) for r in rows]


def counts():
    with _conn() as c:
        due = c.execute("SELECT COUNT(*) FROM puzzles WHERE due <= ?", (_today(),)).fetchone()[0]
        total = c.execute("SELECT COUNT(*) FROM puzzles").fetchone()[0]
        mine = c.execute("SELECT COUNT(*) FROM puzzles WHERE source != ""'starter'").fetchone()[0]
    return due, total, mine


def record_result(puzzle_id, first_try_correct):
    with _conn() as c:
        streak = c.execute("SELECT streak FROM puzzles WHERE id=?", (puzzle_id,)).fetchone()[0]
        streak = streak + 1 if first_try_correct else 0
        days = INTERVALS[min(streak, len(INTERVALS) - 1)] \
            if first_try_correct else 1
        
        due = (dt.date.today() + dt.timedelta(days=days)).isoformat()
        c.execute("UPDATE puzzles SET streak=?, due=? WHERE id=?", (streak, due, puzzle_id))
        return days


def complete_exercise(lesson_id, exercise_idx):
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO lesson_progress VALUES (?,?)", (lesson_id, exercise_idx))


def lesson_done_count(lesson_id):
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM lesson_progress WHERE ""lesson_id=?", (lesson_id,)).fetchone()[0]



def _conn2():
    conn = _conn()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY,
        date TEXT, accuracy INTEGER,
        mistakes INTEGER, blunders INTEGER)"""
    )
    conn.execute("""CREATE TABLE IF NOT EXISTS puzzle_log (date TEXT, first_try INTEGER)""")
    return conn


def record_game(accuracy, mistakes, blunders):
    with _conn2() as c:
        c.execute(
            "INSERT INTO games (date, accuracy, mistakes, blunders) "
            "VALUES (?,?,?,?)",
            (_today(), accuracy, mistakes, blunders)
        )


def log_puzzle_attempt(first_try):
    with _conn2() as c:
        c.execute("INSERT INTO puzzle_log VALUES (?,?)", (_today(), 1 if first_try else 0))


def game_stats(n=20):
    """(accuracies list oldest->newest, avg, best, total_games)."""
    with _conn2() as c:
        rows = c.execute("SELECT accuracy FROM games ORDER BY id DESC ""LIMIT ?", (n,)).fetchall()
        total = c.execute("SELECT COUNT(*) FROM games").fetchone()[0]

    accs = [r[0] for r in reversed(rows)]
    avg = round(sum(accs) / len(accs)) if accs else 0
    best = max(accs) if accs else 0
    return accs, avg, best, total


def puzzle_stats():
    """(attempts, first_try_rate 0..1)."""
    with _conn2() as c:
        rows = c.execute("SELECT COUNT(*), COALESCE(SUM(first_try),0) ""FROM puzzle_log").fetchone()
    attempts, correct = rows
    return attempts, (correct / attempts if attempts else 0.0)


def mistake_totals(n=10):
    """(mistakes, blunders) across the last n games."""
    with _conn2() as c:
        rows = c.execute(
            "SELECT COALESCE(SUM(mistakes),0), "
            "COALESCE(SUM(blunders),0) FROM (SELECT mistakes, "
            "blunders FROM games ORDER BY id DESC LIMIT ?)",
            (n,)
        ).fetchone()
    return rows


def skill_level():
    """1 = brand new, 2 = developing, 3 = improving.
    Based on recent game accuracy and puzzle success."""
    accs, avg, _, total = game_stats(5)
    attempts, rate = puzzle_stats()
    if total >= 3 and avg >= 80 and (attempts < 10 or rate >= 0.7):
        return 3
    if total >= 1 and avg >= 60:
        return 2
    return 1


def get_setting(key, default=None):
    with _conn() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_setting(key, value):
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO settings VALUES (?,?)",(key, str(value)))
