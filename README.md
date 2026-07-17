# Shodan

*Shodan (初段): in Japanese martial arts, the rank of first-degree black
belt — not the end of the journey, but the moment you become a serious
student. That's the promise of this app.*

A clean, spacious chess trainer designed for complete beginners. You play
White against an adjustable AI while a coach panel explains what's
happening in plain language.

## Run it

```bash
pip install pygame python-chess
python main.py
```

That's it — the app works immediately using its built-in AI.

**Optional (recommended):**
- Install Stockfish for a much stronger opponent and real evaluations
  (https://stockfishchess.org — put the executable on your PATH).
- Set an `ANTHROPIC_API_KEY` environment variable to unlock the full
  conversational coach powered by the Claude API. Every answer is
  grounded in engine analysis of the current position, so the coach
  explains accurately AND in friendly plain language. Without a key, a
  built-in rule-based tutor still answers common questions offline.

## How to play

Drag and drop a piece, or click it and then click a destination — green
dots show every legal square (a green ring means a capture). Opponent
moves glide across the board so you never miss what happened.

- **Hint** — draws a green arrow showing a strong move and explains why.
- **Take back** — undoes your last move and the opponent's reply.
- **Show threats** — lights up every one of your pieces that is under
  attack in red. Great for learning to stop hanging pieces.
- **New game** — resets the board.
- **Opponent strength** — four tiers from "Just learning" to "Strong".

The bar on the left shows who is ahead: more white = you're winning.

## Visual vocabulary (consistent everywhere)

| Color | Meaning |
|-------|---------|
| Blue squares | The last move played |
| Amber square | Your selected piece |
| Green dots / arrow | Where you can go / suggested move |
| Red squares | Your pieces under attack |

## Files

- `main.py` — entry point, game loop, event handling
- `config.py` — the design system: spacing scale, palette, layout
- `ui.py` — all drawing (board, highlights, arrows, sidebar cards)
- `engine_ai.py` — Stockfish wrapper with a minimax fallback
- `coach.py` — plain-language event explanations (Phase 2 upgrades this
  to a conversational LLM tutor grounded in engine analysis)

## The chat coach

Type any question in the box (or tap a quick chip like "Why?" or "Any
threats?"). The coach answers in 2-4 friendly sentences, grounded in the
engine's real analysis of the current position. If you make a serious
mistake, the coach offers to take the move back so you can try a better
idea — mistakes become lessons instead of losses.

## Game review

Press "Review game" any time (works best after a finished game). The app
re-analyzes every move, then opens the review screen:

- an estimated accuracy score for your play
- an evaluation graph telling the story of the game — click anywhere on
  it to jump to that moment
- every one of your moves labeled: Great / Good / Inaccuracy / Mistake /
  Blunder, with a plain-language note explaining what happened and what
  the engine preferred
- "Next mistake" jumps straight to your learning moments; mistake moves
  are tinted red on the board
- navigate with the buttons, arrow keys, Home/End; Esc returns to play

## Files

- `tutor_llm.py` — the conversational coach: grounding package builder,
  threaded Claude API calls, offline rule-based fallback
- `analysis.py` — the game reviewer: move classification, accuracy,
  turning points, per-move explanations

## More puzzles: the Lichess database (optional)

Want thousands of real tactics? Run:

    pip install zstandard
    python import_lichess.py          # imports 300 beginner puzzles
    python import_lichess.py 1000     # or more

It downloads the free Lichess puzzle database once, keeps
beginner-rated one-move tactics, and mixes them into your Practice
schedule with friendly theme notes.

## Stats & adaptive coaching

The Stats tab shows your journey: an accuracy trend across reviewed
games, average and best accuracy, mistake counts, puzzle first-try
rate, and lesson progress.

The app also adapts to you. Your coaching level (1-3) is computed from
recent accuracy and puzzle success:

- Level 1 — everything explained, jargon always defined
- Level 2 — the Hint button turns Socratic: first press gives a guiding
  question, second press reveals the answer
- Level 3 — the coach goes quiet on routine moves and only speaks when
  something important happens (captures, threats, mistakes, checks)

The chat coach also receives your level, so its answers grow with you.

## Practice (spaced repetition)

The Practice tab is a puzzle trainer with a twist: alongside the built-in
starter tactics (forks, skewers, back-rank mates, free pieces), every
mistake found in your game reviews automatically becomes a personal
puzzle — you re-face the exact position you got wrong and find the move
you missed.

Scheduling uses spaced repetition: solve a puzzle on the first try and
it returns in 3, then 7, 14, and 30 days; miss it and it comes back
tomorrow. Your progress lives in progress.db next to the app.

## Lessons

The Lessons tab is a step-by-step curriculum: don't give pieces away,
forks, basic checkmates, skewers and open lines, and opening principles.
Each lesson explains one idea in plain language, then has you play the
key move yourself on the board. Completed exercises are remembered.

## Files (new in this phase)

- `storage.py` — SQLite persistence: puzzles, spaced-repetition
  scheduling, lesson progress
- `content.py` — starter puzzles and the lesson curriculum (every
  position verified against the engine)
- `import_lichess.py` — optional importer for the Lichess puzzle
  database
