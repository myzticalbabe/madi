# madi

MADI — the one browsing instrument: fetch, challenge taxonomy, readability, discovery, native scorer, native screen.

[![CI](https://github.com/myzticalbabe/madi/actions/workflows/ci.yml/badge.svg)](https://github.com/myzticalbabe/madi/actions/workflows/ci.yml)
[![Pages Deploy](https://github.com/myzticalbabe/madi/actions/workflows/pages-deploy.yml/badge.svg)](https://github.com/myzticalbabe/madi/actions/workflows/pages-deploy.yml)
[![License: SOUL FORGE](https://img.shields.io/badge/License-SOUL_FORGE-violet.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/myzticalbabe/madi)](https://github.com/myzticalbabe/madi/releases)
[![GitHub stars](https://img.shields.io/github/stars/myzticalbabe/madi?style=social)](https://github.com/myzticalbabe/madi/stargazers)

---

## Overview

`madi` is a browsing instrument for grant and RFP discovery: one place that
fetches a page, says what kind of page came back, and turns the text into
something you can rank and trust.

It has three layers, and you can stop at any of them:

- **Fetch and classify.** `fetch()` makes a plain GET with a full browser header
  set. Every response is classified as `ok`, `blocked` or `error` — and when it
  is blocked, the challenge is named (`cloudflare-iuam`, `captcha-wall`,
  `imperva`, `bot-wall`). A wall is a finding about the environment, never an
  empty result, and the two are never merged.
- **Extract, score and screen.** `main_text()` strips the page chrome and keeps
  the content. `discover_html()` maps the links and forms. `RelevanceScorer`
  scores a page against a query, deterministically, from a seed. `screen_text()`
  screens the extracted text for adversarial content — instruction smuggles,
  section spoofs, path escapes and unicode tricks.
- **Render and interact.** `HyperEdgeBrowser` drives headless Chromium through
  Playwright for pages that need JavaScript, persists login state between runs,
  fills and clicks portal forms, and captures screenshots as evidence.

The core is standard-library-only and has no runtime dependencies. Playwright is
an optional extra, imported lazily: importing `madi` never requires it, and every
render path raises a `RuntimeError` naming exactly what to install.

## Who it is for

- **Researchers and grant writers** who need to reach RFP listings and eligibility
  pages behind client-side portals, and need to tell a blocked page from an empty
  one.
- **Tool builders** who need a fetching primitive that reports its own failures
  honestly — `state`, `challenge`, `detail` and `attempts` are always present.
- **Anyone handling pages as untrusted input.** `screen_text()` exists because the
  text of a fetched page is hostile by default, and it is designed to be used on
  the output of `main_text()` before that text reaches a model, a user, or a
  spreadsheet.

It is part of the [Azazael](https://github.com/myzticalbabe) ecosystem of
education and research tooling.

## Installation

Requires **Python 3.13 or newer**.

```bash
pip install -e .
```

Optional extras:

```bash
pip install -e ".[test]"     # pytest, for the test suite
pip install -e ".[browser]"  # Playwright, for the render and interact rung
playwright install chromium
```

## Usage

`madi` is a library — import the pieces you need.

```python
from madi import fetch, screen_text

page = fetch("https://example.com")
print(page["state"])                       # "ok", "blocked" or "error"
print(page["title"])
print(page["text"][:200])                  # content, page chrome stripped
print(screen_text(page["text"])["state"])  # "clean" or "suspect"
```

`fetch()` does not raise on a transport failure: a failure comes back as
`{"state": "error", "detail": ...}`. A detected wall comes back as
`{"state": "blocked", "challenge": "cloudflare-iuam"}`, so a challenge is
never confused with an empty page.

For pages that need JavaScript, use `HyperEdgeBrowser` (needs the `browser`
extra):

```python
from madi import HyperEdgeBrowser

with HyperEdgeBrowser(evidence_dir="evidence/") as b:
    page = b.goto("https://example.com")
    print(page["state"], page["title"])
```

The module docstring in `src/madi/browser.py` documents the full API.

## Running the tests

```bash
python -m pytest tests/ -v --tb=short
```

The suite is offline-safe: it starts a local HTTP server on `127.0.0.1` and never
touches the internet. One test is skipped unless you ask for it:

```bash
MADI_LIVE_BROWSER=1 python -m pytest tests/ -v --tb=short
```

That one drives a real Chromium against `example.com`, so it needs the `browser`
extra installed and network access.

[CONTRIBUTING.md](CONTRIBUTING.md) has the full setup instructions.

## Architecture

See [Domain Atlas](https://myzticalbabe.github.io) for interactive visualization.

## License

This project is licensed under the **SOUL FORGE License v1.0** — see [LICENSE](LICENSE) for details.

> *"Code is crystallized intention. Tend the fire."*

## Related Repositories

| Repo | Description |
|------|-------------|
| [azazael](https://github.com/myzticalbabe/azazael) | Monorepo: worm registry, cluster system, agent harness |
| [EveUnleashed](https://github.com/myzticalbabe/EveUnleashed) | Gamora, Lucy, Jaeger, Berzerker AIO native on 3.16t |
| [eliza](https://github.com/myzticalbabe/eliza) | Companion runtime: shards, adopted trees |
| [codex-video-engine](https://github.com/myzticalbabe/codex-video-engine) | CODEX Studio desktop app + video engine |
| [ecosystem-orchestrator](https://github.com/myzticalbabe/ecosystem-orchestrator) | ML platform install/orchestration |
| [scribe](https://github.com/myzticalbabe/scribe) | Documentation generation |
| [persephone-sync](https://github.com/myzticalbabe/persephone-sync) | Cross-platform env sync |
| [hydra-mlcluster](https://github.com/myzticalbabe/hydra-mlcluster) | Adaptive ML cluster processing |
| [flaming-sword](https://github.com/myzticalbabe/flaming-sword) | Defensive instrument: sentinel, compliance, formal verification |
| [shardex](https://github.com/myzticalbabe/shardex) | Shard execution engine |
| [krampus](https://github.com/myzticalbabe/krampus) | Composition: MellifluousML, Madi, Gamora, Eve, Lilith |
| [azazael-core](https://github.com/myzticalbabe/azazael-core) | Installable, interpreter-agnostic repackaging |
| [grantforge](https://github.com/myzticalbabe/grantforge) | AI-native grant tooling |
| [madi](https://github.com/myzticalbabe/madi) | Browsing instrument: fetch, challenge taxonomy, scorer |
| [jaeger](https://github.com/myzticalbabe/jaeger) | Durable spans, JSONL ledger, stdlib only |
| [cradle](https://github.com/myzticalbabe/cradle) | Composition over FLAMING SWORD, REAPER, GRIMOIRE |
| [esquire-admissibility](https://github.com/myzticalbabe/esquire-admissibility) | AI-evidence admissibility gates |
| [nurse-ratchet](https://github.com/myzticalbabe/nurse-ratchet) | Behavioural package: person state modelled |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Links

- **Monorepo**: https://github.com/myzticalbabe/azazael
- **Landing Hub**: https://myzticalbabe.github.io
- **Domain Atlas**: https://myzticalbabe.github.io/index.html
- **Issues**: https://github.com/myzticalbabe/madi/issues