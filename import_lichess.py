"""
Import real tactics puzzles from the free Lichess puzzle database into
your practice deck.

Usage:
    pip install zstandard
    python import_lichess.py                # download + import 300 puzzles
    python import_lichess.py 1000           # import up to 1000
    python import_lichess.py puzzles.csv    # use an already-downloaded CSV

What it does:
- downloads lichess_db_puzzle.csv.zst (one-time, ~250 MB) from
  https://database.lichess.org — or reads a local CSV if you pass a path
- keeps beginner-friendly puzzles: rating <= 1300 and solvable in ONE
  move (the app teaches single decisive moves first)
- writes them into progress.db so they appear in the Practice tab,
  mixed into the same spaced-repetition schedule as everything else

Lichess puzzle format note: the FEN is the position BEFORE the
opponent's move; the first move in `Moves` is the opponent playing,
and the rest is the solution. We apply the first move, so the stored
puzzle is exactly the position you must solve.
"""

import io, os, sys, chess, storage, csv, urllib.request


URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"
MAX_RATING = 1300


THEME_NOTES = {
    "mateIn1": "Checkmate in one — the king is attacked with no escape, block, or capture.",
    "fork": "A fork: one piece attacks two targets at once.",
    "pin": "A pin: the piece in front can't move without exposing something more valuable behind it.",
    "skewer": "A skewer: attack the valuable piece in front, win the one behind when it moves.",
    "hangingPiece": "A hanging piece: it can be captured for free.",
    "backRankMate": "Back-rank mate: the king is trapped behind its own pawns.",
    "discoveredAttack": "A discovered attack: moving one piece unveils an attack from another.",
}


def note_for(themes):
    for t in themes.split():
        if t in THEME_NOTES:
            return "Lichess puzzle. " + THEME_NOTES[t]
    return ("Lichess puzzle. Look for checks, captures, and threats — the strongest move is usually one of those.")


def rows_from(path_or_none):
    if path_or_none and os.path.exists(path_or_none):
        print(f"Reading {path_or_none} ...")
        return open(path_or_none, newline="", encoding="utf-8")
    try:
        import zstandard
    except ImportError:
        sys.exit("Please run: pip install zstandard  (needed to decompress the Lichess database)")
    print("Downloading the Lichess puzzle database (~250 MB, one time)...")
    resp = urllib.request.urlopen(URL)
    dctx = zstandard.ZstdDecompressor()
    reader = dctx.stream_reader(resp)
    return io.TextIOWrapper(reader, encoding="utf-8", newline="")


def main():
    limit = 300
    path = None
    for arg in sys.argv[1:]:
        if arg.isdigit():
            limit = int(arg)
        else:
            path = arg

    imported = scanned = 0
    with rows_from(path) as f:
        for row in csv.DictReader(f):
            scanned += 1
            try:
                if int(row["Rating"]) > MAX_RATING:
                    continue
                moves = row["Moves"].split()
                if len(moves) != 2:
                    continue  # single-move solutions only
                board = chess.Board(row["FEN"])
                board.push(chess.Move.from_uci(moves[0]))
                solution = moves[1]
                if chess.Move.from_uci(solution) not in board.legal_moves:
                    continue
                storage.add_puzzle(
                    board.fen(), solution, note_for(row.get("Themes", "")), "lichess"
                )
                imported += 1
                if imported % 50 == 0:
                    print(f"  imported {imported} ...")
                if imported >= limit:
                    break
            except Exception:
                continue
            
    print(f"Done! Imported {imported} puzzles (scanned {scanned:,} rows).")
    print("They'll appear in the Practice tab, mixed into your spaced-repetition schedule.")


if __name__ == "__main__":
    main()
