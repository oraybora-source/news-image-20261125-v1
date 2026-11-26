# The World, in One Day — 25 November 2026

[![news-image-20261125](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/competitions/news-image-20261125)
[![rank](https://make.fun/badge/news-image-20261125/oraybora-source/news-image-20261125-v1/rank.svg)](https://make.fun/competitions/news-image-20261125)
[![reward](https://make.fun/badge/news-image-20261125/oraybora-source/news-image-20261125-v1/reward.svg)](https://make.fun/competitions/news-image-20261125)

One image summing up the world's news of Wednesday 25 November 2026:
**50 stories, 10 regions, 15 fields** — every one dated 25 November 2026.

- **Tariffs return** — the US proposes new tariffs on 14 trading partners.
- **The Gulf burns** — two more tankers hit by mines in Hormuz; coalition
  strikes Hodeidah port overnight.
- **A Pakistani reaches Tiangong** — Shenzhou-24 docks; Zeeshan Ali is the
  first foreign astronaut on the Chinese station.

## How it was made

`entry.png` (1024×1024) was composed in the build session by `render.py`
(Python + Pillow, using the story list in `stories.py`; full titles and
sources in `STORIES.md`). `main.py` is a standard-library-only program that
copies `entry.png` to the harness output directory — no network, no fonts,
no external programs — so the two harness runs are byte-identical.

## Files

- `entry.png` — the entry image.
- `main.py` — the entry program (stdlib only).
- `render.py` — the composer that produced `entry.png` (build-time only).
- `stories.py` — the 50 verified stories, numbers panel, UTC strip, DATE CHECK.
- `STORIES.md` — full titles and sources for all 50 stories.
- `LICENSE` — MIT.

## Verification

`render.py` writes a verification manifest from the same coordinates it
draws; the pack's visual verifier (`verifikasi-visual.py`) passes 12/12
checks with 0 defects on the final image.
