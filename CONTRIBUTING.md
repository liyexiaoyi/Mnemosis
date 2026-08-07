# Contributing to Mnemosis

Thanks for wanting to help! This project is a collaboration between humans
and AI agents, so contributions from both are welcome.

## Project philosophy

Mnemosis models AI memory on how human memory actually works: memories decay,
access reinforces them, sleep consolidates them, source and confidence matter,
and forgetting is a feature, not a bug.

## Getting started

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## How to contribute

1. Open an issue first for non-trivial changes so we can agree on the design.
2. Keep the core dependency-free: only `stdlib` for `mnemosis` itself.
3. Add tests for every new behavior in `tests/`.
4. Update `docs/memory-model.md` when a mechanism changes — every feature must
   trace back to a human memory principle.

## Commit style

- Imperative mood, short subject line.
- Reference the principle your change implements, e.g.
  `consolidation: promote repeated episodic memories during sleep`.

