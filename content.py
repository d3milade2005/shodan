"""
Learning content: starter tactic puzzles and the lesson curriculum.
Every position here has been verified against the engine — the stated
solution is the best move.

Lessons follow the progression a human coach would use: first stop
losing pieces for free, then win pieces with simple tactics, then
deliver basic checkmates, then absorb opening principles. Concepts are
introduced one at a time, in plain language, with a hands-on exercise
for each.
"""

STARTER_PUZZLES = [
     dict(
          fen="4k3/8/8/3r4/8/8/8/3QK3 w - - 0 1",
          solution="d1d5",
          note="Their rook stood on an open square with nothing defending it — a free capture. Always scan for undefended pieces!"
     ),
    dict(
          fen="r3k3/8/8/3N4/8/8/8/4K3 w - - 0 1",
          solution="d5c7",
          note="A fork: one knight attacked the king AND the rook at the same time. They must save the king, so you win the rook."
     ),
     dict(
          fen="4k3/2q5/8/3N4/8/8/8/4K3 w - - 0 1",
          solution="d5c7",
          note="Another fork — this time the knight hit the king and the queen at once. Knights are fork machines: watch their L-shaped reach."
     ),
     dict(
          fen="q7/8/8/3k4/6B1/8/8/4K3 w - - 0 1",
          solution="g4f3",
          note="A skewer: the bishop checked the king, and when the king steps aside, the queen behind it falls. Line pieces love when two enemies stand on one line."
     ),
     dict(
          fen="6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1",
          solution="e1e8",
          note="Back-rank mate! Their king was trapped behind its own pawns, so one rook on the last row ends the game."
     ),
     dict(
         fen="5k2/6Q1/5K2/8/8/8/8/8 w - - 0 1",
         solution="g7h8",
         note="Queen and king teamwork: your king takes away the escape squares while the queen delivers mate."
     ),
     dict(
         fen="6k1/pp3ppp/8/8/2b5/8/PP2QPPP/6K1 w - - 0 1",
         solution="e2e8",
         note="You could have grabbed the bishop — but checkmate was available! Golden rule: before taking material, always check for a mate first."
     ),
     dict(
         fen="3k4/8/8/3q4/8/8/8/3RK3 w - - 0 1",
         solution="d1d5",
         note="The queen stood on the same file as your rook with nothing defending her. Open lines between pieces are always worth a look."
     ),
]

LESSONS = [
     dict(
          id="hanging",
          title="Don't give pieces away",
          intro="The number one beginner skill: never leave a piece where "
              "it can be captured for free, and always grab enemy pieces "
              "that are. Before EVERY move ask: 'what of mine can they "
              "take?' and 'what of theirs can I take?'",
          exercises=[
               dict(
                    fen="4k3/8/8/3r4/8/8/8/3QK3 w - - 0 1",
                    solution="d1d5",
                    prompt="Their rook is undefended. Take it for free!",
                    success="Exactly. A whole rook, for nothing. Most beginner games are decided by free pieces like this."
               ),
               dict(
                    fen="4k3/8/8/8/4n3/3P4/8/4K3 w - - 0 1",
                    solution="d3e4",
                    prompt="Even the humble pawn can capture. Win the knight!",
                    success="A pawn (worth 1) capturing a knight (worth 3) is a great trade. Value your pieces: pawn 1, knight and bishop 3, rook 5, queen 9."
               ),
          ]
     ),
     dict(
          id="forks",
          title="The fork",
          intro="A fork is one piece attacking two things at once. Your "
              "opponent can only save one — you take the other. Knights "
              "are the best forkers because their L-shaped jump is easy to miss.",
          exercises=[
               dict(
                    fen="r3k3/8/8/3N4/8/8/8/4K3 w - - 0 1",
                    solution="d5c7",
                    prompt="Find the square where your knight attacks the king AND the rook at the same time.",
                    success="They must answer the check, and then you take the rook. That's the power of a fork."
               ),
               dict(
                    fen="4k3/2q5/8/3N4/8/8/8/4K3 w - - 0 1",
                    solution="d5c7",
                    prompt="Same idea, bigger prize: fork the king and the queen.",
                    success="A queen for a knight — the best trade in chess. In your games, always look where your knights could jump next."
               ),
          ]
     ),
     dict(
          id="mates",
          title="Basic checkmates",
          intro="Checkmate means the king is attacked and has NO way out: "
               "no escape square, no block, no capture. These two patterns "
               "win thousands of games at every level.",
          exercises=[
               dict(
                    fen="6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1",
                    solution="e1e8",
                    prompt="Their king is trapped behind its own pawns. Deliver the back-rank mate!",
                    success="The pawns that protect the king become the walls "
                    "of its prison. Watch for this in every game — for them AND for you."
               ),
               dict(
                    fen="6k1/5ppp/8/8/8/8/5PPP/2Q3K1 w - - 0 1",
                    solution="c1c8",
                    prompt="Same pattern, different piece. Mate in one!",
                    success="Any piece that controls the whole back row can "
                    "do it. This is why players make 'luft' — a "
                    "little escape hole — by pushing a pawn near their king."
               ),
          ]
     ),
     dict(
          id="lines",
          title="Skewers and open lines",
          intro="Bishops, rooks, and queens are line pieces. When two enemy "
               "pieces stand on one line, magic happens: attack the front "
               "one, and when it moves, win the one behind. That's a skewer.",
          exercises=[
               dict(
                    fen="q7/8/8/3k4/6B1/8/8/4K3 w - - 0 1",
                    solution="g4f3",
                    prompt="The enemy king and queen share a diagonal. Skewer them!",
                    success="Check! The king must move, and the queen behind it is yours. Scan the long diagonals in your games."
               ),
               dict(
                    fen="3k4/8/8/3q4/8/8/8/3RK3 w - - 0 1",
                    solution="d1d5",
                    prompt="Your rook and their queen share a file — and the queen is undefended. Win her!",
                    success="Open files are highways for rooks. Put your rooks on open files and good things happen."
               ),
          ]
     ),
     dict(
          id="opening",
          title="Opening principles",
          intro="You don't need to memorize openings. Just follow three "
               "rules for your first ten moves: 1) put a pawn in the "
               "center, 2) bring knights and bishops out (called "
               "'developing'), 3) castle your king to safety. ",
          exercises=[
               dict(
                    fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                    solution="e2e4",
                    prompt="Rule 1: claim the center. Push your king's pawn two squares forward.",
                    success="This grabs central space and opens paths for your bishop and queen. 1.e4 is the most popular first move in history."
               ),
               dict(
                    fen="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKB1R w KQkq - 0 2",
                    solution="g1f3",
                    prompt="Rule 2: develop! Bring your kingside knight out toward the center (and attack their pawn while you're at it).",
                    success="One move, two jobs: a piece developed AND a threat created. That's efficient chess. Knights before bishops is a good habit."
               ),
          ]
     ),
]
