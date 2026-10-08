# aw-fft-demo4

A dependency-free, spoiler-light newcomer introduction to the original PlayStation *Final Fantasy Tactics*, based on the North American localization and mechanics.

## What's on the page

- **Battles** — CT accumulation driven by Speed, units acting at CT 100, separately charged actions, Move/Jump, elevation, facing, and positioning.
- **Jobs** — Squire and Chemist as foundational jobs without prerequisites, advanced job unlocks via prerequisite job levels, JP purchasing learned abilities.
- **Ivalice** — The kingdom where the story unfolds.
- **Characters** — Profiles of Ramza Beoulve and Delita Hyral (identified as a commoner), spoiler-light descriptions.

## Maintained files

Only four files are part of this feature:

| File | Role |
|------|------|
| `index.html` | Semantic static guide with skip link, landmarks, and anchored sections. |
| `styles.css` | Responsive parchment-toned stylesheet using system serif typography. |
| `tests/test_site.py` | Ancestry-aware standard-library unittest suite. |
| `README.md` | This documentation file. |

## Validation

Run the immutable validation command from the project root:

```
python -m unittest discover -s tests -v
```

The test suite uses only Python's standard library (`unittest`, `html.parser`). No server, subprocess, network access, or external dependencies are required. Tests verify semantic landmarks, accessible skip link, section structure, character profiles, unique IDs, resolving fragments, exactly one local stylesheet reference, absence of active resources, section-scoped factual claims, and prohibited mechanics.

## Usage

Open `index.html` directly in any browser as static HTML. No build steps, installation, or runtime setup are needed.

## Out of scope

This page excludes licenses, weapon triangles, selectable difficulty tiers, later-release systems, other-game mechanics, images, embeds, JavaScript, remote resources, and build infrastructure.
