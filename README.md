# Madi

The one browsing instrument. Three rungs, one shaped result:

1. **Fetch** (stdlib) — GET with full browser headers.
2. **Taxonomy** — every response classified `ok` / `blocked` (wall named:
   cloudflare, captcha, imperva, bot-wall) / `error`. Walls are never
   merged with empty results. Transient failures retry with backoff.
3. **Render** (optional Playwright) — headless Chromium executes the
   page's JavaScript; sessions persist logins; fill/click drives portal
   forms; screenshots keep evidence.

Plus two stdlib-native instruments over extracted text:

- **RelevanceScorer** — seeded lego-block scorer, deterministic from the
  seed alone, strictly rising with query overlap.
- **screen_text** — adversarial screen: instruction smuggles, section
  spoofs, path escapes, unicode tricks, oversized blobs. A probe that
  fires is a finding, never a silent drop.

```python
from madi import fetch, HyperEdgeBrowser

page = fetch("https://example-grants-portal/rfps")
if page["state"] == "ok":
    print(page["title"], len(page["links"]), "links")

with HyperEdgeBrowser(state_dir="~/.madi/browser",
                       evidence_dir="evidence/") as b:
    b.goto("https://portal.example/login")   # log in once, by hand
    b.save_state()                            # next run inherits it
```

Install the core (no dependencies): `pip install madi`.
Add the render rung: `pip install madi[browser] && playwright install chromium`.

Tests: `python -m pytest tests/ -q` — fully offline except the live
render test, gated behind `MADI_LIVE_BROWSER=1`.
